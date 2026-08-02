"""The V3-shaped consumer smoke leg (brickwork#61).

Runs only under settings_consumer (see conftest.py's pytest_ignore_collect).
Exercises the four seams #61 names, plus a page composing the wider shipped
interaction/component set so the leg catches a cross-component integration
break, not just the four named seams:

1. Multi-host shell branching: two simulated tenant hosts render different
   branding through the same shell (consumer.middleware.TenantHostMiddleware
   + consumer.tenants).
2. The BRICKWORK_THEME_RESOLVER tenant resolver: per-host theme/density/brand
   reach the shell's bw_* vars and render as data-* attributes on <html>
   (consumer.theme_resolver, via brickwork.context_processors.theme).
3. A waffle-style feature_checker gating nav: the Reports nav item is hidden
   when its flag is off and visible when on (consumer.features + nav.py).
4. The 422 form-swap loop (BR-BW-HTMX-003): htmx-invalid -> 422 partial,
   non-htmx-invalid -> 200 full page, valid -> 302, through {% bw_form %}.
"""

from __future__ import annotations

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db

ACME_HOST = "acme.example.com"
GLOBEX_HOST = "globex.example.com"


# --- seam 1: multi-host shell branching -------------------------------------


def test_different_hosts_render_different_sidebar_brand(client: Client) -> None:
    acme_html = client.get("/tickets/", SERVER_NAME=ACME_HOST).content.decode()
    globex_html = client.get("/tickets/", SERVER_NAME=GLOBEX_HOST).content.decode()
    assert "Acme Ltd" in acme_html
    assert "Acme Ltd" not in globex_html
    assert "Globex plc" in globex_html
    assert "Globex plc" not in acme_html


def test_unknown_host_falls_back_to_the_default_tenant_without_erroring(client: Client) -> None:
    html = client.get("/tickets/", SERVER_NAME="unmapped.example.com").content.decode()
    assert "Consumer harness" in html


# --- seam 2: the BRICKWORK_THEME_RESOLVER tenant resolver --------------------


def test_theme_resolver_reaches_the_shell_data_attributes_per_host(client: Client) -> None:
    acme_html = client.get("/tickets/", SERVER_NAME=ACME_HOST).content.decode()
    assert 'data-theme="light"' in acme_html
    assert 'data-density="comfortable"' in acme_html
    assert 'data-bw-brand="acme"' in acme_html

    globex_html = client.get("/tickets/", SERVER_NAME=GLOBEX_HOST).content.decode()
    assert 'data-theme="dark"' in globex_html
    assert 'data-density="compact"' in globex_html
    assert 'data-bw-brand="globex"' in globex_html


def test_unknown_host_theme_falls_back_to_defaults_with_no_brand_attribute(client: Client) -> None:
    html = client.get("/tickets/", SERVER_NAME="unmapped.example.com").content.decode()
    assert 'data-theme="light"' in html
    assert "data-bw-brand" not in html


# --- seam 3: the waffle-style feature_checker gating nav ---------------------


def test_reports_nav_item_hidden_when_its_flag_is_off(client: Client) -> None:
    html = client.get("/tickets/", SERVER_NAME=ACME_HOST).content.decode()
    assert "Reports" not in html


def test_reports_nav_item_visible_when_its_flag_is_on(client: Client) -> None:
    html = client.get("/tickets/?flags=reports_beta", SERVER_NAME=ACME_HOST).content.decode()
    assert "Reports" in html
    assert 'href="/reports/"' in html


def test_reports_view_itself_is_reachable_regardless_of_the_flag(client: Client) -> None:
    # BR-BW-NAV-005: nav visibility is display, never authorisation.
    resp = client.get("/reports/", SERVER_NAME=ACME_HOST)
    assert resp.status_code == 200


def test_other_nav_items_stay_visible_regardless_of_the_flag(client: Client) -> None:
    html = client.get("/tickets/", SERVER_NAME=ACME_HOST).content.decode()
    assert 'href="/tickets/"' in html
    assert 'href="/surface/"' in html


# --- seam 4: the 422 form-swap loop through {% bw_form %} -------------------


def test_htmx_invalid_post_returns_422_form_partial(client: Client) -> None:
    resp = client.post(
        "/tickets/new/",
        {"title": "invalid", "priority": "normal"},
        HTTP_HX_REQUEST="true",
        SERVER_NAME=ACME_HOST,
    )
    assert resp.status_code == 422
    html = resp.content.decode()
    assert "bw-app" not in html  # only the form section swaps
    assert 'id="ticket-form"' in html
    assert 'aria-invalid="true"' in html
    assert "aria-describedby" in html
    assert 'role="alert"' in html
    assert "not allowed" in html


def test_non_htmx_invalid_post_redisplays_full_page(client: Client) -> None:
    resp = client.post(
        "/tickets/new/",
        {"title": "invalid", "priority": "normal"},
        SERVER_NAME=ACME_HOST,
    )
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "bw-app" in html
    assert 'aria-invalid="true"' in html


def test_valid_post_creates_and_redirects(client: Client) -> None:
    from consumer.models import Ticket

    resp = client.post(
        "/tickets/new/",
        {"title": "Printer jam", "priority": "urgent"},
        SERVER_NAME=ACME_HOST,
    )
    assert resp.status_code == 302
    ticket = Ticket.objects.get(title="Printer jam")
    assert ticket.tenant_slug == "acme"


# --- the shipped component/interaction surface page --------------------------


def test_surface_page_composes_modal_trigger_slide_over_table_form_and_stepper(client: Client) -> None:
    from consumer.models import Ticket

    Ticket.objects.create(tenant_slug="acme", title="Printer jam", priority="urgent")
    html = client.get("/surface/", SERVER_NAME=ACME_HOST).content.decode()
    # modal trigger: real anchor + the documented htmx swap into the shared root
    assert 'href="/surface/confirm/"' in html
    assert 'hx-target="#bw-modal-root"' in html
    # slide-over trigger: real anchor + its OWN stable root (coexists with the modal)
    assert 'href="/surface/panel/"' in html
    assert 'hx-target="#bw-slide-over-root"' in html
    # selectable data table
    assert "bw-data-table__th--select" in html
    assert 'id="surface-tickets"' in html
    # stepper
    assert "bw-stepper" in html
    assert 'aria-current="step"' in html
    # bw_form (0.15.0 whole-form renderer)
    assert 'id="surface-ticket-form"' in html
    assert 'name="title"' in html
    # toast trigger
    assert 'id="surface-toast-form"' in html
    assert "<script" not in html.lower()  # the composed page ships no JS


def test_surface_modal_trigger_route_returns_the_fragment_on_htmx(client: Client) -> None:
    resp = client.get("/surface/confirm/", HTTP_HX_REQUEST="true", SERVER_NAME=ACME_HOST)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "<html" not in html and "bw-app" not in html
    assert 'role="dialog"' in html
    assert 'id="confirm-clear"' in html


def test_surface_modal_trigger_route_is_a_full_page_with_no_js(client: Client) -> None:
    html = client.get("/surface/confirm/", SERVER_NAME=ACME_HOST).content.decode()
    assert "bw-app" in html
    assert 'method="post"' in html


def test_surface_slide_over_route_returns_the_fragment_on_htmx(client: Client) -> None:
    resp = client.get("/surface/panel/", HTTP_HX_REQUEST="true", SERVER_NAME=ACME_HOST)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "<html" not in html and "bw-app" not in html
    assert 'role="dialog"' in html
    assert "bw-slide-over" in html


def test_surface_slide_over_route_is_a_full_page_with_no_js(client: Client) -> None:
    html = client.get("/surface/panel/", SERVER_NAME=ACME_HOST).content.decode()
    assert "bw-app" in html
    assert "bw-slide-over" in html


def test_surface_toast_action_returns_the_oob_wrapper(client: Client) -> None:
    resp = client.post("/surface/toast/", {}, HTTP_HX_REQUEST="true", SERVER_NAME=ACME_HOST)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'hx-swap-oob="afterbegin:#bw-toast-region"' in html
    assert "bw-toast--success" in html
    assert 'id="surface-toast-status"' in html
