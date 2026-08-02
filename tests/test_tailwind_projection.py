"""Tailwind 4 projection artefact tests (ADR-054 section 4; AC-BW-095, static half).

dist/tailwind-theme.css is the @theme inline projection of the SEMANTIC --bw-*
contract into Tailwind's utility namespaces, so consumer utilities (bg-accent,
rounded-md, shadow-3, text-body-lg, p-4) inherit the brand and both themes.
Every mapped value is a var(--bw-*) reference, never a literal, so theme and
brand switching restyles consumer utilities with no rebuild (the dynamic half
is proven in a11y/projection.spec.mjs over a real Tailwind consumer build).

Like the other dist artefact tests (test_tokens.py), these read the committed
compiled file, never run the node build. The coverage census is two-sided and
derived from dist/tokens.css itself: every semantic colour, radius step,
elevation level, type role (size + line-height companion), and font stack must
be projected, and NOTHING else may be (component-tier tokens, state overlays,
z-index, opacity, motion, and focus are deliberately not part of the
projection: it is the semantic visual contract only).
"""

from __future__ import annotations

import re
from pathlib import Path

_DIST = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist"

_DECL = re.compile(r"^\s*(--[A-Za-z0-9-]+):\s*([^;]+);\s*$")
_PURE_BW_VAR = re.compile(r"^var\(--bw-[a-z0-9-]+\)$")

# Families the projection must NOT touch (ADR-054 section 4: semantic visual
# contract only). Component-tier tokens are every remaining --bw-* family the
# census below does not project, so they are covered by the set-equality test;
# these named families get an explicit guard for a readable failure.
_UNPROJECTED_FAMILY_RE = re.compile(r"var\(--bw-(state|z|opacity|duration|ease|transition|focus|motion)-")


def _theme_block() -> str:
    css = (_DIST / "tailwind-theme.css").read_text()
    assert "@theme inline {" in css, "tailwind-theme.css is missing the @theme inline block"
    return css.split("@theme inline {", 1)[1].rsplit("}", 1)[0]


def _declarations() -> dict[str, str]:
    decls: dict[str, str] = {}
    for line in _theme_block().splitlines():
        if not line.strip():
            continue
        m = _DECL.match(line)
        assert m, f"unparseable @theme inline line: {line!r}"
        assert m.group(1) not in decls, f"duplicate @theme inline key {m.group(1)}"
        decls[m.group(1)] = m.group(2).strip()
    return decls


_ALIAS_BLOCK_MARKER = "courtesy aliases"


def _emitted_bw_names(*, include_aliases: bool = True) -> set[str]:
    """Every --bw-* custom property dist/tokens.css actually emits.

    By default includes the 0.10.0 -> 0.11.0 courtesy alias block (old names
    still resolve, so a reference to one is legitimately "emitted"). Pass
    ``include_aliases=False`` for census logic that must derive its expected
    set from canonical names only: the alias block re-declares re-tiered
    component roles (nav/skeleton/breadcrumb) under their OLD --bw-color-*
    names, which would otherwise wrongly imply those old names should still be
    part of the projected semantic-colour contract.
    """
    css = (_DIST / "tokens.css").read_text()
    if not include_aliases:
        css = css.split(_ALIAS_BLOCK_MARKER, 1)[0]
    names = set(re.findall(r"^\s*(--bw-[a-z0-9-]+):", css, re.M))
    assert names, "no custom properties found in dist/tokens.css"
    return names


# --- shape: a real projection, not the 0.9.0 identity placebo ----------------


def test_theme_inline_block_has_declarations() -> None:
    assert _declarations(), "@theme inline block is empty"


def test_every_value_is_a_pure_bw_var_reference() -> None:
    # AC-BW-095 (static half): never a literal, never a fallback, never a
    # calc/color-mix wrapper: theme and brand switching only works if every
    # utility resolves through the live token
    for key, value in _declarations().items():
        assert _PURE_BW_VAR.match(value), f"{key}: {value!r} is not a pure var(--bw-*) reference"


def test_no_self_referential_bw_identity_mappings_remain() -> None:
    # the 0.9.0 placebo was `--bw-x: var(--bw-x)` rows: --bw-* is not a
    # Tailwind utility namespace, so those generated no utilities at all;
    # every projected key must now be a real namespace key
    offenders = [key for key in _declarations() if key.startswith("--bw-")]
    assert not offenders, f"self-referential --bw-* identity mappings remain: {offenders}"


# --- the load-bearing mappings ----------------------------------------------


def test_load_bearing_mappings_are_exact() -> None:
    decls = _declarations()
    for key, value in {
        "--color-accent": "var(--bw-color-accent)",
        "--color-surface": "var(--bw-color-surface)",
        "--radius-md": "var(--bw-radius-md)",
        "--shadow-3": "var(--bw-elevation-3)",
        # the spacing scale projects via the DYNAMIC base only: the space
        # scale is authored as Tailwind --spacing multiples of 0.25rem
        # (DESIGN.md 6.1), so p-4 = calc(var(--bw-space-1) * 4). 0.11.0 tier
        # re-grammar: --bw-size-space-* / --bw-size-radius-* -> --bw-space-* /
        # --bw-radius-* (the scale IS the role vocabulary, no size- infix).
        "--spacing": "var(--bw-space-1)",
        # a type role is a size + Tailwind 4 companion-syntax line-height pair
        "--text-body-lg": "var(--bw-text-body-lg-size)",
        "--text-body-lg--line-height": "var(--bw-text-body-lg-line-height)",
        "--font-sans": "var(--bw-font-family-sans)",
        # preflight's default stacks follow the brand
        "--default-font-family": "var(--bw-font-family-sans)",
        "--default-mono-font-family": "var(--bw-font-family-mono)",
    }.items():
        assert decls.get(key) == value, f"{key}: expected {value}, got {decls.get(key)!r}"


# --- referenced tokens all exist ---------------------------------------------


def test_every_referenced_bw_token_is_emitted_by_tokens_css() -> None:
    emitted = _emitted_bw_names()
    missing = {key: value for key, value in _declarations().items() if value[len("var(") : -1] not in emitted}
    assert not missing, f"projection references tokens dist/tokens.css does not emit: {missing}"


# --- two-sided coverage census, derived from tokens.css itself ---------------


def test_projection_is_exactly_the_semantic_contract() -> None:
    """Set equality both ways: every semantic colour, radius step, elevation
    level, type role (with its line-height companion), and font stack is
    projected, and nothing outside that contract is (no component tier, state
    overlays, z-index, opacity, motion, or focus; no hand-listed subset that
    could silently drift when a token is added)."""
    # Derived from CANONICAL names only: the courtesy alias block re-declares
    # the re-tiered nav/skeleton/breadcrumb roles under their old --bw-color-*
    # names, which are not part of the semantic-colour contract any more
    # (0.11.0 tier re-grammar moved them to --bw-component-*, which this
    # census deliberately does not project).
    emitted = _emitted_bw_names(include_aliases=False)
    expected: set[str] = {"--spacing", "--default-font-family", "--default-mono-font-family"}
    for name in emitted:
        if m := re.match(r"^--bw-color-([a-z0-9-]+)$", name):
            expected.add(f"--color-{m.group(1)}")
        elif m := re.match(r"^--bw-radius-([a-z0-9-]+)$", name):
            expected.add(f"--radius-{m.group(1)}")
        elif m := re.match(r"^--bw-elevation-([a-z0-9-]+)$", name):
            expected.add(f"--shadow-{m.group(1)}")
        elif m := re.match(r"^--bw-text-([a-z0-9-]+)-size$", name):
            role = m.group(1)
            expected.add(f"--text-{role}")
            if f"--bw-text-{role}-line-height" in emitted:
                expected.add(f"--text-{role}--line-height")
        elif m := re.match(r"^--bw-font-family-([a-z0-9-]+)$", name):
            expected.add(f"--font-{m.group(1)}")
    projected = set(_declarations())
    assert projected == expected, (
        f"projection drifted from the semantic contract; "
        f"missing: {sorted(expected - projected)}; extra: {sorted(projected - expected)}"
    )


def test_deliberately_unprojected_families_do_not_leak() -> None:
    # explicit, readably-named guard on top of the census: the projection is
    # the semantic visual contract only (ADR-054 section 4)
    leaks = {key: value for key, value in _declarations().items() if _UNPROJECTED_FAMILY_RE.search(value)}
    assert not leaks, f"non-semantic token families leaked into the projection: {leaks}"
