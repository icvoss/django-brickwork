"""Direct render tests for _scorecard.html (VIZ-011/012): the shared
dashboard grid arranging N pre-rendered cards.

Covers the empty/omitted-items no-render rule, the per-item span= closed
vocabulary (2/3/4, equal-by-default), the data-* passthrough seam
(bw_data_attrs), and CHT-026's own claim: the SAME grid genuinely composes
both a _stat.html tile and a _chart_card.html card with no chart-specific
branch of its own. That last point is proven by rendering real _stat.html
and _chart_card.html output through the seam, not by asserting on a
hand-written stand-in string that merely looks like one.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from django.template import engines
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_scorecard.html", ctx)


def _stat_markup(label: str = "Revenue", value: str = "1,234") -> str:
    return mark_safe(  # noqa: S308 (test-authored, brickwork's own component output)
        render_to_string("brickwork/components/_stat.html", {"label": label, "value": value})
    )


def _chart_card_markup(mount: str = "Chart placeholder") -> str:
    return mark_safe(  # noqa: S308 (test-authored, brickwork's own component output)
        render_to_string("brickwork/components/_chart_card.html", {"mount": mount})
    )


# --- the floor: no items, no render -----------------------------------------


def test_omitted_items_renders_nothing() -> None:
    out = _render()
    assert out.strip() == ""


def test_empty_items_list_renders_nothing() -> None:
    out = _render(items=[])
    assert out.strip() == ""


# --- the floor: one item arranges into the grid -----------------------------


def test_single_item_renders_the_grid_root_and_one_wrapped_item() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>")}])  # noqa: S308
    assert '<div class="bw-scorecard"' in out
    assert '<div class="bw-scorecard__item">' in out
    assert "<p>Card</p>" in out


def test_multiple_items_each_get_their_own_wrapper() -> None:
    out = _render(
        items=[
            {"content": mark_safe("<p>One</p>")},  # noqa: S308
            {"content": mark_safe("<p>Two</p>")},  # noqa: S308
            {"content": mark_safe("<p>Three</p>")},  # noqa: S308
        ]
    )
    assert out.count('<div class="bw-scorecard__item">') == 3
    assert "<p>One</p>" in out
    assert "<p>Two</p>" in out
    assert "<p>Three</p>" in out


def test_item_order_is_preserved() -> None:
    # The grid must not reorder items: rendered position in the output must
    # match the order supplied, so a caller's own KPI ordering survives.
    out = _render(
        items=[
            {"content": mark_safe("<p>First</p>")},  # noqa: S308
            {"content": mark_safe("<p>Second</p>")},  # noqa: S308
        ]
    )
    assert out.index("First") < out.index("Second")


# --- span= (VIZ-012): closed 2/3/4 vocabulary, equal by default -------------


def test_span_omitted_renders_no_modifier_class() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>")}])  # noqa: S308
    assert 'class="bw-scorecard__item"' in out
    assert "bw-scorecard__item--span" not in out


def test_span_two_renders_the_modifier_class() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": 2}])  # noqa: S308
    assert 'class="bw-scorecard__item bw-scorecard__item--span-2"' in out


def test_span_three_renders_the_modifier_class() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": 3}])  # noqa: S308
    assert "bw-scorecard__item--span-3" in out


def test_span_four_renders_the_modifier_class() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": 4}])  # noqa: S308
    assert "bw-scorecard__item--span-4" in out


def test_span_matches_both_the_int_and_the_numeric_string_form() -> None:
    # scorecard.columns tokens are bare numbers, but a caller assembling
    # items from a view's Python data and a caller writing a static
    # {% include %} with= call are equally realistic sources, one
    # naturally stringly-typed, one not: both "2" and 2 must resolve to
    # the same modifier class.
    for span in (2, "2"):
        out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": span}])  # noqa: S308
        assert "bw-scorecard__item--span-2" in out, f"span={span!r} did not match"


def test_mixed_spans_apply_only_to_the_item_that_set_them() -> None:
    # A fixture that could catch a span leaking onto the wrong item, or onto
    # every item: two items, only the SECOND (non-first) carries a span, so
    # a bug that applies the first item's state to every item is caught.
    out = _render(
        items=[
            {"content": mark_safe("<p>Equal</p>")},  # noqa: S308
            {"content": mark_safe("<p>Wide</p>"), "span": 3},  # noqa: S308
        ]
    )
    wrappers = re.findall(r'<div class="bw-scorecard__item[^"]*">', out)
    assert len(wrappers) == 2
    assert wrappers[0] == '<div class="bw-scorecard__item">'
    assert wrappers[1] == '<div class="bw-scorecard__item bw-scorecard__item--span-3">'


def test_span_zero_renders_no_modifier_class() -> None:
    # 0 matches none of the explicit == 2/3/4 literal branches (int or str
    # form), so it falls through to the bare class exactly like any other
    # unmatched value, matching _stat.html's own trend=False handling in
    # observable effect.
    out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": 0}])  # noqa: S308
    assert "bw-scorecard__item--span" not in out


def test_span_outside_the_closed_vocabulary_renders_no_modifier_class() -> None:
    # Constrain, not escape (ADR-084's stated option for an include-only
    # template with no Python assembly step): an unrecognised span value
    # matches none of the explicit == literal branches, so it is DISCARDED
    # rather than reaching the class attribute at all. The item renders as
    # an untagged (span-1) item with no trace of the unmatched value
    # anywhere in the output, the same silent no-match-no-render behaviour
    # _empty_state.html's own size ladder has.
    out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": 99}])  # noqa: S308
    assert "bw-scorecard__item--span-99" not in out
    assert "bw-scorecard__item--span" not in out
    assert "99" not in out


# --- span= attribute-injection regression (coordinator probe) ---------------
#
# {{ item.span }} interpolated raw into class="..." let a caller-supplied
# value break out of the attribute and open a new one. The fix constrains
# span against explicit {% if %}/{% elif %} == literals rather than
# escaping it, so an unrecognised value (mark_safe'd or not) never reaches
# the attribute at all.


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
    # Non-vacuity guard for the regression test below: proves the (payload,
    # parser, assertion) machinery actually CAN fail, by running it against
    # the literal vulnerable shape the coordinator's probe found
    # ({{ item.span }} interpolated raw into class="...", exactly what
    # _scorecard.html emitted before this fix), reproduced here as an
    # inline template rather than by reverting the real file. If this test
    # cannot fail, the regression test after it proves nothing.
    payload = mark_safe('a" onclick="alert(1)')
    vulnerable_html = engines["django"].from_string('<div class="bw-x{{ span }}">').render({"span": payload})
    assert _event_handler_attrs(vulnerable_html) == [("div", "onclick")], (
        "the detector did not catch the known-vulnerable interpolation shape; "
        "the regression test below cannot be trusted"
    )


def test_span_attribute_injection_payload_cannot_open_a_live_event_handler() -> None:
    # Regression for the defect the coordinator's probe found: {{ item.span }}
    # interpolated directly into class="..." let a caller-supplied value
    # break out of the attribute and open a new one. The assertion below is
    # real, not vacuous, because test_the_detector_itself_catches_the_
    # defect_the_probe_found above proves the same payload/parser pair DOES
    # catch this exact shape when it is actually present.
    payload = mark_safe('a" onclick="alert(1)')
    out = _render(items=[{"content": mark_safe("<p>Card</p>"), "span": payload}])  # noqa: S308

    assert _event_handler_attrs(out) == [], "a live event-handler attribute was injected via span"


# --- data attribute passthrough (bw_data_attrs) ------------------------------


def test_data_attrs_render_on_the_grid_root() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>")}], data={"data-testid": "kpi-grid"})  # noqa: S308
    assert 'class="bw-scorecard" data-testid="kpi-grid"' in out


def test_data_attrs_do_not_render_on_item_wrappers() -> None:
    # The data-* seam is documented as the GRID root's own seam, not
    # per-item: assert it did not leak onto an item wrapper.
    out = _render(items=[{"content": mark_safe("<p>Card</p>")}], data={"data-testid": "kpi-grid"})  # noqa: S308
    item_wrapper = re.search(r'<div class="bw-scorecard__item[^"]*"[^>]*>', out)
    assert item_wrapper is not None
    assert "data-testid" not in item_wrapper.group(0)


# --- CHT-026: the SAME grid genuinely composes both families ----------------


def test_composes_a_real_stat_tile_unchanged() -> None:
    # Proves the claim by rendering real _stat.html output through the seam,
    # not a hand-written stand-in that merely looks like a stat tile.
    stat_html = _stat_markup(label="Revenue", value="£48,290")
    out = _render(items=[{"content": stat_html}])
    assert 'class="bw-stat"' in out
    assert "£48,290" in out
    assert "Revenue" in out


def test_composes_a_real_chart_card_unchanged() -> None:
    chart_html = _chart_card_markup(mount="Line chart mount")
    out = _render(items=[{"content": chart_html}])
    assert 'class="bw-chart-card"' in out
    assert "Line chart mount" in out


def test_composes_a_stat_tile_and_a_chart_card_in_the_same_grid() -> None:
    # CHT-026's own claim, executed: one grid, two different card families,
    # no chart-specific branch, both present in the SAME render.
    out = _render(
        items=[
            {"content": _stat_markup(label="Active users", value="1,204")},
            {"content": _chart_card_markup(mount="Trend mount"), "span": 2},
        ]
    )
    assert 'class="bw-stat"' in out
    assert "Active users" in out
    assert 'class="bw-chart-card"' in out
    assert "Trend mount" in out
    assert "bw-scorecard__item--span-2" in out


# --- escaping: a plain (unmarked) content value is auto-escaped, never ------
# --- treated as trusted markup merely because this seam accepts safe -------
# --- strings elsewhere (mirrors _stat.html's own sparkline seam contract) --


def test_plain_string_content_is_auto_escaped_not_rendered_as_markup() -> None:
    # content is documented as a caller-marked-safe string; an ORDINARY
    # (unmarked) string passed by mistake must render exactly as any other
    # Django context variable would: auto-escaped, never live markup. This
    # is the correctness floor the sparkline/row.cells precedent relies on,
    # proven here rather than merely asserted in the docstring.
    out = _render(items=[{"content": "<script>steal()</script>"}])
    assert "<script>steal()</script>" not in out
    assert "&lt;script&gt;steal()&lt;/script&gt;" in out


def test_marked_safe_content_renders_verbatim() -> None:
    out = _render(items=[{"content": mark_safe("<strong>Trusted</strong>")}])  # noqa: S308
    assert "<strong>Trusted</strong>" in out


# --- root element shape ------------------------------------------------------


def test_grid_root_is_a_div() -> None:
    out = _render(items=[{"content": mark_safe("<p>Card</p>")}])  # noqa: S308
    assert out.lstrip().startswith('<div class="bw-scorecard"')
