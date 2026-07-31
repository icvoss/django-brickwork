"""End-to-end integration tests against the brickwork_testapp.

Runs only under the settings_seams leg (see conftest.py). Exercises the full
vertical slice through real views/URLs/forms: the shell renders with the nav
(active state, badge, external link, section header), the data_table lists rows,
and the 422 HTMX form-validation contract works in both HTMX and no-JS modes.
"""

from __future__ import annotations

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
