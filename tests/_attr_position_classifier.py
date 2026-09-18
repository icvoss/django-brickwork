"""Derived attribute-position interpolation classifier (ADR-097 / #390).

Re-derives every ``attr="{{ ... }}"`` site under
``src/brickwork/templates/brickwork/`` at test time. Sites already emitted
through ``{% bw_attr %}`` / ``{% bw_data_attrs %}`` never appear here: those
tags emit the whole attribute, so there is no consumer ``{{ }}`` left in
attribute position for that value.

Closed-vocabulary author-literal class modifiers written as
``{% if size == "sm" %} ...--sm{% elif ... %}`` likewise never appear: they
carry no ``{{ }}``. Partial-value class tokens
(``class="bw-x bw-x--{{ variant }}"``) and other composed attribute values
do appear, and are classified as ``composed``.

The ``{% extends %}`` group (``_tooltip``, ``_modal``, ``_slide_over``) is
classified ``extends_unreachable`` per ADR-097 section 6: open values arrive
as block content with no Python path for the seam.

Everything else is ``known_exempt`` residue that still uses a raw
attribute-position interpolation. The gate pins that set to a checked-in
inventory so it cannot grow silently, and so a migration that removes a
site must shrink the inventory in the same change.

This module is the shared extraction ADR-097's Affects list names. The gate
that consumes it lives in ``tests/test_attr_position_classifier.py``.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = _REPO_ROOT / "src" / "brickwork" / "templates" / "brickwork"

# ADR-097 section 6: open values arrive as block content; the seam cannot
# reach them. Attribute-position interpolations in these templates are
# still residual, but they are not "forgot to call bw_attr" sites.
EXTENDS_GROUP = frozenset(
    {
        "components/_tooltip.html",
        "components/_modal.html",
        "components/_slide_over.html",
    }
)

Category = str  # composed | extends_unreachable | known_exempt

_COMMENT_BLOCK = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.S)
_HASH_COMMENT = re.compile(r"\{#.*?#\}", re.S)
# One HTML attribute whose quoted value contains at least one {{ ... }}.
_ATTR_INTERP = re.compile(
    r"""(?P<attr>[A-Za-z_:][\w:.-]*)\s*=\s*(?P<q>["'])(?P<val>(?:(?!\2).)*?\{\{(?:(?!\2).)*?)\2""",
    re.S,
)
_VAR = re.compile(r"\{\{\s*(.*?)\s*\}\}", re.S)
_TAG = re.compile(r"\{%.*?%\}", re.S)
# Partial class token: a BEM-style modifier that ends immediately in {{.
_COMPOSED_CLASS_TOKEN = re.compile(r"[\w-]+--\{\{")


@dataclass(frozen=True)
class AttrInterpHit:
    """One attribute-position ``{{ }}`` site in a package template."""

    path: str
    attr: str
    value: str
    line: int

    @property
    def key(self) -> str:
        """Stable identity: path, attribute name, ordered expression texts.

        Line numbers are deliberately absent: comment edits must not churn
        the inventory. Multiplicity of identical keys is carried by
        ``Counter``, not by a line suffix.
        """
        exprs = tuple(part.strip() for part in _VAR.findall(self.value))
        return f"{self.path}|{self.attr}|{'|'.join(exprs)}"


def strip_template_comments(source: str) -> str:
    """Drop ``{% comment %}`` blocks and ``{# #}`` notes so docstring
    examples never count as live render sites (ADR-097 Context section 1
    recorded that miscount twice)."""
    without_blocks = _COMMENT_BLOCK.sub("", source)
    return _HASH_COMMENT.sub("", without_blocks)


def is_composed_attribute_value(value: str) -> bool:
    """True when the quoted attribute value mixes author literals with
    interpolations (or template tags), i.e. is not a whole-value
    ``{{ var }}`` alone."""
    stripped = _TAG.sub("", _VAR.sub("", value))
    return bool(stripped.strip())


def classify_hit(path: str, attr: str, value: str) -> Category:
    """Assign one ADR-097 residue category to a raw attribute interpolation.

    ``seam_covered`` is not returned: those sites do not produce hits.
    ``closed_vocab_author_literal`` is likewise absence-based (no ``{{ }}``).
    """
    if path in EXTENDS_GROUP:
        return "extends_unreachable"
    if attr == "class" and (_COMPOSED_CLASS_TOKEN.search(value) or is_composed_attribute_value(value)):
        return "composed"
    if is_composed_attribute_value(value):
        return "composed"
    return "known_exempt"


def iter_template_paths(root: Path = TEMPLATES_ROOT) -> list[Path]:
    return sorted(root.rglob("*.html"))


def find_attr_interpolations(
    *,
    root: Path = TEMPLATES_ROOT,
    sources: Iterable[tuple[str, str]] | None = None,
) -> list[AttrInterpHit]:
    """Find every attribute-position ``{{ }}`` under ``root``.

    ``sources`` (optional ``(relative_path, source_text)`` pairs) replaces
    the filesystem walk so teeth-checks can inject fixtures without writing
    package templates.
    """
    hits: list[AttrInterpHit] = []
    if sources is None:
        pairs: list[tuple[str, str]] = []
        for path in iter_template_paths(root):
            rel = str(path.relative_to(root)).replace("\\", "/")
            pairs.append((rel, path.read_text(encoding="utf-8")))
    else:
        pairs = list(sources)

    for rel, raw in pairs:
        text = strip_template_comments(raw)
        for match in _ATTR_INTERP.finditer(text):
            start = match.start()
            line = text.count("\n", 0, start) + 1
            hits.append(
                AttrInterpHit(
                    path=rel,
                    attr=match.group("attr"),
                    value=match.group("val"),
                    line=line,
                )
            )
    return hits


def classify_inventory(
    hits: Iterable[AttrInterpHit] | None = None,
    *,
    root: Path = TEMPLATES_ROOT,
) -> dict[Category, Counter[str]]:
    """Classify every hit and return per-category key counters."""
    if hits is None:
        hits = find_attr_interpolations(root=root)
    out: dict[Category, Counter[str]] = {
        "composed": Counter(),
        "extends_unreachable": Counter(),
        "known_exempt": Counter(),
    }
    for hit in hits:
        category = classify_hit(hit.path, hit.attr, hit.value)
        out[category][hit.key] += 1
    return out
