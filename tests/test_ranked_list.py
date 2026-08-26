"""{% bw_ranked_list %} contract tests (icvoss/django-brickwork#183).

Covers geometry (basis="max"/"total", zero/negative-amount degradation),
the href/data/value row options, the empty and loading branches, and
COL-030 (numeric meaning survives with all colour/style stripped, since the
bar is aria-hidden and the label/value text is the sole accessible channel).
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError

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


# --- COL-030: numeric meaning survives with colour/style stripped -----------


def test_label_and_value_text_survive_with_all_colour_and_style_stripped() -> None:
    out = _render()
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "Acme Corp" in stripped
    assert "Globex" in stripped
    assert "Initech" in stripped
    # the label assertions above would still pass if the value span's text
    # were stripped entirely, since the bar itself carries no text of its
    # own to compensate; the numeric meaning must survive too (COL-030).
    assert "400" in stripped
    assert "300" in stripped
    assert "100" in stripped


def test_bar_is_aria_hidden_and_carries_no_visible_text_of_its_own() -> None:
    out = _render(rows=[{"label": "Acme", "amount": 400}])
    bar_match = re.search(r'<span class="bw-ranked-list__bar"[^>]*></span>', out)
    assert bar_match is not None
    assert 'aria-hidden="true"' in bar_match.group(0)


def test_no_progressbar_role_on_any_row() -> None:
    # VIZ-015: a ranked list is an N-way comparison, not one quantity's
    # progress toward a known target, so it deliberately carries no
    # role="progressbar" per row (unlike _progress.html).
    out = _render()
    assert 'role="progressbar"' not in out
