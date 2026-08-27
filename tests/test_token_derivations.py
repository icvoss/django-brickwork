"""Derivation-layer contract tests (DESIGN.md section 3).

Every derived token carries a live CSS expression in $extensions.bw.derived and
keeps its resolved default as $value. These tests recompute each expression by
linear interpolation and assert the result stays within a small tolerance of
the $value baseline, guarding both the tuned percentage constants and future
default-value edits. The mixes run in OKLAB (rectangular, no hue-angle
interpolation): browsers give oklch(1 0 0) an explicit hue of 0, so an oklch
mix rotates every tint's hue toward 0 (amber 58 lands at 4, pink); in oklab an
achromatic partner (black, white, transparent, a chroma-0 token) scales chroma
and preserves the source hue exactly, which is the model implemented here. Hue
IS asserted whenever the computed chroma is perceptible (>= 0.02): a $value
baseline carrying a ramp-step hue instead of the true resolved hue is
dishonest (DESIGN.md section 3).

A second guard asserts the shipped component CSS only references token names the
build actually emits, so a rename or a missed source addition cannot ship a
dangling var().
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SOURCE = _ROOT / "src" / "brickwork" / "tokens" / "source"
_DIST = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"
_FRONTEND = _ROOT / "frontend" / "src"

# Tolerances for the linear oklab-model recomputation against the baseline.
_TOL_L = 0.015
_TOL_C = 0.02
_TOL_ALPHA = 0.01
# Hue honesty: asserted only when the computed chroma is perceptible; below the
# floor the hue is visually powerless and ramp-step baselines are harmless.
_TOL_H = 4.0
_HUE_CHROMA_FLOOR = 0.02

_OKLCH = re.compile(r"^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:/\s*([\d.]+)\s*)?\)$")
_ALIAS = re.compile(r"^\{([a-z0-9.-]+)\}$")
# The full derivation grammar (DESIGN.md section 3): a single color-mix over a
# --bw-color-* reference with an achromatic or token partner, or a plain alias.
_MIX = re.compile(
    r"^color-mix\(in oklab, var\((--bw-color-[a-z0-9-]+)\) (\d+(?:\.\d+)?)%, "
    r"(black|white|transparent|var\(--bw-color-[a-z0-9-]+\))\)$"
)
_VAR = re.compile(r"^var\((--bw-color-[a-z0-9-]+)\)$")


def _load(name: str) -> dict:
    return json.loads((_SOURCE / f"{name}.tokens.json").read_text())


def _parse_oklch(value: str) -> tuple[float, float, float, float]:
    m = _OKLCH.match(value)
    assert m, f"not an oklch literal: {value!r}"
    lightness, chroma, hue, alpha = m.groups()
    return (float(lightness), float(chroma), float(hue), float(alpha) if alpha else 1.0)


def _resolve_alias(value: str, primitives: dict) -> str:
    """Resolve a {primitive.*} alias to its oklch literal (aliases never chain)."""
    m = _ALIAS.match(value)
    if not m:
        return value
    node = primitives
    for part in m.group(1).split("."):
        node = node[part]
    return node["$value"]


class _Theme:
    """One theme file's tokens: baselines (resolved $value) plus derivations."""

    def __init__(self, name: str) -> None:
        primitives = _load("primitive")
        data = _load(f"semantic.{name}")
        self.name = name
        self.baseline: dict[str, str] = {}
        self.derived: dict[str, str] = {}
        for group_key, group in data.items():
            for token_key, token in group.items():
                if token_key.startswith("$"):
                    continue
                css_name = f"--bw-{group_key}-{token_key}"
                self.baseline[css_name] = _resolve_alias(token["$value"], primitives)
                derived = token.get("$extensions", {}).get("bw", {}).get("derived")
                if derived is not None:
                    self.derived[css_name] = derived

    def components(self, css_name: str) -> tuple[float, float, float, float]:
        return _parse_oklch(self.baseline[css_name])


def _themes() -> list[_Theme]:
    return [_Theme("light"), _Theme("dark")]


def _hue_distance(h1: float, h2: float) -> float:
    """Circular distance between two hue angles in degrees."""
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


def _evaluate(theme: _Theme, expression: str) -> tuple[float, float, float, float]:
    """Cartesian oklab interpolation of a derived expression: (L, C, H, alpha).

    Baseline $values (never other derived expressions) resolve the var()
    references, so each token's tolerance is checked independently rather than
    compounding down a chain. ``color-mix(in oklab, ...)`` interpolates the
    RECTANGULAR (L, a, b) triple per CSS Color 4: there is no polar hue angle
    inside oklab itself, only the a/b pair, so the mix is a linear blend of a
    and b and the resulting hue is whatever ``atan2(b, a)`` says afterwards.
    This naturally reproduces "an achromatic partner (black, white,
    transparent, a chroma-0 token) passes the source hue through": achromatic
    means a == b == 0, which leaves the source's own a/b, scaled by its
    mix fraction, untouched by any hue-angle special case. A circular
    shortest-arc hue interpolation (the previous model here) is an oklch
    approximation and diverges from real color-mix(in oklab) once the
    partner carries even a small nonzero chroma (e.g. the authored ink
    token's C=0.005), which is why this function computes a/b directly
    rather than interpolating L/C/H as three independent scalars.
    """
    var_match = _VAR.match(expression)
    if var_match:
        lightness, chroma, hue, alpha = theme.components(var_match.group(1))
        return (lightness, chroma, hue, alpha)
    mix_match = _MIX.match(expression)
    assert mix_match, (
        f"[{theme.name}] derived expression does not match the DESIGN.md section 3 grammar: {expression!r}"
    )
    base_name, percent, partner = mix_match.groups()
    p = float(percent) / 100.0
    l1, c1, h1, a1 = theme.components(base_name)
    a_1, b_1 = c1 * math.cos(math.radians(h1)), c1 * math.sin(math.radians(h1))
    if partner == "transparent":
        # Premultiplied-alpha interpolation: the transparent side contributes no
        # colour, so the components pass through and only alpha scales.
        return (l1, c1, h1, p * a1)
    if partner == "black":
        l2, a_2, b_2, a2 = 0.0, 0.0, 0.0, 1.0
    elif partner == "white":
        l2, a_2, b_2, a2 = 1.0, 0.0, 0.0, 1.0
    else:
        l2, c2, h2, a2 = theme.components(partner[len("var(") : -1])
        a_2, b_2 = c2 * math.cos(math.radians(h2)), c2 * math.sin(math.radians(h2))
    lightness = p * l1 + (1 - p) * l2
    a_mix = p * a_1 + (1 - p) * a_2
    b_mix = p * b_1 + (1 - p) * b_2
    chroma = math.hypot(a_mix, b_mix)
    hue = math.degrees(math.atan2(b_mix, a_mix)) % 360.0 if chroma > 0.0 else h1
    return (lightness, chroma, hue, p * a1 + (1 - p) * a2)


@pytest.mark.parametrize("theme", _themes(), ids=lambda t: t.name)
def test_every_derived_expression_reproduces_its_baseline(theme: _Theme) -> None:
    assert theme.derived, f"expected derived tokens in semantic.{theme.name}"
    for css_name, expression in theme.derived.items():
        lightness, chroma, hue, alpha = _evaluate(theme, expression)
        base_l, base_c, base_h, base_a = theme.components(css_name)
        assert abs(lightness - base_l) <= _TOL_L, (
            f"[{theme.name}] {css_name}: derived L {lightness:.4f} vs baseline "
            f"{base_l:.4f} (tolerance {_TOL_L}); expression {expression!r}"
        )
        assert abs(chroma - base_c) <= _TOL_C, (
            f"[{theme.name}] {css_name}: derived C {chroma:.4f} vs baseline "
            f"{base_c:.4f} (tolerance {_TOL_C}); expression {expression!r}"
        )
        assert abs(alpha - base_a) <= _TOL_ALPHA, (
            f"[{theme.name}] {css_name}: derived alpha {alpha:.4f} vs baseline "
            f"{base_a:.4f} (tolerance {_TOL_ALPHA}); expression {expression!r}"
        )
        if chroma >= _HUE_CHROMA_FLOOR:
            assert _hue_distance(hue, base_h) <= _TOL_H, (
                f"[{theme.name}] {css_name}: derived hue {hue:.1f} vs baseline "
                f"{base_h:.1f} (tolerance {_TOL_H} degrees at chroma >= "
                f"{_HUE_CHROMA_FLOOR}); the $value baseline must carry the true "
                f"resolved hue; expression {expression!r}"
            )


def test_evaluate_mixes_toward_a_chromatic_partner_in_cartesian_oklab() -> None:
    """Direct model check (brickwork#306): a chromatic partner must move the hue.

    Every assertion elsewhere in this module runs against real token data, so a
    future edit that happened to make every mix partner achromatic again (as
    every derivation was before #289) would silently stop exercising this
    property, exactly as it did before #306 was found. This test is independent
    of the token source: it builds a synthetic theme with two colours of
    different, non-opposite hue and asserts the mix lands at the true Cartesian
    (L, a, b) blend rather than on a shortest-arc polar interpolation between
    the two hues.

    Base is red-ish (H 30), partner is blue-ish (H 260); a 60% mix under the
    correct Cartesian model lands near H 0.6 (verified below against a
    hand-computed a/b blend), against roughly H 338 on the polar shortest-arc
    path (which wraps through 0 the "short way" rather than the long way round
    through the two sources' own hues). The two models diverge by around 22.6
    degrees here, several times the module's own 4-degree hue tolerance, so
    this is a clean model discriminator rather than a borderline case.
    """
    theme = _Theme.__new__(_Theme)
    theme.name = "synthetic"
    theme.baseline = {
        "--bw-color-base": "oklch(0.6 0.2 30)",
        "--bw-color-partner": "oklch(0.5 0.15 260)",
    }
    theme.derived = {}

    lightness, chroma, hue, alpha = _evaluate(
        theme, "color-mix(in oklab, var(--bw-color-base) 60%, var(--bw-color-partner))"
    )

    # Hand-computed Cartesian expectation, independent of _evaluate's own code path.
    a1, b1 = 0.2 * math.cos(math.radians(30)), 0.2 * math.sin(math.radians(30))
    a2, b2 = 0.15 * math.cos(math.radians(260)), 0.15 * math.sin(math.radians(260))
    expected_l = 0.6 * 0.6 + 0.4 * 0.5
    expected_a = 0.6 * a1 + 0.4 * a2
    expected_b = 0.6 * b1 + 0.4 * b2
    expected_c = math.hypot(expected_a, expected_b)
    expected_h = math.degrees(math.atan2(expected_b, expected_a)) % 360.0

    assert lightness == pytest.approx(expected_l, abs=1e-9)
    assert chroma == pytest.approx(expected_c, abs=1e-9)
    assert hue == pytest.approx(expected_h, abs=1e-9)
    assert alpha == pytest.approx(1.0, abs=1e-9)

    # The polar shortest-arc model this replaced would land here instead; assert
    # the real result is nowhere near it, so a regression to that model is caught.
    polar_shortest_arc_hue = 30.0 + 0.4 * (((260.0 - 30.0 + 180.0) % 360.0) - 180.0)
    assert _hue_distance(hue, polar_shortest_arc_hue % 360.0) > 15.0, (
        "the Cartesian result should diverge sharply from the polar shortest-arc "
        f"model ({polar_shortest_arc_hue % 360.0:.1f} degrees); got hue {hue:.1f}, "
        "too close to the polar answer to be discriminating the two models"
    )


def test_dark_theme_contains_a_chromatic_partner_mix() -> None:
    """Coverage guard for brickwork#306: dark must exercise the Cartesian model.

    The defect in #306 never fired in either theme because every mix partner
    was exactly achromatic (black, white, or a zero-chroma grey), where polar
    and Cartesian interpolation agree. Light gained a chromatic-partner case
    with the four status -fg tokens (#289: mixed toward --bw-color-status-fg-ink,
    C 0.005). This asserts dark independently carries at least one derivation
    whose partner is genuinely chromatic (chroma above the tokens.css
    quantisation noise floor) AND whose base and partner hues differ enough
    that the Cartesian and polar models produce measurably different results,
    so the coverage this issue asks for cannot silently regress to
    achromatic-only again without this test failing.

    --bw-color-surface-marketing-tint in dark currently supplies this: it mixes
    var(--bw-color-accent) toward var(--bw-color-surface) (dark surface C
    0.005, a different hue to accent), and the two models diverge by roughly
    7.7 degrees on it, per the token's own $description.
    """
    dark = _Theme("dark")
    # Capture BOTH operands and the mix fraction. The polar comparator must be
    # built from the two INPUT colours; building it from the token's own
    # resolved baseline would run the polar formula on the Cartesian answer and
    # compare a number to a perturbation of itself, which passes for the wrong
    # reason.
    mix_pattern = re.compile(
        r"^color-mix\(in oklab, var\((--bw-color-[a-z0-9-]+)\) ([\d.]+)%, "
        r"var\((--bw-color-[a-z0-9-]+)\)\)$"
    )
    chromatic_hue_divergent: list[str] = []
    for css_name, expression in dark.derived.items():
        m = mix_pattern.match(expression)
        if not m:
            continue
        base_name, pct, partner_name = m.group(1), float(m.group(2)), m.group(3)
        _, base_c, base_h, _ = dark.components(base_name)
        _, partner_c, partner_h, _ = dark.components(partner_name)
        # Both operands must carry hue for a hue comparison to mean anything.
        if base_c < 0.002 or partner_c < 0.002:
            continue
        lightness, chroma, hue, alpha = _evaluate(dark, expression)
        if chroma < _HUE_CHROMA_FLOOR:
            continue
        d = (partner_h - base_h + 180) % 360 - 180
        p = pct / 100.0
        polar_hue = (base_h + (1 - p) * d) % 360.0
        if _hue_distance(hue, polar_hue) > _TOL_H:
            chromatic_hue_divergent.append(css_name)

    assert chromatic_hue_divergent, (
        "dark theme has no derived token mixing toward a chromatic partner with "
        "measurable hue divergence between the Cartesian and polar models; the "
        "coverage brickwork#306 asks for has regressed to achromatic-only, which "
        "cannot distinguish a correct _evaluate() from the shortest-arc bug it replaced"
    )


def test_derived_expressions_contain_no_dtcg_braces() -> None:
    # Style Dictionary treats {a.b} inside a value as a reference; a brace in a
    # derived expression would be resolved (or crash) instead of passing through.
    for theme in _themes():
        for css_name, expression in theme.derived.items():
            assert "{" not in expression and "}" not in expression, (
                f"[{theme.name}] {css_name}: derived expression contains a brace "
                f"Style Dictionary would treat as a reference: {expression!r}"
            )


def test_frontend_css_only_references_emitted_token_names() -> None:
    """Every fallback-less var(--bw-*) in the component CSS must be emitted.

    References WITH a fallback, e.g. var(--bw-icon-size, var(--bw-icon-size-md)),
    are per-instance hooks set inline by templates and are exempt; their nested
    fallback references are still collected and checked.
    """
    emitted = set(re.findall(r"^\s*(--bw-[a-z0-9-]+):", (_DIST / "tokens.css").read_text(), re.M))
    assert emitted, "no custom properties found in dist/tokens.css"
    missing: dict[str, set[str]] = {}
    for css_path in sorted(_FRONTEND.glob("*.css")):
        for name, terminator in re.findall(r"var\((--bw-[a-z0-9-]+)\s*([,)])", css_path.read_text()):
            if terminator == ")" and name not in emitted:
                missing.setdefault(css_path.name, set()).add(name)
    assert not missing, f"frontend CSS references token names tokens.css does not emit: {missing}"


@pytest.mark.parametrize(
    "family_name", ["--bw-color-accent-hover", "--bw-color-accent-subtle", "--bw-color-focus-ring"]
)
def test_accent_family_stays_derived_from_var_accent_in_every_theme_scope(family_name: str) -> None:
    """The per-request accent guarantee (brickwork#76, BRANDING.md recipe 3).

    A resolver-driven accent (per role, per tenant, per any request state)
    only works with no rebuild if the shipped stylesheet keeps the accent
    family derived LIVE over var(--bw-color-accent) rather than baking any
    theme scope's value to a literal. Every emitted declaration of each family
    member, in every scope (:root and the [data-theme] blocks alike), must
    reference the accent variable, so an override on the root element
    recolours the family in light and dark both.
    """
    css = (_DIST / "tokens.css").read_text()
    declarations = re.findall(rf"{family_name}:\s*([^;]+);", css)
    assert declarations, f"{family_name} must be emitted in dist/tokens.css"
    for value in declarations:
        assert "var(--bw-color-accent)" in value, (
            f"{family_name} is baked to {value!r} in some scope; it must derive "
            f"from var(--bw-color-accent) so a per-request accent recolours it"
        )
