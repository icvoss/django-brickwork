"""Chart series palette contract (umbrella ADR-082, Decision 5).

The categorical series palette (``--bw-color-chart-1`` .. ``-chart-8``) promises
something no other brand-overridable token does: any two series stay tellable
apart, in either theme, and stay visible on the surface they are drawn on. That
promise is only worth the name if it is executable, so it lives here.

ADR-082 states the guarantee as FOUR properties, deliberately expressed as what
they are properties OF rather than as a list of checks, because a list is what
let the third one go missing for two rounds:

    relation                          property                       here
    -------------------------------   ----------------------------   -----------------
    series against another series     perceptually distinguishable   test_all_pairs_*
    series against another series     distinct identity, not value   test_hue_separation
    series against its surface        visible at all (WCAG 1.4.11)   test_contrast_*
    series against itself, themes     same identity                  test_hue_invariant

All four hold across the retint envelope (chroma down to x0.7), which is their
scope rather than a fifth property.

Two of these exist because a palette that passed everything written at the time
was still wrong:

* An all-pairs distance floor alone accepts two series at the same hue separated
  only by lightness. They read as one colour in two states, not two categories,
  which is COL-030 arriving through a metric that satisfies its own letter.
  Hence the hue-separation floor.
* Separation is a relation BETWEEN series; contrast is a relation between a
  series and its BACKGROUND. No amount of all-pairs measurement can see it, and
  a palette once shipped five of eight light series below 3:1 with every
  separation check green. Hence the contrast floor.

Values are read from the BUILT artefact, not the source, so these assert what
consumers actually receive.
"""

from __future__ import annotations

import itertools
import math
import re
from pathlib import Path

import pytest

_DIST = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist"
_TOKENS_CSS = _DIST / "tokens.css"

# --- the contract's constants, with their provenance -------------------------
# Derived from the package's own evidence BEFORE any candidate palette existed,
# per ADR-082 Decision 4's ordering rule: the tightest pair the package already
# requires a user to tell apart at a glance is danger against warning at 0.1437,
# and adjacent steps within one ramp, which the package treats as one meaning
# rather than distinct categories, measure 0.077 and 0.063. 0.12 sits between.
# The rule is that the palette moves and this constant does not; it has now been
# exercised three times against its own author and held.
_SEPARATION_FLOOR = 0.12
# Categorical identity is carried by hue, not lightness (see module docstring).
_HUE_SEPARATION_FLOOR = 28.0
# WCAG 1.4.11: a data series is a non-text graphical object. 3:1 is the
# package's existing floor for exactly this case, including the 2px focus ring.
_CONTRAST_FLOOR = 3.0
# The retint envelope: below x0.7 chroma no eight-series palette can hold the
# separation floor, so the package stops guaranteeing it (docs/BRANDING.md).
_RETINT_CHROMA_STEPS = (1.0, 0.9, 0.8, 0.7)

# Surfaces a series is drawn on. A chart card is elevated, so dark charts sit on
# surface-raised rather than the base surface.
_SURFACE = {"light": (1.0, 0.0, 0.0), "dark": (0.237, 0.005, 265.0)}

_OKLCH = re.compile(r"oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)")


def _block(selector: str) -> str:
    css = _TOKENS_CSS.read_text()
    start = css.index(selector + " {")
    return css[start : css.index("\n}", start)]


def _series(theme: str) -> list[tuple[float, float, float]]:
    """The eight series of one theme as (L, C, h), in index order."""
    selector = ":root" if theme == "light" else '[data-theme="dark"]'
    block = _block(selector)
    out = []
    for i in range(1, 9):
        m = re.search(rf"--bw-color-chart-{i}:\s*([^;]+);", block)
        assert m, f"--bw-color-chart-{i} missing from {selector}"
        v = _OKLCH.match(m.group(1).strip())
        assert v, f"--bw-color-chart-{i} is not a literal oklch value: {m.group(1)!r}"
        out.append((float(v.group(1)), float(v.group(2)), float(v.group(3))))
    return out


def _oklab(lightness: float, chroma: float, h: float) -> tuple[float, float, float]:
    r = math.radians(h)
    return (lightness, chroma * math.cos(r), chroma * math.sin(r))


def _distance(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def _all_pairs_min(colours) -> tuple[float, int, int]:
    """Smallest oklab distance over ALL pairs, with the offending indices.

    All pairs, not sequential ones: a chart's rendered adjacency is arbitrary
    (any two series can neighbour each other in a legend or as adjacent bars),
    and because lightness and chroma are authored per series a non-sequential
    pair can be the closest one.
    """
    worst = min(
        ((_distance(colours[i], colours[j]), i, j) for i, j in itertools.combinations(range(len(colours)), 2)),
        key=lambda t: t[0],
    )
    return worst


def _hue_gap(h1: float, h2: float) -> float:
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


def _relative_luminance(colour: tuple[float, float, float]) -> float:
    """True WCAG relative luminance for an oklch colour.

    Deliberately NOT an approximation from oklch L alone. An earlier version of
    this file treated oklch L as a proxy for relative luminance by running it
    through the CIELAB inverse, which yields CIE XYZ Y rather than sRGB
    relative luminance: it skips the XYZ-to-sRGB matrix entirely. That
    approximation was conservative for every colour in this palette (it
    understated all 16 series ratios, and every value passed its floor by a
    wider margin under the correct computation), but conservative-by-accident
    is not a basis for a WCAG conformance claim. Contrast is a semver-relevant
    guarantee here, so it is computed properly: oklch to oklab to linear sRGB,
    then the WCAG coefficients.
    """
    r, g, b = _oklab_to_linear_rgb(*_oklab(*colour))
    r, g, b = (max(0.0, min(1.0, v)) for v in (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(l1: float, l2: float) -> float:
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def _in_srgb_gamut(colour: tuple[float, float, float], tolerance: float = 0.001) -> bool:
    """Is this oklch colour renderable in sRGB without clipping?"""
    return all(-tolerance <= v <= 1.0 + tolerance for v in _oklab_to_linear_rgb(*_oklab(*colour)))


def _as_displayed(colour: tuple[float, float, float]) -> tuple[float, float, float]:
    """The colour a browser actually paints, in oklab.

    CSS Color 4 clips an out-of-gamut colour to the destination gamut, so an
    authored value outside sRGB is NOT what a viewer sees. Every property in
    this module is asserted on this function's output rather than on the
    authored oklch, because a guarantee about colours no display can produce
    is not a guarantee.

    This is the defect that made the sixth property necessary. Eleven of the
    sixteen originally-authored series were out of gamut, and the light
    palette measured 0.1632 as authored against 0.0787 as displayed, failing
    its own floor on every ordinary monitor. The authored figures were not
    merely optimistic: the worst pair moved from 6/7 to 5/7 under clipping, so
    they pointed at the wrong problem as well as the wrong magnitude.
    """
    r, g, b = _oklab_to_linear_rgb(*_oklab(*colour))
    r, g, b = (max(0.0, min(1.0, v)) for v in (r, g, b))
    return _linear_rgb_to_oklab(r, g, b)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_series_is_renderable_in_srgb(theme):
    """The sixth property: an authored colour outside sRGB is not the shipped colour.

    Without this, every other assertion in this module can measure a colour no
    browser will paint. It is listed last among the properties but it is
    logically first: it is what makes the others describe reality.
    """
    out_of_gamut = [idx for idx, c in enumerate(_series(theme), start=1) if not _in_srgb_gamut(c)]
    assert not out_of_gamut, (
        f"{theme} theme: series {out_of_gamut} fall outside sRGB and will be clipped by the "
        "browser, so the colour shipped is not the colour authored. Re-author them inside "
        "the gamut rather than relaxing this check."
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("chroma_scale", _RETINT_CHROMA_STEPS)
def test_all_pairs_separation_holds_across_the_retint_envelope(theme, chroma_scale):
    """Every pair stays >= the floor, at full chroma and throughout the envelope.

    The envelope is the point: a fixture measuring only the shipped palette
    verifies the one configuration nobody worries about, the one the package
    authored and can see. The guarantee bites on brand palettes the package will
    never observe, so the retint is simulated here.
    """
    palette = [_as_displayed((L, C * chroma_scale, h)) for L, C, h in _series(theme)]
    worst, i, j = _all_pairs_min(palette)
    assert worst >= _SEPARATION_FLOOR, (
        f"{theme} theme at chroma x{chroma_scale}: series {i + 1} and {j + 1} are "
        f"{worst:.4f} apart in oklab, below the {_SEPARATION_FLOOR} floor. "
        "Move the palette, not the floor (ADR-082 Decision 4)."
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_hue_separation_so_identity_is_carried_by_hue(theme):
    """No two series may be the same hue at different lightness.

    An all-pairs distance floor alone accepts such a pair and calls it separated.
    A viewer does not: it reads as one series in two states.
    """
    series = _series(theme)
    for i, j in itertools.combinations(range(8), 2):
        gap = _hue_gap(series[i][2], series[j][2])
        assert gap >= _HUE_SEPARATION_FLOOR, (
            f"{theme} theme: series {i + 1} (hue {series[i][2]:g}) and {j + 1} "
            f"(hue {series[j][2]:g}) are only {gap:.1f} degrees apart, below the "
            f"{_HUE_SEPARATION_FLOOR} floor. They would read as one colour in two states."
        )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_contrast_against_own_surface(theme):
    """Every series clears WCAG 1.4.11 on the surface it is drawn on.

    Not implied by any separation check: eight colours can be perfectly
    distinguishable from each other and all of them invisible on white.
    """
    surface = _relative_luminance(_SURFACE[theme])
    for idx, colour in enumerate(_series(theme), start=1):
        ratio = _contrast(_relative_luminance(colour), surface)  # clipped inside
        assert ratio >= _CONTRAST_FLOOR, (
            f"{theme} theme: series {idx} measures {ratio:.2f}:1 against its surface, "
            f"below WCAG 1.4.11's {_CONTRAST_FLOOR}:1 for non-text graphical objects."
        )


def test_hue_is_invariant_across_themes():
    """A series' identity is its hue, so it may not change when the theme does.

    Lightness and chroma are authored per theme (BR-BW-TOK-002); hue is held. If
    chart-3 were olive in light and turquoise in dark, a user switching theme
    would see the series change identity and any legend or documentation naming
    a colour would break silently.
    """
    light, dark = _series("light"), _series("dark")
    for idx, ((_, _, hl), (_, _, hd)) in enumerate(zip(light, dark, strict=True), start=1):
        assert _hue_gap(hl, hd) == pytest.approx(0.0, abs=0.5), (
            f"series {idx} shifts hue between themes ({hl:g} light, {hd:g} dark). "
            "Authoring per theme moves lightness and chroma, never hue."
        )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_separation_floor_rejects_a_collapsed_palette(theme):
    """Teeth-check on the CONSTANT, not on the assertion that reads it.

    ADR-082 Decision 4 requires the calibrated threshold be shown to reject a
    deliberately collapsed palette. A floor no realistic palette can fail is not
    a guarantee, and this is the demonstration kept executable rather than run
    once: a constant demonstrated to have teeth stops being demonstrated the
    moment nobody runs the demonstration.
    """
    series = _series(theme)
    collapsed = list(series)
    l2, c2, h2 = collapsed[1]
    collapsed[2] = (l2 + 0.01, c2, h2 + 2.0)  # series 3 moved onto series 2
    worst, _, _ = _all_pairs_min([_oklab(*c) for c in collapsed])
    assert worst < _SEPARATION_FLOOR, (
        f"the {_SEPARATION_FLOOR} floor accepted a palette with two series "
        f"{worst:.4f} apart. The floor has no teeth and the other assertions in "
        "this module prove nothing."
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_chart_token_in_the_vocabulary_is_emitted(theme):
    """ADR-082 Decision 1 fixes the vocabulary; nothing in it may go missing.

    A token a consumer's adapter reads via getComputedStyle() and does not find
    returns an empty string rather than raising, so an absent token degrades a
    consumer's chart silently (icvoss/django-brickwork#288's false-affordance
    rule, in its stricter silent-failure form).
    """
    block = _block(":root" if theme == "light" else '[data-theme="dark"]')
    expected = [f"--bw-color-chart-{i}" for i in range(1, 9)] + [
        "--bw-color-chart-axis",
        "--bw-color-chart-grid",
        "--bw-color-chart-axis-label",
        "--bw-color-chart-tooltip-bg",
        "--bw-color-chart-tooltip-text",
        "--bw-color-chart-tooltip-border",
    ]
    missing = [name for name in expected if f"{name}:" not in block]
    assert not missing, f"{theme} theme is missing chart tokens: {missing}"


# --- chart chrome, which the four series properties say nothing about --------
# The eight series get four properties; axis, grid, axis-label and the tooltip
# trio originally got none, and their contrast figures lived only in token
# $descriptions where nothing could check them. Two of those figures were
# wrong when first written (14.7 and 12.1 against a true 12.5 and 9.7): not a
# functional defect, since both clear AA comfortably, but an unverified number
# in shipped metadata is the same class of claim this module exists to gate.


def _token(theme: str, name: str) -> tuple[float, float, float]:
    """One chrome token of one theme as (L, C, h), from the built artefact."""
    block = _block(":root" if theme == "light" else '[data-theme="dark"]')
    m = re.search(rf"--bw-color-{name}:\s*([^;]+);", block)
    assert m, f"--bw-color-{name} missing from the {theme} block"
    v = _OKLCH.match(m.group(1).strip())
    assert v, f"--bw-color-{name} is not a literal oklch value: {m.group(1)!r}"
    return (float(v.group(1)), float(v.group(2)), float(v.group(3)))


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_axis_clears_the_non_text_contrast_floor(theme):
    """The axis line is a non-text graphical object, so WCAG 1.4.11 applies.

    Gridlines deliberately do NOT appear here: a gridline is decoration that
    must recede behind the data rather than a graphical object conveying
    information, so holding it to 3:1 would make it compete with the series.
    That exemption is a decision, recorded in the token's own $description,
    not an oversight.
    """
    ratio = _contrast(_relative_luminance(_token(theme, "chart-axis")), _relative_luminance(_SURFACE[theme]))
    assert ratio >= _CONTRAST_FLOOR, (
        f"{theme} theme: chart-axis measures {ratio:.2f}:1 against its surface, "
        f"below WCAG 1.4.11's {_CONTRAST_FLOOR}:1."
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_axis_label_clears_the_text_contrast_floor(theme):
    """Axis tick labels are text, so the AA floor is 4.5:1, not 3:1."""
    ratio = _contrast(_relative_luminance(_token(theme, "chart-axis-label")), _relative_luminance(_SURFACE[theme]))
    assert ratio >= 4.5, (
        f"{theme} theme: chart-axis-label measures {ratio:.2f}:1 against its surface, "
        "below the 4.5:1 AA floor for text."
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_tooltip_text_clears_aa_on_its_own_background(theme):
    """Tooltip text against tooltip background, not against the page surface.

    A tooltip carries its own background, so the page surface is irrelevant to
    it. This is the same relation-matters point the series contrast test makes:
    the pairing has to be the one that actually renders.
    """
    ratio = _contrast(
        _relative_luminance(_token(theme, "chart-tooltip-text")),
        _relative_luminance(_token(theme, "chart-tooltip-bg")),
    )
    assert ratio >= 4.5, (
        f"{theme} theme: chart-tooltip-text measures {ratio:.2f}:1 on chart-tooltip-bg, "
        "below the 4.5:1 AA floor for text."
    )


# --- the fifth property: colour-vision deficiency ----------------------------
# Found by asking what a fifth property would be, after the fourth (contrast
# against surface) was itself found the same way. The palette does NOT hold the
# 0.12 separation floor under dichromatic vision, and no eight-colour palette
# can: the best achievable all-pairs floor across normal vision plus all three
# dichromacies is 0.1025, below the 0.077-to-0.1437 band the package's own
# evidence brackets as distinguishable. Six series reach 0.1402, five reach
# 0.1919. That is a fact about eight-colour categorical palettes, not about
# this one, and re-solving cannot change it (ADR-082 Decision 5).
#
# So the separation guarantee is scoped to normal colour vision, and COL-030's
# standing NO carries the CVD case: "Is meaning ever conveyed by colour alone
# (status dots, chart series, diff)? -> NO (standing rule): every colour-coded
# element ships a paired text/icon/label." CHT-014's swatch-plus-text-label
# pairing is the mechanism, promoted to CORE because it discharges a standing
# NO for the whole family rather than serving an occasional need.
#
# These tests therefore assert the DOCUMENTED CVD floor, not 0.12. The point is
# not that the palette passes; it is that the figures are pinned and visible, so
# a future palette change that makes CVD worse than what ADR-082 records fails
# here instead of going unnoticed.
#
# SANITY-CHECKING THIS SIMULATION, which matters because a subtly wrong CVD
# model produces confident wrong numbers in BOTH directions. The expected
# signature, verified when this was written:
#   red vs green collapses to 18% of normal separation under deuteranopia
#   red vs blue survives at 88% under deuteranopia
#   tritanopia leaves red/green alone (105%), affecting the blue-yellow axis
# If a change to these transforms breaks that signature, the model is wrong
# regardless of whether the assertions below still pass.

# The measured floor across all three dichromacies and both themes, recorded in
# ADR-082. A documented limit, not an aspiration: the true minimum is 0.0153
# (protanopia, light, series 1 against 5). Pinned just under what is measured,
# because a generous margin here would let the palette degrade silently, which
# is the whole failure this figure exists to catch.
#
# This value moved once already, from 0.020, when the palette was re-authored
# inside the sRGB gamut. That is the mechanism working: the gamut fix changed
# the colours, the CVD figures moved with them, and this test failed rather
# than quietly tracking the change. Re-measure and update deliberately when the
# palette moves; never widen the margin to make a failure go away.
_CVD_DOCUMENTED_FLOOR = 0.015

_LMS_SIM = {
    "protanopia": lambda l_ch, m_ch, s_ch: (2.02344 * m_ch - 2.52581 * s_ch, m_ch, s_ch),
    "deuteranopia": lambda l_ch, m_ch, s_ch: (l_ch, 0.494207 * l_ch + 1.24827 * s_ch, s_ch),
    "tritanopia": lambda l_ch, m_ch, s_ch: (l_ch, m_ch, -0.395913 * l_ch + 0.801109 * m_ch),
}


def _oklab_to_linear_rgb(lightness: float, a: float, b: float) -> tuple[float, float, float]:
    l_, m_, s_ = (
        lightness + 0.3963377774 * a + 0.2158037573 * b,
        lightness - 0.1055613458 * a - 0.0638541728 * b,
        lightness - 0.0894841775 * a - 1.2914855480 * b,
    )
    l_ch, m_ch, s_ch = l_**3, m_**3, s_**3
    return (
        4.0767416621 * l_ch - 3.3077115913 * m_ch + 0.2309699292 * s_ch,
        -1.2684380046 * l_ch + 2.6097574011 * m_ch - 0.3413193965 * s_ch,
        -0.0041960863 * l_ch - 0.7034186147 * m_ch + 1.7076147010 * s_ch,
    )


def _linear_rgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    def cbrt(x: float) -> float:
        return x ** (1 / 3) if x > 0 else 0.0

    l_ch = cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ch = cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ch = cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * l_ch + 0.7936177850 * m_ch - 0.0040720468 * s_ch,
        1.9779984951 * l_ch - 2.4285922050 * m_ch + 0.4505937099 * s_ch,
        0.0259040371 * l_ch + 0.7827717662 * m_ch - 0.8086757660 * s_ch,
    )


def _simulate_dichromacy(colour: tuple[float, float, float], kind: str) -> tuple[float, float, float]:
    """One oklch colour as a dichromat sees it, returned in oklab."""
    r, g, b = _oklab_to_linear_rgb(*_oklab(*colour))
    r, g, b = (max(0.0, min(1.0, v)) for v in (r, g, b))
    lms = (
        17.8824 * r + 43.5161 * g + 4.11935 * b,
        3.45565 * r + 27.1554 * g + 3.86714 * b,
        0.0299566 * r + 0.184309 * g + 1.46709 * b,
    )
    l_ch, m_ch, s_ch = _LMS_SIM[kind](*lms)
    r2 = 0.0809444479 * l_ch - 0.130504409 * m_ch + 0.116721066 * s_ch
    g2 = -0.0102485335 * l_ch + 0.0540193266 * m_ch - 0.113614708 * s_ch
    b2 = -0.000365296938 * l_ch - 0.00412161469 * m_ch + 0.693511405 * s_ch
    r2, g2, b2 = (max(0.0, min(1.0, v)) for v in (r2, g2, b2))
    return _linear_rgb_to_oklab(r2, g2, b2)


def test_the_dichromacy_simulation_still_behaves():
    """Guard the MODEL before trusting any number it produces.

    Without this, a broken transform yields plausible figures and the
    assertions below go quietly meaningless. Uses the package's own primitive
    red/green/blue at step 600, whose behaviour under each dichromacy is a
    textbook result rather than a property of the chart palette.
    """
    red, green, blue = (0.577, 0.215, 27), (0.627, 0.155, 149), (0.546, 0.192, 262)
    normal_rg = _distance(_oklab(*red), _oklab(*green))
    normal_rb = _distance(_oklab(*red), _oklab(*blue))

    deut_rg = _distance(_simulate_dichromacy(red, "deuteranopia"), _simulate_dichromacy(green, "deuteranopia"))
    assert deut_rg / normal_rg < 0.30, (
        "red and green should collapse under deuteranopia (measured 18% of normal when written); "
        f"got {deut_rg / normal_rg:.0%}. The simulation is wrong."
    )
    deut_rb = _distance(_simulate_dichromacy(red, "deuteranopia"), _simulate_dichromacy(blue, "deuteranopia"))
    assert deut_rb / normal_rb > 0.70, (
        "red and blue should largely survive deuteranopia (measured 88% when written); "
        f"got {deut_rb / normal_rb:.0%}. The simulation is wrong."
    )
    trit_rg = _distance(_simulate_dichromacy(red, "tritanopia"), _simulate_dichromacy(green, "tritanopia"))
    assert trit_rg / normal_rg > 0.90, (
        "tritanopia affects the blue-yellow axis and should leave red/green alone "
        f"(measured 105% when written); got {trit_rg / normal_rg:.0%}. The simulation is wrong."
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("kind", sorted(_LMS_SIM))
def test_dichromatic_separation_is_no_worse_than_documented(theme, kind):
    """Pin the CVD figures ADR-082 records, so they cannot silently degrade.

    This asserts the DOCUMENTED floor, deliberately far below the 0.12 normal
    vision floor, because eight categorical colours cannot hold 0.12 under
    dichromacy at all. Passing here is not a claim that the series are
    distinguishable to a dichromat: they are not, and COL-030's paired
    text label is what carries the meaning (CHT-014, CORE).
    """
    simulated = [_simulate_dichromacy(c, kind) for c in _series(theme)]
    worst, i, j = _all_pairs_min(simulated)
    assert worst >= _CVD_DOCUMENTED_FLOOR, (
        f"{theme} theme under {kind}: series {i + 1} and {j + 1} are {worst:.4f} apart, "
        f"worse than the {_CVD_DOCUMENTED_FLOOR} figure ADR-082 records. The palette has "
        "degraded for dichromatic viewers; ADR-082's recorded figures need re-measuring "
        "and the change needs justifying, not the floor lowering."
    )
