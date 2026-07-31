"""Render tests for _filter_bar.html (#15).

The filter bar is structure only: an inline GET form of consumer fields rendered
through forms/_field.html, with a documented htmx swap contract and a no-JS
floor. These assert the no-JS form shape, the field rendering, the optional
htmx attributes, and the submit/clear actions.
"""

from __future__ import annotations

from django import forms
from django.template.loader import render_to_string


class _FilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[("", "Any"), ("active", "Active"), ("draft", "Draft")],
    )


def _render(**ctx) -> str:
    return render_to_string("brickwork/components/_filter_bar.html", ctx)


def _fields():
    form = _FilterForm()
    return [form["q"], form["status"]]


def test_is_a_get_form_no_js_floor() -> None:
    out = _render(fields=_fields())
    assert '<form class="bw-filter-bar"' in out
    assert 'method="get"' in out


def test_renders_each_field_through_the_field_partial() -> None:
    out = _render(fields=_fields())
    # both consumer fields are present, rendered via _field.html (bw-field class)
    assert out.count("bw-field") >= 2
    assert "Search" in out and "Status" in out


def test_submit_button_default_label() -> None:
    out = _render(fields=_fields())
    assert 'type="submit"' in out
    assert "Filter" in out


def test_custom_submit_label() -> None:
    out = _render(fields=_fields(), submit_label="Apply")
    assert "Apply" in out


def test_clear_link_only_when_href_given() -> None:
    assert "Clear" not in _render(fields=_fields())
    out = _render(fields=_fields(), clear_href="/gadgets/")
    assert 'href="/gadgets/"' in out
    assert "Clear" in out


def test_no_htmx_attributes_by_default() -> None:
    out = _render(fields=_fields())
    assert "hx-get" not in out
    assert "hx-target" not in out


def test_htmx_swap_contract_when_hx_get_given() -> None:
    out = _render(fields=_fields(), hx_get="/gadgets/filter/", hx_target="#gadgets")
    assert 'hx-get="/gadgets/filter/"' in out
    assert 'hx-target="#gadgets"' in out
    assert 'hx-trigger="submit"' in out
    # the no-JS floor is unchanged: still a GET form
    assert 'method="get"' in out
