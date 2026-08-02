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
    alias resolving to the primitive tier (the two-tier DTCG design). Includes the
    state overlays (colours with alpha); excludes elevation (shadow strings, not
    colour values). Only $value is scanned: the $extensions.bw.derived expressions
    are deliberately color-mix()/var() strings, not oklch literals (DESIGN.md
    section 3), and are verified separately in test_token_derivations.py."""
    values: list[str] = []
    for name in ("semantic.light", "semantic.dark"):
        data = json.loads((_SOURCE / f"{name}.tokens.json").read_text())
        values.extend(_iter_values(data["color"]))
        values.extend(_iter_values(data["state"]))
    return values


def _elevation_values() -> list[str]:
    """Elevation shadow strings, both themes. Not oklch literals themselves, but
    they carry embedded colours, so the hex/hsl ban still applies to them."""
    values: list[str] = []
    for name in ("semantic.light", "semantic.dark"):
        data = json.loads((_SOURCE / f"{name}.tokens.json").read_text())
        values.extend(_iter_values(data["elevation"]))
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
    # Elevation values are colour-bearing shadow strings, so they are scanned
    # here too, even though they are exempt from the oklch-literal shape check.
    for v in _primitive_colour_values() + _semantic_colour_values() + _elevation_values():
        assert not _HEX.search(v), f"hex colour {v!r} found (BR-BW-TOK-003)"
        assert not _HSL.search(v), f"hsl colour {v!r} found (BR-BW-TOK-003)"


# --- BR-BW-TOK-002: every semantic colour has an AUTHORED dark value ---------


@pytest.mark.parametrize("group", ["color", "state", "elevation"])
def test_light_and_dark_define_the_same_semantic_names(group: str) -> None:
    light = json.loads((_SOURCE / "semantic.light.tokens.json").read_text())[group]
    dark = json.loads((_SOURCE / "semantic.dark.tokens.json").read_text())[group]
    light_names = {k for k in light if not k.startswith("$")}
    dark_names = {k for k in dark if not k.startswith("$")}
    assert light_names == dark_names, (
        f"light and dark must define the SAME {group} token names (BR-BW-TOK-002); differ: {light_names ^ dark_names}"
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


@pytest.mark.parametrize("filename", ["tokens.css", "tailwind-theme.css"])
def test_no_static_reference_a_manifest_storage_would_fail_on(filename: str) -> None:
    # Django/WhiteNoise ManifestStaticFilesStorage rewrites @import/url() targets by
    # regex WITHOUT skipping comments, so a shipped CSS file must not contain any
    # `@import "..."` or `url(...)` (even in a comment) that points at a file this
    # package does not ship, or `collectstatic` fails for the consumer with a
    # MissingFileError. This regression guards the icvlocal.com finding (0.1.0):
    # a header comment example `@import "tailwindcss"` broke every consumer's
    # collectstatic. data: URIs and SVG fragment refs (url(#...)) are fine.
    css = (_DIST / filename).read_text()
    assert '@import "' not in css and "@import '" not in css, (
        f"{filename} contains an @import that ManifestStaticFilesStorage will try "
        f"to resolve (even in a comment) and fail collectstatic on."
    )
    bad_urls = re.findall(r"url\((?!['\"]?(?:#|data:))[^)]+\)", css)
    assert not bad_urls, f"{filename} has url() references a manifest storage would resolve: {bad_urls}"


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


def test_typography_tokens_are_shipped() -> None:
    # #7: a consumer must be able to rebrand typography token-first (the family
    # trio + a size/weight/line-height scale), the same way it rebrands colour.
    css = (_DIST / "tokens.css").read_text()
    for token in (
        "--bw-font-family-sans:",
        "--bw-font-family-display:",
        "--bw-font-family-mono:",
        "--bw-font-size-md:",
        "--bw-font-weight-bold:",
        "--bw-font-line-height-normal:",
    ):
        assert token in css, f"missing typography token {token}"


def test_shell_css_consumes_the_font_family_token() -> None:
    # overriding --bw-font-family-sans must actually rebrand the shell, so the
    # shipped component CSS has to reference the token, not a hardcoded stack.
    css = (_DIST / "brickwork.css").read_text()
    assert "var(--bw-font-family-sans)" in css
    assert "var(--bw-font-family-display)" in css


# 0.11.0 tier re-grammar: the nav/skeleton/breadcrumb roles re-tiered from
# --bw-color-* to --bw-component-* (rename-table.md), but stayed genuinely
# theme-variant (their derived values still differ light vs dark), so they
# legitimately appear in the dark block under their new component-tier names.
# This is the closed set of component-tier names allowed there; any OTHER
# --bw-component-* token (button-radius, icon-size, etc.) is not theme-variant
# and must not leak in.
_DARK_BLOCK_COMPONENT_ALLOWLIST = (
    "--bw-component-nav-item-active-bg",
    "--bw-component-nav-item-active-text",
    "--bw-component-nav-item-active-border",
    "--bw-component-nav-item-disabled-text",
    "--bw-component-nav-section-text",
    "--bw-component-breadcrumb-current",
    "--bw-component-breadcrumb-separator",
    "--bw-component-skeleton-bg",
    "--bw-component-skeleton-shimmer",
)


def test_dark_block_overrides_surface_to_a_dark_value() -> None:
    css = (_DIST / "tokens.css").read_text()
    dark_block = css.split('[data-theme="dark"]')[1].split("}")[0]
    # the dark block must set surface, and only theme-variant tokens: colour,
    # state overlays, elevation, and the closed set of re-tiered component
    # colour roles above (never the size/density scales or any other component
    # token)
    assert "--bw-color-surface:" in dark_block
    for line in dark_block.splitlines():
        line = line.strip()
        if not line.startswith("--bw-"):
            continue
        name = line.split(":", 1)[0]
        assert line.startswith(("--bw-color-", "--bw-state-", "--bw-elevation-")) or name in (
            _DARK_BLOCK_COMPONENT_ALLOWLIST
        ), f"non-theme token leaked into the dark block: {line}"


def test_info_and_accent_are_distinct_colours() -> None:
    # #13: accent (brand) and info (status/notice) are distinct semantic roles;
    # they must not resolve to the identical value, or a UI that uses both side by
    # side (or colour-codes by role) can't tell them apart. Regression for the
    # 0.2.0 collision where both mapped to the same blue primitive.
    css = (_DIST / "tokens.css").read_text()

    def _val(name: str) -> str:
        # the :root value for a token
        import re

        m = re.search(rf"--{name}:\s*([^;]+);", css)
        assert m, f"{name} not found in tokens.css"
        return m.group(1).strip()

    assert _val("bw-color-info") != _val("bw-color-accent"), "info must differ from accent"
    assert _val("bw-color-info-subtle") != _val("bw-color-accent-subtle"), "info-subtle must differ from accent-subtle"


def test_tailwind_bridge_is_theme_inline() -> None:
    # 0.10.0: the bridge is the REAL projection (Tailwind namespace keys ->
    # var(--bw-*) references), not the 0.9.0 self-referential identity block;
    # the full projection contract lives in test_tailwind_projection.py.
    tw = (_DIST / "tailwind-theme.css").read_text()
    assert "@theme inline" in tw
    assert "--color-surface: var(--bw-color-surface);" in tw
