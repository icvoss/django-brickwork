"""Direct unit tests for the form helpers + the field-renderer tag.

Uses a small inline form (no testapp needed) to exercise bw_field_widget's aria
wiring, the readonly path, render_field_errors, and the _field.html partial's
error/help rendering, all in the default settings leg.
"""

from __future__ import annotations

import pytest
from django import forms
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

from brickwork.services.forms import (
    field_error_id,
    is_htmx_validation_request,
    render_field_errors,
)


class _Form(forms.Form):
    name = forms.CharField(help_text="Your full name")
    age = forms.IntegerField(required=False)

    def clean_name(self):
        value = self.cleaned_data["name"]
        if value == "bad":
            raise forms.ValidationError("That name is not allowed.")
        return value


def _bound(data=None):
    form = _Form(data=data) if data is not None else _Form()
    if data is not None:
        form.is_valid()
    return form


# --- bw_field_widget aria wiring ------------------------------------------


def _render_widget(field, **kw) -> str:
    return Template("{% load brickwork_forms %}{% bw_field_widget field %}").render(Context({"field": field, **kw}))


def test_valid_field_widget_has_no_aria_invalid() -> None:
    field = _bound()["name"]
    out = _render_widget(field)
    assert "aria-invalid" not in out
    # help text is described-by even when valid
    assert "aria-describedby" in out and f"{field.auto_id}_help" in out


def test_errored_field_widget_is_aria_invalid_and_describes_errors() -> None:
    field = _bound({"name": "bad"})["name"]
    out = _render_widget(field)
    assert 'aria-invalid="true"' in out
    assert f"{field.auto_id}_errors" in out


def test_readonly_widget_sets_readonly_attr() -> None:
    field = _bound()["name"]
    out = Template("{% load brickwork_forms %}{% bw_field_widget field readonly=True %}").render(
        Context({"field": field})
    )
    assert "readonly" in out


# --- bw_field_widget class stamping -----------------------------------------


class _ZooForm(forms.Form):
    """One field per widget family, to pin the class-stamping matrix."""

    name = forms.CharField()
    subscribed = forms.BooleanField(required=False, help_text="Tick to subscribe")
    colour = forms.ChoiceField(choices=[("r", "Red"), ("g", "Green")], widget=forms.RadioSelect)
    tags = forms.MultipleChoiceField(
        required=False,
        choices=[("a", "Alpha"), ("b", "Beta")],
        widget=forms.CheckboxSelectMultiple,
    )
    status = forms.ChoiceField(choices=[("d", "Draft"), ("p", "Published")])


def test_checkbox_widget_gets_bw_checkbox_not_bw_input() -> None:
    out = _render_widget(_ZooForm()["subscribed"])
    assert 'class="bw-checkbox"' in out
    assert "bw-input" not in out


def test_checkbox_widget_keeps_aria_describedby_for_help_text() -> None:
    field = _ZooForm()["subscribed"]
    out = _render_widget(field)
    assert f'aria-describedby="{field.auto_id}_help"' in out


def test_text_input_keeps_bw_input() -> None:
    out = _render_widget(_ZooForm()["name"])
    assert 'class="bw-input"' in out


def test_select_keeps_bw_input() -> None:
    out = _render_widget(_ZooForm()["status"])
    assert 'class="bw-input"' in out
    assert "bw-checkbox" not in out and "bw-radio" not in out


def test_radio_select_stamps_bw_radio_on_every_option() -> None:
    out = _render_widget(_ZooForm()["colour"])
    # the group wrapper div inherits the as_widget attrs, and every option
    # input inherits them too (option_inherits_attrs): wrapper + 2 options
    assert out.count('type="radio"') == 2
    assert out.count('class="bw-radio"') == 3
    assert "bw-input" not in out


def test_checkbox_select_multiple_stamps_bw_checkbox_on_every_option() -> None:
    out = _render_widget(_ZooForm()["tags"])
    assert out.count('type="checkbox"') == 2
    assert out.count('class="bw-checkbox"') == 3  # group wrapper + 2 options
    assert "bw-input" not in out and "bw-radio" not in out


# --- _field.html partial ---------------------------------------------------


def test_field_partial_renders_label_help_and_error_container() -> None:
    field = _bound({"name": "bad"})["name"]
    html = render_to_string("brickwork/forms/_field.html", {"field": field})
    assert "Your full name" in html  # help text
    assert 'role="alert"' in html  # error container announces
    assert "not allowed" in html  # the error message
    assert "bw-field--invalid" in html


def test_field_partial_valid_has_no_invalid_class() -> None:
    field = _bound()["name"]
    html = render_to_string("brickwork/forms/_field.html", {"field": field})
    assert "bw-field--invalid" not in html


# --- service helpers -------------------------------------------------------


def test_render_field_errors_returns_messages() -> None:
    field = _bound({"name": "bad"})["name"]
    assert render_field_errors(field) == ["That name is not allowed."]


def test_render_field_errors_empty_when_valid() -> None:
    field = _bound()["name"]
    assert render_field_errors(field) == []


def test_field_error_id_convention() -> None:
    field = _bound()["name"]
    assert field_error_id(field) == f"{field.auto_id}_errors"


class _Req:
    def __init__(self, htmx=None, header=None):
        self.headers = {"HX-Request": "true"} if header else {}
        if htmx is not None:
            self.htmx = htmx


def test_is_htmx_validation_request_header_and_duck_type() -> None:
    assert is_htmx_validation_request(_Req(header=True))
    assert is_htmx_validation_request(_Req(htmx=True))
    assert not is_htmx_validation_request(_Req())


# --- whole-form renderer ({% bw_form %} / forms/_form.html, brickwork#53) --


class _ContactForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()
    reference = forms.CharField(widget=forms.HiddenInput, initial="ref-123")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("first_name") == "bad":
            raise forms.ValidationError("Something went wrong with your submission.")
        return cleaned


def _render_bw_form(form, **kwargs) -> str:
    # pass every kwarg through the context (as ctx_<name>) rather than
    # inlining Python literals into the template source, so a rows= list of
    # lists (not expressible as a bare template literal) works the same as
    # a plain string/int kwarg.
    ctx = {"form": form}
    parts = []
    for key, value in kwargs.items():
        ctx_key = f"ctx_{key}"
        ctx[ctx_key] = value
        parts.append(f"{key}={ctx_key}")
    source = f"{{% load brickwork_forms %}}{{% bw_form form {' '.join(parts)} %}}"
    return Template(source).render(Context(ctx))


def test_bw_form_renders_every_visible_field_through_field_chrome() -> None:
    form = _ContactForm()
    out = _render_bw_form(form)
    for name in ("first_name", "last_name", "email"):
        auto_id = f"id_{name}"
        assert f'id="{auto_id}"' in out
        assert f'id="{auto_id}_errors"' in out  # the _field.html error container


def test_bw_form_never_emits_a_form_element() -> None:
    form = _ContactForm()
    out = _render_bw_form(form)
    assert "<form" not in out
    assert "</form>" not in out


def test_bw_form_renders_non_field_errors() -> None:
    form = _ContactForm(data={"first_name": "bad", "last_name": "Smith", "email": "a@example.com"})
    form.is_valid()
    out = _render_bw_form(form)
    assert "bw-form-errors" in out
    assert "Something went wrong with your submission." in out


def test_bw_form_renders_hidden_fields_unwrapped() -> None:
    form = _ContactForm()
    out = _render_bw_form(form)
    assert 'type="hidden"' in out
    assert 'name="reference"' in out
    # a hidden field is not wrapped in the field chrome (no bw-field div for it)
    assert 'id="id_reference_errors"' not in out


def test_bw_form_layout_grid_applies_the_grid_class() -> None:
    form = _ContactForm()
    out = _render_bw_form(form, layout="grid", grid_columns=2)
    assert "bw-form-fields--grid" in out
    assert "--bw-form-grid-columns: 2" in out


def test_bw_form_layout_stacked_is_the_default() -> None:
    form = _ContactForm()
    out = _render_bw_form(form)
    assert "bw-form-fields--stacked" in out
    assert "--bw-form-grid-columns" not in out


def test_bw_form_invalid_layout_raises() -> None:
    form = _ContactForm()
    with pytest.raises(TemplateSyntaxError):
        _render_bw_form(form, layout="columns")


def test_bw_form_invalid_grid_columns_raises() -> None:
    form = _ContactForm()
    with pytest.raises(TemplateSyntaxError):
        _render_bw_form(form, layout="grid", grid_columns=0)


def test_bw_form_rows_groups_named_fields_on_one_row() -> None:
    form = _ContactForm()
    out = _render_bw_form(form, rows=[["first_name", "last_name"]])
    # both grouped fields render inside the SAME grouped row wrapper, in order
    first_idx = out.index('id="id_first_name"')
    last_idx = out.index('id="id_last_name"')
    grouped_marker_idx = out.rindex("bw-field-row--grouped", 0, first_idx)
    email_idx = out.index('id="id_email"')
    assert grouped_marker_idx < first_idx < last_idx < email_idx
    assert out.count("bw-field-row--grouped") == 1


def test_bw_form_field_absent_from_rows_falls_back_stacked() -> None:
    # email is not named in rows=, so it must still render, on its own row
    form = _ContactForm()
    out = _render_bw_form(form, rows=[["first_name", "last_name"]])
    assert 'id="id_email"' in out


def test_bw_form_rows_dom_order_follows_grouping_order() -> None:
    # email grouped ahead of first_name/last_name: the grouped row renders at
    # its first-named member's original form position (email is 3rd in form
    # order, so the ungrouped first_name/last_name still precede it)
    form = _ContactForm()
    out = _render_bw_form(form, rows=[["email", "last_name"]])
    email_idx = out.index('id="id_email"')
    last_name_idx = out.index('id="id_last_name"')
    first_name_idx = out.index('id="id_first_name"')
    # first_name is ungrouped and sits before the group's anchor (email, form
    # position 3rd); the group itself keeps email before last_name (group order)
    assert first_name_idx < email_idx < last_name_idx


def test_bw_form_default_no_rows_is_one_field_per_row() -> None:
    form = _ContactForm()
    out = _render_bw_form(form)
    assert "bw-field-row--grouped" not in out


# --- 422 preservation via bw_form ------------------------------------------


def test_bw_form_bound_invalid_preserves_aria_describedby_wiring() -> None:
    form = _ContactForm(data={"first_name": "", "last_name": "Smith", "email": "not-an-email"})
    form.is_valid()
    out = _render_bw_form(form)
    for name in ("first_name", "email"):
        auto_id = f"id_{name}"
        error_id = f"{auto_id}_errors"
        assert f'aria-describedby="{error_id}"' in out
        assert f'id="{error_id}"' in out
        assert 'role="alert"' in out
