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


# --- badge ----------------------------------------------------------------


def test_badge_renders_with_variant() -> None:
    out = _render('{% bw_badge "Active" variant="success" %}')
    assert "bw-badge--success" in out and "Active" in out


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
