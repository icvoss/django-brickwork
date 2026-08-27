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
_SURFACE_L = {"light": 1.0, "dark": 0.237}

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


def _relative_luminance(lightness: float) -> float:
    """Approximate sRGB relative luminance from oklch lightness."""
    lstar = lightness * 100.0
    return lstar / 903.3 if lstar <= 8.0 else ((lstar + 16.0) / 116.0) ** 3


def _contrast(l1: float, l2: float) -> float:
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("chroma_scale", _RETINT_CHROMA_STEPS)
def test_all_pairs_separation_holds_across_the_retint_envelope(theme, chroma_scale):
    """Every pair stays >= the floor, at full chroma and throughout the envelope.

    The envelope is the point: a fixture measuring only the shipped palette
    verifies the one configuration nobody worries about, the one the package
    authored and can see. The guarantee bites on brand palettes the package will
    never observe, so the retint is simulated here.
    """
    palette = [_oklab(L, C * chroma_scale, h) for L, C, h in _series(theme)]
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
    surface = _relative_luminance(_SURFACE_L[theme])
    for idx, (lightness, _, _) in enumerate(_series(theme), start=1):
        ratio = _contrast(_relative_luminance(lightness), surface)
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
