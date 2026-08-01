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
    options = re.findall(r'<li[^>]*role="option"[^>]*>', html)
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
