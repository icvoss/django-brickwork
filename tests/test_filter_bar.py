"""Render tests for _filter_bar.html (#15).

The filter bar is structure only: an inline GET form of consumer fields rendered
through forms/_field.html, with a documented htmx swap contract and a no-JS
floor. These assert the no-JS form shape, the field rendering, the optional
htmx attributes, and the submit/clear actions.
"""

from __future__ import annotations

from pathlib import Path

from django import forms
from django.template.loader import render_to_string

_ROOT = Path(__file__).resolve().parent.parent
_COMPILED_CSS = (_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css").read_text(
    encoding="utf-8"
)

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


def test_filter_actions_align_to_the_plain_field_control_edge() -> None:
    """Filter context replaces the generic field tail with its own flex gap.

    A bare ``align-items: flex-end`` aligns a button with the field wrapper's
    empty-error/margin tail, not the visible input. Keeping both contextual
    rules in the compiled asset catches a source-only CSS fix that a wheel
    would not ship.
    """
    css = _COMPILED_CSS.replace(" ", "").replace("\n", "")
    assert ".bw-filter-bar__fields.bw-field{margin-block-end:0}" in css
    assert ".bw-filter-bar__actions{margin-block-end:var(--bw-space-1)}" in css


def test_filter_field_error_container_and_widget_wiring_survive_alignment() -> None:
    form = _FilterForm(data={"status": "active"})
    assert form.is_valid()
    form.add_error("q", "Search needs a term.")

    out = _render(fields=[form["q"]])

    assert 'aria-describedby="id_q_errors"' in out
    assert 'id="id_q_errors" role="alert"' in out
    assert "Search needs a term." in out


def test_beautiful_default_filter_bar_has_fg_mix_edge_and_ambient() -> None:
    # Mirror test_card.test_beautiful_default_bare_card_*: control deck reads
    # on white with the same fg-mix hairline and soft ambient under elev-1.
    import re

    css = (_ROOT / "frontend" / "src" / "components.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules = [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]
    bodies = [body for sel, body in rules if sel.strip() == ".bw-filter-bar"]
    assert bodies, "missing .bw-filter-bar rule"
    body = bodies[0]
    assert "color-mix(in oklab, var(--bw-color-fg)" in body
    assert "var(--bw-elevation-1)" in body
    assert "0 4px 14px -4px" in body
    assert "inset 0 1px 0 0" not in body
    # Built bundle carries the ambient (package product, not only source).
    assert "0 4px 14px -4px" in _COMPILED_CSS
    assert ".bw-filter-bar{" in _COMPILED_CSS.replace(" ", "")
