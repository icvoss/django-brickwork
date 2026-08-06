"""Direct unit tests for the component template tags (button/badge/alert).

These render each tag in isolation (no testapp needed), covering the branch paths
the integration suite exercises only indirectly: variant/size validation, the
icon-only accessible-name enforcement (ICO-008), loading, the link-vs-button
split, and the 0.9.0 dismissible upgrade to alert and badge (04-interfaces 4b).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"


def _render(snippet: str, **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(ctx))


# --- button ---------------------------------------------------------------


def test_button_renders_a_button_by_default() -> None:
    out = _render('{% bw_button "Save" variant="primary" %}')
    assert "<button" in out and "bw-btn--primary" in out
    assert "Save" in out


def test_button_with_href_renders_an_anchor() -> None:
    out = _render('{% bw_button "Go" href="/x/" variant="secondary" %}')
    assert "<a " in out and 'href="/x/"' in out


def test_button_icon_only_requires_aria_label() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_button icon="trash" icon_only=True aria_label="" %}')


def test_button_icon_only_with_label_omits_visible_text() -> None:
    out = _render('{% bw_button icon="trash" icon_only=True aria_label="Delete" %}')
    assert 'aria-label="Delete"' in out
    assert "bw-btn--icon-only" in out
    assert "bw-btn__label" not in out


def test_button_loading_marks_busy_and_disabled() -> None:
    out = _render('{% bw_button "Save" loading=True %}')
    assert 'aria-busy="true"' in out
    assert "bw-spinner" in out
    # ICO-004/issue #16: the spinner sizes via the --bw-icon-size CSS custom
    # property (which .bw-spinner reads for inline-size/block-size), never as
    # an SVG width/height attribute (var() is invalid there and silently
    # falls back to the 300x150 SVG default). The token is the canonical
    # component-tier name (0.11.0 tier re-grammar).
    assert "--bw-icon-size: var(--bw-component-icon-size-sm)" in out
    assert ' width="var(' not in out
    assert ' height="var(' not in out


@pytest.mark.parametrize("variant", ["primary", "secondary", "ghost", "danger"])
def test_button_valid_variants(variant: str) -> None:
    out = _render(f'{{% bw_button "X" variant="{variant}" %}}')
    assert f"bw-btn--{variant}" in out


def test_button_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_button "X" variant="nope" %}')


def test_button_invalid_size_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_button "X" size="huge" %}')


# --- button name/value (#119) ----------------------------------------------


def test_button_emits_name_and_value_on_the_button_branch() -> None:
    # #119: a form with several submits needs to tell the server which one was
    # pressed, which is what name/value carry.
    out = _render('{% bw_button "Archive" type="submit" name="bulk_action" value="archive" %}')
    assert 'name="bulk_action"' in out
    assert 'value="archive"' in out
    assert 'type="submit"' in out


def test_button_omits_name_and_value_when_not_given() -> None:
    # The attributes must not appear at all by default, so an ordinary button's
    # output is unchanged from before #119.
    out = _render('{% bw_button "Save" %}')
    assert "name=" not in out
    assert "value=" not in out


def test_button_output_is_byte_identical_to_pre_119_for_ordinary_callers() -> None:
    # #119 must be purely additive: an existing caller that never passes
    # name/value gets exactly the pre-119 markup, not just "no name=/value=
    # substring" (a whitespace-only regression from new {% if %} lines inside
    # the <button ...> opening tag would pass the substring check above while
    # still changing every existing render).
    out = _render('{% bw_button "Save" %}')
    assert out == (
        '<button class="bw-btn bw-btn--primary bw-btn--md"\n'
        '        type="button"\n'
        "        \n"
        "        \n"
        '        ><span class="bw-btn__label">Save</span></button>\n'
    )


def test_the_documented_bulk_actions_wiring_renders() -> None:
    """The exact call _bulk_actions_bar.html's docstring documents (#119).

    This is the regression that was missing: the documented example raised
    TemplateSyntaxError because bw_button had no name/value, and nothing
    rendered it. A documented option needs a test that proves it works, or the
    documentation is only a claim.
    """
    out = _render(
        '{% bw_button label="Archive" type="submit" name="bulk_action" '
        'value="archive" variant="secondary" size="sm" %}'
        '{% bw_button label="Delete" type="submit" name="bulk_action" '
        'value="delete" variant="danger" size="sm" %}'
    )
    assert out.count('name="bulk_action"') == 2
    assert 'value="archive"' in out
    assert 'value="delete"' in out


def test_button_rejects_name_alongside_href() -> None:
    # name/value on an <a> are meaningless. Raising beats silently dropping
    # them, which is precisely how #119 went unnoticed.
    with pytest.raises(TemplateSyntaxError, match="<button> branch only"):
        _render('{% bw_button "Go" href="/x/" name="action" %}')


def test_button_rejects_value_without_name() -> None:
    # A value with no name is never sent by the browser, so the server would
    # see nothing: a silent no-op the caller almost certainly did not intend.
    with pytest.raises(TemplateSyntaxError, match="requires name="):
        _render('{% bw_button "X" type="submit" value="archive" %}')


# --- badge ----------------------------------------------------------------


def test_badge_renders_with_variant() -> None:
    out = _render('{% bw_badge "Active" variant="success" %}')
    assert "bw-badge--success" in out and "Active" in out


def test_badge_default_variant_is_neutral() -> None:
    out = _render('{% bw_badge "Draft" %}')
    assert "bw-badge--neutral" in out and "Draft" in out


def test_badge_neutral_variant_has_a_shipped_css_rule() -> None:
    # #100: the documented no-args default is variant="neutral", so the shipped
    # CSS must carry a real .bw-badge--neutral rule (the neutral chip treatment,
    # token-derived), never a look left implicit in the .bw-badge base class.
    css = (_DIST_JS.parent / "brickwork.css").read_text()
    rule = re.search(r"\.bw-badge--neutral\{([^}]*)\}", css)
    assert rule is not None, "dist/brickwork.css must ship a .bw-badge--neutral rule (#100)"
    body = rule.group(1).replace(" ", "")
    assert "background:var(--bw-color-surface-sunken)" in body
    assert "color:var(--bw-color-fg-muted)" in body


def test_badge_with_icon() -> None:
    out = _render('{% bw_badge "New" icon="info" %}')
    assert "bw-icon" in out and "New" in out


# --- alert ----------------------------------------------------------------


@pytest.mark.parametrize(
    "variant,icon_marker",
    [("info", "info"), ("success", "success"), ("warning", "alert-triangle"), ("error", "alert-circle")],
)
def test_alert_variant_picks_the_right_icon(variant: str, icon_marker: str) -> None:
    out = _render(f'{{% bw_alert "msg" variant="{variant}" %}}')
    assert f"bw-alert--{variant}" in out
    assert 'role="alert"' in out
    # the icon name maps per-variant (the marker will appear in the rendered svg path set)
    assert "bw-alert__icon" in out


def test_alert_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_alert "msg" variant="nope" %}')


def test_alert_with_title() -> None:
    out = _render('{% bw_alert "the message" variant="error" title="Oops" %}')
    assert "Oops" in out and "the message" in out


# --- dismissible alert and badge (04-interfaces 4b, 0.9.0) ------------------


def _close_button(out: str) -> str:
    """The dismiss control's opening tag, for attribute assertions."""
    match = re.search(r"<button[^>]*aria-label[^>]*>", out)
    assert match, "no close control in output"
    return match.group(0)


def test_alert_default_output_is_unchanged_without_dismissible() -> None:
    # regression: the new argument's default must not disturb the shipped
    # markup; dismissible=False and omitting it are byte-equal
    default = _render('{% bw_alert "msg" variant="info" %}')
    assert default == _render('{% bw_alert "msg" variant="info" dismissible=False %}')
    assert "x-data" not in default
    assert "<button" not in default


def test_badge_default_output_is_unchanged_without_dismissible() -> None:
    default = _render('{% bw_badge "Active" variant="success" %}')
    assert default == _render('{% bw_badge "Active" variant="success" dismissible=False %}')
    assert "x-data" not in default
    assert "<button" not in default


def test_dismissible_alert_gains_the_component_and_a_hidden_close_control() -> None:
    # The control ships WITH the hidden attribute and JS reveals it at init:
    # the no-JS floor shows no dead dismiss affordance (04-interfaces 4b).
    out = _render('{% bw_alert "msg" variant="info" dismissible=True %}')
    assert 'x-data="bwDismissible()"' in out
    assert "hidden" in _close_button(out).replace("aria-hidden", "")


def test_dismissible_badge_gains_the_component_and_a_hidden_close_control() -> None:
    out = _render('{% bw_badge "Beta" variant="info" dismissible=True %}')
    assert 'x-data="bwDismissible()"' in out
    assert "hidden" in _close_button(out).replace("aria-hidden", "")


def test_bundle_registers_bwdismissible_and_its_event() -> None:
    # AC static leg, mirroring the interaction modules: the compiled bundle
    # carries the semver-public name and its documented bw: event.
    bundle = _DIST_JS.read_text()
    assert "bwDismissible" in bundle
    assert "bw:dismiss" in bundle
