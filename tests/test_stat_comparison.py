"""Direct render tests for _stat_comparison.html (VIZ-019/020).

VIZ-019: a this-vs-last-period comparison tile, current=/previous=/
period_label=, delta rendered via _trend_indicator.html internally.
VIZ-020: brickwork does not compute the delta; current, previous and
trend_label all arrive pre-formatted from the caller. These tests assert
the template renders exactly the caller-supplied values with no arithmetic
or derivation performed on them, and that trend/trend_label are taken
straight through to _trend_indicator.html unmodified (never derived from
current/previous: see the template's own header comment for why deriving
direction from the two values is period-comparison business logic under
VIZ-020, not merely rendering).

Mirrors test_stat.py's own structure (the KPI tile this component sits
beside) and test_trend_indicator.py's own trend-fallback assertions (the
partial this component composes, never duplicates).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from brickwork.icons import get_icon

_SR_WRAPPED = r'class="[^"]*(?:sr-only|visually-hidden)[^"]*"[^>]*>\s*%s'


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_stat_comparison.html", ctx)


# --- VIZ-019: current/previous/period_label render verbatim ------------------


def test_current_and_previous_render_as_supplied_with_no_arithmetic() -> None:
    out = _render(current="1,234", previous="987")
    assert "1,234" in out
    assert "987" in out
    assert "bw-stat-comparison__current" in out
    assert "bw-stat-comparison__previous" in out


def test_period_label_renders_as_visible_text_after_previous() -> None:
    out = _render(current="1,234", previous="987", period_label="vs last month")
    assert "vs last month" in out
    # Ordering: period_label follows previous in the same container, so it
    # reads in DOM order right after the value it qualifies (VIZ-019's "not
    # left as floating text"), rather than appearing before current/label.
    previous_index = out.index("987")
    period_index = out.index("vs last month")
    assert period_index > previous_index


def test_period_label_omitted_renders_no_period_caption() -> None:
    out = _render(current="1,234", previous="987")
    assert "bw-stat-comparison__period" not in out


def test_label_renders_the_overline_when_supplied() -> None:
    out = _render(label="Revenue", current="1,234", previous="987")
    assert re.search(r'class="[^"]*bw-stat-comparison__label[^"]*"[^>]*>[^<]*Revenue', out)


def test_label_omitted_renders_no_label_row() -> None:
    out = _render(current="1,234", previous="987")
    assert "bw-stat-comparison__label" not in out


# --- VIZ-020: no delta computation happens in this template ------------------


def test_a_non_numeric_pre_formatted_pair_renders_without_raising() -> None:
    # VIZ-020: brickwork never parses current/previous as numbers, so a
    # caller-formatted pair that could not be sign-checked (percentages,
    # currency strings, or plain words) must still render cleanly. A
    # template that tried to derive trend from current/previous would need
    # to parse these as numbers and could not.
    out = _render(current="48%", previous="52%")
    assert "48%" in out
    assert "52%" in out


def test_trend_and_trend_label_are_independent_of_current_and_previous() -> None:
    # The caller may supply a trend that does not match a naive numeric
    # comparison of current/previous (e.g. cost falling is a caller-defined
    # "good" direction rendered as trend="up"); the template must render
    # exactly the supplied trend, never re-derive one from the two values.
    out = _render(current="52", previous="48", trend="down", trend_label="improved")
    assert get_icon("arrow-down") in out
    assert get_icon("arrow-up") not in out
    assert "improved" in out


def test_omitting_trend_renders_no_trend_row_even_though_current_differs_from_previous() -> None:
    # If this template ever derived trend from current vs previous, a
    # differing pair would always produce a trend row. It must not: no
    # trend key means no trend row, matching _trend_indicator.html's own
    # falsy-trend guard exactly.
    out = _render(current="1,234", previous="987")
    assert "bw-trend" not in out


# --- delta composition: via _trend_indicator.html, never duplicated ----------


def test_trend_up_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(current="12", previous="8", trend="up")
    assert get_icon("arrow-up") in out, "no up glyph rendered for trend='up'"
    assert re.search(_SR_WRAPPED % "increased", out), (
        "trend='up' without trend_label must render a visually-hidden 'increased' fallback"
    )


def test_trend_down_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(current="3", previous="9", trend="down")
    assert get_icon("arrow-down") in out, "no down glyph rendered for trend='down'"
    assert re.search(_SR_WRAPPED % "decreased", out), (
        "trend='down' without trend_label must render a visually-hidden 'decreased' fallback"
    )


def test_trend_flat_renders_no_directional_arrow_or_words() -> None:
    out = _render(current="0", previous="0", trend="flat")
    assert "bw-trend" in out
    assert get_icon("arrow-up") not in out
    assert get_icon("arrow-down") not in out
    assert "increased" not in out and "decreased" not in out


def test_trend_label_refines_the_accessible_text() -> None:
    out = _render(current="12", previous="8", trend="up", trend_label="Up 12% on last month")
    assert "Up 12% on last month" in out
    assert "increased" in out


@pytest.mark.parametrize("trend_value", [None, "", 0, False])
def test_falsy_trend_renders_no_trend_row(trend_value: object) -> None:
    out = _render(current="12", previous="8", trend=trend_value)
    assert "bw-trend" not in out, f"rendered a trend row for trend={trend_value!r}"


def test_absent_trend_key_renders_no_trend_row() -> None:
    out = _render(current="12", previous="8")
    assert "bw-trend" not in out


def test_css_class_seam_passes_bw_stat_comparison_trend_onto_the_trend_row() -> None:
    # Mirrors _stat.html's own composition (#334): this component's own
    # bw-stat-comparison__trend class rides alongside _trend_indicator.html's
    # bw-trend on the SAME element, so a consumer stylesheet may select
    # either. Proves the css_class seam is actually wired, not merely
    # documented: an unwired seam and a correctly wired one are otherwise
    # indistinguishable from the trend assertions above alone.
    out = _render(current="12", previous="8", trend="up")
    match = re.search(r'<span class="(bw-trend[^"]*)">', out)
    assert match is not None, "no bw-trend element found in the rendered output"
    classes = match.group(1).split()
    assert "bw-trend" in classes
    assert "bw-trend--up" in classes
    assert "bw-stat-comparison__trend" in classes
    assert "bw-stat-comparison__trend--up" in classes


# --- AC-BW-074 equivalent: directional meaning survives with colour stripped -


def test_directional_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(current="12", previous="8", trend="up", trend_label="Up 12% on last month")
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped, "the directional glyph disappears when styling is stripped"
    assert "Up 12% on last month" in stripped, "the trend text disappears when styling is stripped"


# --- escaping: current/previous/period_label/label are TEXT-position only ----
#
# All four reach only text position in this template (no attribute position
# renders any of them), so Django's default auto-escaping is the correct
# mechanism (see the template's own header comment). These assertions prove
# a value that would break out of an attribute is rendered inert as escaped
# text, and that the input actually reached the render rather than being
# silently dropped (a raised TemplateSyntaxError or an empty render would
# hide behind a bare "not in out" assertion).


def test_current_previous_and_period_label_are_escaped() -> None:
    out = _render(
        current="<script>alert(1)</script>",
        previous='" onmouseover="alert(2)',
        period_label="<b>vs</b> last month",
    )
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert 'onmouseover="alert(2)"' not in out
    assert "&quot;" in out or "&#x27;" in out or "&#39;" in out
    assert "<b>vs</b>" not in out
    assert "&lt;b&gt;vs&lt;/b&gt;" in out


def test_label_is_escaped() -> None:
    out = _render(label="<script>alert(1)</script>", current="1", previous="1")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


# --- size (mirrors _stat.html's VIZ-027 seam) --------------------------------


def test_size_maps_to_modifier_classes() -> None:
    assert "bw-stat-comparison--sm" in _render(current="1", previous="1", size="sm")
    assert "bw-stat-comparison--lg" in _render(current="1", previous="1", size="lg")
    assert "bw-stat-comparison--" not in _render(current="1", previous="1")


def test_an_unrecognised_size_value_renders_the_bare_class_with_no_modifier() -> None:
    # size is matched against the closed set with explicit literals, not
    # interpolated: a value outside {"sm", "lg"} (including the default
    # "md") must render the bare bw-stat-comparison class, never a
    # bw-stat-comparison--<whatever the caller passed> false affordance.
    out = _render(current="1", previous="1", size="md")
    assert "bw-stat-comparison--" not in out
    out = _render(current="1", previous="1", size="xl")
    assert "bw-stat-comparison--" not in out


class _AttributeCollector(HTMLParser):
    """Collects (tag, attribute-name) pairs from real parsed attributes.

    Deliberately not a substring/regex check: a payload that lands as text
    content rather than an attribute (e.g. escaped into the class value's
    own quoted string) must not be mistaken for a live attribute by a test
    that only greps for the substring "onclick".
    """

    def __init__(self) -> None:
        super().__init__()
        self.attrs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, _value in attrs:
            self.attrs.append((tag, name))


def _event_handler_attrs(html: str) -> list[tuple[str, str]]:
    parser = _AttributeCollector()
    parser.feed(html)
    return [(tag, name) for tag, name in parser.attrs if name.startswith("on")]


def test_the_detector_itself_catches_the_defect_the_probe_found() -> None:
    # Non-vacuity guard for the regression test below: proves the
    # (payload, parser, assertion) machinery actually CAN fail, by running
    # it against the literal vulnerable shape the coordinator's probe
    # found ({{ size }} interpolated raw into class="...", exactly what
    # _stat_comparison.html emitted before this fix), reproduced here as
    # an inline template rather than by reverting the real file. If this
    # test cannot fail, the regression test after it proves nothing.
    payload = mark_safe('a" onclick="alert(1)')
    vulnerable_html = engines["django"].from_string('<div class="bw-x{{ size }}">').render({"size": payload})
    assert _event_handler_attrs(vulnerable_html) == [("div", "onclick")], (
        "the detector did not catch the known-vulnerable interpolation shape; "
        "the regression test below cannot be trusted"
    )


def test_size_attribute_injection_payload_cannot_open_a_live_event_handler() -> None:
    # Regression for the defect the coordinator's probe found: {{ size }}
    # interpolated directly into class="..." let a caller-supplied value
    # break out of the attribute and open a new one. The fix constrains
    # size against explicit {% if %}/{% elif %} literals rather than
    # escaping it, so an unrecognised value (mark_safe'd or not) never
    # reaches the attribute at all: the assertion below is real, not
    # vacuous, because test_the_detector_itself_catches_the_defect_the_
    # probe_found above proves the same payload/parser pair DOES catch
    # this exact shape when it is actually present.
    payload = mark_safe('a" onclick="alert(1)')
    out = _render(current="1", previous="1", size=payload)

    assert _event_handler_attrs(out) == [], "a live event-handler attribute was injected via size"

    # The closed set holds too: an unmatched size value renders no
    # modifier class at all (the constrain-not-escape fix), so the
    # payload neither opens a new attribute NOR appears as an unexpected
    # modifier or as text anywhere in the output.
    assert "bw-stat-comparison--" not in out
    assert "onclick" not in out
    assert "alert(1)" not in out


# --- the documented usage renders through the real template loader ----------


def test_documented_usage_renders() -> None:
    html = (
        engines["django"]
        .from_string(
            '{% include "brickwork/components/_stat_comparison.html" with '
            'label="Revenue" current="1,234" previous="987" '
            'period_label="vs last month" trend="up" trend_label="25% up" %}'
        )
        .render({})
    )
    assert "bw-stat-comparison" in html
    assert "Revenue" in html
    assert "1,234" in html
    assert "987" in html
    assert "vs last month" in html
    assert "25% up" in html
    assert get_icon("arrow-up") in html


# --- never raises: this is a plain {% include %}, no Python-side validation -


def test_missing_optional_context_never_raises() -> None:
    # No TemplateSyntaxError is expected anywhere in this component: unlike
    # bw_ranked_list or bw_gauge (tags with Python-side validation), this is
    # a structural include with the same "never raise on missing optional
    # context" contract _stat.html and _trend_indicator.html both carry.
    try:
        _render(current="1", previous="1")
    except TemplateSyntaxError:
        pytest.fail("_stat_comparison.html raised on minimal required context")
