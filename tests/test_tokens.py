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


_FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"

# CSS comments can sit anywhere inside a conditional-rule prelude (including
# between a feature name and its value), so they are stripped before any of
# the patterns below run; otherwise a comment breaks the adjacency a naive
# regex relies on and a literal slips through undetected.
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)

# The three CSS at-rule forms whose prelude can carry a media condition, each
# matched up to its terminator (the rule's opening brace for @media, the
# statement's semicolon for @import and @custom-media, which have no block).
_MEDIA_RULE_PRELUDE = re.compile(r"@media[^{;]*(?=\{)", re.S)
_IMPORT_STATEMENT = re.compile(r"@import[^;]*;", re.S)
_CUSTOM_MEDIA_STATEMENT = re.compile(r"@custom-media[^;]*;", re.S)

# The blanket rule (PR #227 review, comment 5412033886): a px/rem length
# literal anywhere inside one of the preludes above, case-insensitive unit.
_LENGTH_LITERAL = re.compile(r"\b\d+(?:\.\d+)?(?:px|rem)\b", re.I)


def _hardcoded_media_conditions(css: str) -> list[str]:
    """Every @media/@import/@custom-media prelude in ``css`` carrying a
    px/rem length literal anywhere inside it, comments stripped first.

    Scope and threat model (per the PR #227 review ruling): this is a
    regression pin against CSS a contributor might plausibly write, not an
    adversarial boundary. It scans frontend/src/**/*.css for the three
    at-rule forms whose prelude can hold a media condition and flags any
    length literal found there, in any position, in any comparator
    direction, inside calc(), across a line break, or written with an
    upper-case unit. It does NOT attempt to defeat deliberate obfuscation
    (escaped CSS identifiers, string-encoded values reassembled at build
    time): that is review's job, not the regex's. No shipped prelude
    legitimately carries a length literal: viewport features resolve
    through --theme(--breakpoint-*), and the non-viewport features this
    codebase actually uses (prefers-reduced-motion, print, orientation)
    carry no length at all.
    """
    stripped = _CSS_COMMENT.sub(" ", css)
    offenders = []
    for pattern in (_MEDIA_RULE_PRELUDE, _IMPORT_STATEMENT, _CUSTOM_MEDIA_STATEMENT):
        for match in pattern.finditer(stripped):
            prelude = match.group(0)
            if _LENGTH_LITERAL.search(prelude):
                offenders.append(prelude)
    return offenders


def test_frontend_source_has_no_hardcoded_length_in_a_media_condition() -> None:
    # W0.1: every viewport breakpoint in frontend/src/ must route through the
    # generated --theme(--breakpoint-*) tokens (breakpoint.tokens.json), never
    # a literal length repeated at each call site. A literal reintroduces the
    # drift the token source was built to close: one breakpoint value living
    # in N places instead of one place N call sites reference.
    #
    # See _hardcoded_media_conditions for the guard's scope and threat model.
    offenders: list[str] = []
    for css_path in sorted(_FRONTEND_SRC.rglob("*.css")):
        text = css_path.read_text()
        for prelude in _hardcoded_media_conditions(text):
            offenders.append(f"{css_path.relative_to(_FRONTEND_SRC)}: {prelude}")
    assert not offenders, f"hardcoded length in a media condition; use --theme(--breakpoint-*) instead: {offenders}"


def test_dist_brickwork_css_has_no_var_inside_a_media_condition() -> None:
    # The failure mode this whole slice exists to prevent: a var(--bw-*)
    # reference inside an @media condition. A media condition cannot resolve
    # a CSS custom property (browsers evaluate media queries before the
    # cascade that would supply var()'s value), so any var() there is dead on
    # arrival at parse time, silently matching nothing rather than raising.
    # The generated breakpoint values are deliberately emitted as literals
    # (not var()) into the @theme block for exactly this reason; this
    # asserts the compiled artefact still reflects that, catching a
    # regression in generation even if the source-level guard above is
    # somehow satisfied. Case-insensitive: VAR(--bw-breakpoint-md) is valid
    # CSS and must be caught the same as var(...).
    css = (_DIST / "brickwork.css").read_text()
    offenders = [
        match.group(0)
        for match in _MEDIA_RULE_PRELUDE.finditer(_CSS_COMMENT.sub(" ", css))
        if re.search(r"var\(", match.group(0), re.I)
    ]
    assert not offenders, f"var() found inside an @media condition in dist/brickwork.css: {offenders}"


# --- #288: every shipped --bw-text-*-family token must be consumed --------

# The DEFINED set comes from token-manifest.json's "overridable" array, not a
# regex over tokens.css's :root block. The manifest is itself a generated,
# already-flattened artefact (one name per shipped token), so reading it
# avoids re-deriving :root-extraction logic that a second `:root { ... }`
# block in tokens.css (the 0.10.0 courtesy-alias block) could quietly break.
_TEXT_FAMILY_TOKEN = re.compile(r"--bw-text-[a-z0-9]+(?:-[a-z0-9]+)*-family")

# The `code` role deliberately bypasses the role layer: .bw-prose code/pre
# read --bw-font-family-mono directly (DESIGN.md 7.4), not this token, so
# --bw-text-code-family is a genuine token-nothing-reads exemption, not a
# bug. Wiring it means changing what a live rendering path (every
# consumer's prose) resolves through, which is out of scope for the #288
# false-affordance fix and is tracked as its own issue. This is a named,
# single-token exemption, never a pattern: a second token added here
# without the same justification is a regression, not a fix, and the
# quantifier assertion below still fails for it.
_TEXT_FAMILY_EXEMPT = frozenset({"--bw-text-code-family"})


def _defined_text_family_tokens() -> set[str]:
    manifest = json.loads((_DIST / "token-manifest.json").read_text())
    return {name for name in manifest["overridable"] if _TEXT_FAMILY_TOKEN.fullmatch(name)}


def _consumed_text_family_tokens(css: str) -> set[str]:
    """Token names actually read by a font-family declaration in ``css``.

    This is deliberately NOT a bare ``var(--bw-text-*-family)`` substring
    search. tokens.css (and the compiled brickwork.css, which inlines the
    same :root block) contains lines shaped like
    ``--bw-text-heading-display-family: var(--bw-font-family-display);``:
    that is the token's DEFINITION, and its value never happens to be
    ``var(--bw-text-*-family)`` for the same token, so a naive scan of
    tokens.css would not vacuously self-match there. But dist/tokens.js
    DOES print the courtesy shape ``"text_x_family": "var(--bw-text-x-family)"``
    for every token (a JS reference helper, not a CSS rule), so scanning
    that file, or any similar reference table, would rubber-stamp every
    token as consumed regardless of whether any component reads it. The
    matcher below only counts a token as consumed when it appears as the
    VALUE of a ``font-family`` DECLARATION (``font-family: var(--bw-text-
    ...-family)``), which is the only shape an actual consuming rule can
    take; a token's own definition line has the token as the property being
    set, never as a font-family value, so the two are structurally
    distinguishable by property name, not by which file happens to hold
    them.
    """
    consumed: set[str] = set()
    for match in re.finditer(r"font-family\s*:\s*var\(\s*(--bw-text-[a-z0-9-]+-family)\s*\)", css):
        consumed.add(match.group(1))
    return consumed


def test_text_family_exemption_list_is_not_stale() -> None:
    # The exemption above is only honest if the token it names still exists.
    # If the code role is later wired (or the token deleted outright), this
    # fails and forces the exemption to be removed in the same change,
    # rather than it sitting there silently exempting nothing forever.
    defined = _defined_text_family_tokens()
    stale = sorted(_TEXT_FAMILY_EXEMPT - defined)
    assert not stale, (
        f"--bw-text-*-family exemption names a token no longer in the manifest "
        f"(remove it from _TEXT_FAMILY_EXEMPT): {stale}"
    )


def test_every_text_family_token_is_consumed_by_a_font_family_rule() -> None:
    # #288: 7 of 13 shipped --bw-text-*-family tokens were read by nothing,
    # so setting them had no effect (a false affordance). This is the
    # checkable form of that rule: derive the shipped set from the manifest
    # (never a hardcoded list, or a newly added dead token is invisible),
    # and derive the consumed set from BOTH the authored source
    # (frontend/src/*.css, what a contributor actually writes) and the
    # compiled bundle (dist/brickwork.css, what a consumer actually loads),
    # so a build-pipeline drop between the two is caught either way.
    #
    # --bw-text-code-family is excluded via the named _TEXT_FAMILY_EXEMPT
    # set above (the `code` role bypasses the role layer by design pending
    # its own issue); every other token must still be consumed, and adding
    # a second token to that exemption without matching justification does
    # not shrink what this assertion checks.
    defined = _defined_text_family_tokens() - _TEXT_FAMILY_EXEMPT
    assert defined, "expected at least one --bw-text-*-family token in the manifest"
    assert len(defined) > 1, (
        "the defined set has only one member; an 'every token has a consumer' "
        "assertion cannot be exercised meaningfully against a singleton (see #286)"
    )

    frontend_css = "\n".join(path.read_text() for path in sorted(_FRONTEND_SRC.glob("*.css")))
    consumed_in_source = _consumed_text_family_tokens(frontend_css)
    consumed_in_dist = _consumed_text_family_tokens((_DIST / "brickwork.css").read_text())

    dead_in_source = sorted(defined - consumed_in_source)
    dead_in_dist = sorted(defined - consumed_in_dist)

    assert not dead_in_source, (
        f"--bw-text-*-family tokens defined but consumed by no font-family rule in frontend/src/*.css: {dead_in_source}"
    )
    assert not dead_in_dist, (
        f"--bw-text-*-family tokens defined but consumed by no font-family rule "
        f"in dist/brickwork.css (build dropped a source rule): {dead_in_dist}"
    )
