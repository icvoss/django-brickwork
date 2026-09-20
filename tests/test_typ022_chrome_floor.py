"""TYP-022 chrome-floor gate (icvoss/django-brickwork#581).

Content / legibility floor is ``--bw-font-size-xs``. Chrome may use
``--bw-font-size-2xs`` / ``--bw-text-overline-size`` for overlines and
micro-labels only. Body, interactive labels, form help/error, and table
cell content must never resolve there (docs/DESIGN.md overline consumer
rule; wall TYP-022 as amended by #281).
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND = _ROOT / "frontend" / "src"
_TOKENS = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "tokens.css"

# Selectors that MAY set font-size to 2xs / overline-size. Chrome only.
_CHROME_2XS_SELECTORS = frozenset(
    {
        ".bw-stat__label",
        ".bw-stat-comparison__label",
        ".bw-nav__section-label",
        ".bw-hero__eyebrow",
        ".bw-section__overline",
        ".bw-listing-card__tag",
        ".bw-feature-card__badge",
        ".bw-feature-card__eyebrow",
        ".bw-feature-card__cta",
        ".bw-directory__number",
        ".bw-token-specimen__flag",
        ".bw-token-specimen__value",
        ".bw-token-specimen__pair-floor",
        ".bw-token-specimen__pair-measured",
    }
)

_2XS_FONT_SIZE_RE = re.compile(
    r"font-size:\s*var\(--bw-(?:font-size-2xs|text-overline-size)\)",
)
_RULE_START_RE = re.compile(r"([^{}]+)\{", re.MULTILINE)

# Role tokens that must stay at or above the content floor (xs), never 2xs.
_CONTENT_ROLE_SIZE_TOKENS = (
    "--bw-text-body-lg-size",
    "--bw-text-body-md-size",
    "--bw-text-body-sm-size",
    "--bw-text-label-size",
    "--bw-text-caption-size",
)

# Shipped component selectors for the four excluded categories. Each must
# declare a font-size that is not 2xs / overline-size.
_EXCLUDED_SELECTOR_FRAGMENTS = (
    # Interactive control labels
    (r"\.bw-btn\s*\{[^}]*font-size:\s*([^;]+);", "button label"),
    # Form help / error
    (r"\.bw-field__help\s*\{[^}]*font-size:\s*([^;]+);", "field help"),
    (r"\.bw-field__error\s*\{[^}]*font-size:\s*([^;]+);", "field error"),
    # Table cell content
    (r"\.bw-data-table__td\s*\{[^}]*font-size:\s*([^;]+);", "data-table cell"),
    # Body / prose (prose inherits body; its root measure rule must not be 2xs)
    (r"\.bw-prose\s*\{[^}]*font-size:\s*([^;]+);", "prose body"),
)


def _frontend_css_files() -> list[Path]:
    return sorted(_FRONTEND.glob("*.css"))


def _selectors_using_2xs(css: str) -> list[str]:
    """Every selector list whose rule body sets font-size to 2xs/overline."""
    found: list[str] = []
    for match in _2XS_FONT_SIZE_RE.finditer(css):
        before = css[: match.start()]
        starts = list(_RULE_START_RE.finditer(before))
        if not starts:
            continue
        selector = starts[-1].group(1).strip()
        # Drop comments that can sit between rules.
        selector = re.sub(r"/\*.*?\*/", "", selector, flags=re.S).strip()
        found.append(selector)
    return found


def test_every_2xs_font_size_site_is_named_chrome() -> None:
    offenders: list[str] = []
    for path in _frontend_css_files():
        css = path.read_text(encoding="utf-8")
        for selector_list in _selectors_using_2xs(css):
            parts = [p.strip() for p in selector_list.split(",")]
            for part in parts:
                # Allow multi-class / descendant only when the leaf matches.
                leaf = part.split()[-1] if part else part
                if leaf not in _CHROME_2XS_SELECTORS:
                    offenders.append(f"{path.name}: {part}")
    assert not offenders, "TYP-022: 2xs / overline-size used outside the chrome allowlist:\n" + "\n".join(offenders)


def test_content_type_roles_do_not_resolve_to_2xs() -> None:
    tokens = _TOKENS.read_text(encoding="utf-8")
    for name in _CONTENT_ROLE_SIZE_TOKENS:
        match = re.search(rf"{re.escape(name)}:\s*([^;]+);", tokens)
        assert match is not None, f"{name} missing from tokens.css"
        value = match.group(1).strip()
        assert "2xs" not in value, f"{name} resolves to 2xs ({value})"
        assert "overline" not in value, f"{name} resolves via overline ({value})"


def test_excluded_component_roles_do_not_use_2xs_font_size() -> None:
    components = (_FRONTEND / "components.css").read_text(encoding="utf-8")
    for pattern, label in _EXCLUDED_SELECTOR_FRAGMENTS:
        match = re.search(pattern, components, flags=re.S)
        assert match is not None, f"{label}: no font-size declaration found"
        value = match.group(1).strip()
        assert "2xs" not in value, f"{label} uses 2xs ({value})"
        assert "overline" not in value, f"{label} uses overline-size ({value})"
