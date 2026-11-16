"""{% bw_combobox %} contract tests (04-interfaces section 4b, 0.9.0).

One markup, progressively enhanced: the base (no-JS floor) control is a native
<select> built from the field's choices, and it STAYS the submitted form
control at all times; the enhanced field wrapper ships WITH the hidden
attribute and only bwCombobox's init swaps the two (the upgrade-at-init
doctrine run forwards again). Selection lives in the floor select, never in
Alpine state, so a 422 re-render rehydrates the component from the DOM
(BR-BW-HTMX-003; the end-to-end leg is in test_integration.py). Given a bound
field the tag renders inside the forms/_field.html chrome, inheriting its
label/help/error wiring. Render-time enforcement (field or the explicit
name/options/selected trio, options_url in the default server filter mode,
the filter_mode whitelist) raises TemplateSyntaxError exactly as bw_button
does.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django import forms
from django.template import engines
from django.template.exceptions import TemplateSyntaxError

from tests._class_contract import PENDING_BWUI_CSS_PIN, styled_bw_classes

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_COLOURS = [("red", "Red"), ("green", "Green"), ("blue", "Blue")]
_TAGS = [("alpha", "Alpha"), ("beta", "Beta")]


class _Form(forms.Form):
    colour = forms.ChoiceField(choices=_COLOURS, label="Colour", help_text="Pick one.")
    tags = forms.MultipleChoiceField(required=False, choices=_TAGS, label="Tags")


def _bound(data: dict | None = None) -> _Form:
    form = _Form(data=data) if data is not None else _Form()
    if data is not None:
        form.is_valid()
    return form


_TAG = '{% bw_combobox field=field options_url="/opts/colours/" %}'


def _render(src: str = _TAG, **ctx: object) -> str:
    ctx.setdefault("field", _bound()["colour"])
    return engines["django"].from_string("{% load brickwork_interactions %}" + src).render(ctx)


def _tag_of(html: str, marker: str) -> str:
    """The opening tag carrying ``marker``, for attribute assertions."""
    match = re.search(rf"<[a-z]+[^>]*{marker}[^>]*>", html)
    assert match, f"no tag carrying {marker!r} in output"
    return match.group(0)


def _bare_hidden(tag: str) -> bool:
    """Whether the tag carries the hidden ATTRIBUTE (not aria-hidden)."""
    return "hidden" in tag.replace("aria-hidden", "")


# --- the no-JS floor: the native select carries form state ---------------------


def test_floor_is_a_native_select_of_the_field_choices() -> None:
    html = _render()
    floor = _tag_of(html, "bw-combobox__floor")
    assert floor.startswith("<select")
    assert 'name="colour"' in floor
    for value, label in _COLOURS:
        assert f'value="{value}"' in html and label in html


def test_bound_selection_is_marked_on_the_floor() -> None:
    html = _render(field=_bound({"colour": "green"})["colour"])
    green = re.search(r'<option[^>]*value="green"[^>]*>', html)
    assert green and "selected" in green.group(0)


def test_multiple_mode_floor_is_a_select_multiple_with_selections() -> None:
    html = _render(
        '{% bw_combobox field=field multiple=True options_url="/opts/tags/" %}',
        field=_bound({"colour": "red", "tags": ["alpha", "beta"]})["tags"],
    )
    floor = _tag_of(html, "bw-combobox__floor")
    assert "multiple" in floor
    for value in ("alpha", "beta"):
        option = re.search(rf'<option[^>]*value="{value}"[^>]*>', html)
        assert option and "selected" in option.group(0)


def test_floor_is_the_only_unhidden_control_at_rest() -> None:
    # BR-BW-HTMX-001: with no JS running the native select is the whole
    # experience; the enhanced field wrapper ships hidden and only bwCombobox
    # reveals it at init (a dead enhanced control is worse than none).
    html = _render()
    assert not _bare_hidden(_tag_of(html, "bw-combobox__floor"))
    assert _bare_hidden(_tag_of(html, "bw-combobox__field"))


# --- component hooks and behaviour config --------------------------------------


def test_root_and_component_config_hooks() -> None:
    html = _render()
    assert "data-bw-combobox" in html
    assert "bwCombobox(" in html
    assert re.search(r"filterMode:\s*['\"]server['\"]", html)
    assert re.search(r"multiple:\s*false", html)
    assert re.search(r"allowCreate:\s*false", html)


def test_behaviour_flags_flow_into_the_component_config() -> None:
    html = _render(
        '{% bw_combobox field=field multiple=True allow_create=True options_url="/opts/tags/" %}',
        field=_bound()["tags"],
    )
    assert re.search(r"multiple:\s*true", html)
    assert re.search(r"allowCreate:\s*true", html)


def test_client_filter_mode_flows_into_the_component_config() -> None:
    html = _render('{% bw_combobox field=field filter_mode="client" %}')
    assert re.search(r"filterMode:\s*['\"]client['\"]", html)


# --- the enhanced field: APG combobox wiring ------------------------------------


def test_input_carries_the_apg_combobox_wiring() -> None:
    html = _render()
    field_input = _tag_of(html, "bw-combobox__input")
    assert 'role="combobox"' in field_input
    assert 'aria-autocomplete="list"' in field_input
    assert "aria-expanded" in field_input
    assert 'aria-controls="bw-listbox-id_colour"' in field_input


def test_listbox_follows_the_stable_id_convention() -> None:
    # BR-BW-HTMX-005: bw-listbox-<field id> is the documented swap target.
    listbox = _tag_of(_render(), "bw-combobox__listbox")
    assert 'role="listbox"' in listbox
    assert 'id="bw-listbox-id_colour"' in listbox


def test_client_mode_prerenders_the_option_list() -> None:
    # client mode filters in place, so every option must already be in the DOM
    html = _render('{% bw_combobox field=field filter_mode="client" %}')
    # the empty and failure rows are also role="option" (aria-disabled, below),
    # but they are messages, not choices
    options = [
        row
        for row in re.findall(r'<li[^>]*role="option"[^>]*>', html)
        if "bw-combobox__empty" not in row and "bw-combobox__error" not in row
    ]
    assert len(options) == 3
    for option in options:
        assert "data-bw-value=" in option
        assert 'id="' in option


def test_multiple_mode_ships_the_chip_machinery_with_accessible_removal() -> None:
    # CMP-028/CBH-020: selections render as chips whose remove control is an
    # icon-only button with an enforced aria-label (ICO-008, wired internally).
    html = _render(
        '{% bw_combobox field=field multiple=True options_url="/opts/tags/" %}',
        field=_bound({"colour": "red", "tags": ["alpha"]})["tags"],
    )
    assert "bw-combobox__chip" in html
    assert "aria-label" in _tag_of(html, "bw-combobox__chip-remove")
    assert "bw-combobox__chip" not in _render()


def test_empty_message_defaults_translated_and_overrides() -> None:
    html = _render()
    assert _tag_of(html, "bw-combobox__empty")
    assert "No matches" in html  # CMP-029: the package-supplied fallback
    custom = _render('{% bw_combobox field=field options_url="/o/" empty_message="Nothing here" %}')
    assert "Nothing here" in custom


def test_empty_and_failure_rows_are_disabled_options_so_the_listbox_is_never_childless() -> None:
    # axe aria-required-children: a visible listbox must own an option. When no
    # option matches (or a server request failed) the only visible row is the
    # message, so it is an aria-disabled option: announced, never chosen.
    client = _render('{% bw_combobox field=field filter_mode="client" %}')
    empty = _tag_of(client, "bw-combobox__empty")
    assert 'role="option"' in empty
    assert 'aria-disabled="true"' in empty
    server = _render('{% bw_combobox field=field options_url="/o/" %}')
    error = _tag_of(server, "data-bw-combobox-error")
    assert 'role="option"' in error
    assert 'aria-disabled="true"' in error


def test_placeholder_flows_to_the_enhanced_input() -> None:
    html = _render('{% bw_combobox field=field options_url="/o/" placeholder="Filter colours" %}')
    assert 'placeholder="Filter colours"' in _tag_of(html, "bw-combobox__input")


# --- field-chrome composition (forms/_field.html) -------------------------------


def test_renders_inside_the_field_chrome_with_error_wiring() -> None:
    # BR-BW-A11Y-002 by inheritance: the bound field renders through the field
    # renderer, so label, help, aria-describedby and the error container all
    # arrive without the combobox duplicating them.
    field = _bound({"colour": "", "tags": []})["colour"]
    html = _render(field=field)
    assert 'class="bw-field' in html
    assert "bw-field--invalid" in html
    assert re.search(r'<label[^>]*for="[^"]+"', html)
    assert "Colour" in html
    assert "Pick one." in html
    assert 'role="alert"' in html
    assert "This field is required." in html
    assert "id_colour_errors" in html  # the aria-describedby error id pairing


# --- htmx wiring: present in server mode, absent in client mode -----------------


def test_server_mode_carries_the_options_url_and_client_mode_does_not() -> None:
    # CBH-019/BR-BW-HTMX-008: the debounced server filter needs the consumer's
    # endpoint; client mode is a documented degradation that wires no htmx.
    assert "/opts/colours/" in _render()
    client = _render('{% bw_combobox field=field filter_mode="client" %}')
    assert "hx-get" not in client
    assert "hx-trigger" not in client


# --- render-time enforcement raises ---------------------------------------------


@pytest.mark.parametrize(
    "src",
    [
        # neither a field nor the explicit trio
        '{% bw_combobox options_url="/o/" %}',
        # server mode (the default) without options_url (CBH-019)
        "{% bw_combobox field=field %}",
        # filter_mode whitelist
        '{% bw_combobox field=field options_url="/o/" filter_mode="fuzzy" %}',
    ],
)
def test_invalid_arguments_raise(src: str) -> None:
    with pytest.raises(TemplateSyntaxError):
        _render(src)


def test_explicit_trio_renders_the_floor_without_a_form_field() -> None:
    html = _render(
        "{% bw_combobox name='colour' options=options selected='green' options_url='/o/' %}",
        options=_COLOURS,
    )
    floor = _tag_of(html, "bw-combobox__floor")
    assert 'name="colour"' in floor
    green = re.search(r'<option[^>]*value="green"[^>]*>', html)
    assert green and "selected" in green.group(0)


# --- the shipped JS bundle contract ----------------------------------------------


def test_bundle_registers_bwcombobox_with_documented_events() -> None:
    bundle = _DIST_JS.read_text()
    assert "bwCombobox" in bundle
    for event in ("bw:combobox:open", "bw:combobox:close", "bw:combobox:select", "bw:combobox:create"):
        assert event in bundle


# --- the raise (docs/components/combobox.md, CMB-019, 031, 050, 052) -----------


def test_multiple_mode_root_carries_the_frame_modifier_and_single_mode_does_not() -> None:
    # CMB-031: the modifier is what moves the frame from the input to the field
    # wrapper; single mode keeps the bare shared input frame (CMB-030).
    multiple = _render(
        '{% bw_combobox field=field multiple=True filter_mode="client" %}',
        field=_bound()["tags"],
    )
    assert 'class="bw-combobox bw-combobox--size-md bw-combobox--multiple"' in multiple
    assert "bw-combobox--multiple" not in _render()


def test_status_region_is_a_polite_live_region_with_template_supplied_strings() -> None:
    # CMB-052 and CMB-072: the strings are rendered here so no English
    # originates in script; {count} is the only token script fills in.
    html = _render()
    status = _tag_of(html, "data-bw-combobox-status")
    assert 'role="status"' in status
    assert 'aria-live="polite"' in status
    assert "bw-visually-hidden" in status
    assert 'data-bw-status-loading="Loading options"' in status
    assert 'data-bw-status-one="1 result available"' in status
    assert 'data-bw-status-other="{count} results available"' in status


def test_status_region_sits_inside_the_hidden_enhanced_wrapper() -> None:
    # The no-JS floor never exposes dead enhanced markup (BR-BW-HTMX-001).
    html = _render()
    assert html.index("bw-combobox__field") < html.index("bw-combobox__listbox") < html.index("data-bw-combobox-status")
    assert _bare_hidden(_tag_of(html, "bw-combobox__field"))


def test_server_mode_ships_a_hidden_translated_failure_row_and_client_mode_does_not() -> None:
    # CMB-019 / OQ-CMB-1: a failed server-filter request must be visible, so the
    # row exists up front; client mode makes no request and has nothing to fail.
    server = _render()
    error = _tag_of(server, "data-bw-combobox-error")
    assert _bare_hidden(error)
    assert "bw-combobox__error" in error
    assert "Options could not be loaded. Type to try again." in server
    assert "data-bw-combobox-error" not in _render('{% bw_combobox field=field filter_mode="client" %}')


def test_bundle_carries_the_raise_hooks() -> None:
    bundle = _DIST_JS.read_text()
    for hook in (
        "data-bw-combobox-status",
        "data-bw-combobox-error",
        "aria-busy",
        "htmx:beforeRequest",
        "htmx:afterRequest",
        "aria-labelledby",
    ):
        assert hook in bundle


def test_pending_pin_classes_expire_once_the_pin_styles_them() -> None:
    # The pending allowlist (tests/_class_contract.py) exists only until the
    # vendored @bwui/css carries these rules. When it does, drop the entry in
    # the pin-bump PR: a stale entry would silently exempt a class from the
    # "every emitted class is styled" contract.
    now_styled = sorted(PENDING_BWUI_CSS_PIN & styled_bw_classes())
    assert not now_styled, f"remove from PENDING_BWUI_CSS_PIN, the vendored CSS now styles: {now_styled}"


# --- the completion pass (docs/components/combobox.md, owner ruling 2026-11-16) ---
# Size, groups, clear, readonly, disabled, per-option disabled, aria_label,
# error_message and the multiple-mode announcements (icvoss/django-brickwork#742).


@pytest.mark.parametrize("step", ["xs", "sm", "md", "lg", "xl"])
def test_size_emits_the_size_class_for_every_step(step: str) -> None:
    # CMB-002 / AC-CMB-032: one class re-points the control role variables, so
    # the frame, chips, rows and text follow the step.
    html = _render('{% bw_combobox field=field options_url="/o/" size="' + step + '" %}')
    assert f"bw-combobox--size-{step}" in _tag_of(html, "data-bw-combobox")


def test_size_defaults_to_md_and_rejects_anything_else() -> None:
    assert "bw-combobox--size-md" in _render()
    for bad in ("huge", "2xl", ""):
        with pytest.raises(TemplateSyntaxError):
            _render('{% bw_combobox field=field options_url="/o/" size="' + bad + '" %}')


def test_clear_control_ships_hidden_with_a_translated_name() -> None:
    # CMB-015: hidden until bwCombobox finds a value or a query on an operable control.
    html = _render()
    clear = _tag_of(html, "bw-combobox__clear")
    assert _bare_hidden(clear)
    assert 'aria-label="Clear selection"' in clear
    assert "data-bw-combobox-clear" in clear
    assert clear.startswith("<button") and 'type="button"' in clear
    multiple = _render('{% bw_combobox field=field multiple=True options_url="/o/" %}', field=_bound()["tags"])
    assert 'aria-label="Clear all"' in _tag_of(multiple, "bw-combobox__clear")


def test_status_region_carries_the_multiple_mode_announcement_strings() -> None:
    # CMB-052 / AC-CMB-035: no English originates in script.
    status = _tag_of(_render(), "data-bw-combobox-status")
    assert 'data-bw-status-added="{label} added"' in status
    assert 'data-bw-status-removed="{label} removed"' in status
    assert 'data-bw-status-cleared="Selection cleared"' in status


def test_disabled_disables_the_floor_and_the_input_and_submits_nothing() -> None:
    html = _render('{% bw_combobox field=field options_url="/o/" disabled=True %}')
    assert re.search(r"\bdisabled\b", _tag_of(html, "bw-combobox__floor"))
    assert re.search(r"\bdisabled\b", _tag_of(html, "bw-combobox__input"))
    assert 'type="hidden"' not in html


def test_readonly_is_a_disabled_floor_plus_hidden_inputs_that_submit_the_value() -> None:
    # CMB-025: shown and submitted, not editable, with no JavaScript as well.
    html = _render(
        '{% bw_combobox field=field options_url="/o/" readonly=True %}',
        field=_bound({"colour": "green"})["colour"],
    )
    floor = _tag_of(html, "bw-combobox__floor")
    assert re.search(r"\bdisabled\b", floor)
    assert 'aria-readonly="true"' in floor
    field_input = _tag_of(html, "bw-combobox__input")
    assert re.search(r"\breadonly\b", field_input)
    assert 'aria-readonly="true"' in field_input
    hidden = re.findall(r'<input type="hidden"[^>]*>', html)
    assert hidden == ['<input type="hidden" name="colour" value="green">']


def test_readonly_multiple_submits_every_selected_value() -> None:
    html = _render(
        '{% bw_combobox field=field multiple=True readonly=True options_url="/o/" %}',
        field=_bound({"colour": "red", "tags": ["alpha", "beta"]})["tags"],
    )
    assert re.findall(r'<input type="hidden" name="tags" value="([^"]+)">', html) == ["alpha", "beta"]


def test_disabled_and_readonly_are_exclusive() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_combobox field=field options_url="/o/" disabled=True readonly=True %}')


def test_aria_label_names_the_input_when_given() -> None:
    html = _render(
        "{% bw_combobox name='colour' options=options filter_mode='client' aria_label='Colour' %}",
        options=_COLOURS,
    )
    assert 'aria-label="Colour"' in _tag_of(html, "bw-combobox__input")


def test_a_bound_field_with_no_label_and_no_aria_label_raises() -> None:
    class Unlabelled(forms.Form):
        colour = forms.ChoiceField(choices=_COLOURS, label=" ")

    field = Unlabelled()["colour"]
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_combobox field=field options_url="/o/" %}', field=field)
    ok = _render('{% bw_combobox field=field options_url="/o/" aria_label="Colour" %}', field=field)
    assert 'aria-label="Colour"' in _tag_of(ok, "bw-combobox__input")


def test_error_message_overrides_the_translated_failure_row() -> None:
    html = _render('{% bw_combobox field=field options_url="/o/" error_message="Try later" %}')
    assert "Try later" in _tag_of_with_text(html, "data-bw-combobox-error", "Try later")


def _tag_of_with_text(html: str, marker: str, text: str) -> str:
    match = re.search(rf"<li[^>]*{marker}[^>]*>{re.escape(text)}</li>", html)
    assert match, f"no row carrying {marker!r} and text {text!r}"
    return match.group(0)


def test_disabled_options_flag_the_row_and_the_floor_option() -> None:
    # CMB-016: aria-disabled on the listbox row, disabled on the floor option.
    html = _render('{% bw_combobox field=field filter_mode="client" disabled_options=locked %}', locked=["green"])
    row = re.search(r'<li[^>]*data-bw-value="green"[^>]*>', html)
    assert row and 'aria-disabled="true"' in row.group(0)
    floor_option = re.search(r'<option[^>]*value="green"[^>]*>', html)
    assert floor_option and "disabled" in floor_option.group(0)
    red = re.search(r'<li[^>]*data-bw-value="red"[^>]*>', html)
    assert red and "aria-disabled" not in red.group(0)


def test_options_mapping_may_carry_disabled_and_group() -> None:
    html = _render(
        "{% bw_combobox name='depot' options=options filter_mode='client' %}",
        options=[
            {"value": "a", "label": "Aberdeen", "group": "Scotland"},
            {"value": "d", "label": "Dundee", "group": "Scotland", "disabled": True},
            {"value": "b", "label": "Bristol", "group": "England"},
            {"value": "x", "label": "Elsewhere"},
        ],
    )
    assert len(re.findall(r'<li class="bw-combobox__group"', html)) == 2
    labels = re.findall(r'<span class="bw-combobox__group-label" id="([^"]+)">([^<]+)</span>', html)
    assert [text for _, text in labels] == ["Scotland", "England"]
    # Each group list is a role="group" named by its heading.
    for label_id, _ in labels:
        assert f'role="group" aria-labelledby="{label_id}"' in html
    dundee = re.search(r'<li[^>]*data-bw-value="d"[^>]*>', html)
    assert dundee and 'aria-disabled="true"' in dundee.group(0)
    # The ungrouped option renders outside any group, and the floor groups too.
    assert html.count("<optgroup") == 2
    assert "Elsewhere" in html


def test_a_bound_fields_optgroup_choices_render_as_groups() -> None:
    # CMB-017 / AC-CMB-033: grouped choices are no longer flattened.
    class Grouped(forms.Form):
        depot = forms.ChoiceField(
            choices=[("Scotland", [("a", "Aberdeen"), ("d", "Dundee")]), ("England", [("b", "Bristol")])],
            label="Depot",
        )

    html = _render('{% bw_combobox field=field filter_mode="client" %}', field=Grouped()["depot"])
    assert html.count('<optgroup label="') == 2
    assert 'label="Scotland"' in html and 'label="England"' in html
    assert len(re.findall(r'<li class="bw-combobox__group"', html)) == 2
    # Option ids stay unique and sequential across groups.
    ids = re.findall(r'<li class="bw-combobox__option"\s+id="([^"]+)"', html)
    assert ids == ["bw-listbox-id_depot-opt-0", "bw-listbox-id_depot-opt-1", "bw-listbox-id_depot-opt-2"]


def test_ungrouped_choices_render_no_group_wrappers() -> None:
    html = _render()
    assert "bw-combobox__group" not in html
    assert "<optgroup" not in html


def test_bundle_carries_the_completion_hooks() -> None:
    bundle = _DIST_JS.read_text()
    for hook in ("data-bw-combobox-clear", "bw-combobox__group", "bwStatusAdded", "bwStatusRemoved", "bwStatusCleared"):
        assert hook in bundle
