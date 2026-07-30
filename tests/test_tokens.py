"""Token-layer contract tests (BR-BW-TOK-*), validating source + built artefacts.

These read the committed DTCG source and the committed compiled artefacts in
static/brickwork/dist/. They do NOT run Style Dictionary (node) at test time: the
built files are shipped artefacts (the package product), so the suite asserts on
what is actually shipped. A separate CI frontend-build job rebuilds and asserts
the artefacts are up to date with source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_PKG = Path(__file__).resolve().parent.parent / "src" / "brickwork"
_SOURCE = _PKG / "tokens" / "source"
_DIST = _PKG / "static" / "brickwork" / "dist"

_OKLCH = re.compile(r"^oklch\(")
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}")
_HSL = re.compile(r"hsl\(")


def _iter_values(node: object):
    """Yield every DTCG $value in a token tree."""
    if isinstance(node, dict):
        if "$value" in node:
            yield node["$value"]
        for key, child in node.items():
            if not key.startswith("$"):
                yield from _iter_values(child)


_ALIAS = re.compile(r"^\{[a-z0-9.-]+\}$")


def _primitive_colour_values() -> list[str]:
    """Raw colour literals from the primitive tier (where the oklch values live)."""
    data = json.loads((_SOURCE / "primitive.tokens.json").read_text())
    return list(_iter_values(data["primitive"]))


def _semantic_colour_values() -> list[str]:
    """Semantic colour values: each is either an oklch literal or a {primitive.*}
    alias resolving to the primitive tier (the two-tier DTCG design)."""
    values: list[str] = []
    for name in ("semantic.light", "semantic.dark"):
        data = json.loads((_SOURCE / f"{name}.tokens.json").read_text())
        values.extend(_iter_values(data["color"]))
    return values


# --- BR-BW-TOK-003: colour tokens authored in oklch, never hex/hsl -----------


def test_primitive_colour_literals_are_all_oklch() -> None:
    values = _primitive_colour_values()
    assert values, "expected colour tokens in the primitive tier"
    for v in values:
        assert _OKLCH.match(v), f"primitive colour {v!r} is not oklch (BR-BW-TOK-003)"


def test_semantic_colour_values_are_oklch_or_primitive_aliases() -> None:
    # Semantics reference the primitive tier via DTCG {primitive.*} aliases (the
    # intended two-tier design), or carry an oklch literal directly. Neither is
    # ever hex/hsl. This asserts no semantic value smuggles in a non-oklch literal.
    for v in _semantic_colour_values():
        assert _OKLCH.match(v) or _ALIAS.match(v), (
            f"semantic colour {v!r} is neither an oklch literal nor a {{primitive.*}} alias (BR-BW-TOK-003)"
        )


def test_no_hex_or_hsl_in_any_colour_source() -> None:
    for v in _primitive_colour_values() + _semantic_colour_values():
        assert not _HEX.search(v), f"hex colour {v!r} found (BR-BW-TOK-003)"
        assert not _HSL.search(v), f"hsl colour {v!r} found (BR-BW-TOK-003)"


# --- BR-BW-TOK-002: every semantic colour has an AUTHORED dark value ---------


def test_light_and_dark_define_the_same_semantic_names() -> None:
    light = json.loads((_SOURCE / "semantic.light.tokens.json").read_text())["color"]
    dark = json.loads((_SOURCE / "semantic.dark.tokens.json").read_text())["color"]
    light_names = {k for k in light if not k.startswith("$")}
    dark_names = {k for k in dark if not k.startswith("$")}
    assert light_names == dark_names, (
        f"light and dark must define the SAME semantic colour names (BR-BW-TOK-002); differ: {light_names ^ dark_names}"
    )


def test_dark_values_are_actually_different_from_light() -> None:
    # "Authored, not derived" is a source discipline, but a trivial proxy is that
    # the surface/fg roles genuinely differ between the two files (a copy-paste of
    # light into dark would be caught here).
    light = json.loads((_SOURCE / "semantic.light.tokens.json").read_text())["color"]
    dark = json.loads((_SOURCE / "semantic.dark.tokens.json").read_text())["color"]
    for role in ("surface", "fg", "border"):
        assert light[role]["$value"] != dark[role]["$value"], (
            f"dark {role} equals light {role}; dark must be authored (BR-BW-TOK-002)"
        )


# --- Built artefacts: stable filenames, expected shape ------------------------


@pytest.mark.parametrize("filename", ["tokens.css", "tailwind-theme.css", "tokens.js"])
def test_stable_named_artefact_exists(filename: str) -> None:
    path = _DIST / filename
    assert path.is_file(), f"missing built artefact {filename} (run npm run build:tokens)"
    assert path.stat().st_size > 0, f"{filename} is empty"


def test_tokens_css_has_the_theme_and_density_selectors() -> None:
    css = (_DIST / "tokens.css").read_text()
    for selector in (
        ":root",
        '[data-theme="light"]',
        '[data-theme="dark"]',
        '[data-density="compact"]',
        '[data-density="comfortable"]',
        '[data-density="spacious"]',
    ):
        assert selector in css, f"tokens.css is missing the {selector} block"


def test_tokens_css_uses_namespaced_bw_names_in_oklch() -> None:
    css = (_DIST / "tokens.css").read_text()
    assert "--bw-color-surface:" in css
    assert "--bw-icon-size-md:" in css
    # colour values remain oklch in the compiled output (not down-converted)
    assert "oklch(" in css
    assert "#" not in css.split(":root")[1].split("}")[0], "hex leaked into :root colours"


def test_dark_block_overrides_surface_to_a_dark_value() -> None:
    css = (_DIST / "tokens.css").read_text()
    dark_block = css.split('[data-theme="dark"]')[1].split("}")[0]
    # the dark block must set surface, and only colour tokens (no size/density)
    assert "--bw-color-surface:" in dark_block
    assert "--bw-size-" not in dark_block
    assert "--bw-density-" not in dark_block


def test_tailwind_bridge_is_theme_inline() -> None:
    tw = (_DIST / "tailwind-theme.css").read_text()
    assert "@theme inline" in tw
    assert "--bw-color-surface:" in tw
