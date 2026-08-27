"""Direct render tests for _trend_indicator.html (VIZ-017).

VIZ-017 extracts _stat.html's own trend block (VIZ-002, BR-BW-TPL-007,
AC-BW-073/074) into a standalone partial so a table cell or scorecard can
reuse the same accessible trend contract without the whole KPI tile. This
extraction is faithful by construction only if the extracted output matches
_stat.html's own output under the same inputs, so the tests below mirror
test_stat.py's own trend assertions one-for-one AND add the equivalence
check the extraction is graded on: the same trend/trend_label inputs must
produce the same glyph, the same hidden fallback word, and the same visible
label text, differing only in the (deliberately renamed, see the template's
own header comment) root class.
"""

from __future__ import annotations

import re

from django.template.loader import render_to_string

from brickwork.icons import get_icon

# Matches the fallback text inside a visually-hidden wrapper, mirroring
# test_stat.py's own pattern exactly.
_SR_WRAPPED = r'class="[^"]*(?:sr-only|visually-hidden)[^"]*"[^>]*>\s*%s'


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_trend_indicator.html", ctx)


def _render_stat_trend(**ctx: object) -> str:
    """Render _stat.html with a fixed label/value and return only its trend
    fragment (the <span class="bw-stat__trend ..."> ... </span> block), so
    the equivalence test compares the trend markup alone rather than the
    whole tile."""
    out = render_to_string("brickwork/components/_stat.html", {"label": "Active", "value": "12", **ctx})
    match = re.search(r'<span class="bw-stat__trend[^"]*">.*?</span>\s*</span>', out, re.DOTALL)
    assert match is not None, "no bw-stat__trend fragment found in _stat.html's own rendered output"
    return match.group(0)


def _render_indicator_fragment(**ctx: object) -> str:
    out = _render(**ctx)
    match = re.search(r'<span class="bw-trend[^"]*">.*?</span>\s*</span>', out, re.DOTALL)
    assert match is not None, "no bw-trend fragment found in _trend_indicator.html's own rendered output"
    return match.group(0)


# --- the documented usage example (header comment) must actually render -----


def test_documented_table_cell_usage_renders() -> None:
    from django.template import engines

    html = (
        engines["django"]
        .from_string(
            '{% include "brickwork/components/_trend_indicator.html" with trend="up" trend_label="12% on last month" %}'
        )
        .render({})
    )
    assert "bw-trend" in html
    assert "12% on last month" in html


# --- AC-BW-073: the trend fallback, mirroring test_stat.py's own cases ------


def test_trend_up_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(trend="up")
    assert get_icon("arrow-up") in out, "no up glyph rendered for trend='up'"
    assert re.search(_SR_WRAPPED % "increased", out), (
        "trend='up' without trend_label must render a visually-hidden 'increased' fallback"
    )


def test_trend_down_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(trend="down")
    assert get_icon("arrow-down") in out, "no down glyph rendered for trend='down'"
    assert re.search(_SR_WRAPPED % "decreased", out), (
        "trend='down' without trend_label must render a visually-hidden 'decreased' fallback"
    )


def test_trend_flat_renders_no_directional_arrow_or_words() -> None:
    out = _render(trend="flat")
    assert "bw-trend" in out
    assert get_icon("arrow-up") not in out
    assert get_icon("arrow-down") not in out
    assert "increased" not in out and "decreased" not in out


def test_trend_label_refines_the_accessible_text() -> None:
    out = _render(trend="up", trend_label="Up 12% on last month")
    assert "Up 12% on last month" in out
    # The hidden directional fallback stays even with a trend_label, matching
    # _stat.html's own redundancy-is-the-safe-failure rule (BR-BW-TPL-007).
    assert "increased" in out


def test_any_other_trend_value_takes_the_flat_treatment() -> None:
    # _stat.html's own {% if %}/{% elif %}/{% else %} ladder falls through to
    # the flat branch for any unrecognised value, with no raise: the
    # extraction must preserve that exact fallback rather than adding new
    # validation _stat.html never had.
    out = _render(trend="sideways")
    assert get_icon("minus") in out
    assert re.search(_SR_WRAPPED % "unchanged", out)


# --- AC-BW-074: directional meaning survives with colour stripped -----------


def test_directional_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(trend="up", trend_label="Up 12% on last month")
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped, "the directional glyph disappears when styling is stripped"
    assert "Up 12% on last month" in stripped, "the trend text disappears when styling is stripped"


def test_bare_trend_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(trend="down")
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped
    assert "decreased" in stripped


# --- the extraction's own acceptance criterion: identical to _stat.html -----


def _normalise(fragment: str) -> str:
    """Rename the class prefix and collapse inter-tag whitespace, so the
    comparison below is exact on everything that carries meaning (which
    class the SVG icon resolves to, the hidden fallback word, the visible
    trend_label text, the element nesting and ordering) while ignoring the
    one intentional difference (bw-stat__trend vs bw-trend, reasoned about in
    _trend_indicator.html's own header comment) and incidental indentation
    from the two templates' different surrounding context."""
    renamed = fragment.replace("bw-stat__trend", "bw-trend")
    return re.sub(r">\s+<", "><", renamed.strip())


def test_extracted_partial_matches_stat_html_trend_output_up() -> None:
    stat_fragment = _render_stat_trend(trend="up", trend_label="17 days faster")
    indicator_fragment = _render_indicator_fragment(trend="up", trend_label="17 days faster")
    assert _normalise(stat_fragment) == _normalise(indicator_fragment)


def test_extracted_partial_matches_stat_html_trend_output_down_no_label() -> None:
    stat_fragment = _render_stat_trend(trend="down")
    indicator_fragment = _render_indicator_fragment(trend="down")
    assert _normalise(stat_fragment) == _normalise(indicator_fragment)


def test_extracted_partial_matches_stat_html_trend_output_flat() -> None:
    stat_fragment = _render_stat_trend(trend="flat")
    indicator_fragment = _render_indicator_fragment(trend="flat")
    assert _normalise(stat_fragment) == _normalise(indicator_fragment)
