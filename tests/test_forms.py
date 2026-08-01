"""Direct unit tests for the form helpers + the field-renderer tag.

Uses a small inline form (no testapp needed) to exercise bw_field_widget's aria
wiring, the readonly path, render_field_errors, and the _field.html partial's
error/help rendering, all in the default settings leg.
"""

from __future__ import annotations

from django import forms
from django.template import Context, Template
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
