"""{% bw_tabs %} and tab_panel contract tests (04-interfaces section 4b, 0.8.0).

The tag renders the TABLIST ONLY as the no-JS floor: each tab is a real
anchor to its url (default ?tab=<key> on the current path), the server
selects the active tab, and switching is an ordinary navigation (CBH-015,
AC-BW-085). Deliberately NO role="tablist"/"tab" and NO roving tabindex in
the shipped markup: role="tab" plus tabindex="-1" would make non-active tabs
keyboard-unreachable with no JavaScript running (the _dropdown.html
upgrade-at-init doctrine); bwTabs wires the APG semantics at init. Panels
are consumer markup wrapped in the semver-public tab_panel partial, which
supplies the stable bw-tabpanel-<id>-<key> id (BR-BW-HTMX-005) and the
tabpanel wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.test import RequestFactory
from django.utils.safestring import mark_safe

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_TABS = [
    {"key": "overview", "label": "Overview"},
    {"key": "details", "label": "Details", "badge": 3},
    {"key": "activity", "label": "Activity"},
]

_TAG = "{% bw_tabs tabs=tabs active=active id='demo' %}"


def _render(src: str = _TAG, *, request: object = None, **ctx: object) -> str:
    ctx.setdefault("tabs", _TABS)
    ctx.setdefault("active", "overview")
    return engines["django"].from_string("{% load brickwork_interactions %}" + src).render(ctx, request=request)


def _render_panel(**ctx: object) -> str:
    ctx.setdefault("tabs_id", "demo")
    ctx.setdefault("key", "overview")
    ctx.setdefault("active", "overview")
    ctx.setdefault("content", mark_safe("<p>Panel content.</p>"))
    src = (
        '{% include "brickwork/components/_tabs.html#tab_panel" '
        "with tabs_id=tabs_id key=key active=active content=content lazy_url=lazy_url %}"
    )
    return engines["django"].from_string(src).render(ctx)


# --- the no-JS floor: real anchors, server-selected active -------------------


def test_renders_one_real_anchor_per_tab_with_default_querystring_urls() -> None:
    request = RequestFactory().get("/interactions/")
    html = _render(request=request)
    assert html.count('class="bw-tabs__tab') == 3
    assert 'href="/interactions/?tab=overview"' in html
    assert 'href="/interactions/?tab=details"' in html
    assert 'href="/interactions/?tab=activity"' in html


def test_an_explicit_tab_url_wins_over_the_default() -> None:
    tabs = [{"key": "one", "label": "One", "url": "/custom/"}, {"key": "two", "label": "Two"}]
    html = _render(tabs=tabs, active="one")
    assert 'href="/custom/"' in html


def test_the_active_tab_is_marked_server_side() -> None:
    html = _render(active="details")
    assert html.count("bw-tabs__tab--active") == 1
    assert html.count('aria-current="page"') == 1
    # the marker sits on the details anchor specifically
    active_pos = html.index("bw-tabs__tab--active")
    assert html.index("bw-tab-demo-details") > active_pos
    assert 'data-bw-tab-key="details"' in html


def test_no_tabs_aria_roles_or_roving_tabindex_in_server_markup() -> None:
    # role="tab" + tabindex="-1" without arrow-key handling would strand a
    # keyboard user on a no-JS page; bwTabs adds the APG wiring at init.
    html = _render()
    assert 'role="tablist"' not in html
    assert 'role="tab"' not in html
    assert "aria-selected" not in html
    assert "tabindex" not in html


def test_tab_ids_and_panel_id_pairing_follow_the_stable_convention() -> None:
    # BR-BW-HTMX-005: bw-tab-<id>-<key> anchors, bw-tabpanel-<id>-<key> panels.
    html = _render()
    assert 'id="bw-tab-demo-overview"' in html
    assert 'data-bw-tab-panel-id="bw-tabpanel-demo-overview"' in html


def test_badge_renders_including_zero() -> None:
    html = _render()
    assert '<span class="bw-tabs__badge">3</span>' in html
    zero = _render(tabs=[{"key": "one", "label": "One", "badge": 0}], active="one")
    assert '<span class="bw-tabs__badge">0</span>' in zero
    none = _render(tabs=[{"key": "one", "label": "One"}], active="one")
    assert "bw-tabs__badge" not in none


def test_style_variants() -> None:
    assert "bw-tabs--underline" in _render()  # the default (CMP-024)
    assert "bw-tabs--pill" in _render("{% bw_tabs tabs=tabs active=active id='demo' style='pill' %}")


def test_alpine_component_and_behaviour_args_are_wired() -> None:
    html = _render()
    assert 'x-data="bwTabs(' in html
    assert "id: 'demo'" in html
    assert "active: 'overview'" in html
    assert "urlSync: true" in html and "lazyLoad: false" in html
    flags = _render("{% bw_tabs tabs=tabs active=active id='demo' url_sync=False lazy_load=True %}")
    assert "urlSync: false" in flags and "lazyLoad: true" in flags


def test_label_is_escaped() -> None:
    html = _render(tabs=[{"key": "one", "label": "<b>bold</b>"}], active="one")
    assert "<b>bold</b>" not in html


# --- render-time enforcement raises ------------------------------------------


def test_missing_required_arguments_are_parse_errors() -> None:
    for src in ("{% bw_tabs %}", "{% bw_tabs tabs=tabs %}", "{% bw_tabs tabs=tabs active='overview' %}"):
        with pytest.raises(TemplateSyntaxError):
            engines["django"].from_string("{% load brickwork_interactions %}" + src)


def test_duplicate_tab_key_raises() -> None:
    # mirrors BR-BW-NAV-002's duplicate-key discipline
    tabs = [{"key": "one", "label": "One"}, {"key": "one", "label": "Again"}]
    with pytest.raises(TemplateSyntaxError):
        _render(tabs=tabs, active="one")


@pytest.mark.parametrize(
    "src, ctx",
    [
        (_TAG, {"tabs": []}),
        (_TAG, {"tabs": "not-a-list"}),
        (_TAG, {"tabs": [{"key": "one"}]}),  # missing label
        (_TAG, {"tabs": [{"label": "No key"}]}),
        (_TAG, {"tabs": [{"key": "has space", "label": "Bad key"}]}),  # not id-safe
        (_TAG, {"active": "missing"}),  # active must match a tab key
        (_TAG, {"active": ""}),
        ("{% bw_tabs tabs=tabs active=active id='1-leading-digit' %}", {}),  # id not id-safe
        ("{% bw_tabs tabs=tabs active=active id='demo' style='sideways' %}", {}),
    ],
)
def test_invalid_arguments_raise(src: str, ctx: dict) -> None:
    with pytest.raises(TemplateSyntaxError):
        _render(src, **ctx)


# --- the tab_panel partial (semver-public, BR-BW-TPL-001) --------------------


def test_active_panel_carries_the_full_tabpanel_wiring_and_is_visible() -> None:
    html = _render_panel()
    assert 'id="bw-tabpanel-demo-overview"' in html
    assert 'role="tabpanel"' in html
    assert 'aria-labelledby="bw-tab-demo-overview"' in html
    assert 'tabindex="0"' in html
    assert "hidden" not in html
    assert "<p>Panel content.</p>" in html


def test_inactive_panel_is_hidden() -> None:
    html = _render_panel(key="details", active="overview")
    assert 'id="bw-tabpanel-demo-details"' in html
    assert "hidden" in html


def test_lazy_url_wires_the_intersect_once_htmx_swap() -> None:
    # CBH-014: content loads when the panel first becomes visible. intersect
    # once (not revealed) fires on the same IntersectionObserver primitive
    # regardless of how visibility changed, including bwTabs flipping the
    # hidden property directly via JS on selection.
    html = _render_panel(lazy_url="/interactions/panels/activity/")
    assert 'hx-get="/interactions/panels/activity/"' in html
    assert 'hx-trigger="intersect once"' in html
    assert 'hx-target="this"' in html
    assert "hx-get" not in _render_panel()


def test_unsafe_panel_content_is_escaped() -> None:
    html = _render_panel(content="<script>alert(1)</script>")
    assert "<script>" not in html


# --- the shipped JS bundle contract ------------------------------------------


def test_bundle_registers_bwtabs_and_emits_the_change_event() -> None:
    bundle = _DIST_JS.read_text()
    assert "bwTabs" in bundle
    assert "bw:tabs:change" in bundle
