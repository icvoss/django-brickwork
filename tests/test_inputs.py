"""Direct render tests for the 0.13.0 input chrome + sidebar collapse
(issues #57 and #58): toggle switch (BR-BW-INPUT-001, both the standalone
{% bw_toggle %} tag and the bw_field_widget opt-in), tag input
(BR-BW-INPUT-002), dropzone (BR-BW-INPUT-003), the date/time picker CSS
chrome, and the app shell's sidebar collapse toggle (SHL-003/004).

Toggle-tag and toggle-widget tests mirror test_components.py's/test_forms.py's
own _render helpers respectively; tag input and dropzone are plain
{% include %}-consumed partials, rendered directly via render_to_string like
test_feedback.py's progress tests; the sidebar collapse tests render the shell
template like test_shell.py.
"""

from __future__ import annotations

import re

import pytest
from django import forms
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

# --- toggle tag ({% bw_toggle %}) -------------------------------------------


def _render_toggle(snippet: str, **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(ctx))


def test_toggle_renders_a_checkbox_switch_with_id_name_label() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" name="email_alerts" %}')
    assert '<input class="bw-toggle bw-checkbox"' in out
    assert 'type="checkbox"' in out
    assert 'role="switch"' in out
    assert 'id="email-alerts"' in out
    assert 'name="email_alerts"' in out
    assert "Email alerts" in out


def test_toggle_name_defaults_to_id_when_omitted() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" %}')
    assert 'name="email-alerts"' in out


def test_toggle_checked_renders_checked_attribute() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" checked=True %}')
    assert "checked" in out


def test_toggle_unchecked_by_default() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" %}')
    assert "checked" not in out


def test_toggle_disabled_renders_disabled_attribute() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" disabled=True %}')
    assert "disabled" in out


def test_toggle_value_defaults_to_on() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" %}')
    assert 'value="on"' in out


def test_toggle_custom_value_is_reflected() -> None:
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" value="yes" %}')
    assert 'value="yes"' in out


def test_toggle_missing_label_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render_toggle('{% bw_toggle id="email-alerts" %}')


def test_toggle_empty_label_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render_toggle('{% bw_toggle "" id="email-alerts" %}')


@pytest.mark.parametrize("blank", ["   ", "\t", "\n", " \t\n "])
def test_toggle_whitespace_only_label_is_not_an_accessible_name(blank: str) -> None:
    # A whitespace-only label is truthy in Python, so the existing "not label"
    # check the docstring/error already claims to enforce did not actually
    # reject it before the strip-and-rebind fix. Calls the tag directly: a raw
    # newline inside {% bw_toggle "..." %} does not survive Django's parser.
    from brickwork.templatetags.brickwork_components import bw_toggle

    with pytest.raises(TemplateSyntaxError):
        bw_toggle(blank, id="email-alerts")


def test_toggle_padded_label_is_stripped_not_rejected() -> None:
    out = _render_toggle('{% bw_toggle "  Email alerts  " id="email-alerts" %}')
    assert re.search(r'class="bw-toggle-field__label">\s*Email alerts\s*</span>', out)
    assert "  Email alerts  " not in out


def test_toggle_non_str_label_via_ordinary_template_syntax_does_not_raise() -> None:
    # #330 regression: bw_toggle's label = label.strip() raised AttributeError
    # on any non-str value. {% bw_toggle n id='x' %} with an int context
    # variable is ordinary Django, not a contrived call; this is the exact
    # repro from the #330 report. Fails without the fix.
    out = _render_toggle('{% bw_toggle n id="email-alerts" %}', n=5)
    assert re.search(r'class="bw-toggle-field__label">\s*5\s*</span>', out)


def test_toggle_mark_safed_label_is_not_double_escaped() -> None:
    # #330 regression 2: label.strip() dropped __html__ from a caller-supplied
    # SafeString (format_html, a model property, or any pre-escaped-HTML
    # helper), so the template's own auto-escaping then escaped it a second
    # time. Fails without the fix: "Tom &amp; more" renders as
    # "Tom &amp;amp; more" instead of the correct single-escaped source.
    from django.utils.html import format_html

    label = format_html("Tom {} more", "&")
    out = _render_toggle('{% bw_toggle n id="email-alerts" %}', n=label)
    assert "Tom &amp; more" in out
    assert "&amp;amp;" not in out


def test_toggle_plain_ampersand_label_is_still_escaped() -> None:
    # #330 requirement 8, the trap: an ordinary never-safe string must still
    # be escaped as normal. Fails if the fix over-corrects into marking
    # every label safe (the #329 defect class).
    out = _render_toggle('{% bw_toggle "Tom & more" id="email-alerts" %}')
    assert "Tom &amp; more" in out


def test_toggle_mark_safe_bold_label_is_not_re_escaped() -> None:
    # #330 requirement 6: mark_safe's existing documented pass-through must
    # not regress into escaped text.
    from django.utils.safestring import mark_safe

    out = _render_toggle('{% bw_toggle n id="email-alerts" %}', n=mark_safe("<b>Email alerts</b>"))
    assert "<b>Email alerts</b>" in out


def test_toggle_gettext_lazy_label_still_works_and_is_stripped() -> None:
    # #330 requirement 7: gettext_lazy worked before the #327 strip was
    # added and must keep working.
    from django.utils.translation import gettext_lazy

    out = _render_toggle('{% bw_toggle n id="email-alerts" %}', n=gettext_lazy("  Email alerts  "))
    assert re.search(r'class="bw-toggle-field__label">\s*Email alerts\s*</span>', out)


def test_toggle_missing_id_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render_toggle('{% bw_toggle "Email alerts" %}')


def test_toggle_label_is_associated_via_wrapping_label_element() -> None:
    # the label wraps both the input and the visible text, an implicit
    # <label>...<input>...text</label> association (no for/id pairing needed,
    # but the wrapper itself must be a real <label>)
    out = _render_toggle('{% bw_toggle "Email alerts" id="email-alerts" %}')
    assert re.search(r'<label class="bw-toggle-field">\s*<input', out)
    assert re.search(r'class="bw-toggle-field__label">\s*Email alerts\s*</span>\s*</label>', out)


# --- toggle widget opt-in (bw_field_widget) ---------------------------------


class _ToggleForm(forms.Form):
    subscribed = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "bw-toggle"}))
    agree = forms.BooleanField(required=False)  # plain checkbox, no opt-in


def _render_field_widget(field, **kw) -> str:
    return Template("{% load brickwork_forms %}{% bw_field_widget field %}").render(Context({"field": field, **kw}))


def test_toggle_opted_in_checkbox_gets_role_switch_and_bw_toggle_class() -> None:
    out = _render_field_widget(_ToggleForm()["subscribed"])
    assert 'role="switch"' in out
    assert 'class="bw-toggle bw-checkbox"' in out


def test_plain_checkbox_does_not_get_role_switch() -> None:
    # regression guard: the opt-in is genuinely opt-in, not the new default
    # for every checkbox
    out = _render_field_widget(_ToggleForm()["agree"])
    assert "role=" not in out
    assert 'class="bw-checkbox"' in out
    assert "bw-toggle" not in out


# --- tag input ---------------------------------------------------------------


def _render_tag_input(**ctx: object) -> str:
    ctx.setdefault("label", "Tags")
    ctx.setdefault("id", "tags")
    ctx.setdefault("name", "tags")
    return render_to_string("brickwork/components/_tag_input.html", ctx)


def test_tag_input_floor_is_a_real_submittable_text_input() -> None:
    out = _render_tag_input()
    assert '<input class="bw-input bw-tag-input__floor"' in out
    assert 'type="text"' in out
    assert 'id="tags"' in out
    assert 'name="tags"' in out


def test_tag_input_multiline_renders_a_textarea_floor_instead() -> None:
    out = _render_tag_input(multiline=True)
    assert '<textarea class="bw-input bw-tag-input__floor"' in out
    assert 'id="tags"' in out
    assert 'name="tags"' in out
    assert "<input" not in out


def test_tag_input_prefilled_value_appears_in_the_floor_input() -> None:
    out = _render_tag_input(value="alpha,beta")
    assert 'value="alpha,beta"' in out


def test_tag_input_chip_container_is_present_for_alpine_to_enhance() -> None:
    out = _render_tag_input()
    assert re.search(r'<div class="bw-tag-input__chips"[^>]*data-bw-tag-input-chips', out)


def test_tag_input_wrapper_carries_the_alpine_hook() -> None:
    out = _render_tag_input()
    assert 'x-data="bwTagInput()"' in out
    assert "data-bw-tag-input" in out


def test_tag_input_is_labelled() -> None:
    out = _render_tag_input(label="Skill tags")
    assert re.search(r'<label class="bw-field__label" for="tags">\s*Skill tags\s*</label>', out)


def test_tag_input_errors_mark_input_aria_invalid_and_render_error_text() -> None:
    out = _render_tag_input(errors=["This field is required."])
    assert 'aria-invalid="true"' in out
    assert "This field is required." in out
    assert "bw-field--invalid" in out


# --- dropzone ------------------------------------------------------------


def _render_dropzone(**ctx: object) -> str:
    ctx.setdefault("label", "Upload files")
    ctx.setdefault("id", "upload")
    ctx.setdefault("name", "upload")
    return render_to_string("brickwork/components/_dropzone.html", ctx)


def test_dropzone_renders_a_native_file_input_not_replaced() -> None:
    out = _render_dropzone()
    assert re.search(r'<input class="bw-dropzone__input"\s+type="file"', out)
    assert 'id="upload"' in out
    assert 'name="upload"' in out


def test_dropzone_file_input_is_never_disabled_or_hidden_attribute() -> None:
    # visually-hidden (a CSS class) is fine; the HTML disabled/hidden
    # attributes, which would remove the control from the tab order or the
    # a11y tree, must never be present on the no-JS floor
    out = _render_dropzone()
    input_tag = re.search(r"<input[^>]*bw-dropzone__input[^>]*>", out).group(0)
    assert " disabled" not in input_tag
    assert " hidden" not in input_tag


def test_dropzone_file_input_sits_inside_a_labelled_label_element() -> None:
    out = _render_dropzone(label="Upload files")
    assert re.search(r'<label class="bw-dropzone"[^>]*for="upload"[\s\S]*?type="file"', out)
    assert "Upload files" in out


def test_dropzone_multiple_attribute_is_reflected() -> None:
    out = _render_dropzone(multiple=True)
    input_tag = re.search(r"<input[^>]*bw-dropzone__input[^>]*>", out).group(0)
    assert "multiple" in input_tag


def test_dropzone_multiple_omitted_by_default() -> None:
    out = _render_dropzone()
    input_tag = re.search(r"<input[^>]*bw-dropzone__input[^>]*>", out).group(0)
    assert "multiple" not in input_tag


def test_dropzone_accept_attribute_is_passed_through() -> None:
    out = _render_dropzone(accept="image/*")
    assert 'accept="image/*"' in out


def test_dropzone_alpine_hook_is_present() -> None:
    out = _render_dropzone()
    assert 'x-data="bwDropzone()"' in out
    assert "data-bw-dropzone" in out
    assert "data-bw-dropzone-input" in out


def test_dropzone_errors_mark_input_aria_invalid_and_render_error_text() -> None:
    out = _render_dropzone(errors=["A file is required."])
    input_tag = re.search(r"<input[^>]*bw-dropzone__input[^>]*>", out).group(0)
    assert 'aria-invalid="true"' in input_tag
    assert "A file is required." in out


# --- date/time chrome --------------------------------------------------------


class _DateTimeForm(forms.Form):
    starts_on = forms.DateField(widget=forms.DateInput)
    starts_at = forms.TimeField(widget=forms.TimeInput)
    starts_when = forms.DateTimeField(widget=forms.DateTimeInput)


@pytest.mark.parametrize("field_name", ["starts_on", "starts_at", "starts_when"])
def test_date_time_widgets_carry_bw_input_for_the_css_chrome(field_name: str) -> None:
    out = _render_field_widget(_DateTimeForm()[field_name])
    assert 'class="bw-input"' in out


# --- sidebar collapse (shell/app.html) --------------------------------------


def _render_shell(**ctx: object) -> str:
    return render_to_string("brickwork/shell/app.html", ctx)


def test_sidebar_has_the_stable_id_the_toggle_controls() -> None:
    html = _render_shell()
    assert re.search(r'<aside class="bw-sidebar" id="bw-sidebar"', html)


def test_sidebar_toggle_button_carries_aria_expanded_and_aria_controls() -> None:
    html = _render_shell()
    assert re.search(
        r'<button type="button"\s+class="[^"]*bw-sidebar__toggle[^"]*"\s+aria-expanded="true"\s+aria-controls="bw-sidebar"',
        html,
    )


def test_sidebar_toggle_carries_translated_collapse_and_expand_labels() -> None:
    html = _render_shell()
    assert 'aria-label="Collapse sidebar"' in html
    assert 'data-bw-sidebar-collapse-label="Collapse sidebar"' in html
    assert 'data-bw-sidebar-expand-label="Expand sidebar"' in html


def test_sidebar_toggle_carries_the_alpine_click_hook() -> None:
    html = _render_shell()
    assert "data-bw-sidebar-toggle" in html
    assert 'x-data="bwSidebarCollapse()"' in html


def test_sidebar_toggle_is_a_real_button_element() -> None:
    html = _render_shell()
    button = re.search(r"<button[^>]*bw-sidebar__toggle[^>]*>", html)
    assert button, "the sidebar toggle must be a real <button>, not a div/span"


def test_sidebar_collapsed_state_keeps_nav_labels_in_the_accessible_tree() -> None:
    # SHL-004: the collapsed CSS hook (.bw-sidebar[data-bw-collapsed]) clips
    # nav label text visually via the bw-visually-hidden clip technique; it
    # must NEVER be removed via aria-hidden or the hidden attribute, or a
    # screen reader user loses every nav item's name while collapsed. This is
    # a source-level guard on the shared clip rule (mirrors test_shell.py's
    # own source-scanning pattern), since the shell template itself renders
    # identically regardless of the (purely CSS/JS-driven) collapse state.
    import pathlib

    css_path = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "src" / "shell.css"
    css = css_path.read_text(encoding="utf-8")
    collapsed_block = re.search(r"\.bw-sidebar\[data-bw-collapsed\] \.bw-nav__label,[\s\S]*?\{([\s\S]*?)\}", css)
    assert collapsed_block, "expected a [data-bw-collapsed] .bw-nav__label rule in shell.css"
    rule_body = collapsed_block.group(1)
    assert "display: none" not in rule_body
    assert "visibility: hidden" not in rule_body
    assert "clip-path: inset(50%)" in rule_body


def test_no_aria_hidden_is_applied_to_collapsed_sidebar_nav_labels_in_markup() -> None:
    # the shell markup itself never stamps aria-hidden on nav labels; the
    # collapse behaviour is 100% CSS attribute-state, never a markup change
    html = _render_shell()
    assert "bw-nav__label" not in html or "aria-hidden" not in re.search(r"bw-sidebar__nav[\s\S]*?</nav>", html).group(
        0
    ).replace("bw-nav__label", "")


# --- token manifest (--bw-component-toggle-*) --------------------------------


def test_toggle_component_tokens_are_in_the_overridable_manifest() -> None:
    from brickwork.services.token_manifest import overridable_names

    names = overridable_names()
    assert "--bw-component-toggle-track-width" in names
    assert "--bw-component-toggle-track-height" in names
    assert "--bw-component-toggle-thumb-size" in names
    assert "--bw-component-toggle-thumb-inset" in names


def test_toggle_component_tokens_are_actually_emitted_in_tokens_css() -> None:
    import pathlib

    css = (
        pathlib.Path(__file__).resolve().parent.parent
        / "src"
        / "brickwork"
        / "static"
        / "brickwork"
        / "dist"
        / "tokens.css"
    ).read_text()
    for name in (
        "--bw-component-toggle-track-width",
        "--bw-component-toggle-track-height",
        "--bw-component-toggle-thumb-size",
        "--bw-component-toggle-thumb-inset",
    ):
        assert f"{name}:" in css
