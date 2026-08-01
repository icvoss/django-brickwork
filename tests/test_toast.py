"""{% bw_toast %} and _toast_region.html contract tests (04-interfaces section 4b, 0.9.0).

The tag renders ONE toast, always server-side: there is deliberately no
client-side creation API (BR-BW-HTMX-007), so the markup the tag emits is the
whole delivery contract whether it arrives via an hx-swap-oob wrapper or a
full-page render. A close control is ALWAYS rendered (CBH-012, WCAG 2.2.1) and
a danger toast announces assertively via role="alert". _toast_region.html is
the stacking container and polite live region carrying the stable
#bw-toast-region id (BR-BW-HTMX-005, A11Y-013); an empty region renders no
toast. Render-time enforcement (the intent whitelist rejecting "neutral", the
duration whitelist, the action label/url pairing) raises TemplateSyntaxError
exactly as bw_button does.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_TAG = '{% bw_toast "Widget saved." intent="success" %}'


def _render(src: str = _TAG, **ctx: object) -> str:
    return engines["django"].from_string("{% load brickwork_interactions %}" + src).render(ctx)


def _render_region(**ctx: object) -> str:
    return render_to_string("brickwork/components/_toast_region.html", ctx)


def _root_tag(html: str) -> str:
    """The toast's opening <div ...> tag only, for attribute assertions."""
    start = html.index("<div")
    return html[start : html.index(">", start)]


# --- one toast: markup and hooks ----------------------------------------------


def test_root_carries_the_intent_class_and_data_hook() -> None:
    html = _render()
    assert "bw-toast bw-toast--success" in _root_tag(html)
    assert "data-bw-toast" in _root_tag(html)


def test_each_render_gets_a_unique_id() -> None:
    # bw:toast:* events carry { id }, so every server-rendered toast needs one;
    # two toasts prepended into one region must never collide.
    first = re.search(r'id="([^"]+)"', _root_tag(_render()))
    second = re.search(r'id="([^"]+)"', _root_tag(_render()))
    assert first and second
    assert first.group(1) != second.group(1)


def test_component_config_defaults_to_normal_duration() -> None:
    html = _render()
    assert "bwToast(" in html
    assert re.search(r"duration:\s*['\"]normal['\"]", html)


@pytest.mark.parametrize("duration", ["short", "long", "persistent"])
def test_duration_flows_into_the_component_config(duration: str) -> None:
    html = _render(f'{{% bw_toast "Saved." intent="info" duration="{duration}" %}}')
    assert re.search(rf"duration:\s*['\"]{duration}['\"]", html)


def test_danger_toast_announces_assertively() -> None:
    assert 'role="alert"' in _render('{% bw_toast "Failed." intent="danger" %}')


@pytest.mark.parametrize("intent", ["success", "warning", "info"])
def test_non_danger_toasts_stay_polite(intent: str) -> None:
    # the region's aria-live="polite" carries the announcement; only danger
    # escalates to role="alert"
    assert 'role="alert"' not in _render(f'{{% bw_toast "msg" intent="{intent}" %}}')


def test_intent_icon_is_decorative() -> None:
    html = _render()
    assert "bw-toast__icon" in html
    assert 'aria-hidden="true"' in html


def test_message_renders_in_the_message_slot_and_is_escaped() -> None:
    html = _render('{% bw_toast message intent="info" %}', message="<b>bold</b>")
    assert "bw-toast__message" in html
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_close_control_is_always_rendered_with_an_accessible_name() -> None:
    # CBH-012: even a persistent toast can always be dismissed.
    for src in (_TAG, '{% bw_toast "Sticky." intent="warning" duration="persistent" %}'):
        html = _render(src)
        close = re.search(r"<button[^>]*bw-toast__close[^>]*>", html)
        assert close
        assert re.search(r'aria-label="[^"]+"', close.group(0))


def test_action_renders_as_a_single_link() -> None:
    html = _render('{% bw_toast "Archived." intent="success" action_label="Undo" action_url="/undo/" %}')
    action = re.search(r"<a[^>]*bw-toast__action[^>]*>", html)
    assert action and 'href="/undo/"' in action.group(0)
    assert "Undo" in html
    assert "bw-toast__action" not in _render()


def test_toast_never_steals_focus_and_ships_no_script() -> None:
    # BR-BW-JS-006: arrival never moves focus; no autofocus marker, no script.
    html = _render()
    assert "autofocus" not in html
    assert "<script" not in html.lower()


# --- render-time enforcement raises -------------------------------------------


def test_missing_required_arguments_are_parse_errors() -> None:
    for src in ("{% bw_toast %}", '{% bw_toast "msg" %}'):
        with pytest.raises(TemplateSyntaxError):
            engines["django"].from_string("{% load brickwork_interactions %}" + src)


@pytest.mark.parametrize(
    "src",
    [
        # CMP-022: the whitelist rejects "neutral" explicitly, and anything unknown
        '{% bw_toast "msg" intent="neutral" %}',
        '{% bw_toast "msg" intent="error" %}',
        '{% bw_toast "msg" intent="loud" %}',
        # duration whitelist (CBH-009)
        '{% bw_toast "msg" intent="info" duration="forever" %}',
        # CMP-023: the inline action is a pair; half an action is an authoring error
        '{% bw_toast "msg" intent="info" action_label="Undo" %}',
        '{% bw_toast "msg" intent="info" action_url="/undo/" %}',
    ],
)
def test_invalid_arguments_raise(src: str) -> None:
    with pytest.raises(TemplateSyntaxError):
        _render(src)


# --- the region include (stable target, polite live region) --------------------


def test_region_carries_the_stable_id_live_region_and_hooks() -> None:
    html = _render_region()
    assert 'id="bw-toast-region"' in html  # BR-BW-HTMX-005
    assert 'aria-live="polite"' in html  # A11Y-013
    assert "data-bw-toast-region" in html
    assert 'x-data="bwToastRegion()"' in html


def test_region_position_defaults_to_top_end() -> None:
    assert "bw-toast-region--top-end" in _render_region()


@pytest.mark.parametrize("position", ["top-start", "bottom-end", "bottom-start"])
def test_region_position_variants(position: str) -> None:
    # logical positions (CBH-010) so RTL mirrors for free
    assert f"bw-toast-region--{position}" in _render_region(position=position)


def test_region_ships_the_collapse_control_hidden() -> None:
    # CBH-011: at most 3 visible, older ones behind "+N more". The control
    # exists from the start but only JS ever reveals it: a visible control
    # that does nothing is worse than no control.
    html = _render_region()
    more = re.search(r"<button[^>]*bw-toast-region__more[^>]*>", html)
    assert more
    assert "hidden" in more.group(0).replace("aria-hidden", "")


def test_empty_region_renders_no_toast_and_no_script() -> None:
    html = _render_region()
    assert "bw-toast--" not in html
    assert "<script" not in html.lower()


# --- the shipped JS bundle contract --------------------------------------------


def test_bundle_registers_the_toast_pair_with_documented_events() -> None:
    bundle = _DIST_JS.read_text()
    assert "bwToast" in bundle and "bwToastRegion" in bundle
    assert "bw:toast:show" in bundle
    assert "bw:toast:dismiss" in bundle
    # both documented dismissal reasons survive minification as literals
    for reason in ("timeout", "dismiss"):
        assert reason in bundle


def test_bundle_ships_no_client_side_creation_api() -> None:
    # BR-BW-HTMX-007: toast markup is always server-rendered; no showToast()
    # entry point, ever.
    assert "showToast" not in _DIST_JS.read_text()
