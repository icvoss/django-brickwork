"""Tier-discipline tests (ADR-054 section 2, "the tier rule, a locked regression
test") and the Phase-d runtime-override acceptance test (ADR-054 section 7).

The tier rule: authored/shipped component CSS references SEMANTIC and
COMPONENT tokens only, never a primitive or a raw colour ramp directly.
Primitives are build-time input from 0.11.0 (the tier re-grammar); Style
Dictionary resolves every reference to a literal by emit time, so a primitive
reference in shipped CSS or in tokens.css itself is a locked regression, not a
style preference.

The Phase-d acceptance test proves the architecture's runtime-recolouring
claim at the unit level: a brand overriding --bw-color-accent (the ONE token a
brand sets) must recompute the whole derived accent family in the browser with
no rebuild, which requires every derived accent-family declaration to be a
live var(--bw-color-accent) reference, never a baked literal.
"""

from __future__ import annotations

import re
from pathlib import Path

_DIST = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist"

_PRIMITIVE_VAR = re.compile(r"var\(--bw-primitive-[a-z0-9-]+\)")
_PRIMITIVE_DECL = re.compile(r"^\s*--bw-primitive-[a-z0-9-]+:", re.M)


# --- tier discipline: no primitive ever reaches shipped output --------------


def test_compiled_component_css_never_references_a_primitive() -> None:
    css = (_DIST / "brickwork.css").read_text()
    offenders = _PRIMITIVE_VAR.findall(css)
    assert not offenders, f"dist/brickwork.css references primitives directly (tier violation): {offenders}"


def test_tokens_css_emits_no_primitive_declaration() -> None:
    # Primitives are build-time input only from 0.11.0: Style Dictionary has
    # resolved every semantic/component reference to a literal by emit time, so
    # tokens.css must declare zero --bw-primitive-* custom properties (only the
    # canonical + alias blocks, neither of which is a primitive).
    css = (_DIST / "tokens.css").read_text()
    offenders = _PRIMITIVE_DECL.findall(css)
    assert not offenders, f"tokens.css emits primitive declarations (tier violation): {offenders}"


def test_tailwind_theme_css_never_references_a_primitive() -> None:
    css = (_DIST / "tailwind-theme.css").read_text()
    offenders = _PRIMITIVE_VAR.findall(css)
    assert not offenders, f"tailwind-theme.css references primitives directly (tier violation): {offenders}"


def test_authored_frontend_source_never_references_a_primitive() -> None:
    # Belt-and-braces on the AUTHORED (pre-build) source too, not just the
    # compiled artefact: a primitive reference here would always compile
    # through unresolved (primitives are never emitted), so this would fail
    # loudly at build time regardless, but pinning it at the source keeps the
    # failure close to the authoring mistake.
    frontend = Path(__file__).resolve().parent.parent / "frontend" / "src"
    offenders: dict[str, list[str]] = {}
    for css_path in sorted(frontend.glob("*.css")):
        found = _PRIMITIVE_VAR.findall(css_path.read_text())
        if found:
            offenders[css_path.name] = found
    assert not offenders, f"authored frontend CSS references primitives directly (tier violation): {offenders}"


# --- Phase-d: runtime accent override recolours the derived family ----------

# The accent-family tokens a brand override must recolour with no rebuild.
_ACCENT_FAMILY = (
    "--bw-color-accent-hover",
    "--bw-color-accent-subtle",
    "--bw-color-focus-ring",
)

# color-mix(...) may itself carry the accent reference bare (var(--bw-color-accent))
# or nested inside another color-mix()/var() call (e.g. mixed against the accent's
# own subtle derivation); either way "the whole expression contains a live
# reference to var(--bw-color-accent) and is not a literal" is the property that
# matters, so this only rejects an expression with NO such reference at all.
_LIVE_REFERENCE = re.compile(r"var\(--bw-color-accent\)")
_BAKED_LITERAL = re.compile(r"^oklch\(")


def _root_block(css: str) -> str:
    return css.split(":root {", 1)[1].split("}", 1)[0]


def _declared_values(block: str, name: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(rf"^\s*{re.escape(name)}:\s*([^;]+);", block, re.M)]


def test_derived_accent_family_are_live_references_not_baked_literals() -> None:
    """The architecture's acceptance criterion (ADR-054 section 7): overriding
    --bw-color-accent at :root must recompute --bw-color-accent-hover,
    --bw-color-accent-subtle, and --bw-color-focus-ring in-browser with no
    rebuild. That is only true if each is emitted as a color-mix(...)/var(...)
    expression that REFERENCES var(--bw-color-accent), never a literal oklch
    value baked in at build time."""
    css = (_DIST / "tokens.css").read_text()
    for name in _ACCENT_FAMILY:
        values = _declared_values(css, name)
        assert values, f"{name} not found in tokens.css"
        for value in values:
            assert not _BAKED_LITERAL.match(value), (
                f"{name}: {value!r} is a baked oklch literal, not a live reference "
                f"(Phase-d runtime override would not recolour this)"
            )
            assert _LIVE_REFERENCE.search(value), (
                f"{name}: {value!r} does not reference var(--bw-color-accent) at all "
                f"(Phase-d runtime override would not recolour this)"
            )


def test_derived_accent_family_present_in_every_theme_and_density_block() -> None:
    # The live-reference property must hold everywhere the family is declared
    # (light, dark, and any density variant), not just once at :root.
    css = (_DIST / "tokens.css").read_text()
    for name in _ACCENT_FAMILY:
        count = len(re.findall(rf"^\s*{re.escape(name)}:", css, re.M))
        assert count >= 2, f"{name} expected in at least the light and dark blocks, found {count} declaration(s)"
