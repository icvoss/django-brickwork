"""End-to-end integration tests against the brickwork_testapp.

Runs only under the settings_seams leg (see conftest.py). Exercises the full
vertical slice through real views/URLs/forms: the shell renders with the nav
(active state, badge, external link, section header), the list and dashboard
pages route through the shipped 0.5.0 patterns (list.html / dashboard.html)
with real filter, stat, and activity content, the nav slot carries the
testapp's own property switcher, and the 422 HTMX form-validation contract
works in both HTMX and no-JS modes.
"""

from __future__ import annotations

import re

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture
def widgets():
    from brickwork_testapp.models import Widget

    Widget.objects.create(name="Alpha", status="active")
    Widget.objects.create(name="Beta", status="draft")
    return Widget.objects.all()


# --- the shell + nav + table render end-to-end -----------------------------


def test_list_page_renders_through_the_shell(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-app" in html and "bw-sidebar" in html and "bw-workspace" in html
    assert "Alpha" in html and "Beta" in html
    assert "bw-data-table" in html


def test_list_page_has_a_skip_link_and_no_script(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-skip-link" in html and 'href="#bw-main"' in html
    assert "<script" not in html.lower()  # the no-JS floor: shell ships no JS


def test_layout_context_passthrough_selects_topbar(client: Client, widgets) -> None:
    # SHL-001: the testapp's context processor passes ?layout=topbar through to
    # the shell's data-layout hook; the default (and anything invalid) stays
    # sidebar. Same DOM either way; only the attribute flips.
    assert 'data-layout="sidebar"' in client.get("/widgets/").content.decode()
    assert 'data-layout="topbar"' in client.get("/widgets/?layout=topbar").content.decode()
    assert 'data-layout="sidebar"' in client.get("/widgets/?layout=bogus").content.decode()


def test_nav_marks_the_current_route_active(client: Client, widgets) -> None:
    # BR-BW-NAV-001: the widgets item resolves active via resolver_match.
    html = client.get("/widgets/").content.decode()
    assert 'aria-current="page"' in html
    assert "bw-nav__link--active" in html


def test_nav_renders_badge_external_and_section_header(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-nav__badge" in html and "12" in html  # NAV-010
    assert 'target="_blank"' in html and 'rel="noopener noreferrer"' in html  # NAV-018
    assert "bw-nav__section-label" in html and "Admin" in html  # NAV-002


def test_empty_list_shows_the_empty_state(client: Client) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-empty-state" in html
    assert "No widgets yet" in html


# --- the 422 form-validation contract (BR-BW-HTMX-003) ---------------------


def test_htmx_invalid_post_returns_422_form_partial(client: Client) -> None:
    resp = client.post("/widgets/new/", {"name": "invalid", "status": "draft"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 422
    html = resp.content.decode()
    # only the form section, not the whole shell (targeted swap)
    assert "bw-app" not in html
    assert 'id="widget-form"' in html
    # accessible error wiring (BR-BW-A11Y-002)
    assert 'aria-invalid="true"' in html
    assert "aria-describedby" in html
    assert 'role="alert"' in html
    assert "not allowed" in html


def test_non_htmx_invalid_post_redisplays_full_page(client: Client) -> None:
    # BR-BW-HTMX-001: with no JS, the same view returns a full working page.
    resp = client.post("/widgets/new/", {"name": "invalid", "status": "draft"})
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "bw-app" in html  # the full shell
    assert 'aria-invalid="true"' in html


def test_valid_post_creates_and_redirects(client: Client) -> None:
    from brickwork_testapp.models import Widget

    resp = client.post("/widgets/new/", {"name": "Gamma", "status": "active"})
    assert resp.status_code == 302
    assert Widget.objects.filter(name="Gamma").exists()


# --- breadcrumbs + account menu render through the shell --------------------


def test_breadcrumbs_render_with_the_current_page_unlinked(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert '<ol class="bw-breadcrumbs__list">' in html
    assert '<span class="bw-breadcrumbs__current" aria-current="page">Widgets</span>' in html


def test_form_page_breadcrumb_trail_links_intermediates(client: Client) -> None:
    html = client.get("/widgets/new/").content.decode()
    assert '<a class="bw-breadcrumbs__link" href="/widgets/">Widgets</a>' in html
    assert '<span class="bw-breadcrumbs__current" aria-current="page">Widget</span>' in html


def test_account_menu_renders_without_aria_menu_semantics(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-account-menu__trigger-label" in html
    assert "bw-account-menu__item--danger" in html  # the Sign out item
    # a details/summary disclosure of links, never an ARIA menu
    assert 'role="menu"' not in html
    assert 'role="menuitem"' not in html


# --- the list page routes through patterns/list.html (0.5.0) ----------------


def test_list_page_routes_through_the_list_pattern(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-filter-bar" in html  # the filled filter_bar region
    assert "bw-card" in html  # the pattern-shaped table card
    # documented region order: filter bar above the table card
    assert html.index("bw-filter-bar") < html.index('id="widgets-table"')


def test_list_filter_bar_narrows_rows_via_plain_get(client: Client, widgets) -> None:
    # TBL-003's no-JS floor: the filter bar is a plain GET form the view reads.
    html = client.get("/widgets/?status=draft").content.decode()
    assert "Beta" in html
    assert "Alpha" not in html
    html = client.get("/widgets/?q=alp").content.decode()
    assert "Alpha" in html
    assert "Beta" not in html


def test_list_pagination_appears_beyond_one_page(client: Client) -> None:
    from brickwork_testapp.models import Widget

    for i in range(12):
        Widget.objects.create(name=f"W{i:02d}", status="draft")
    html = client.get("/widgets/").content.decode()
    assert "bw-pagination" in html  # the pattern's list_pagination default, wired from page_obj


# --- the dashboard routes through patterns/dashboard.html (0.5.0) -----------


def test_dashboard_renders_stat_tiles_from_real_aggregates(client: Client, widgets) -> None:
    html = client.get("/dashboard/").content.decode()
    assert html.count("bw-stat__value") == 3
    assert "Total widgets" in html and "Active" in html and "Draft" in html
    # two widgets in the fixture: total=2, active=1, draft=1
    assert re.search(r"bw-stat__value[^>]*>\s*2\b", html)
    # the delta surface carries its accessible text label (BR-BW-TPL-007)
    assert "One more than last week" in html


def test_dashboard_activity_lists_recent_widgets(client: Client, widgets) -> None:
    html = client.get("/dashboard/").content.decode()
    assert 'id="activity-table"' in html
    assert "Alpha" in html and "Beta" in html


def test_dashboard_marks_its_nav_item_active(client: Client, widgets) -> None:
    html = client.get("/dashboard/").content.decode()
    assert 'aria-current="page"' in html


def test_form_page_still_extends_the_plain_shell(client: Client) -> None:
    # The form pages keep the default base parent (shell/app.html): no pattern
    # regions leak into them.
    html = client.get("/widgets/new/").content.decode()
    assert "bw-app" in html
    assert "bw-filter-bar" not in html


# --- the nav slot carries the testapp's own switcher (AC-BW-078) ------------


def test_property_switcher_fills_the_nav_slot(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert "bw-sidebar__switcher-trigger" in html  # the consumer's own <details>
    assert "Switch property" in html
    # positioned above the nav render in the sidebar
    assert html.index("bw-sidebar__switcher") < html.index("bw-nav__")


# --- server-side sort (data_table structure only) --------------------------


def test_data_table_sort_reorders_rows(client: Client, widgets) -> None:
    html = client.get("/widgets/?sort=-name").content.decode()
    # Beta should appear before Alpha under descending name sort
    assert html.index("Beta") < html.index("Alpha")


# --- theme axes render on the shell ----------------------------------------


def test_shell_carries_default_theme_axes(client: Client, widgets) -> None:
    html = client.get("/widgets/").content.decode()
    assert 'data-theme="light"' in html
    assert 'data-density="comfortable"' in html
    assert 'dir="ltr"' in html


# --- the 0.8.0 interaction set page (04-interfaces section 4b) --------------


def test_interactions_page_composes_all_four_components_as_floors(client: Client, widgets) -> None:
    html = client.get("/interactions/").content.decode()
    # dropdown floor: a details disclosure of plain links, no menu semantics
    assert '<details class="bw-dropdown"' in html
    assert 'href="/widgets/new/?via=dropdown"' in html
    assert 'role="menu"' not in html and 'role="menuitem"' not in html
    # tabs floor: real anchors with the server-selected panel visible
    assert 'href="/interactions/?tab=details"' in html
    assert 'id="bw-tabpanel-itx-overview"' in html
    # modal trigger: a real anchor to the full-page floor route, plus the
    # documented hx-get swap into the shell's modal root (BR-BW-HTMX-005)
    assert 'href="/interactions/confirm/"' in html
    assert 'hx-target="#bw-modal-root"' in html
    # disclosure group: three native details sharing one accordion name
    assert html.count('name="itx-faq"') == 3
    # the composed floor page ships no script at all (BR-BW-HTMX-001)
    assert "<script" not in html.lower()


def test_interactions_page_marks_its_nav_item_active(client: Client) -> None:
    html = client.get("/interactions/").content.decode()
    assert "bw-nav__link--active" in html
    assert "Interactions" in html


def test_tabs_floor_renders_the_active_panel_and_hides_the_rest(client: Client) -> None:
    html = client.get("/interactions/").content.decode()
    overview = re.search(r'<div class="bw-tabs__panel"[^>]*id="bw-tabpanel-itx-overview"[^>]*>', html)
    details = re.search(r'<div class="bw-tabs__panel"[^>]*id="bw-tabpanel-itx-details"[^>]*>', html)
    assert overview and "hidden" not in overview.group(0)
    assert details and "hidden" in details.group(0)


def test_lazy_tab_is_server_rendered_when_it_is_the_active_tab(client: Client) -> None:
    # AC-BW-085: the no-JS floor renders the active panel full-page, so the
    # lazy wiring is dropped and the content is inline.
    html = client.get("/interactions/?tab=activity").content.decode()
    activity = re.search(r'<div class="bw-tabs__panel"[^>]*id="bw-tabpanel-itx-activity"[^>]*>', html)
    assert activity and "hidden" not in activity.group(0)
    assert "hx-trigger" not in html
    assert "Priya restocked Alpha" in html


def test_lazy_tab_carries_the_intersect_once_swap_when_inactive(client: Client) -> None:
    html = client.get("/interactions/").content.decode()
    assert 'hx-get="/interactions/panels/activity/"' in html
    assert 'hx-trigger="intersect once"' in html
    assert 'hx-target="this"' in html
    # the skeleton placeholder reserves the swap's space (BR-BW-HTMX-009)
    assert "bw-skeleton" in html


def test_unknown_tab_falls_back_to_the_first(client: Client) -> None:
    html = client.get("/interactions/?tab=bogus").content.decode()
    overview = re.search(r'<div class="bw-tabs__panel"[^>]*id="bw-tabpanel-itx-overview"[^>]*>', html)
    assert overview and "hidden" not in overview.group(0)


def test_lazy_panel_route_returns_the_partial_only(client: Client) -> None:
    html = client.get("/interactions/panels/activity/").content.decode()
    assert "bw-app" not in html and "<html" not in html
    assert "Priya restocked Alpha" in html


# --- the modal's two documented render paths (one partial) ------------------


def test_confirm_route_htmx_returns_the_modal_fragment(client: Client) -> None:
    resp = client.get("/interactions/confirm/", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "<html" not in html and "bw-app" not in html  # a fragment, not a page
    assert 'role="dialog"' in html
    assert 'x-data="bwModal(' in html
    assert 'id="confirm-reset"' in html
    assert 'aria-labelledby="confirm-reset-title"' in html


def test_confirm_route_plain_get_is_a_full_working_page(client: Client) -> None:
    # BR-BW-HTMX-006: the floor is a real page presenting the same content
    # and action through the shell.
    html = client.get("/interactions/confirm/").content.decode()
    assert "bw-app" in html  # rendered through the shell
    assert "Reset demo data" in html
    assert 'method="post"' in html and 'action="/interactions/confirm/"' in html
    # the close control is a real anchor back out (close_url), never a dead
    # trigger (AC-BW-086)
    assert re.search(r'<a class="bw-modal__close[^>]*href="/interactions/"', html)


def test_confirm_post_htmx_closes_the_modal_server_side(client: Client, widgets) -> None:
    resp = client.post("/interactions/confirm/", {"confirm": "RESET"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 204
    trigger = resp["HX-Trigger"]
    assert "bw:modal:close" in trigger and "confirm-reset" in trigger
    from brickwork_testapp.models import Widget

    assert Widget.objects.count() == 0


def test_confirm_post_no_js_redirects_to_the_interactions_page(client: Client, widgets) -> None:
    resp = client.post("/interactions/confirm/", {"confirm": "RESET"})
    assert resp.status_code == 302
    assert resp["Location"] == "/interactions/"


# --- the 0.9.0 overlay pair: toast delivery + combobox floor -----------------


def test_toast_demo_page_ships_the_shell_region_and_no_script(client: Client) -> None:
    # the shell's one #bw-toast-region include (BR-BW-HTMX-005): every shell
    # page has a working toast target out of the box, empty and invisible
    html = client.get("/toasts/").content.decode()
    assert 'id="bw-toast-region"' in html
    assert 'aria-live="polite"' in html
    assert "bw-toast--" not in html  # an empty region shows no toast
    assert "<script" not in html.lower()  # the floor page ships no JS


def test_toast_htmx_post_returns_the_oob_wrapper(client: Client) -> None:
    # BR-BW-HTMX-007: the only creation path is server-rendered markup riding
    # an OOB wrapper; the rest of the response is the ordinary main swap.
    resp = client.post("/toasts/action/", {"intent": "success"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'hx-swap-oob="afterbegin:#bw-toast-region"' in html
    assert "bw-toast--success" in html
    assert "data-bw-toast" in html
    assert "bw-toast__close" in html  # CBH-012: always dismissible
    assert "bw-app" not in html  # a fragment, never a full page
    assert 'id="toast-demo-status"' in html  # the main swap content


def test_toast_no_js_post_falls_back_to_the_alert_floor(client: Client) -> None:
    # BR-BW-HTMX-001/STA-008: POST -> redirect -> the same feedback as a
    # messages banner alert; the toast is never the only form.
    resp = client.post("/toasts/action/", {"intent": "success"}, follow=True)
    assert resp.redirect_chain == [("/toasts/", 302)]
    html = resp.content.decode()
    assert "bw-alert--success" in html
    assert "Demo data saved." in html
    assert "bw-toast--" not in html


def test_dismissible_instances_render_on_the_toast_page(client: Client) -> None:
    # one dismissible alert + one dismissible badge (04-interfaces 4b)
    html = client.get("/toasts/").content.decode()
    assert html.count('x-data="bwDismissible()"') == 2


def test_combobox_page_floor_is_the_native_select(client: Client) -> None:
    html = client.get("/comboboxes/").content.decode()
    floor = re.search(r'<select[^>]*name="colour"[^>]*>', html)
    assert floor and "bw-combobox__floor" in floor.group(0)
    assert "hidden" not in floor.group(0).replace("aria-hidden", "")
    # the enhanced field wrapper ships hidden; only bwCombobox reveals it
    field = re.search(r"<div[^>]*bw-combobox__field[^>]*>", html)
    assert field and "hidden" in field.group(0).replace("aria-hidden", "")
    assert "<script" not in html.lower()


def test_combobox_page_multiple_floor_is_a_select_multiple(client: Client) -> None:
    html = client.get("/comboboxes/").content.decode()
    tags = re.search(r'<select[^>]*name="tags"[^>]*>', html)
    assert tags and "multiple" in tags.group(0)


def test_combobox_options_endpoint_returns_the_option_list_partial(client: Client) -> None:
    html = client.get("/comboboxes/options/colour/?q=gr").content.decode()
    assert "bw-app" not in html and "<html" not in html
    assert 'role="option"' in html
    assert 'data-bw-value="green"' in html
    assert 'data-bw-value="red"' not in html


def test_combobox_422_rerender_keeps_the_selection(client: Client) -> None:
    # BR-BW-HTMX-003: selections survive a failed submit through POST data
    # carried by the floor controls, never through Alpine state.
    resp = client.post(
        "/comboboxes/",
        {"colour": "green", "tags": ["alpha", "beta"], "reason": ""},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 422
    html = resp.content.decode()
    assert "bw-app" not in html  # only the form section swaps
    assert 'id="combobox-form"' in html
    for value in ("green", "alpha", "beta"):
        option = re.search(rf'<option[^>]*value="{value}"[^>]*>', html)
        assert option and "selected" in option.group(0)
    assert "This field is required." in html


def test_combobox_non_htmx_invalid_post_redisplays_full_page(client: Client) -> None:
    # BR-BW-HTMX-001: with no JS the same view returns a full working page.
    resp = client.post("/comboboxes/", {"colour": "green", "tags": [], "reason": ""})
    assert resp.status_code == 200
    assert "bw-app" in resp.content.decode()


def test_combobox_valid_post_redirects(client: Client) -> None:
    resp = client.post("/comboboxes/", {"colour": "red", "reason": "Because."})
    assert resp.status_code == 302
    assert resp["Location"] == "/comboboxes/"
