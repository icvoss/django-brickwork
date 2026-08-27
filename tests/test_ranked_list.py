"""{% bw_ranked_list %} contract tests (icvoss/django-brickwork#183).

Covers geometry (basis="max"/"total", zero/negative-amount degradation),
the href/data/value row options, the empty and loading branches, and the
shared data-visualisation encoding contract (ADR-081): numeric meaning
survives with all colour/style stripped (COL-030), the bar is aria-hidden
and carries no text, the geometry is a unitless custom property, and no
per-row progressbar semantics leak in (VIZ-015). The contract assertions
themselves live in ``tests/_encoding_contract.py`` so the next family member
(sparkline, trend indicator, gauge/scorecard) is built against the same
mechanism rather than a fresh regex.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

from tests._encoding_contract import (
    assert_bar_is_aria_hidden_and_empty,
    assert_geometry_is_a_unitless_custom_property,
    assert_no_progressbar_semantics,
    assert_ordered_list_element_survives_stripping,
    assert_text_nodes_are_not_aria_hidden,
    assert_text_survives_colour_and_style_stripped,
)

_ROWS = [
    {"label": "Acme Corp", "amount": 400},
    {"label": "Globex", "amount": 300},
    {"label": "Initech", "amount": 100},
]


def _render(src: str = "{% bw_ranked_list rows=rows %}", **ctx: object) -> str:
    ctx.setdefault("rows", _ROWS)
    return engines["django"].from_string("{% load brickwork_components %}" + src).render(ctx)


# --- the floor: an <ol> of visible label + value text -----------------------


def test_floor_is_an_ordered_list_of_visible_label_and_value() -> None:
    out = _render()
    assert '<ol class="bw-ranked-list"' in out
    assert out.count("bw-ranked-list__row") == 3
    assert re.search(r'class="bw-ranked-list__label">Acme Corp', out)
    assert re.search(r'class="bw-ranked-list__value">400<', out)


def test_label_option_sets_the_aria_label() -> None:
    out = _render('{% bw_ranked_list rows=rows label="Top accounts" %}')
    assert 'aria-label="Top accounts"' in out


def test_label_omitted_renders_no_aria_label() -> None:
    out = _render()
    assert "aria-label" not in out


# --- basis geometry: computed in Python, closed vocabulary ------------------


def test_basis_max_scales_the_largest_row_to_full_width() -> None:
    out = _render('{% bw_ranked_list rows=rows basis="max" %}')
    assert "--bw-ranked-list-value: 100" in out  # 400/400
    assert "--bw-ranked-list-value: 75" in out  # 300/400
    assert "--bw-ranked-list-value: 25" in out  # 100/400


def test_basis_total_scales_rows_to_share_of_the_whole() -> None:
    out = _render('{% bw_ranked_list rows=rows basis="total" %}')
    assert "--bw-ranked-list-value: 50" in out  # 400/800
    assert "--bw-ranked-list-value: 38" in out  # 300/800, rounded
    assert "--bw-ranked-list-value: 12" in out  # 100/800, rounded


def test_basis_default_is_max() -> None:
    assert _render('{% bw_ranked_list rows=rows basis="max" %}') == _render()


def test_basis_rejects_anything_outside_the_closed_vocabulary() -> None:
    with pytest.raises(TemplateSyntaxError, match="basis"):
        _render('{% bw_ranked_list rows=rows basis="share" %}')


def test_zero_amount_degrades_to_a_zero_width_bar() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 400}, {"label": "New", "amount": 0}])
    assert "--bw-ranked-list-value: 0" in out
    assert "New" in out  # the label/value text still renders


def test_negative_amount_degrades_to_a_zero_width_bar() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 400}, {"label": "Refund", "amount": -50}])
    assert "Refund" in out
    # the negative row's own bar is zero-width; it must not go negative or
    # push another row's calc() out of the valid 0-100 range
    assert "-bw-ranked-list-value: -" not in out


def test_all_zero_amounts_never_raise_a_zero_division() -> None:
    out = _render(rows=[{"label": "A", "amount": 0}, {"label": "B", "amount": 0}])
    assert out.count("--bw-ranked-list-value: 0") == 2


def test_basis_total_rejects_mixed_signs() -> None:
    # basis="total" sums every amount for the denominator, so a negative row
    # can push the sum to zero or below even though another row is
    # genuinely positive; the old code then rendered EVERY row (including
    # the positive one) at a zero-width bar, silently discarding real data.
    # Share-of-total is undefined with mixed signs, so this is a render-time
    # error rather than a silently wrong bar.
    with pytest.raises(TemplateSyntaxError, match="basis"):
        _render(
            '{% bw_ranked_list rows=rows basis="total" %}',
            rows=[{"label": "P", "amount": 100}, {"label": "N", "amount": -200}],
        )


def test_basis_max_with_mixed_signs_still_renders_positives_proportionally() -> None:
    # basis="max" is unaffected by the basis="total" mixed-sign rule: the
    # denominator is max(), which a negative row is never the largest of
    # unless every amount is non-positive, so the positive row still gets
    # its real proportional width and the negative row degrades to zero.
    out = _render(
        '{% bw_ranked_list rows=rows basis="max" %}',
        rows=[{"label": "P", "amount": 100}, {"label": "N", "amount": -200}],
    )
    assert "--bw-ranked-list-value: 100" in out
    assert "--bw-ranked-list-value: 0" in out


# --- the optional per-row value/href/data -----------------------------------


def test_value_defaults_to_the_unformatted_amount() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 1234}])
    assert re.search(r'class="bw-ranked-list__value">1234', out)


def test_value_override_renders_the_caller_supplied_string() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 1234, "value": "£1,234.00"}])
    assert "£1,234.00" in out
    assert "1234.0" not in out


def test_href_renders_the_row_as_a_real_anchor() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 400, "href": "/accounts/acme/"}])
    assert re.search(r'<a class="bw-ranked-list__row" href="/accounts/acme/"', out)


def test_without_href_the_row_is_a_plain_div_never_a_fake_link() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 400}])
    assert "<a " not in out
    assert re.search(r'<div class="bw-ranked-list__row"', out)


def test_row_data_mapping_emits_escaped_consumer_owned_attributes() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 400, "data": {"data-account": "acme"}}])
    assert 'data-account="acme"' in out


def test_row_data_rejects_non_consumer_data_attributes() -> None:
    with pytest.raises(TemplateSyntaxError, match="ranked list row"):
        _render(rows=[{"label": "Acme", "amount": 400, "data": {"data-bw-x": "1"}}])


def test_component_level_data_mapping_lands_on_the_ol_root() -> None:
    out = _render("{% bw_ranked_list rows=rows data=data %}", data={"data-testid": "top-accounts"})
    assert re.search(r'<ol class="bw-ranked-list"[^>]*data-testid="top-accounts"', out)


# --- rows validation ---------------------------------------------------------


def test_row_missing_label_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="label"):
        _render(rows=[{"amount": 100}])


def test_row_missing_amount_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="amount"):
        _render(rows=[{"label": "Acme"}])


def test_row_non_numeric_amount_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="numeric"):
        _render(rows=[{"label": "Acme", "amount": "lots"}])


def test_row_that_is_not_a_mapping_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="mapping"):
        _render(rows=["Acme"])


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_row_non_finite_amount_raises(amount: float) -> None:
    # NaN and +/-Infinity pass float()/Decimal() conversion but are not a
    # position on the number line: an unfiltered database aggregate can
    # hand one to a consumer, and round() previously crashed on it with a
    # bare ValueError instead of this component's own friendly error.
    with pytest.raises(TemplateSyntaxError, match="finite"):
        _render(rows=[{"label": "Acme", "amount": 400}, {"label": "Bad", "amount": amount}])


def test_row_decimal_amount_below_float_precision_is_not_corrupted_to_zero() -> None:
    # Decimal("1e-1000") underflows to 0.0 through float(), which would
    # render a genuinely positive row as an identical zero-width bar to a
    # true zero amount. Computed in Decimal, it is honestly negligible
    # against a much larger row, not a corrupted false zero.
    out = _render(rows=[{"label": "Acme", "amount": 400}, {"label": "Tiny", "amount": Decimal("1e-1000")}])
    assert "--bw-ranked-list-value: 100" in out
    assert "--bw-ranked-list-value: 0" in out
    assert "Tiny" in out


def test_row_decimal_amount_above_float_range_does_not_crash() -> None:
    # Decimal("1e10000") overflows to inf through float(), which then hit
    # the same bare round() ValueError as defect 1. Decimal's own exponent
    # range comfortably represents it, so it renders rather than crashing.
    out = _render(rows=[{"label": "Acme", "amount": Decimal("1e10000")}])
    assert "--bw-ranked-list-value: 100" in out


def test_basis_is_validated_even_while_loading() -> None:
    # rows is ignored while loading=True, but basis is a contract violation
    # regardless of whether rows are being rendered this call: the docstring
    # previously claimed both were ignored while loading, which was already
    # false for basis before this fix.
    with pytest.raises(TemplateSyntaxError, match="basis"):
        _render('{% bw_ranked_list rows=rows loading=True basis="bogus" %}')


def test_rows_that_is_an_empty_mapping_raises_not_renders_empty_state() -> None:
    # {} is falsey, so it previously bypassed the list/tuple type check
    # entirely and fell through to the empty-state branch, while a
    # non-empty mapping correctly raised; the type check must not depend on
    # truthiness.
    with pytest.raises(TemplateSyntaxError, match="list/tuple"):
        _render(rows={})


def test_rows_none_still_renders_the_empty_state() -> None:
    out = _render('{% bw_ranked_list rows=rows empty_body="Nothing yet." %}', rows=None)
    assert "bw-empty-state" in out


# --- empty branch (VIZ-021, _empty_state.html at size="sm") -----------------


def test_empty_rows_composes_the_empty_state_at_size_sm() -> None:
    out = _render(
        '{% bw_ranked_list rows=rows empty_heading="No accounts" empty_body="Add one to see it here." %}',
        rows=[],
    )
    assert "bw-empty-state" in out
    assert "bw-empty-state--size-sm" in out
    assert "No accounts" in out
    assert "Add one to see it here." in out


def test_empty_rows_with_action_renders_the_action_link() -> None:
    out = _render(
        '{% bw_ranked_list rows=rows empty_body="Nothing yet." '
        'empty_action_href="/accounts/new/" empty_action_label="Add an account" %}',
        rows=[],
    )
    assert 'href="/accounts/new/"' in out
    assert "Add an account" in out


def test_empty_rows_without_action_renders_no_action_link() -> None:
    out = _render('{% bw_ranked_list rows=rows empty_body="Nothing yet." %}', rows=[])
    assert "bw-empty-state__action-link" not in out
    assert "bw-btn--primary" not in out


# --- loading branch (STA-004) ------------------------------------------------


def test_loading_shows_a_skeleton_and_ignores_rows() -> None:
    out = _render("{% bw_ranked_list rows=rows loading=True %}")
    assert "bw-skeleton" in out
    assert "Acme Corp" not in out
    assert "bw-empty-state" not in out


# --- encoding contract (ADR-081): shared with every viz family member ------


def test_label_and_value_text_survive_with_all_colour_and_style_stripped() -> None:
    out = _render()
    # the label assertions alone would still pass if the value span's text
    # were stripped entirely, since the bar itself carries no text of its
    # own to compensate; the numeric meaning must survive too (COL-030).
    # Scoped to the label/value spans' own text content, not a
    # whole-document scan: a row's href (e.g. "/accounts/400/") must not be
    # able to satisfy the "400" needle in place of the value span's text.
    assert_text_survives_colour_and_style_stripped(
        out,
        "Acme Corp",
        "Globex",
        "Initech",
        "400",
        "300",
        "100",
        text_classes=("bw-ranked-list__label", "bw-ranked-list__value"),
    )


def test_bar_is_aria_hidden_and_carries_no_visible_text_of_its_own() -> None:
    # a fixture of THREE rows, not one: a single-row fixture cannot tell
    # "every bar is aria-hidden" from "the only bar is aria-hidden", so it
    # cannot exercise the "every element" guarantee this helper claims. A
    # template that aria-hid only its first bar (e.g. `{% if forloop.first
    # %}`) would still pass a one-row check while leaving every other row's
    # geometry exposed to the accessibility tree.
    out = _render()
    assert_bar_is_aria_hidden_and_empty(out, bar_class="bw-ranked-list__bar", expected_count=3)


def test_no_progressbar_role_on_any_row() -> None:
    # VIZ-015: a ranked list is an N-way comparison, not one quantity's
    # progress toward a known target, so it deliberately carries no
    # progressbar semantics per row. _progress.html is the one component
    # that legitimately keeps full progressbar wiring; see the family
    # boundary test near the end of this file.
    out = _render()
    assert_no_progressbar_semantics(out)


def test_label_and_value_spans_are_never_aria_hidden_only_the_bar_is() -> None:
    # a regression that copied aria-hidden from the bar onto the text spans
    # would remove the one channel COL-030 depends on while still passing
    # the "bar is aria-hidden" check above; guard the text spans separately.
    # A fixture of THREE rows (six spans total), not one: see the "every
    # element" reasoning on the bar test above; the same vacuity applies
    # here identically.
    out = _render()
    assert_text_nodes_are_not_aria_hidden(
        out, text_classes=("bw-ranked-list__label", "bw-ranked-list__value"), expected_count=6
    )


def test_text_nodes_hidden_by_an_ancestor_row_are_caught() -> None:
    # rung 4a of the accessibility-tree ladder: aria-hidden="true" on the
    # ROW WRAPPER, not on the label/value spans themselves and not nested
    # inside them, removes both spans from the accessibility tree just as
    # completely while their own tags and subtrees stay entirely clean. The
    # earlier nested-child fix (rung 3) only ever looked INWARD from the
    # text element; this looks OUTWARD at its ancestors, which no prior
    # check did.
    #
    # Mutated on the SECOND row's wrapper, not the first (icvoss/
    # django-brickwork#286): a violation on the first of several matching
    # elements is indistinguishable from a check that only ever looked at
    # the first element in the first place, since a naive re.search would
    # still find a clean, unhidden row afterwards and could report that as
    # "found one, therefore the property holds" if a helper were ever
    # careless about scanning every match. Globex is the second row, and
    # every row wrapper's own opening tag is identical text (no
    # distinguishing attribute), so a plain ``str.replace(..., 1)`` always
    # mutates the FIRST occurrence (Acme), never the second, silently
    # asserting the property against the wrong, still-clean row: split on
    # the marker to target the second occurrence specifically.
    out = _render()
    before, marker, after = out.partition('<div class="bw-ranked-list__row">')
    before2, marker2, after2 = after.partition('<div class="bw-ranked-list__row">')
    mutated = before + marker + before2 + '<div class="bw-ranked-list__row" aria-hidden="true">' + after2
    assert mutated != out, "the row-wrapper mutation did not change the rendered html: fixture assumption is stale"
    with pytest.raises(AssertionError):
        assert_text_nodes_are_not_aria_hidden(
            mutated, text_classes=("bw-ranked-list__label", "bw-ranked-list__value"), expected_count=6
        )
    with pytest.raises(AssertionError):
        assert_text_survives_colour_and_style_stripped(
            mutated,
            "Globex",
            "300",
            text_classes=("bw-ranked-list__label", "bw-ranked-list__value"),
        )


def test_text_nodes_hidden_by_the_component_root_are_caught() -> None:
    # rung 4b: aria-hidden="true" on the component's OWN <ol> root hides
    # every row beneath it at once. Necessarily a single-element mutation
    # (there is only one list root to hide), unlike rung 4a above where the
    # violation is planted on a non-first element among several; that
    # asymmetry is inherent to "the root" being singular, not a gap in this
    # test.
    out = _render()
    mutated = out.replace('<ol class="bw-ranked-list">', '<ol class="bw-ranked-list" aria-hidden="true">', 1)
    assert mutated != out, "the root mutation did not change the rendered html: fixture assumption is stale"
    with pytest.raises(AssertionError):
        assert_text_nodes_are_not_aria_hidden(
            mutated, text_classes=("bw-ranked-list__label", "bw-ranked-list__value"), expected_count=6
        )
    with pytest.raises(AssertionError):
        assert_text_survives_colour_and_style_stripped(
            mutated,
            "Acme Corp",
            "400",
            text_classes=("bw-ranked-list__label", "bw-ranked-list__value"),
        )


def test_aria_hidden_false_on_an_ancestor_does_not_count_as_hiding() -> None:
    # aria-hidden="false" is a real, legal ARIA value meaning "not hidden",
    # not a synonym for the attribute's absence; a range-builder keyed on
    # the mere presence of the attribute name rather than its value would
    # wrongly treat this row as hidden and fail a genuinely conformant
    # render. str.replace(..., 1) mutates the FIRST occurrence, Acme's row,
    # so the assertions below check Acme/400, the row actually mutated, not
    # a row this call never touched.
    out = _render()
    mutated = out.replace(
        '<div class="bw-ranked-list__row">', '<div class="bw-ranked-list__row" aria-hidden="false">', 1
    )
    assert mutated != out, "the row-wrapper mutation did not change the rendered html: fixture assumption is stale"
    assert_text_nodes_are_not_aria_hidden(
        mutated, text_classes=("bw-ranked-list__label", "bw-ranked-list__value"), expected_count=6
    )
    assert_text_survives_colour_and_style_stripped(
        mutated,
        "Acme Corp",
        "400",
        text_classes=("bw-ranked-list__label", "bw-ranked-list__value"),
    )


def test_geometry_is_a_unitless_custom_property_not_a_width_or_percent_string() -> None:
    # the bar's CSS turns this bare number into a length with its own
    # calc(); a template regression that emitted "75%" or "width: 75%"
    # directly would bypass that seam and hardcode layout server-side.
    # Scoped to the bar element's own style attribute: an unrelated
    # max-width/width on a page wrapper elsewhere must not fail this.
    out = _render()
    assert_geometry_is_a_unitless_custom_property(
        out, property_name="--bw-ranked-list-value", geometry_class="bw-ranked-list__bar"
    )


def test_ol_ordering_survives_with_all_colour_and_style_stripped() -> None:
    # rank order is itself meaning (position 1 outranks position 2); a
    # regression that demoted the <ol> to a <div> or <ul> would discard that
    # meaning while every label/value string still passed the text checks
    # above, so the element itself is checked, not just its text content.
    out = _render()
    assert_ordered_list_element_survives_stripping(out, list_class="bw-ranked-list")


# --- boundary: _progress.html legitimately keeps the role ------------------


def test_progress_keeps_full_progressbar_semantics_outside_the_ranked_group() -> None:
    # VIZ-015 scopes the "no progressbar" rule to the ranked/N-way
    # comparison family, not a blanket ban across the package:
    # _progress.html is the ONE component built for a single quantity's
    # progress toward a known target, so it must go on carrying the full
    # role/aria-valuenow/-valuemin/-valuemax wiring. The ARIA values
    # themselves are already pinned by
    # test_feedback.py::test_determinate_progress_has_full_aria_wiring, so
    # this test does not re-assert those attributes (that would be a
    # duplicate assertion on the same render, drifting into two slightly
    # different opinions about the same wiring). Instead it encodes the
    # boundary distinction using the group's own contract: the family's "no
    # progressbar semantics" helper must actively RAISE against
    # _progress.html's output, proving this component is deliberately
    # outside the group rather than merely untested by it.
    out = render_to_string("brickwork/components/_progress.html", {"label": "Import progress", "value": 42})
    with pytest.raises(AssertionError):
        assert_no_progressbar_semantics(out)
