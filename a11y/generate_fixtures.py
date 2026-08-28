"""Render brickwork pages to standalone HTML fixtures for the axe + no-JS suite.

Renders whole pages (list, dashboard, form, form-with-errors, wizard,
settings, console, confirm, auth, the three marketing pages) through the
shipped shells in both light and dark themes, inlines the compiled
brickwork.css, and writes self-contained HTML files under a11y/fixtures/.
Playwright then loads each file:// and runs axe-core (WCAG 2.2 AA) plus a
no-JS assertion.

Every page here is composed from a SHELL plus the shipped COMPONENTS, which
is what a consumer now does: 2.0.0 (ADR-056) retired the page and pattern
tier, so whole pages are copy-paste examples the consumer owns (see
src/brickwork/examples/, deliberately off the template loader path) rather
than templates to extend. The shells, components, forms, and nav are all
unchanged and still shipped, so rendering the REAL components in their real
compositions still means the a11y gate catches a contrast regression from a
bad token or a missing aria wiring on any shipped component.

Run: DJANGO_SETTINGS_MODULE=tests.settings_seams PYTHONPATH=src:.:tests \
     python a11y/generate_fixtures.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import django

django.setup()

from django import forms  # noqa: E402
from django.template import engines  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from brickwork.models import NavContext  # noqa: E402
from brickwork.services.navigation import resolve_active_item, visible_items  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
OUT = Path(__file__).resolve().parent / "fixtures"
OUT.mkdir(exist_ok=True)

_STATIC_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*brickwork\.css">')


def _inline_css(html: str) -> str:
    """Replace the {% static %} stylesheet link with the compiled CSS inline, so
    the fixture is self-contained for a file:// load."""
    return _STATIC_LINK.sub(f"<style>{CSS}</style>", html)


def _nav_context(request):
    from brickwork_testapp.nav import MAIN_NAV

    ctx = NavContext(request=request, permission_checker=lambda _p: True, feature_checker=lambda _f: True)
    items = visible_items(MAIN_NAV, ctx)
    active = resolve_active_item(items, request.resolver_match)
    return items, active


def _base_context(request, theme: str, *, layout: str = "sidebar"):
    items, active = _nav_context(request)
    return {
        "request": request,
        "bw_nav_items": items,
        "bw_active_nav_item": active,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        # the shell's SHL-001 layout ARG ("sidebar" default, or "topbar")
        "layout": layout,
    }


# The list page composition. 2.0.0 (ADR-056) retired the page/pattern tier:
# patterns/list.html is gone, so the fixture composes the shell and the
# components directly, the same shape a consumer now copies from
# examples/app/list.html. It extends the testapp's own chrome template (nav,
# breadcrumbs, account menu, switcher slots) so the fixture keeps exactly the
# page it had before: populated filter bar, titled alert, badge legend,
# card-wrapped records table, definition-variant summary table.
_LIST_SOURCE = (
    '{% extends "brickwork_testapp/base.html" %}'
    "{% load brickwork_components %}"
    "{% block page_title %}Widgets{% endblock %}"
    "{% block page_header %}"
    '{% include "brickwork/components/_page_header.html" %}'
    "{% endblock %}"
    "{% block page_actions %}"
    '{% bw_button "New widget" href="/widgets/new/" icon="plus" variant="primary" %}'
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    # the filter bar, wired from the real filter form
    '{% include "brickwork/components/_filter_bar.html" with fields=filter_form'
    ' filter_bar_id="widget-filters" clear_href="/widgets/" %}'
    # a titled banner alert so the axe gate covers the loud page-level status
    # surface with BOTH a title and a message, in both themes. Included rather
    # than called through {% bw_alert %}: the plain include is the shape the
    # copy-paste examples use (see examples/app/confirm.html).
    '{% include "brickwork/components/_alert.html" with variant="warning"'
    ' title="Planned maintenance" message="Widget exports are paused while'
    ' storage is upgraded. Existing widgets are unaffected." %}'
    # the widget lifecycle legend: all four intent badges, so the gate sees
    # every badge tint pair against both theme backgrounds
    '<p class="widget-status-legend">'
    '{% bw_badge "Active" variant="success" icon="check" %}'
    '{% bw_badge "Draft" variant="info" %}'
    '{% bw_badge "Archived" variant="warning" %}'
    '{% bw_badge "Deprecated" variant="danger" %}'
    "</p>"
    # the records table in a card: the pattern's old default table card,
    # inlined here as the card element wrapping the real _data_table.html
    '<div class="bw-card">'
    '<div class="bw-card__body">'
    '{% include "brickwork/components/_data_table.html" %}'
    "</div>"
    "</div>"
    # the definition-variant facts table (the row-header, one-entity shape)
    "<h2>Workspace summary</h2>"
    '{% include "brickwork/components/_data_table.html" with table_id="workspace-facts"'
    ' variant="definition" rows=summary_facts empty_heading="No summary yet"'
    ' empty_body="Create a widget to populate the workspace summary." %}'
    '{% include "brickwork/components/_pagination.html" %}'
    "</div>"
    "{% endblock %}"
)


def render_list(theme: str, *, menu_open: bool = False, layout: str = "sidebar") -> str:
    from brickwork_testapp.forms import WidgetFilterForm
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/widgets/")
    request.resolver_match = resolve("/widgets/")
    rows = [
        # row 1 is selected so the axe gate covers the selected-row treatment
        # (bw-data-table__row--selected) in both themes
        {"id": 1, "cells": ["Alpha", "Active"], "url": "/widgets/1/edit/", "selected": True},
        {"id": 2, "cells": ["Beta", "Draft"], "url": "/widgets/2/edit/"},
    ]
    columns = [
        {"label": "Name", "sortable": True, "sort_key": "name", "sort_key_desc": "-name", "next_sort": "-name"},
        {"label": "Status", "sortable": True, "sort_key": "status", "sort_key_desc": "-status", "next_sort": "status"},
    ]
    # the definition-variant facts table on the list page (matches the view's
    # summary_facts shape)
    summary_facts = [
        {"label": "Total widgets", "value": "2"},
        {"label": "Active", "value": "1"},
        {"label": "Draft", "value": "1"},
    ]
    ctx = _base_context(request, theme, layout=layout)
    ctx.update(
        {
            # _LIST_SOURCE composes the page from the shell and the
            # components, so the axe gate still examines the fully-composed
            # list page (AC-BW-077): populated filter bar, table card,
            # badges, titled alert, definition table, selected row.
            # columns/rows/table_id/empty_* feed the card-wrapped table.
            "title": "Widgets",
            "description": "Everything in the harness.",
            "filter_form": WidgetFilterForm(),
            "table_id": "widgets-table",
            "columns": columns,
            "rows": rows,
            "current_sort": "",
            "empty_heading": "No widgets yet",
            "empty_body": "Create your first widget to get started.",
            "summary_facts": summary_facts,
        }
    )
    if menu_open:
        # render the account-menu disclosure initially open so axe examines the
        # open panel (colour contrast, landmark labelling) in this theme
        ctx["account_menu_open"] = True
    html = engines["django"].from_string(_LIST_SOURCE).render(ctx, request=request)
    return _inline_css(html)


# The dashboard composition. As with _LIST_SOURCE, patterns/dashboard.html
# went with the 2.0.0 clean break (ADR-056), so the fixture composes the shell
# and the components directly, following examples/app/dashboard.html: the stat
# row in its own bw-stat-grid, a content card, and the recent-activity table
# card.
_DASHBOARD_SOURCE = (
    '{% extends "brickwork_testapp/base.html" %}'
    "{% block page_title %}Dashboard{% endblock %}"
    "{% block page_header %}"
    '{% include "brickwork/components/_page_header.html" %}'
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    # three stat tiles: up and down deltas so the glyph plus accessible-text
    # pairing is examined in both themes (BR-BW-TPL-007)
    '<div class="bw-stat-grid">'
    '{% include "brickwork/components/_stat.html" with label="Total widgets"'
    ' value=stats.total icon="folder" href="/widgets/" %}'
    '{% include "brickwork/components/_stat.html" with label="Active"'
    ' value=stats.active trend="up" trend_label="One more than last week" %}'
    '{% include "brickwork/components/_stat.html" with label="Draft"'
    ' value=stats.draft trend="down" trend_label="One fewer than last week" %}'
    "</div>"
    # the general-purpose content region
    '{% include "brickwork_testapp/_panel_card.html" with panel_title="Getting started"'
    ' panel_body="Create widgets, file them by status, and watch the workspace numbers move." %}'
    # the recent-activity table card, inlined the same way as on the list page
    "<h2>Recent activity</h2>"
    '<div class="bw-card">'
    '<div class="bw-card__body">'
    '{% include "brickwork/components/_data_table.html" %}'
    "</div>"
    "</div>"
    "</div>"
    "{% endblock %}"
)


def render_dashboard(theme: str) -> str:
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/dashboard/")
    request.resolver_match = resolve("/dashboard/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            # _DASHBOARD_SOURCE composes the same page the pattern used to
            # build: three stat tiles (up + down deltas so the glyph +
            # accessible-text pairing is examined in both themes,
            # BR-BW-TPL-007), the content card, and the recent-activity
            # table card (AC-BW-077).
            "title": "Dashboard",
            "description": "The workspace at a glance.",
            "stats": {"total": 2, "active": 1, "draft": 1},
            # the pattern's dashboard_activity default reads these from context
            "table_id": "activity-table",
            "columns": [
                {"label": "Name", "sortable": False},
                {"label": "Status", "sortable": False},
            ],
            "rows": [
                {"id": 1, "cells": ["Alpha", "Active"], "url": "/widgets/1/edit/"},
                {"id": 2, "cells": ["Beta", "Draft"], "url": "/widgets/2/edit/"},
            ],
            "empty_heading": "No activity yet",
            "empty_body": "Create a widget to see it appear here.",
        }
    )
    html = engines["django"].from_string(_DASHBOARD_SOURCE).render(ctx, request=request)
    return _inline_css(html)


def render_form(theme: str, *, with_errors: bool) -> str:
    from brickwork_testapp.forms import WidgetForm
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/widgets/new/")
    request.resolver_match = resolve("/widgets/new/")
    # name="invalid" + status="archived" triggers BOTH a field error (inline,
    # aria-describedby wired) and the non-field form-errors block, so the axe
    # gate sees both error surfaces in both themes.
    form = WidgetForm(data={"name": "invalid", "status": "archived"}) if with_errors else WidgetForm()
    if with_errors:
        form.is_valid()  # populate errors
    ctx = _base_context(request, theme)
    ctx["form"] = form
    return _inline_css(render_to_string("brickwork_testapp/widget_form.html", ctx, request=request))


# --- the 0.8.0 interaction set fixtures --------------------------------------
#
# interactions-<theme>.html            the composed floor page (first tab active)
# interactions-open-<theme>.html       server-renderable open floor states: the
#                                      second tab active + the first disclosure
#                                      open (axe sees the open floor; the open
#                                      dropdown/modal states are JS states and
#                                      are axed in a11y/interactions.spec.mjs)
# interactions-tab-lazy-<theme>.html   the lazy tab active, content inline (the
#                                      AC-BW-085 floor navigation target)
# interactions-js-<theme>.html         the JS leg: the same page plus the
#                                      host-app boot (Alpine + @alpinejs/focus
#                                      module builds and htmx from node_modules,
#                                      then registerBrickworkComponents(Alpine)
#                                      and Alpine.start(): the FIXTURE is the
#                                      host application here, so it may start
#                                      Alpine; brickwork itself never does)
# interactions-modal-page-<theme>.html the modal's full-page no-JS floor route
# fragments/modal-confirm.html         the htmx GET response (swapped into
#                                      #bw-modal-root); kept out of the axe
#                                      glob (a fragment is not a document)
# fragments/tab-panel-activity.html    the lazy panel hx-get response
#
# In-page URLs are rewired to fixture-relative targets so both Playwright legs
# exercise REAL navigations and REAL htmx swaps under file://.

FRAGMENTS = OUT / "fragments"

# The host-application boot for the JS leg. Loads the ESM module builds (the
# cdn builds auto-start Alpine, which would race the registration) plus the
# htmx classic script, from the repo's own node_modules two levels up from
# a11y/fixtures/. Requires alpinejs, @alpinejs/focus, and htmx.org as harness
# devDependencies.
_JS_BOOT = """<script src="../../node_modules/htmx.org/dist/htmx.min.js"></script>
<script type="module">
  import Alpine from "../../node_modules/alpinejs/dist/module.esm.js";
  import focus from "../../node_modules/@alpinejs/focus/dist/module.esm.js";
  import { registerBrickworkComponents } from "../../src/brickwork/static/brickwork/dist/brickwork.js";
  Alpine.plugin(focus);
  registerBrickworkComponents(Alpine);
  window.Alpine = Alpine;
  Alpine.start();
</script>
"""


def _rewire_interactions(html: str, theme: str) -> str:
    """Point in-page URLs at fixture-relative targets (file:// has no Django).

    Attribute-specific: the modal trigger's hx-get fetches the fragment while
    the same URL as href navigates to the full-page floor fixture, exactly
    mirroring the two documented render paths.
    """
    replacements = [
        ('hx-get="/interactions/confirm/"', 'hx-get="fragments/modal-confirm.html"'),
        ('href="/interactions/confirm/"', f'href="interactions-modal-page-{theme}.html"'),
        ('hx-get="/interactions/panels/activity/"', 'hx-get="fragments/tab-panel-activity.html"'),
        ('href="/interactions/?tab=overview"', f'href="interactions-{theme}.html"'),
        ('href="/interactions/?tab=details"', f'href="interactions-open-{theme}.html"'),
        ('href="/interactions/?tab=activity"', f'href="interactions-tab-lazy-{theme}.html"'),
        # dropdown item selection must stay on-page under file:// so the
        # keyboard suite can assert close-on-select + focus return
        ('href="/widgets/new/?via=dropdown"', 'href="#dd-new-widget"'),
        ('href="/widgets/?status=draft"', 'href="#dd-draft-widgets"'),
        # the nav entry and the modal's close_href both lead back to the page
        ('href="/interactions/"', f'href="interactions-{theme}.html"'),
    ]
    for old, new in replacements:
        html = html.replace(old, new)
    return html


def _interactions_request():
    from django.urls import resolve

    request = RequestFactory().get("/interactions/")
    request.resolver_match = resolve("/interactions/")
    return request


def render_interactions(
    theme: str,
    *,
    active_tab: str = "overview",
    disclosure_open: bool = False,
    inject_js: bool = False,
) -> str:
    from brickwork_testapp.views import interactions_context

    request = _interactions_request()
    ctx = _base_context(request, theme)
    ctx.update(interactions_context(active_tab, disclosure_open=disclosure_open))
    html = _inline_css(render_to_string("brickwork_testapp/interactions.html", ctx, request=request))
    html = _rewire_interactions(html, theme)
    if inject_js:
        html = html.replace("</body>", _JS_BOOT + "</body>")
    return html


def render_modal_page(theme: str) -> str:
    """The modal's no-JS floor: the confirm route rendered as a full page."""
    from django.urls import resolve

    request = RequestFactory().get("/interactions/confirm/")
    request.resolver_match = resolve("/interactions/confirm/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            "title": "Reset demo data",
            "modal_id": "confirm-reset",
            "close_href": "/interactions/",
            "backdrop_dismiss": True,
        }
    )
    html = _inline_css(render_to_string("brickwork_testapp/interaction_confirm.html", ctx, request=request))
    return _rewire_interactions(html, theme)


def render_modal_fragment() -> str:
    """The htmx GET response: the consumer's modal partial only. Written under
    fragments/ so the axe glob (documents only) never lints a bare fragment."""
    from django.urls import resolve

    request = RequestFactory().get("/interactions/confirm/", headers={"HX-Request": "true"})
    request.resolver_match = resolve("/interactions/confirm/")
    ctx = {
        "title": "Reset demo data",
        "modal_id": "confirm-reset",
        "close_href": "/interactions/",
        "backdrop_dismiss": True,
    }
    return render_to_string("brickwork_testapp/_confirm_modal.html", ctx, request=request)


def render_activity_fragment() -> str:
    return render_to_string("brickwork_testapp/_activity_panel.html")


# --- the 0.9.0 overlay-pair fixtures (toast, combobox, dismissible) -----------
#
# toasts-<theme>.html                  the toast page at rest: empty region,
#                                      the delivery form, and the dismissible
#                                      alert + badge with their close controls
#                                      still hidden (no dead control on the
#                                      no-JS floor)
# toasts-flash-<theme>.html            the plain-POST redirect state: the same
#                                      feedback rendered as a messages banner
#                                      alert (STA-008, the toast's no-JS
#                                      floor), zero toasts
# toasts-stack-<theme>.html            the full-page delivery path: four
#                                      persistent toasts (one per intent)
#                                      inside the region in the SETTLED
#                                      collapsed state (data-bw-visible
#                                      stamped, the oldest hidden, "+1 more"
#                                      revealed with its count filled), so axe
#                                      examines the stack and the overflow
#                                      control statically in both themes
# toasts-js-<theme>.html               the JS leg: the page plus the host-app
#                                      boot; the delivery buttons are rewired
#                                      to static OOB fragments so REAL htmx
#                                      swaps run under file://
# comboboxes-<theme>.html              the combobox page at rest: native
#                                      select floors visible, enhanced field
#                                      wrappers hidden (the no-JS floor)
# comboboxes-js-<theme>.html           the JS leg: tags pre-selected
#                                      (alpha + beta) so chips render at init;
#                                      the colour input's server-filter hx-get
#                                      rewired to a static option fragment
# fragments/toast-oob-<intent>.html    the htmx delivery response per intent
#                                      (the REAL _toast_oob.html partial).
#                                      duration "persistent" so stacks never
#                                      drain mid-test (the live endpoint
#                                      defaults to "normal"; the deviation is
#                                      test determinism only)
# fragments/toast-oob-short.html       duration "short" for the token-read
#                                      timing legs
# fragments/toast-oob-action.html      a persistent toast carrying the single
#                                      optional action link (CMP-023)
# fragments/combobox-options-green.html the filtered option-list response
#                                      (the REAL _combobox_options.html
#                                      partial, filtered as ?q=gre would be)
#
# SINGLE POINT OF ADJUSTMENT (lane coordination): every testapp URL, template
# name and stable id this section depends on is collected below. If the
# testapp lane shipped different names, fix them here and nowhere else.
TOASTS_PAGE_PATH = "/toasts/"
TOASTS_PAGE_TEMPLATE = "brickwork_testapp/toasts.html"
TOAST_ACTION_PATH = "/toasts/action/"
TOAST_OOB_TEMPLATE = "brickwork_testapp/_toast_oob.html"
COMBOBOX_PAGE_PATH = "/comboboxes/"
COMBOBOX_PAGE_TEMPLATE = "brickwork_testapp/comboboxes.html"
COMBOBOX_OPTIONS_PATH = "/comboboxes/options/colour/"
COMBOBOX_OPTIONS_TEMPLATE = "brickwork_testapp/_combobox_options.html"
COMBOBOX_LISTBOX_ID = "bw-listbox-id_colour"

_TOAST_MESSAGE = "Demo data saved."

# The four delivery intents, and the stacked-fixture order (newest first, as
# afterbegin prepending would leave them). The oldest sits beyond the three
# newest and carries the hidden attribute in the collapsed state.
_TOAST_INTENTS = ("success", "info", "warning", "danger")
_STACK_TOASTS = (
    ("toast-stack-1", "danger"),
    ("toast-stack-2", "success"),
    ("toast-stack-3", "warning"),
    ("toast-stack-4", "info"),
)


class _FlashMessage:
    """A rendered stand-in for a django.contrib.messages flash: toasts.html
    reads only str(message) and message.level_tag (the alert variant), so the
    fixture captures the redirect-then-banner state without the messages
    middleware."""

    level_tag = "success"

    def __str__(self) -> str:
        return _TOAST_MESSAGE


def _rewire_toasts_js(html: str) -> str:
    """Point the delivery form at static fragments (file:// has no Django).

    The form-level hx-post cannot POST under file://, so it is stripped and
    each intent button gains its own hx-get to that intent's pre-rendered OOB
    fragment: htmx cancels the native submit on a button carrying an hx
    attribute inside a form, so clicking a button performs a REAL htmx swap
    of the real response shape (main swap + OOB wrapper)."""
    html = html.replace(f'hx-post="{TOAST_ACTION_PATH}"', "")
    for intent in _TOAST_INTENTS:
        html = html.replace(
            f'name="intent" value="{intent}"',
            f'name="intent" value="{intent}" hx-get="fragments/toast-oob-{intent}.html" '
            'hx-target="#toast-demo-status" hx-swap="outerHTML"',
        )
    return html


def _toasts_request():
    from django.urls import resolve

    request = RequestFactory().get(TOASTS_PAGE_PATH)
    request.resolver_match = resolve(TOASTS_PAGE_PATH)
    return request


def render_toasts(theme: str, *, flash: bool = False, inject_js: bool = False) -> str:
    request = _toasts_request()
    ctx = _base_context(request, theme)
    # mirror ToastDemoView's context exactly (no fixture drift)
    ctx.update({"title": "Toasts", "description": "Server-delivered feedback, floor first."})
    if flash:
        ctx["messages"] = [_FlashMessage()]
    html = _inline_css(render_to_string(TOASTS_PAGE_TEMPLATE, ctx, request=request))
    if inject_js:
        html = _rewire_toasts_js(html)
        html = html.replace("</body>", _JS_BOOT + "</body>")
    return html


def _stack_toast_html(toast_id: str, intent: str, *, hidden: bool) -> str:
    """One server-rendered toast in its settled state: data-bw-visible is the
    marker bwToast stamps once the enter transition ran, and hidden is the
    collapse state bwToastRegion applies beyond the three newest; stamping
    both here models the settled stack for a static axe pass."""
    from django.template import Context, Template

    tag = Template(
        '{% load brickwork_interactions %}{% bw_toast message variant=intent duration="persistent" id=toast_id %}'
    )
    html = tag.render(Context({"message": _TOAST_MESSAGE, "intent": intent, "toast_id": toast_id}))
    settled = "data-bw-toast data-bw-visible hidden>" if hidden else "data-bw-toast data-bw-visible>"
    return html.replace("data-bw-toast>", settled)


def render_toast_stack(theme: str) -> str:
    """The full-page delivery path (BR-BW-HTMX-007 names it alongside the OOB
    wrapper): four intent toasts rendered inside the shell's region, in the
    collapsed overflow state with "+1 more" revealed and its count filled."""
    html = render_toasts(theme)
    toasts = "".join(
        _stack_toast_html(toast_id, intent, hidden=(toast_id == _STACK_TOASTS[-1][0]))
        for toast_id, intent in _STACK_TOASTS
    )
    html = html.replace("data-bw-toast-region>", "data-bw-toast-region>" + toasts, 1)
    html = html.replace(
        '<button class="bw-toast-region__more" type="button" hidden data-bw-toast-more>',
        '<button class="bw-toast-region__more" type="button" data-bw-toast-more>',
    )
    return html.replace("<span data-bw-toast-more-count>0</span>", "<span data-bw-toast-more-count>1</span>")


def render_toast_fragment(intent: str, duration: str) -> str:
    """The htmx delivery response: the REAL consumer partial (OOB wrapper plus
    the ordinary main swap), written under fragments/ so the axe glob (documents
    only) never lints it."""
    return render_to_string(TOAST_OOB_TEMPLATE, {"intent": intent, "duration": duration, "message": _TOAST_MESSAGE})


def render_toast_action_fragment() -> str:
    """The delivery response for a toast carrying the single optional action
    link (CMP-023). The testapp partial takes no action arguments, so the same
    wrapper shape is assembled here with a deterministic id the spec can
    address."""
    from django.template import Context, Template

    tag = Template(
        "{% load brickwork_interactions %}"
        '<div hx-swap-oob="afterbegin:#bw-toast-region">'
        '{% bw_toast message variant="info" duration="persistent" '
        'action_label="View widgets" action_href="#toast-action-target" id="toast-with-action" %}'
        "</div>\n"
        '<p id="toast-demo-status">Sent an action toast.</p>'
    )
    return tag.render(Context({"message": _TOAST_MESSAGE}))


def _rewire_comboboxes_js(html: str) -> str:
    """Point the server-filter hx-get at the static option fragment.

    hx-include="this" is stripped alongside: it would append ?q=... to the
    file:// URL, and the query's server-side travel is the Python integration
    suite's leg; the htmx leg here proves the debounced trigger, the request
    discipline, and the listbox swap. The form-level hx-post (the 422 path,
    equally Python-owned) is stripped so no file:// POST is ever attempted."""
    html = html.replace(f'hx-get="{COMBOBOX_OPTIONS_PATH}"', 'hx-get="fragments/combobox-options-green.html"')
    html = html.replace(' hx-include="this"', "")
    return html.replace(f'hx-post="{COMBOBOX_PAGE_PATH}"', "")


def render_comboboxes(theme: str, *, selected: bool = False, inject_js: bool = False) -> str:
    from brickwork_testapp.forms import SKILL_OPTIONS, ComboDemoForm
    from django.urls import resolve

    request = RequestFactory().get(COMBOBOX_PAGE_PATH)
    request.resolver_match = resolve(COMBOBOX_PAGE_PATH)
    ctx = _base_context(request, theme)
    # mirror ComboboxDemoView's context exactly (no fixture drift); the
    # selected variant carries initial tags so the chips run renders at init
    ctx.update(
        {
            "title": "Comboboxes",
            "description": "Filterable selection over a native select floor.",
            "skill_options": SKILL_OPTIONS,
        }
    )
    ctx["form"] = ComboDemoForm(initial={"tags": ["alpha", "beta"]}) if selected else ComboDemoForm()
    html = _inline_css(render_to_string(COMBOBOX_PAGE_TEMPLATE, ctx, request=request))
    if inject_js:
        html = _rewire_comboboxes_js(html)
        html = html.replace("</body>", _JS_BOOT + "</body>")
    return html


def render_combobox_options_fragment() -> str:
    """The server filter endpoint's response for a "gre" query: the REAL
    option-list partial with the one matching option."""
    return render_to_string(
        COMBOBOX_OPTIONS_TEMPLATE,
        {"listbox_id": COMBOBOX_LISTBOX_ID, "options": [("green", "Green")]},
    )


# --- the 0.10.0 Tailwind projection proof (AC-BW-095, the dynamic half) ------
#
# projection-<theme>.html is a CONSUMER page: no brickwork.css, no component
# classes, only Tailwind utilities from a REAL Tailwind 4 build over the
# shipped dist/tailwind-theme.css fragment (compiled at generation time by
# a11y/build-projection-css.mjs through @tailwindcss/node, the same compiler
# the Vite plugin uses), inlined alongside dist/tokens.css so the fixture is
# self-contained under file://. a11y/projection.spec.mjs asserts the utilities
# resolve through the LIVE --bw-* tokens: flipping data-theme and adding a
# data-bw-brand override both restyle the page with no rebuild. Both theme
# variants join the axe gate automatically (axe.spec.mjs walks every fixture
# .html in this directory).
#
# The single candidate list below feeds BOTH the Tailwind build (as argv, so
# the compiled CSS always contains exactly these utilities) and the page
# markup; keeping one list means the two can never drift.

PROJECTION_UTILITIES = (
    # the page canvas, so the dark fixture genuinely renders dark for axe
    "bg-surface",
    "text-fg",
    # the probed card: colour pair, radius step, elevation level, spacing
    # step, and a type role (size + line-height companion)
    "bg-accent",
    "text-fg-on-accent",
    "rounded-md",
    "shadow-3",
    "p-4",
    "text-body-lg",
)

# The brand override is baked into the page but inert until the spec stamps
# data-bw-brand="proof" on <html> (the shell's root hook: derived tokens
# compute at :root). oklch(0.5 0.2 300) is an arbitrary, visibly different
# purple; the spec compares computed values probe-to-probe against the same
# literal.
_PROJECTION_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tailwind projection proof (__THEME__)</title>
<style>__TOKENS_CSS__</style>
<style>__CONSUMER_CSS__</style>
<style>[data-bw-brand="proof"] { --bw-color-accent: oklch(0.5 0.2 300); }</style>
</head>
<body class="bg-surface text-fg">
<main>
  <h1 class="text-body-lg">Tailwind projection proof</h1>
  <p id="projection-card" class="bg-accent text-fg-on-accent rounded-md shadow-3 p-4 text-body-lg">
    Consumer utilities styled by the --bw-* tokens alone.
  </p>
</main>
</body>
</html>
"""


def build_projection_css() -> str:
    """Run the real Tailwind 4 consumer build once per generation run."""
    result = subprocess.run(
        ["node", str(ROOT / "a11y" / "build-projection-css.mjs"), *PROJECTION_UTILITIES],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return result.stdout


def render_projection(theme: str, consumer_css: str) -> str:
    tokens_css = (ROOT / "src/brickwork/static/brickwork/dist/tokens.css").read_text()
    return (
        _PROJECTION_PAGE.replace("__THEME__", theme)
        .replace("__TOKENS_CSS__", tokens_css)
        .replace("__CONSUMER_CSS__", consumer_css)
    )


# --- the 0.12.0 feedback fixtures (#56/#60) -----------------------------------
#
# feedback-<theme>.html is a standalone (non-shell) page, mirroring the
# projection fixture's self-contained shape rather than a full testapp route:
# these three components (skeleton, tooltip, progress) are isolated widgets
# with no dedicated demo page of their own yet, so the fixture composes the
# REAL component templates directly (bw_skeleton tag, an extends-consumed
# tooltip partial, and the plain-include progress bar) with the compiled
# brickwork.css inlined, exactly as the shell-routed fixtures inline it.
# Covers: a skeleton group (STA-004, aria-busy + hidden shapes), a tooltip
# (trigger + bubble, no-JS floor plus the JS-enhanced bwTooltip open state,
# WAI-ARIA APG Tooltip pattern), and a progress bar in both the determinate
# and indeterminate treatments (STA-007). The JS boot registers bwTooltip so
# axe also examines the OPEN bubble state, not just the floor.

_FEEDBACK_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feedback components (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Feedback components</h1>

  <section aria-labelledby="skeleton-heading">
    <h2 id="skeleton-heading">Skeleton</h2>
    __SKELETON__
  </section>

  <section aria-labelledby="tooltip-heading">
    <h2 id="tooltip-heading">Tooltip</h2>
    __TOOLTIP__
  </section>

  <section aria-labelledby="progress-heading">
    <h2 id="progress-heading">Progress</h2>
    __PROGRESS_DETERMINATE__
    __PROGRESS_INDETERMINATE__
  </section>
</main>
__JS_BOOT__
</body>
</html>
"""

_FEEDBACK_TOOLTIP_SOURCE = (
    '{% extends "brickwork/components/_tooltip.html" %}'
    "{% block tooltip_trigger %}"
    '<button type="button" class="bw-btn bw-btn--ghost bw-btn--sm bw-btn--icon-only" aria-label="More info">'
    "?"
    "</button>"
    "{% endblock %}"
)


def _render_skeleton_fixture() -> str:
    from django.template import Context, Template

    return Template('{% load brickwork_components %}{% bw_skeleton variant="row" count=3 %}').render(Context({}))


def _render_tooltip_fixture(*, open_state: bool) -> str:
    html = (
        engines["django"]
        .from_string(_FEEDBACK_TOOLTIP_SOURCE)
        .render({"id": "feedback-tip", "text": "More information about this field"})
    )
    if open_state:
        # Model the JS-enhanced open state statically (mirrors
        # render_toast_stack's settled-state stamping): bwTooltip.open()
        # removes `hidden` from the bubble and stamps data-bw-open on the
        # root, so axe also examines the bubble WHILE visible, not just the
        # closed no-JS floor. Regex rather than a literal-whitespace replace
        # so this survives a reformat of _tooltip.html's own indentation.
        html = re.sub(r"(x-data=\"bwTooltip\([^)]*\)\")", r"\1 data-bw-open", html, count=1)
        html = re.sub(r"(data-bw-tooltip-bubble)\s+hidden>", r"\1>", html, count=1)
    return html


def _render_progress_fixture(*, value: int | None, show_value: bool = False) -> str:
    ctx = {"label": "Import progress" if value is not None else "Loading widgets"}
    if value is not None:
        ctx["value"] = value
        ctx["show_value"] = show_value
    return render_to_string("brickwork/components/_progress.html", ctx)


def render_feedback(theme: str, *, inject_js: bool = False, tooltip_open: bool = False) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    page = (
        _FEEDBACK_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__SKELETON__", _render_skeleton_fixture())
        .replace("__TOOLTIP__", _render_tooltip_fixture(open_state=tooltip_open))
        .replace("__PROGRESS_DETERMINATE__", _render_progress_fixture(value=42, show_value=True))
        .replace("__PROGRESS_INDETERMINATE__", _render_progress_fixture(value=None))
    )
    return page.replace("__JS_BOOT__", _JS_BOOT if inject_js else "")


# --- the 0.13.0 input chrome fixtures (#57/#58) -------------------------------
#
# inputs-<theme>.html is a standalone (non-shell) page, mirroring the
# feedback fixture's self-contained shape: these components (toggle, tag
# input, dropzone, a styled date input) have no dedicated demo page of their
# own yet, so the fixture composes the REAL component templates directly
# (the {% bw_toggle %} tag, the tag-input and dropzone {% include %}
# partials, and a DateInput rendered through bw_field_widget for the
# ::-webkit-calendar-picker-indicator chrome) with the compiled brickwork.css
# inlined. Covers: a toggle switch (role=switch, WCAG 4.1.2 accessible name),
# a tag input (labelled text floor + the chip container Alpine enhances), a
# dropzone (native <input type="file">, visually hidden but never removed
# from the tab order or the a11y tree), and a styled date input.
#
# sidebar-collapsed-<theme>.html re-renders the ordinary list fixture (real
# shell, real nav) with the sidebar's [data-bw-collapsed] attribute stamped
# statically (mirroring render_toast_stack's settled-state stamping
# technique): axe then examines the COLLAPSED state itself, the one most at
# risk of losing nav-item accessible names, in both themes, not just the
# expanded floor every other shell-routed fixture already covers.

_INPUTS_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Input chrome (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Input chrome</h1>

  <section aria-labelledby="toggle-heading">
    <h2 id="toggle-heading">Toggle</h2>
    __TOGGLE__
  </section>

  <section aria-labelledby="tag-input-heading">
    <h2 id="tag-input-heading">Tag input</h2>
    __TAG_INPUT__
  </section>

  <section aria-labelledby="dropzone-heading">
    <h2 id="dropzone-heading">Dropzone</h2>
    __DROPZONE__
  </section>

  <section aria-labelledby="date-heading">
    <h2 id="date-heading">Date field</h2>
    __DATE_FIELD__
  </section>
</main>
</body>
</html>
"""


def _render_toggle_fixture() -> str:
    from django.template import Context, Template

    return Template('{% load brickwork_components %}{% bw_toggle "Email alerts" id="email-alerts" %}').render(
        Context({})
    )


def _render_tag_input_fixture() -> str:
    return render_to_string(
        "brickwork/components/_tag_input.html",
        {"label": "Skill tags", "id": "skill-tags", "name": "skill_tags", "value": "django,python"},
    )


def _render_dropzone_fixture() -> str:
    return render_to_string(
        "brickwork/components/_dropzone.html",
        {"label": "Upload files", "id": "upload", "name": "upload", "help_text": "PNG or JPG, up to 10MB."},
    )


def _render_date_field_fixture() -> str:
    from django import forms
    from django.template import Context, Template

    class _DateForm(forms.Form):
        starts_on = forms.DateField(widget=forms.DateInput, label="Starts on")

    field = _DateForm()["starts_on"]
    widget = Template("{% load brickwork_forms %}{% bw_field_widget field %}").render(Context({"field": field}))
    label = f'<label for="{field.auto_id}">{field.label}</label>'
    return f'<div class="bw-field">{label}<div class="bw-field__control">{widget}</div></div>'


def render_inputs(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _INPUTS_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__TOGGLE__", _render_toggle_fixture())
        .replace("__TAG_INPUT__", _render_tag_input_fixture())
        .replace("__DROPZONE__", _render_dropzone_fixture())
        .replace("__DATE_FIELD__", _render_date_field_fixture())
    )


# --- the bw_ranked_list fixture (icvoss/django-brickwork#183) -----------------
#
# ranked-list-<theme>.html is a standalone (non-shell) page, mirroring
# render_inputs' self-contained shape: the component has no dedicated demo
# page of its own yet, so the fixture composes the REAL {% bw_ranked_list %}
# tag directly (populated, linked rows; the empty branch composing
# _empty_state.html at size="sm"; the loading skeleton) with the compiled
# brickwork.css inlined. Covers: the ordered-list floor with visible label/
# value text and an aria-hidden bar (VIZ-015/COL-030), a linked row
# (VIZ-024), the empty state's action link, and the loading skeleton
# (STA-004).

_RANKED_LIST_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ranked list (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Ranked list</h1>

  <section aria-labelledby="ranked-list-populated-heading">
    <h2 id="ranked-list-populated-heading">Top accounts</h2>
    __RANKED_LIST_POPULATED__
  </section>

  <section aria-labelledby="ranked-list-empty-heading">
    <h2 id="ranked-list-empty-heading">Empty</h2>
    __RANKED_LIST_EMPTY__
  </section>

  <section aria-labelledby="ranked-list-loading-heading">
    <h2 id="ranked-list-loading-heading">Loading</h2>
    __RANKED_LIST_LOADING__
  </section>
</main>
</body>
</html>
"""

_RANKED_LIST_ROWS = [
    {"label": "Acme Corp", "amount": 4000, "value": "£4,000", "href": "/accounts/acme/"},
    {"label": "Globex", "amount": 3000, "value": "£3,000", "href": "/accounts/globex/"},
    {"label": "Initech", "amount": 1000, "value": "£1,000", "href": "/accounts/initech/"},
]


def _render_ranked_list_fixture(**ctx: object) -> str:
    from django.template import Context, Template

    return Template(
        "{% load brickwork_components %}"
        "{% bw_ranked_list rows=rows basis=basis label=label loading=loading "
        "empty_heading=empty_heading empty_body=empty_body "
        "empty_action_href=empty_action_href empty_action_label=empty_action_label %}"
    ).render(
        Context(
            {
                "rows": [],
                "basis": "max",
                "label": "",
                "loading": False,
                "empty_heading": "",
                "empty_body": "",
                "empty_action_href": "",
                "empty_action_label": "",
                **ctx,
            }
        )
    )


def render_ranked_list(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _RANKED_LIST_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace(
            "__RANKED_LIST_POPULATED__",
            _render_ranked_list_fixture(rows=_RANKED_LIST_ROWS, label="Top accounts"),
        )
        .replace(
            "__RANKED_LIST_EMPTY__",
            _render_ranked_list_fixture(
                empty_heading="No accounts yet",
                empty_body="Add one to see it here.",
                empty_action_href="/accounts/new/",
                empty_action_label="Add an account",
            ),
        )
        .replace("__RANKED_LIST_LOADING__", _render_ranked_list_fixture(loading=True))
    )


# --- Sparkline (VIZ-003/004/005/006) -----------------------------------------
#
# Covers: neutral tone (the plain single-series line), trend tone in all
# three directions (up/down/flat, each pairing the stroke colour with the
# decorative glyph + visually-hidden text VIZ-004/COL-030 require), and a
# highlighted point (VIZ-005). Sized inside a fixed-height wrapper so the
# viewBox-scaling <svg> (no intrinsic size of its own, per the component's
# own Responsive note) renders at a sane on-page size for axe/visual
# inspection, mirroring how _stat.html's own bw-stat__sparkline slot
# constrains this same shape.

_SPARKLINE_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sparkline (__THEME__)</title>
__CSS__
<style>.sparkline-demo { max-width: 16rem; block-size: 3rem; }</style>
</head>
<body class="bw-body">
<main>
  <h1>Sparkline</h1>

  <section aria-labelledby="sparkline-neutral-heading">
    <h2 id="sparkline-neutral-heading">Neutral</h2>
    <div class="sparkline-demo">__SPARKLINE_NEUTRAL__</div>
  </section>

  <section aria-labelledby="sparkline-trend-up-heading">
    <h2 id="sparkline-trend-up-heading">Trend, up</h2>
    <div class="sparkline-demo">__SPARKLINE_TREND_UP__</div>
  </section>

  <section aria-labelledby="sparkline-trend-down-heading">
    <h2 id="sparkline-trend-down-heading">Trend, down</h2>
    <div class="sparkline-demo">__SPARKLINE_TREND_DOWN__</div>
  </section>

  <section aria-labelledby="sparkline-trend-flat-heading">
    <h2 id="sparkline-trend-flat-heading">Trend, flat</h2>
    <div class="sparkline-demo">__SPARKLINE_TREND_FLAT__</div>
  </section>

  <section aria-labelledby="sparkline-highlight-heading">
    <h2 id="sparkline-highlight-heading">Highlighted point</h2>
    <div class="sparkline-demo">__SPARKLINE_HIGHLIGHT__</div>
  </section>
</main>
</body>
</html>
"""


def _render_sparkline_fixture(**ctx: object) -> str:
    from django.template import Context, Template

    return Template(
        "{% load brickwork_components %}"
        "{% bw_sparkline points=points label=label value=value tone=tone highlight_index=highlight_index %}"
    ).render(
        Context(
            {
                "points": [10, 12, 9, 14, 18, 15, 20],
                "label": "Revenue, last 7 days",
                "value": "",
                "tone": "neutral",
                "highlight_index": None,
                **ctx,
            }
        )
    )


def render_sparkline(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _SPARKLINE_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace(
            "__SPARKLINE_NEUTRAL__",
            _render_sparkline_fixture(value="1,234"),
        )
        .replace(
            "__SPARKLINE_TREND_UP__",
            _render_sparkline_fixture(points=[10, 11, 13, 16, 20], tone="trend", value="20"),
        )
        .replace(
            "__SPARKLINE_TREND_DOWN__",
            _render_sparkline_fixture(points=[20, 16, 13, 11, 10], tone="trend", value="10"),
        )
        .replace(
            "__SPARKLINE_TREND_FLAT__",
            _render_sparkline_fixture(points=[10, 10, 10, 10], tone="trend", value="10"),
        )
        .replace(
            "__SPARKLINE_HIGHLIGHT__",
            _render_sparkline_fixture(highlight_index=6, value="20"),
        )
    )


# --- the _data_table.html empty-state action CTA (icvoss/django-brickwork#185)
#
# data-table-empty-cta-<theme>.html is a standalone (non-shell) page,
# mirroring render_ranked_list's shape above: list-*/dashboard-*.html
# already cover the populated/sortable/definition/selected states with
# non-empty rows (AC-BW-077), so the empty branch's new action CTA is the
# one surface not otherwise reached: neither fixture ever renders
# _data_table.html with an empty rows list. Covers: the empty state's real
# <a class="bw-btn bw-btn--primary"> anchor, keyboard-reachable and labelled
# by empty_action_label, for both the records and definition variants.

_DATA_TABLE_EMPTY_CTA_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data table empty state (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Data table empty state</h1>

  <section aria-labelledby="data-table-empty-cta-records-heading">
    <h2 id="data-table-empty-cta-records-heading">Records, empty, with action</h2>
    __DATA_TABLE_EMPTY_CTA_RECORDS__
  </section>

  <section aria-labelledby="data-table-empty-cta-definition-heading">
    <h2 id="data-table-empty-cta-definition-heading">Definition, empty, with action</h2>
    __DATA_TABLE_EMPTY_CTA_DEFINITION__
  </section>
</main>
</body>
</html>
"""


def render_data_table_empty_cta(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    records_table = render_to_string(
        "brickwork/components/_data_table.html",
        {
            "table_id": "properties-table",
            "columns": [
                {"label": "Name", "sortable": False},
                {"label": "Status", "sortable": False},
            ],
            "rows": [],
            "empty_heading": "No properties yet",
            "empty_body": "Add your first property to see it listed here.",
            "empty_action_href": "/properties/new/",
            "empty_action_label": "Add your first property",
        },
    )
    definition_table = render_to_string(
        "brickwork/components/_data_table.html",
        {
            "table_id": "facts-table",
            "variant": "definition",
            "rows": [],
            "empty_heading": "No facts yet",
            "empty_body": "Facts appear here once the record is complete.",
            "empty_action_href": "/facts/new/",
            "empty_action_label": "Add a fact",
        },
    )
    return (
        _DATA_TABLE_EMPTY_CTA_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__DATA_TABLE_EMPTY_CTA_RECORDS__", records_table)
        .replace("__DATA_TABLE_EMPTY_CTA_DEFINITION__", definition_table)
    )


# --- the bw_theme_switch fixtures (icvoss/django-brickwork#117) ---------------
#
# theme-switch-<theme>.html    a standalone page (mirrors render_inputs'
#                               self-contained shape: the component has no
#                               dedicated demo page of its own yet) composing
#                               the REAL {% bw_theme_switch %} tag directly,
#                               no-JS floor: the control ships the
#                               bw-theme-switch--pre-init class (icvoss/
#                               django-brickwork#272, visibility: hidden,
#                               forced onto every descendant too, not only
#                               the root: supersedes the unconditional
#                               hidden attribute this shipped with through
#                               3.11.0), so axe examines an EMPTY page here
#                               (the control contributes nothing usable to
#                               the accessibility tree until JS reveals it).
# theme-switch-js-<theme>.html the JS leg: the real host-app boot
#                               (_JS_BOOT, real Alpine, real
#                               registerBrickworkComponents) so bwThemeSwitch
#                               actually runs its init() and reveals the
#                               control, exactly the reveal-at-init dismissible
#                               and tooltip legs already exercise; the axe
#                               loop then walks the REVEALED fieldsets of
#                               radios, not a static stand-in. Two instances
#                               on the one page (ADR-060: default axes "theme
#                               density dir", and a second, brand-inclusive
#                               instance via brands=) so axe also proves two
#                               live instances never collide (unique ids and
#                               radio group names, #117's own uniqueness
#                               contract), plus one locked-axis instance
#                               (locked_axes="theme": the disabled fieldset +
#                               note branch, #117's SHL-003 precedence rule)
#                               that no other fixture here renders.
# theme-switch-invalid-root-js-<theme>.html
#                               the JS leg with a BOGUS data-theme baked into
#                               <html> from render time (review fix, #117
#                               blocker 2: the consumer-template-mistake case
#                               has to be present in the served HTML, since a
#                               file:// page.reload() discards a
#                               page.evaluate() mutation before it ever
#                               reaches bwThemeSwitch's own init()).
# theme-switch-compact-open-js-<theme>.html
#                               layout="compact" (icvoss/django-brickwork#235),
#                               the JS leg, with the <details> disclosure
#                               stamped [open] statically in the served HTML
#                               (the render_sidebar_collapsed/
#                               render_theme_switch_invalid_root "stamp a
#                               settled state into the fixture" technique,
#                               never a page.evaluate() + reload, which a
#                               file:// reload would discard): axe needs the
#                               panel actually visible to examine the
#                               trigger/panel pairing and the compact
#                               options' own 44px target size, not a closed
#                               disclosure contributing nothing to the tree.
#                               A dedicated compact-only instance (axes=
#                               "theme density dir", layout="compact"), kept
#                               separate from the three inline instances
#                               above so neither page's own axe pass, nor the
#                               inline instances' own uniqueness contract,
#                               is disturbed by adding a fourth one there.
_THEME_SWITCH_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theme switch (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Theme switch</h1>

  <section aria-labelledby="default-heading">
    <h2 id="default-heading">Default axes</h2>
    __DEFAULT__
  </section>

  <section aria-labelledby="brand-heading">
    <h2 id="brand-heading">Brand-inclusive</h2>
    __BRAND__
  </section>

  <section aria-labelledby="locked-heading">
    <h2 id="locked-heading">Theme axis locked</h2>
    __LOCKED__
  </section>
</main>
__JS_BOOT__
</body>
</html>
"""


def _render_theme_switch_default_fixture() -> str:
    from django.template import Context, Template

    return Template("{% load brickwork_theming %}{% bw_theme_switch %}").render(Context({}))


def _render_theme_switch_brand_fixture() -> str:
    from django.template import Context, Template

    return Template(
        '{% load brickwork_theming %}{% bw_theme_switch axes="theme density dir brand" brands=brands %}'
    ).render(Context({"brands": {"acme": "Acme", "globex": "Globex"}}))


def _render_theme_switch_locked_fixture(theme: str) -> str:
    from django.template import Context, Template

    # bw_theme MUST match this page's own <html data-theme="__THEME__">
    # substitution below (icvoss/django-brickwork#117 review): the locked
    # radio's checked state is resolved from bw_theme at RENDER time, the
    # same context variable the shell itself reads, never from <html> at JS
    # runtime, so this fixture's server render and its own <html> attribute
    # have to agree by construction, exactly as a real resolver-backed page
    # would (resolve_theme_attributes -> the SAME value onto both bw_theme
    # and the shell's own <html data-theme>).
    return Template('{% load brickwork_theming %}{% bw_theme_switch axes="theme" locked_axes="theme" %}').render(
        Context({"bw_theme": theme})
    )


# chart-card-<theme>.html is a standalone (non-shell) page, mirroring
# render_ranked_list's self-contained shape above: the component has no
# dedicated demo page of its own yet, so the fixture EXTENDS the real
# _chart_card.html (title/actions/chart_legend blocks filled, exactly as a
# consumer would) for the populated, loading, error and empty states, plus a
# populated card demonstrating legend_position="side", with the compiled
# brickwork.css inlined. Covers: the real {% bw_chart_mount %} tag's
# accessible-name pairing (role="img" + aria-label, CHT-012) in the populated
# card, the loading skeleton (STA-004), the composed _alert.html error
# surface (STA-008/009, CHT-010), and the composed _empty_state.html at
# size="sm" with its action link (STA-001/002, CHT-008).

_CHART_CARD_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chart card (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Chart card</h1>

  <section aria-labelledby="chart-card-populated-heading">
    <h2 id="chart-card-populated-heading">Revenue by month</h2>
    __CHART_CARD_POPULATED__
  </section>

  <section aria-labelledby="chart-card-side-legend-heading">
    <h2 id="chart-card-side-legend-heading">Side legend</h2>
    __CHART_CARD_SIDE_LEGEND__
  </section>

  <section aria-labelledby="chart-card-loading-heading">
    <h2 id="chart-card-loading-heading">Loading</h2>
    __CHART_CARD_LOADING__
  </section>

  <section aria-labelledby="chart-card-error-heading">
    <h2 id="chart-card-error-heading">Error</h2>
    __CHART_CARD_ERROR__
  </section>

  <section aria-labelledby="chart-card-empty-heading">
    <h2 id="chart-card-empty-heading">Empty</h2>
    __CHART_CARD_EMPTY__
  </section>
</main>
</body>
</html>
"""


def _render_chart_card_fixture(*, title: str = "", legend: str = "", **ctx: object) -> str:
    from django.template import Context, Template

    blocks = ""
    if title:
        blocks += f'{{% block title %}}<h2 class="bw-card__title">{title}</h2>{{% endblock %}}'
    if legend:
        blocks += f'{{% block chart_legend %}}<div class="bw-chart-card__legend">{legend}</div>{{% endblock %}}'
    source = "{% extends 'brickwork/components/_chart_card.html' %}{% load brickwork_components %}" + blocks
    return Template(source).render(Context(ctx))


def render_chart_card(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    from django.template import Context, Template
    from django.utils.safestring import mark_safe

    mount = Template(
        "{% load brickwork_components %}"
        '{% bw_chart_mount aria_label="Revenue by month" min_height="16rem" aspect_ratio="16 / 9" %}'
    ).render(Context({}))
    return (
        _CHART_CARD_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace(
            "__CHART_CARD_POPULATED__",
            _render_chart_card_fixture(title="Revenue by month", mount=mark_safe(mount)),  # noqa: S308
        )
        .replace(
            "__CHART_CARD_SIDE_LEGEND__",
            _render_chart_card_fixture(
                title="Signups by channel",
                legend="Organic, Paid, Referral",
                legend_position="side",
                mount=mark_safe(mount),  # noqa: S308
            ),
        )
        .replace("__CHART_CARD_LOADING__", _render_chart_card_fixture(title="Revenue by month", loading=True))
        .replace(
            "__CHART_CARD_ERROR__",
            _render_chart_card_fixture(
                title="Revenue by month",
                error=True,
                error_title="Could not load",
                error_message="Try again later.",
            ),
        )
        .replace(
            "__CHART_CARD_EMPTY__",
            _render_chart_card_fixture(
                title="Revenue by month",
                empty=True,
                empty_body="Nothing to plot yet.",
                empty_action_href="/reports/new/",
                empty_action_label="Create a report",
            ),
        )
    )


# --- the bw_theme_switch fixtures (icvoss/django-brickwork#117) ---------------
#
# theme-switch-<theme>.html    a standalone page (mirrors render_inputs'
#                               self-contained shape: the component has no
#                               dedicated demo page of its own yet) composing
#                               the REAL {% bw_theme_switch %} tag directly,
#                               no-JS floor: the control ships the
#                               bw-theme-switch--pre-init class (icvoss/
#                               django-brickwork#272, visibility: hidden,
#                               forced onto every descendant too, not only
#                               the root: supersedes the unconditional
#                               hidden attribute this shipped with through
#                               3.11.0), so axe examines an EMPTY page here
#                               (the control contributes nothing usable to
#                               the accessibility tree until JS reveals it).
# theme-switch-js-<theme>.html the JS leg: the real host-app boot
#                               (_JS_BOOT, real Alpine, real
#                               registerBrickworkComponents) so bwThemeSwitch
#                               actually runs its init() and reveals the
#                               control, exactly the reveal-at-init dismissible
#                               and tooltip legs already exercise; the axe
#                               loop then walks the REVEALED fieldsets of
#                               radios, not a static stand-in. Two instances
#                               on the one page (ADR-060: default axes "theme
#                               density dir", and a second, brand-inclusive
#                               instance via brands=) so axe also proves two
#                               live instances never collide (unique ids and
#                               radio group names, #117's own uniqueness
#                               contract), plus one locked-axis instance
#                               (locked_axes="theme": the disabled fieldset +
#                               note branch, #117's SHL-003 precedence rule)
#                               that no other fixture here renders.
# theme-switch-invalid-root-js-<theme>.html
#                               the JS leg with a BOGUS data-theme baked into
#                               <html> from render time (review fix, #117
#                               blocker 2: the consumer-template-mistake case
#                               has to be present in the served HTML, since a
#                               file:// page.reload() discards a
#                               page.evaluate() mutation before it ever
#                               reaches bwThemeSwitch's own init()).
# theme-switch-compact-open-js-<theme>.html
#                               layout="compact" (icvoss/django-brickwork#235),
#                               the JS leg, with the <details> disclosure
#                               stamped [open] statically in the served HTML
#                               (the render_sidebar_collapsed/
#                               render_theme_switch_invalid_root "stamp a
#                               settled state into the fixture" technique,
#                               never a page.evaluate() + reload, which a
#                               file:// reload would discard): axe needs the
#                               panel actually visible to examine the
#                               trigger/panel pairing and the compact
#                               options' own 44px target size, not a closed
#                               disclosure contributing nothing to the tree.
#                               A dedicated compact-only instance (axes=
#                               "theme density dir", layout="compact"), kept
#                               separate from the three inline instances
#                               above so neither page's own axe pass, nor the
#                               inline instances' own uniqueness contract,
#                               is disturbed by adding a fourth one there.
_THEME_SWITCH_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theme switch (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Theme switch</h1>

  <section aria-labelledby="default-heading">
    <h2 id="default-heading">Default axes</h2>
    __DEFAULT__
  </section>

  <section aria-labelledby="brand-heading">
    <h2 id="brand-heading">Brand-inclusive</h2>
    __BRAND__
  </section>

  <section aria-labelledby="locked-heading">
    <h2 id="locked-heading">Theme axis locked</h2>
    __LOCKED__
  </section>
</main>
__JS_BOOT__
</body>
</html>
"""


def _render_theme_switch_default_fixture() -> str:
    from django.template import Context, Template

    return Template("{% load brickwork_theming %}{% bw_theme_switch %}").render(Context({}))


def _render_theme_switch_brand_fixture() -> str:
    from django.template import Context, Template

    return Template(
        '{% load brickwork_theming %}{% bw_theme_switch axes="theme density dir brand" brands=brands %}'
    ).render(Context({"brands": {"acme": "Acme", "globex": "Globex"}}))


def _render_theme_switch_locked_fixture(theme: str) -> str:
    from django.template import Context, Template

    # bw_theme MUST match this page's own <html data-theme="__THEME__">
    # substitution below (icvoss/django-brickwork#117 review): the locked
    # radio's checked state is resolved from bw_theme at RENDER time, the
    # same context variable the shell itself reads, never from <html> at JS
    # runtime, so this fixture's server render and its own <html> attribute
    # have to agree by construction, exactly as a real resolver-backed page
    # would (resolve_theme_attributes -> the SAME value onto both bw_theme
    # and the shell's own <html data-theme>).
    return Template('{% load brickwork_theming %}{% bw_theme_switch axes="theme" locked_axes="theme" %}').render(
        Context({"bw_theme": theme})
    )


_TREND_INDICATOR_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trend indicator (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Trend indicator</h1>

  <section aria-labelledby="trend-indicator-up-heading">
    <h2 id="trend-indicator-up-heading">Up, with label</h2>
    __TREND_INDICATOR_UP__
  </section>

  <section aria-labelledby="trend-indicator-down-heading">
    <h2 id="trend-indicator-down-heading">Down, no label</h2>
    __TREND_INDICATOR_DOWN__
  </section>

  <section aria-labelledby="trend-indicator-flat-heading">
    <h2 id="trend-indicator-flat-heading">Flat</h2>
    __TREND_INDICATOR_FLAT__
  </section>
</main>
</body>
</html>
"""


def _render_trend_indicator_fixture(**ctx: object) -> str:
    return render_to_string("brickwork/components/_trend_indicator.html", ctx)


def render_trend_indicator(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _TREND_INDICATOR_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__TREND_INDICATOR_UP__", _render_trend_indicator_fixture(trend="up", trend_label="17 days faster"))
        .replace("__TREND_INDICATOR_DOWN__", _render_trend_indicator_fixture(trend="down"))
        .replace("__TREND_INDICATOR_FLAT__", _render_trend_indicator_fixture(trend="flat"))
    )


# --- the _data_table.html empty-state action CTA (icvoss/django-brickwork#185)
#
# data-table-empty-cta-<theme>.html is a standalone (non-shell) page,
# mirroring render_ranked_list's shape above: list-*/dashboard-*.html
# already cover the populated/sortable/definition/selected states with
# non-empty rows (AC-BW-077), so the empty branch's new action CTA is the
# one surface not otherwise reached: neither fixture ever renders
# _data_table.html with an empty rows list. Covers: the empty state's real
# <a class="bw-btn bw-btn--primary"> anchor, keyboard-reachable and labelled
# by empty_action_label, for both the records and definition variants.

_DATA_TABLE_EMPTY_CTA_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data table empty state (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Data table empty state</h1>

  <section aria-labelledby="data-table-empty-cta-records-heading">
    <h2 id="data-table-empty-cta-records-heading">Records, empty, with action</h2>
    __DATA_TABLE_EMPTY_CTA_RECORDS__
  </section>

  <section aria-labelledby="data-table-empty-cta-definition-heading">
    <h2 id="data-table-empty-cta-definition-heading">Definition, empty, with action</h2>
    __DATA_TABLE_EMPTY_CTA_DEFINITION__
  </section>
</main>
</body>
</html>
"""


def render_theme_switch(theme: str, *, inject_js: bool = False) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    page = (
        _THEME_SWITCH_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__DEFAULT__", _render_theme_switch_default_fixture())
        .replace("__BRAND__", _render_theme_switch_brand_fixture())
        .replace("__LOCKED__", _render_theme_switch_locked_fixture(theme))
    )
    return page.replace("__JS_BOOT__", _JS_BOOT if inject_js else "")


def render_theme_switch_invalid_root(theme: str) -> str:
    """The JS leg with a BOGUS data-theme baked into <html> from render time
    (icvoss/django-brickwork#117 review): the consumer-template-mistake case
    (a stray or mistyped data-theme value) has to be present in the SERVED
    HTML, not applied via a post-load page.evaluate() + page.reload(), since
    a file:// reload re-fetches the static file and any prior DOM mutation
    is lost before bwThemeSwitch's own init() ever sees it (a reload proves
    nothing about a value that was never actually there when the page
    loaded). Stamped statically here, mirroring render_sidebar_collapsed's
    own "stamp a CSS/DOM state into the fixture" technique, rather than
    mutating and reloading."""
    html = render_theme_switch(theme, inject_js=True)
    return html.replace(
        f'<html lang="en" data-theme="{theme}">', '<html lang="en" data-theme="MISCONFIGURED-VALUE">', 1
    )


_THEME_SWITCH_COMPACT_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theme switch, compact (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Theme switch, compact</h1>

  <section aria-labelledby="compact-heading">
    <h2 id="compact-heading">Compact disclosure</h2>
    __COMPACT__
  </section>

  <!-- Trailing flow content (tester follow-up, icvoss/django-brickwork#272
  gate run): the compact control's own root is display: inline-flex, sized
  to its trigger, with the [open] panel taken out of flow via position:
  absolute, so nothing about the trigger's own box changing size or
  visibility moves the trigger itself. Without a sibling block AFTER it,
  the reveal has nothing in normal flow to displace, so the Layout
  Instability API records no entry at all even when the control genuinely
  regresses to the old zero-footprint-until-init defect: the page has
  nothing below the control that COULD move. This section mirrors the
  issue's own consumer measurement (the actions row growing pushes a
  sibling MAIN block down by its own height delta): a real block of body
  content after the control, so a reveal that changes the trigger's flow
  height (broken) genuinely displaces this content, while a reveal that
  only changes visibility (fixed, box already reserved) does not. -->
  <section aria-labelledby="compact-body-heading">
    <h2 id="compact-body-heading">Body content</h2>
    <p>This paragraph sits after the compact control in normal flow, the same
    relationship the issue's own consumer measurement showed (a header
    actions row growing pushes page content below it). Its own position is
    what the layout-shift assertion below actually measures.</p>
  </section>
</main>
__JS_BOOT__
</body>
</html>
"""


def _render_theme_switch_compact_fixture() -> str:
    from django.template import Context, Template

    return Template(
        '{% load brickwork_theming %}{% bw_theme_switch axes="theme density dir" layout="compact" %}'
    ).render(Context({}))


def render_theme_switch_compact(theme: str) -> str:
    """layout="compact" (icvoss/django-brickwork#235), the NO-JS floor
    (icvoss/django-brickwork#272 review): no _JS_BOOT at all, disclosure
    left closed exactly as the server renders it. Proves the reserved
    pre-init state (bw-theme-switch--pre-init) genuinely hides the compact
    control too, not only the inline instances the pre-existing no-JS test
    covered: the two layouts share one root element, but only a dedicated
    render of the compact tag proves it, since theme-switch-<theme>.html
    never renders layout="compact" at all."""
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _THEME_SWITCH_COMPACT_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__COMPACT__", _render_theme_switch_compact_fixture())
        .replace("__JS_BOOT__", "")
    )


def render_theme_switch_compact_open(theme: str) -> str:
    """layout="compact" (icvoss/django-brickwork#235), the JS leg, with the
    <details> disclosure stamped [open] statically in the served HTML (the
    render_sidebar_collapsed/render_theme_switch_invalid_root "stamp a
    settled state into the fixture" technique): a file:// page.reload()
    would discard a page.evaluate()-driven open(), so the open state has to
    already be in the markup the page is served with for axe to examine the
    trigger/panel pairing and the compact options' own target sizes, rather
    than a closed disclosure that contributes nothing to the tree."""
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    page = (
        _THEME_SWITCH_COMPACT_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__COMPACT__", _render_theme_switch_compact_fixture())
        .replace("__JS_BOOT__", _JS_BOOT)
    )
    return page.replace(
        '<details class="bw-theme-switch__disclosure">', '<details class="bw-theme-switch__disclosure" open>', 1
    )


def render_sidebar_collapsed(theme: str) -> str:
    """The list fixture's shell, with the sidebar's collapsed CSS state
    stamped statically so axe examines [data-bw-collapsed] itself (SHL-004:
    nav labels clip visually but must stay in the accessible tree)."""
    html = render_list(theme)
    html = html.replace(
        '<aside class="bw-sidebar" id="bw-sidebar"', '<aside class="bw-sidebar" data-bw-collapsed id="bw-sidebar"', 1
    )
    html = html.replace('aria-expanded="true"', 'aria-expanded="false"', 1)
    return html


# --- the 0.14.0 slide-over + stepper + wizard fixtures (#55/#59) --------------
#
# slide-over-open-<theme>.html  the slide-over's OPEN state, stamped
#                               statically (mirroring the tooltip-open and
#                               sidebar-collapsed techniques above): bwSlideOver
#                               sets isOpen, [data-bw-open] on the root, and
#                               moves focus into the panel, so this fixture
#                               emulates that settled state without a JS boot,
#                               giving axe a real dialog-open surface to walk
#                               (dialog semantics, labelling, focusable
#                               content) in both themes.
# stepper-<theme>.html          a standalone page (mirrors render_feedback's
#                               shape) with all three step statuses present
#                               (complete/current/upcoming) so axe examines
#                               the aria-current wiring and the glyph +
#                               hidden-text status pairing.
# wizard-<theme>.html           patterns/wizard.html rendered through the
#                               full shell (mirrors render_list/render_
#                               dashboard: a real pattern page, not a
#                               standalone fixture) with the stepper plus a
#                               minimal step form and a back link, so axe
#                               examines the composed page.

_SLIDE_OVER_OPEN_SOURCE = (
    '{% extends "brickwork/components/_slide_over.html" %}'
    "{% block slide_over_body %}"
    '<form id="fx-slide-over-form"><label for="fx-slide-over-input">Widget name'
    '<input id="fx-slide-over-input" name="name" data-bw-autofocus></label></form>'
    "{% endblock %}"
    '{% block slide_over_footer %}<footer class="bw-slide-over__footer">'
    '<button type="submit" form="fx-slide-over-form">Save</button></footer>{% endblock %}'
)

_STEPPER_STEPS = [
    {"label": "Account", "status": "complete"},
    {"label": "Business details", "status": "current"},
    {"label": "Review", "status": "upcoming"},
]

_STEPPER_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stepper (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Stepper</h1>
  <section aria-labelledby="stepper-heading">
    <h2 id="stepper-heading">Horizontal</h2>
    __STEPPER_HORIZONTAL__
  </section>
  <section aria-labelledby="stepper-vertical-heading">
    <h2 id="stepper-vertical-heading">Vertical</h2>
    __STEPPER_VERTICAL__
  </section>
</main>
</body>
</html>
"""


def render_slide_over_open(theme: str) -> str:
    """The slide-over's JS-set OPEN state, stamped statically (the fixture
    boots no Alpine): [data-bw-open] on the root plus the removed hidden
    guard, matching what bwSlideOver.open() does at runtime, so axe examines
    the panel while genuinely presented, not the closed no-JS floor."""
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    body = engines["django"].from_string(_SLIDE_OVER_OPEN_SOURCE).render({"title": "Edit widget"})
    body = re.sub(r'(x-data="bwSlideOver\([^)]*\)")', r"\1 data-bw-open", body, count=1)
    page = (
        "<!doctype html>\n"
        f'<html lang="en" data-theme="{theme}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Slide-over open ({theme})</title>\n"
        f"<style>{css}</style>\n"
        "</head>\n"
        '<body class="bw-body">\n'
        "<main><h1>Slide-over (open)</h1></main>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )
    return page


def render_stepper(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    horizontal = render_to_string(
        "brickwork/components/_stepper.html", {"steps": _STEPPER_STEPS, "orientation": "horizontal"}
    )
    vertical = render_to_string(
        "brickwork/components/_stepper.html", {"steps": _STEPPER_STEPS, "orientation": "vertical"}
    )
    return (
        _STEPPER_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__STEPPER_HORIZONTAL__", horizontal)
        .replace("__STEPPER_VERTICAL__", vertical)
    )


# The wizard step composition. patterns/wizard.html was retired with the rest
# of the page tier in 2.0.0 (ADR-056), so this composes the shell and the
# components directly, following examples/app/wizard.html: page header,
# stepper, the step's own form, and the back-link nav row.
_WIZARD_SOURCE = (
    '{% extends "brickwork/shell/app.html" %}'
    "{% block page_title %}Set up your store{% endblock %}"
    "{% block page_header %}"
    '{% include "brickwork/components/_page_header.html" %}'
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    '{% include "brickwork/components/_stepper.html" with orientation=stepper_orientation %}'
    '<div class="bw-wizard__step">'
    '<form id="fx-wizard-form"><label for="fx-wizard-input">Business name'
    '<input id="fx-wizard-input" name="business_name" data-bw-autofocus></label>'
    '<button type="submit">Continue</button></form>'
    "</div>"
    '<nav class="bw-wizard__nav" aria-label="Wizard navigation">'
    '<a class="bw-btn bw-btn--ghost" href="{{ back_url }}">Back</a>'
    "</nav>"
    "</div>"
    "{% endblock %}"
)


def render_wizard(theme: str) -> str:
    """A wizard step rendered through the full shell, mirroring
    render_list/render_dashboard: a minimal step form plus a back link, so
    axe examines the composed page (stepper + step body + nav)."""
    from django.urls import resolve

    request = RequestFactory().get("/interactions/")
    request.resolver_match = resolve("/interactions/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            "title": "Set up your store",
            "description": "A quick multi-step setup.",
            "steps": _STEPPER_STEPS,
            "back_url": "/interactions/",
        }
    )
    html = engines["django"].from_string(_WIZARD_SOURCE).render(ctx)
    return _inline_css(html)


# --- the 0.15.0 table bulk-selection + whole-form fixtures (#53/#54) ---------
#
# table-selection-<theme>.html   a standalone page (mirrors render_feedback's
#                                shape) composing the REAL _data_table.html
#                                with selectable=True plus the REAL
#                                _bulk_actions_bar.html (extend-consumed, both
#                                inside one shared <form>), a couple of rows,
#                                one pre-checked, so axe examines the row
#                                checkboxes' labelling, the header select-all
#                                checkbox, and the always-visible bulk bar.
# bw-form-<theme>.html          a standalone page composing {% bw_form %}
#                                twice: a valid grid-layout render and a
#                                bound-invalid render (both field-level and
#                                non-field errors), inside a bare <form> the
#                                fixture itself owns (mirrors the documented
#                                consumer contract), so axe examines the
#                                whole-form renderer's field chrome, grid
#                                layout, and 422 error surfaces.

_TABLE_SELECTION_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Table selection (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Table selection</h1>
  <form method="post" action="#">
    __BULK_BAR__
    __TABLE__
  </form>
</main>
</body>
</html>
"""

_TABLE_SELECTION_BULK_BAR_SOURCE = (
    '{% extends "brickwork/components/_bulk_actions_bar.html" %}'
    "{% block bulk_actions_buttons %}"
    '<button type="submit" name="bulk_action" value="archive">Archive</button>'
    '<button type="submit" name="bulk_action" value="delete">Delete</button>'
    "{% endblock %}"
)


def render_table_selection(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    bulk_bar = (
        engines["django"].from_string(_TABLE_SELECTION_BULK_BAR_SOURCE).render({"select_all_href": "?select_all=1"})
    )
    columns = [
        {"label": "Name", "sortable": False},
        {"label": "Status", "sortable": False},
    ]
    rows = [
        {"id": 1, "cells": ["Alpha", "Active"], "selected": True},
        {"id": 2, "cells": ["Beta", "Draft"]},
    ]
    table = render_to_string(
        "brickwork/components/_data_table.html",
        {
            "table_id": "selection-table",
            "columns": columns,
            "rows": rows,
            "selectable": True,
            "sticky_header": True,
        },
    )
    return (
        _TABLE_SELECTION_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__BULK_BAR__", bulk_bar)
        .replace("__TABLE__", table)
    )


# --- the bwSortable set (icvoss/django-brickwork#214) ------------------------
#
# sortable-<theme>.html      the no-JS floor ONLY: three items, each with a
#                            real move-up/move-down <form method="post">
#                            pair (BR-BW-HTMX-001, documented in
#                            frontend/src/js/sortable.js's own header), and
#                            no drag/keyboard chrome at all (nothing for
#                            bwSortable to enhance without JS present).
# sortable-js-<theme>.html   the same list, boots Alpine + htmx, adds
#                            x-data="bwSortable(...)" and the aria-live
#                            status region: axe examines the JS-enhanced
#                            list, a11y/sortable.spec.mjs drives the drag
#                            and keyboard paths and the persistence POST.

_SORTABLE_ITEM_SOURCE = """{% for item in items %}<li class="bw-sortable-item" data-bw-sort-id="{{ item.id }}" draggable="{{ draggable|yesno:'true,false' }}">
  <span>{{ item.label }}</span>
  <form method="post" action="#">
    <button type="submit" name="move" value="up-{{ item.id }}" {% if forloop.first %}disabled{% endif %}>Move up</button>
    <button type="submit" name="move" value="down-{{ item.id }}" {% if forloop.last %}disabled{% endif %}>Move down</button>
  </form>
</li>
{% endfor %}"""

_SORTABLE_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sortable list (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Sortable list</h1>
  <div>
    <ul __XDATA__>
      __ITEMS__
    </ul>
    __STATUS__
  </div>
</main>
</body>
</html>
"""

_SORTABLE_ITEMS = [
    {"id": 1, "label": "Alpha"},
    {"id": 2, "label": "Beta"},
    {"id": 3, "label": "Gamma"},
]


def render_sortable(theme: str, *, inject_js: bool = False, with_url: bool = False) -> str:
    """with_url=False (the default JS fixture) leaves bwSortable's url unset,
    so _persist()'s own guard no-ops and a move's resulting DOM order is
    observable directly: this repo's own reorder fragment mock is STATIC
    (it cannot echo the posted order back), so wiring a url would round-trip
    every move through htmx.ajax and silently revert it to the fragment's
    fixed order before the test could assert against it. with_url=True
    (sortable-js-persist-<theme>.html) is for the dedicated persistence
    round-trip test alone, which asserts the swap itself rather than a
    sequence of moves."""
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    items = (
        engines["django"].from_string(_SORTABLE_ITEM_SOURCE).render({"items": _SORTABLE_ITEMS, "draggable": inject_js})
    )
    url = "fragments/sortable-reorder.html" if with_url else ""
    xdata = f"x-data=\"bwSortable({{ url: '{url}' }})\"" if inject_js else ""
    status = (
        '<div data-bw-sort-status data-bw-sort-status-template="Position {position} of {count}" '
        'aria-live="polite" class="bw-visually-hidden"></div>'
        if inject_js
        else ""
    )
    html = (
        _SORTABLE_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__XDATA__", xdata)
        .replace("__ITEMS__", items)
        .replace("__STATUS__", status)
    )
    if inject_js:
        html = html.replace("</body>", _JS_BOOT + "</body>")
    return html


# --- the bwTagInput carrier set (icvoss/django-brickwork#237) ----------------
#
# tag-input-js-<theme>.html   two REAL {% include %} instances of
#                              _tag_input.html (single-line and multiline),
#                              wrapped in a real <form> so the commit-on-
#                              submit data-loss guard has something to
#                              listen for, and boots Alpine so bwTagInput's
#                              own init() performs the carrier takeover
#                              (a11y/tag_input.spec.mjs drives chip commit,
#                              chip remove, carrier serialisation, and
#                              commit-on-submit for both variants). The
#                              static (non-JS) tag input already renders
#                              inside inputs-<theme>.html above; this page
#                              exists only for the JS leg.

_TAG_INPUT_JS_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tag input carrier (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Tag input carrier</h1>
  <form id="tag-input-form" method="post" action="#">
    <section aria-labelledby="tag-input-heading">
      <h2 id="tag-input-heading">Tag input</h2>
      __TAG_INPUT__
    </section>
    <section aria-labelledby="tag-input-multiline-heading">
      <h2 id="tag-input-multiline-heading">Tag input (multiline)</h2>
      __TAG_INPUT_MULTILINE__
    </section>
    <button type="submit">Save</button>
  </form>
</main>
</body>
</html>
"""


def _render_tag_input_multiline_fixture() -> str:
    return render_to_string(
        "brickwork/components/_tag_input.html",
        {
            "label": "Related topics",
            "id": "related-topics",
            "name": "related_topics",
            "value": "alpha,beta",
            "multiline": True,
        },
    )


def render_tag_input_js(theme: str) -> str:
    """The JS leg for bwTagInput's carrier takeover (#237): both the
    single-line and multiline floors, each pre-filled with two committed
    tags via `value`, so the fixture's own load already exercises the 422
    re-render parse path (init() reads the server-rendered value into chips
    before the carrier takeover runs)."""
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    html = (
        _TAG_INPUT_JS_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__TAG_INPUT__", _render_tag_input_fixture())
        .replace("__TAG_INPUT_MULTILINE__", _render_tag_input_multiline_fixture())
    )
    return html.replace("</body>", _JS_BOOT + "</body>")


def render_sortable_reorder_fragment() -> str:
    """The persistence endpoint's response: the REAL <ul> markup re-rendered
    server-side, exactly as bwSortable's outerHTML swap expects. outerHTML
    targets the root ELEMENT alone (the <ul>), never its status sibling, so
    this returns only that element, matching a real reorder view's response
    shape (a11y/sortable.spec.mjs drives the round trip)."""
    items = engines["django"].from_string(_SORTABLE_ITEM_SOURCE).render({"items": _SORTABLE_ITEMS, "draggable": True})
    return f"<ul x-data=\"bwSortable({{ url: 'fragments/sortable-reorder.html' }})\">{items}</ul>"


_BW_FORM_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Whole-form renderer (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Whole-form renderer</h1>
  <section aria-labelledby="valid-heading">
    <h2 id="valid-heading">Grid layout</h2>
    <form method="post" action="#">
      __VALID_FORM__
      <button type="submit">Save</button>
    </form>
  </section>
  <section aria-labelledby="invalid-heading">
    <h2 id="invalid-heading">Bound, invalid</h2>
    <form method="post" action="#">
      __INVALID_FORM__
      <button type="submit">Save</button>
    </form>
  </section>
</main>
</body>
</html>
"""


def render_bw_form_fixture(theme: str) -> str:
    from brickwork_testapp.forms import WidgetForm

    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    valid_form = WidgetForm()
    invalid_form = WidgetForm(data={"name": "invalid", "status": "archived"})
    invalid_form.is_valid()  # populate field + non-field errors
    valid_html = (
        engines["django"]
        .from_string('{% load brickwork_forms %}{% bw_form form layout="grid" grid_columns=2 %}')
        .render({"form": valid_form})
    )
    invalid_html = (
        engines["django"].from_string("{% load brickwork_forms %}{% bw_form form %}").render({"form": invalid_form})
    )
    return (
        _BW_FORM_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__VALID_FORM__", valid_html)
        .replace("__INVALID_FORM__", invalid_html)
    )


# --- the 1.1.0 page-templates kit fixtures (#73's account-menu sign-out is
# fixtured alongside them since both ship in the same release) -------------
#
# Every page below composes a shell plus components directly. The shipped
# page tier (brickwork/pages/*.html) was retired in 2.0.0 (ADR-056): whole
# pages are now copy-paste examples the consumer owns, so these fixtures
# follow the same compositions the shipped examples carry (see
# src/brickwork/examples/app/*.html and examples/auth/signin.html) rather
# than extending a package-supplied page.
#
# form-page-<theme>.html         the app shell plus a real consumer <form>
#                                 wrapping {% bw_form form %} and a submit
#                                 button.
# settings-<theme>.html          the app shell plus {% bw_tabs %} over a
#                                 non-empty settings_tabs + active_tab (the
#                                 real tabs floor) and a _card wrapping
#                                 {% bw_form %}.
# console-<theme>.html           the app shell plus _empty_state.html, wired
#                                 from heading+body.
# console-sm-<theme>.html        the app shell plus _empty_state.html at
#                                 size="sm" (#218), nested inside a bw-card.
# confirm-<theme>.html           the centred shell plus a warning _alert and
#                                 a POST form + cancel link.
# auth-signin-<theme>.html       the auth shell plus a consumer <form>
#                                 wrapping {% bw_form form %} (a small
#                                 login-shaped form), a submit, a secondary
#                                 link, and the shell's brand_wordmark filled
#                                 so axe sees the branded panel.
# account-menu-post-<theme>.html a standalone page (mirrors render_feedback's
#                                 self-contained shape) rendering
#                                 _account_menu.html OPEN with a normal link
#                                 item and a method="post" danger sign-out
#                                 item, rendered with a request+CSRF context
#                                 so the token renders.

# Composes the app shell and the components directly: the page tier was
# retired in 2.0.0 (ADR-056). Follows examples/app/form.html, where the
# consumer owns the <form> element and the submit sits inside it beside the
# fields.
_FORM_PAGE_SOURCE = (
    "{% extends 'brickwork/shell/app.html' %}"
    "{% load brickwork_forms brickwork_components %}"
    "{% block page_title %}New widget{% endblock %}"
    "{% block page_header %}"
    '{% include "brickwork/components/_page_header.html" %}'
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    '<form method="post" action="/widgets/new/">'
    "{% csrf_token %}"
    "{% bw_form form %}"
    '{% bw_button label="Save" type="submit" variant="primary" %}'
    "</form>"
    "</div>"
    "{% endblock %}"
)


def render_form_page(theme: str) -> str:
    from brickwork_testapp.forms import WidgetForm
    from django.urls import resolve

    request = RequestFactory().get("/widgets/new/")
    request.resolver_match = resolve("/widgets/new/")
    ctx = _base_context(request, theme)
    ctx.update({"title": "New widget", "description": "Create a widget.", "form": WidgetForm()})
    html = engines["django"].from_string(_FORM_PAGE_SOURCE).render(ctx, request=request)
    return _inline_css(html)


_SETTINGS_TABS = [
    {"key": "profile", "label": "Profile"},
    {"key": "billing", "label": "Billing"},
]

# Composes the app shell and the components directly: the page tier was
# retired in 2.0.0 (ADR-056). Follows examples/app/settings.html: {% bw_tabs %}
# over the server-selected active_tab (each tab a real ?tab= link, so the
# no-JS floor is free), then the active section's body.
_SETTINGS_BODY_SOURCE = (
    "{% extends 'brickwork/shell/app.html' %}"
    "{% load brickwork_forms brickwork_interactions %}"
    "{% block page_title %}Settings{% endblock %}"
    "{% block page_header %}"
    '{% include "brickwork/components/_page_header.html" %}'
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    "{% bw_tabs settings_tabs active=active_tab id='settings' %}"
    '<div class="bw-card">'
    '<div class="bw-card__body">'
    "{% bw_form form %}"
    "</div>"
    "</div>"
    "</div>"
    "{% endblock %}"
)


def render_settings(theme: str) -> str:
    from brickwork_testapp.forms import WidgetForm
    from django.urls import resolve

    request = RequestFactory().get("/settings/?tab=profile")
    request.resolver_match = resolve("/settings/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            "title": "Settings",
            "settings_tabs": _SETTINGS_TABS,
            "active_tab": "profile",
            "form": WidgetForm(),
        }
    )
    html = engines["django"].from_string(_SETTINGS_BODY_SOURCE).render(ctx)
    return _inline_css(html)


# Composes the app shell and the components directly: the page tier was
# retired in 2.0.0 (ADR-056). Follows examples/app/console.html: a blank-slate
# section whose body is _empty_state.html, wired from the heading and body the
# fixture supplies (the component ships no default copy, STA-003).
_CONSOLE_SOURCE = (
    "{% extends 'brickwork/shell/app.html' %}"
    "{% block page_header %}"
    '{% include "brickwork/components/_page_header.html" %}'
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    '{% include "brickwork/components/_empty_state.html" %}'
    "</div>"
    "{% endblock %}"
)


def render_console(theme: str, *, size: str | None = None) -> str:
    from django.urls import resolve

    request = RequestFactory().get("/dashboard/")
    request.resolver_match = resolve("/dashboard/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            "title": "Reports",
            "bw_page_title": "Reports",
            "heading": "No reports yet",
            "body": "Generate your first report to see it appear here.",
        }
    )
    # size="sm" (ADR-060, STA-019, #218): the in-panel scale, exercised here
    # nested inside a bw-card rather than the bare page-filling default, so
    # axe sees the demoted <p> heading and the plain action-link treatment
    # against a bounded container, not just the page-filling floor above.
    if size == "sm":
        ctx["size"] = "sm"
        source = (
            "{% extends 'brickwork/shell/app.html' %}"
            "{% block page_header %}"
            '{% include "brickwork/components/_page_header.html" %}'
            "{% endblock %}"
            "{% block content %}"
            '<div class="bw-section-stack">'
            '<div class="bw-card">'
            '<div class="bw-card__body">'
            '{% include "brickwork/components/_empty_state.html" %}'
            "</div></div></div>"
            "{% endblock %}"
        )
        html = engines["django"].from_string(source).render(ctx, request=request)
        return _inline_css(html)
    html = engines["django"].from_string(_CONSOLE_SOURCE).render(ctx, request=request)
    return _inline_css(html)


# Composes the CENTRED shell and the components directly: the page tier was
# retired in 2.0.0 (ADR-056). Follows examples/app/confirm.html, which drops
# the sidebar and topbar so a confirmation is a deliberate interruption; the
# destructive action is a POST form and cancel is a plain anchor.
_CONFIRM_SOURCE = (
    "{% extends 'brickwork/shell/centred.html' %}"
    "{% load brickwork_components %}"
    "{% block page_title %}Delete this widget?{% endblock %}"
    "{% block content %}"
    '<div class="bw-section-stack">'
    "<h1>Delete this widget?</h1>"
    '<div class="bw-alert bw-alert--warning" role="alert">'
    '<div class="bw-alert__body">'
    '<p class="bw-alert__title">Delete this widget?</p>'
    '<p class="bw-alert__message">This cannot be undone.</p>'
    "</div>"
    "</div>"
    '<form method="post" action="/widgets/1/delete/">'
    "{% csrf_token %}"
    '{% bw_button label="Delete" type="submit" variant="danger" %}'
    "</form>"
    '{% bw_button label="Cancel" href="/widgets/" variant="ghost" %}'
    "</div>"
    "{% endblock %}"
)


def render_confirm(theme: str) -> str:
    request = RequestFactory().get("/widgets/1/delete/")
    ctx = {"request": request, "bw_theme": theme, "bw_density": "comfortable", "bw_dir": "ltr"}
    html = engines["django"].from_string(_CONFIRM_SOURCE).render(ctx, request=request)
    return _inline_css(html)


class _DemoSigninForm(forms.Form):
    """A small login-shaped form, deliberately backend-agnostic-named (the
    field name is not asserted anywhere; the fixture only proves the axe
    gate examines real, labelled field chrome inside auth_body)."""

    email = forms.EmailField(label="Email address")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


# Composes the AUTH shell and the components directly: the page tier was
# retired in 2.0.0 (ADR-056). Follows examples/auth/signin.html: brickwork
# ships no auth view, form, or URL and names no field, so the heading, the
# <form>, and the secondary link all live here, in the page the consumer owns.
_AUTH_SIGNIN_SOURCE = (
    "{% extends 'brickwork/shell/auth.html' %}"
    "{% load brickwork_forms brickwork_components %}"
    "{% block page_title %}Sign in{% endblock %}"
    '{% block brand_wordmark %}<span class="bw-auth__brand">Acme</span>{% endblock %}'
    "{% block content %}"
    '<div class="bw-section-stack">'
    "<h1>Sign in</h1>"
    '<form method="post" action="/accounts/login/">'
    "{% csrf_token %}"
    "{% bw_form form %}"
    '{% bw_button label="Sign in" type="submit" variant="primary" %}'
    "</form>"
    '{% bw_button label="Forgot password?" href="/accounts/password/reset/" variant="ghost" size="sm" %}'
    "</div>"
    "{% endblock %}"
)


def render_auth_signin(theme: str) -> str:
    request = RequestFactory().get("/accounts/login/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "form": _DemoSigninForm(),
    }
    html = engines["django"].from_string(_AUTH_SIGNIN_SOURCE).render(ctx, request=request)
    return _inline_css(html)


_ACCOUNT_MENU_ITEMS = [
    {"label": "Settings", "url": "/settings/", "icon": "settings"},
    {"label": "Sign out", "url": "/logout/", "icon": "log-out", "danger": True, "method": "post"},
]

_ACCOUNT_MENU_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Account menu, POST sign-out (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Account menu (open, POST sign-out)</h1>
  __ACCOUNT_MENU__
</main>
</body>
</html>
"""


def render_account_menu_post(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    request = RequestFactory().get("/")
    menu_html = render_to_string(
        "brickwork/components/_account_menu.html",
        {"items": _ACCOUNT_MENU_ITEMS, "menu_open": True},
        request=request,
    )
    return (
        _ACCOUNT_MENU_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__ACCOUNT_MENU__", menu_html)
    )


# --- the 1.2.0 marketing kit fixtures (brickwork.marketing, BR-BW-MKT-002) ---
#
# The three marketing pages went the same way as the app page tier in 2.0.0
# (ADR-056), so each fixture below composes the marketing shell and the
# marketing section components directly, filling every band with
# representative content so axe still examines the fully composed page.
#
# landing-<theme>.html   hero, logo cloud, feature grid, stat band,
#                        testimonial, CTA.
# pricing-<theme>.html   hero, a 3-tier pricing table (one highlighted, "Most
#                        popular" badge), FAQ, CTA.
# about-<theme>.html     hero, a prose about body, stat band, testimonial,
#                        CTA.
#
# None of the three needs a resolver_match: the marketing shell's nav is a
# plain list of links with no active-route resolver dependency
# (04-interfaces.md 4d), unlike the app shell's {% bw_nav %}.
#
# The header, footer, and legal chrome is identical across the three, so it is
# shared here rather than repeated in each source string.
_MARKETING_CHROME = (
    "{% load brickwork_components %}"
    "{% block marketing_nav %}"
    '<a href="#features">Features</a>'
    '<a href="#pricing">Pricing</a>'
    '<a href="#about">About</a>'
    "{% endblock %}"
    "{% block marketing_actions %}"
    '<a href="#signin">Sign in</a>'
    '{% bw_button "Get started" href="#start" variant="primary" size="sm" %}'
    "{% endblock %}"
    "{% block footer_legal %}&copy; 2026 Acme Ltd. All rights reserved.{% endblock %}"
)

# The section includes, each wired from the same context names the retired
# marketing pages wired them from, so every fixture's context data is unchanged.
_MKT_HERO = (
    '{% include "brickwork_marketing/components/_hero.html" with eyebrow=eyebrow'
    " heading=heading lede=lede primary_cta=primary_cta secondary_cta=secondary_cta"
    " media=media align=align %}"
)
_MKT_STATS = '{% include "brickwork_marketing/components/_stat_band.html" with heading=stats_heading stats=stats %}'
_MKT_TESTIMONIAL = (
    '{% include "brickwork_marketing/components/_testimonial.html" with quote=quote'
    " author=author role=role avatar=avatar logo=testimonial_logo %}"
)
_MKT_CTA = (
    '{% include "brickwork_marketing/components/_cta.html" with heading=cta_heading'
    " body=cta_body primary_cta=cta_primary secondary_cta=cta_secondary"
    " band=cta_band %}"
)

_LANDING_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _MKT_HERO
    + '{% include "brickwork_marketing/components/_logo_cloud.html" with'
    " heading=logo_cloud_heading logos=logos greyscale=logo_cloud_greyscale %}"
    '{% include "brickwork_marketing/components/_feature_grid.html" with'
    " heading=features_heading lede=features_lede items=features"
    " columns=features_columns %}" + _MKT_STATS + _MKT_TESTIMONIAL + _MKT_CTA + "{% endblock %}"
    "{% block marketing_footer %}"
    '<div class="bw-marketing-footer__group">'
    "<h3>Product</h3>"
    '<a href="#features">Features</a>'
    '<a href="#pricing">Pricing</a>'
    "</div>"
    '<div class="bw-marketing-footer__group">'
    "<h3>Company</h3>"
    '<a href="#about">About</a>'
    '<a href="#contact">Contact</a>'
    "</div>"
    "{% endblock %}"
)

_PRICING_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _MKT_HERO
    + '{% include "brickwork_marketing/components/_pricing_table.html" with'
    " heading=pricing_heading lede=pricing_lede tiers=tiers note=pricing_note %}"
    '{% include "brickwork_marketing/components/_faq.html" with heading=faq_heading'
    " items=faq_items single_open=faq_single_open %}" + _MKT_CTA + "{% endblock %}"
)

_ABOUT_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _MKT_HERO
    + '<div class="bw-section-stack">'
    "<h2>Our story</h2>"
    "<p>Acme was founded in 2019 to make widget management simple for teams of"
    " every size. What started as a weekend project is now trusted by teams"
    " across the world.</p>"
    "<p>We believe software should be fast, accessible, and beautiful by"
    " default, so every team can focus on their work, not their tools.</p>"
    "</div>" + _MKT_STATS + _MKT_TESTIMONIAL + _MKT_CTA + "{% endblock %}"
)

_MARKETING_LOGOS = [
    {"src": "/static/demo/acme.svg", "alt": "Acme Corp"},
    {"src": "/static/demo/globex.svg", "alt": "Globex"},
    {"src": "/static/demo/initech.svg", "alt": "Initech"},
]

_MARKETING_FEATURES = [
    {"icon": "check", "heading": "Fast by default", "body": "Every page loads in under a second, out of the box."},
    {"icon": "lock", "heading": "Secure", "body": "SOC 2 Type II certified, with audit logs on every action."},
    {"icon": "users", "heading": "Built for teams", "body": "Roles, permissions, and shared workspaces from day one."},
]

_MARKETING_STATS = [
    {"value": "10,000+", "label": "Teams"},
    {"value": "99.9%", "label": "Uptime"},
    {"value": "24%", "label": "Faster onboarding", "trend": "up", "trend_label": "24% faster than last quarter"},
]

_MARKETING_TESTIMONIAL = {
    "quote": "Acme cut our onboarding time in half and the support team is fantastic.",
    "author": "Ada Lovelace",
    "role": "VP Engineering, Globex",
}

_MARKETING_TIERS = [
    {
        "name": "Starter",
        "price": "$9",
        "period": "/month",
        "description": "For individuals and small teams.",
        "features": ["Up to 5 users", "Community support"],
        "cta": {"label": "Choose Starter", "url": "#starter"},
    },
    {
        "name": "Pro",
        "price": "$29",
        "period": "/month",
        "description": "For growing teams.",
        "features": ["Up to 50 users", "Priority support", "Advanced analytics"],
        "cta": {"label": "Choose Pro", "url": "#pro"},
        "highlighted": True,
        "badge": "Most popular",
    },
    {
        "name": "Enterprise",
        "price": "Contact us",
        "description": "For large organisations.",
        "features": ["Unlimited users", "Dedicated support", "Custom SLAs"],
        "cta": {"label": "Contact sales", "url": "#enterprise"},
    },
]

_MARKETING_FAQ = [
    {"question": "Can I cancel at any time?", "answer": "Yes, cancel from your billing settings at any time."},
    {"question": "Is there a free trial?", "answer": "Every plan starts with a 14-day free trial, no card required."},
    {"question": "Do you offer discounts for non-profits?", "answer": "Yes, contact sales for a non-profit discount."},
]

_MARKETING_CTA = {
    "cta_heading": "Ready to get started?",
    "cta_body": "Join thousands of teams already using Acme.",
    "cta_primary": {"label": "Start free trial", "url": "#start"},
    "cta_secondary": {"label": "Talk to sales", "url": "#sales"},
}


def render_landing(theme: str) -> str:
    request = RequestFactory().get("/marketing/landing/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Acme",
        "bw_page_title": "Acme: ship faster, together",
        "eyebrow": "New: Acme 2.0",
        "heading": "Ship faster, together",
        "lede": "The all-in-one platform for teams who want to spend less time on tooling and more time building.",
        "primary_cta": {"label": "Get started", "url": "#start"},
        "secondary_cta": {"label": "See features", "url": "#features"},
        "logo_cloud_heading": "Trusted by teams at",
        "logos": _MARKETING_LOGOS,
        "features_heading": "Everything you need",
        "features_lede": "One platform, every workflow.",
        "features": _MARKETING_FEATURES,
        "stats_heading": "By the numbers",
        "stats": _MARKETING_STATS,
        **_MARKETING_TESTIMONIAL,
        **_MARKETING_CTA,
    }
    html = engines["django"].from_string(_LANDING_SOURCE).render(ctx, request=request)
    return _inline_css(html)


def render_pricing(theme: str) -> str:
    request = RequestFactory().get("/marketing/pricing/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Pricing",
        "bw_page_title": "Pricing, Acme",
        "eyebrow": "Pricing",
        "heading": "Plans for every team",
        "lede": "Simple, transparent pricing. No hidden fees.",
        "pricing_heading": "Choose your plan",
        "tiers": _MARKETING_TIERS,
        "pricing_note": "Prices exclude applicable tax. Annual billing saves 20%.",
        "faq_heading": "Frequently asked questions",
        "faq_items": _MARKETING_FAQ,
        "faq_single_open": True,
        **_MARKETING_CTA,
    }
    html = engines["django"].from_string(_PRICING_SOURCE).render(ctx, request=request)
    return _inline_css(html)


def render_about(theme: str) -> str:
    request = RequestFactory().get("/marketing/about/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "About Acme",
        "bw_page_title": "About, Acme",
        "eyebrow": "About us",
        "heading": "We're building the future of team software",
        "lede": "Founded in 2019, Acme is trusted by teams across the world.",
        "stats_heading": "Acme in numbers",
        "stats": _MARKETING_STATS,
        **_MARKETING_TESTIMONIAL,
        **_MARKETING_CTA,
    }
    html = engines["django"].from_string(_ABOUT_SOURCE).render(ctx, request=request)
    return _inline_css(html)


# --- the hero media_placement axis (ADR-057 section 1a, icvoss/django-brickwork#118) ---
#
# None of landing/pricing/about above ever passes media_placement, so they all
# render the "below" default: the "behind" and "beside" CSS this option adds
# (.bw-hero--media-behind, .bw-hero--media-beside in frontend/src/marketing.css)
# had no fixture rendering it, so axe was never actually examining it and the
# 320-414px sweep never actually measured "beside" collapsing to one column.
#
# "behind" is the contrast-sensitive one (headline over an illustration), so
# this fixture stacks THREE behind heroes with different media, to prove the
# scrim/inverse-surface contrast guarantee holds regardless of what the
# caller passes as media, not just for one hand-picked image:
#   1. no media at all (the section still needs to hold its own contrast)
#   2. a very light illustration (pale background, pale shapes)
#   3. a very dark illustration (near-black background)
# A "beside" hero follows, with a real <img> in its media slot so the radius
# scoping change (img keeps --bw-radius-lg, svg does not) is exercised here
# alongside the placement axis itself.
_HERO_PLACEMENT_BEHIND_NO_MEDIA = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Behind, no media" heading="Still legible with nothing behind it"'
    ' lede="The inverse surface and scrim are the contrast guarantee, not the media."'
    ' primary_cta=primary_cta media_placement="behind" %}'
)
_HERO_PLACEMENT_BEHIND_LIGHT_MEDIA = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Behind, light media" heading="Legible over a pale illustration"'
    ' lede="A light backdrop is the harder case for a scrim to hold contrast against."'
    ' primary_cta=primary_cta media=light_media media_placement="behind" %}'
)
_HERO_PLACEMENT_BEHIND_DARK_MEDIA = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Behind, dark media" heading="Legible over a near-black illustration"'
    ' lede="A dark backdrop should not need a different scrim to stay legible."'
    ' primary_cta=primary_cta media=dark_media media_placement="behind" %}'
)
_HERO_PLACEMENT_BESIDE = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Beside" heading="Copy and media side by side from 48rem"'
    ' lede="Collapses to one column below the breakpoint; must not scroll the page sideways."'
    ' primary_cta=primary_cta secondary_cta=secondary_cta media=beside_media media_placement="beside" %}'
)

_HERO_PLACEMENT_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _HERO_PLACEMENT_BEHIND_NO_MEDIA
    + _HERO_PLACEMENT_BEHIND_LIGHT_MEDIA
    + _HERO_PLACEMENT_BEHIND_DARK_MEDIA
    + _HERO_PLACEMENT_BESIDE
    + "{% endblock %}"
)


def render_hero_media_placement(theme: str) -> str:
    from django.utils.safestring import mark_safe

    request = RequestFactory().get("/marketing/hero-media-placement/")
    # Decorative (the illustration repeats what the copy already says), so it
    # is hidden from the accessibility tree rather than given an empty
    # role="img"/aria-label (axe correctly flags an empty accessible name),
    # matching sections/hero/split-media.html's own documented convention.
    light_media = mark_safe(  # noqa: S308 - our own fixture markup
        '<svg viewBox="0 0 480 320" aria-hidden="true" focusable="false">'
        '<rect width="480" height="320" fill="#f5f2e9"/>'
        '<circle cx="240" cy="160" r="90" fill="#ece5d3"/>'
        "</svg>"
    )
    dark_media = mark_safe(  # noqa: S308 - our own fixture markup
        '<svg viewBox="0 0 480 320" aria-hidden="true" focusable="false">'
        '<rect width="480" height="320" fill="#050506"/>'
        '<circle cx="240" cy="160" r="90" fill="#121214"/>'
        "</svg>"
    )
    beside_media = mark_safe('<img src="/static/demo/acme.svg" alt="" width="480" height="320">')  # noqa: S308
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Hero media placement",
        "bw_page_title": "Hero media placement, Acme",
        "primary_cta": {"label": "Get started", "url": "#start"},
        "secondary_cta": {"label": "See features", "url": "#features"},
        "light_media": light_media,
        "dark_media": dark_media,
        "beside_media": beside_media,
    }
    html = engines["django"].from_string(_HERO_PLACEMENT_SOURCE).render(ctx, request=request)
    return _inline_css(html)


# --- the CTA width axis (ADR-057 section 1a, #98/#118 pattern) ----------------
#
# width="bleed" (bw-cta--bleed) had no fixture rendering it before this: none
# of landing/pricing/about/sections-<theme>.html ever pass width, so axe never
# examined the escape-the-shell CSS and the 320-414px sweep never actually
# measured whether a full-bleed band avoids the classic horizontal-overflow
# bug. This fixture stacks all four band x width combinations (tint/plain x
# contained/bleed) so the source-order specificity tie between .bw-cta--tint
# and .bw-cta--bleed (both single-class selectors) is exercised on a real
# tinted, full-bleed band, not just read off the CSS.
_CTA_WIDTH_CONTAINED_PLAIN = (
    '{% include "brickwork_marketing/components/_cta.html" with'
    ' heading="Contained, plain band" body="The unchanged default: no width, no band override."'
    ' primary_cta_label="Start free trial" primary_cta_href="#start"'
    ' secondary_cta_label="Talk to us" secondary_cta_href="#contact" band="plain" %}'
)
_CTA_WIDTH_CONTAINED_TINT = (
    '{% include "brickwork_marketing/components/_cta.html" with'
    ' heading="Contained, tinted band" body="band=tint with no width: the pre-existing composition."'
    ' primary_cta_label="Start free trial" primary_cta_href="#start"'
    ' secondary_cta_label="Talk to us" secondary_cta_href="#contact" band="tint" %}'
)
_CTA_WIDTH_BLEED_PLAIN = (
    '{% include "brickwork_marketing/components/_cta.html" with'
    ' heading="Full-bleed, plain band" body="width=bleed on the page surface, no tint."'
    ' primary_cta_label="Start free trial" primary_cta_href="#start"'
    ' secondary_cta_label="Talk to us" secondary_cta_href="#contact" band="plain" width="bleed" %}'
)
_CTA_WIDTH_BLEED_TINT = (
    '{% include "brickwork_marketing/components/_cta.html" with'
    ' heading="Full-bleed, tinted band" body="Both classes present: the source-order specificity tie."'
    ' primary_cta_label="Start free trial" primary_cta_href="#start"'
    ' secondary_cta_label="Talk to us" secondary_cta_href="#contact" band="tint" width="bleed" %}'
)

_CTA_WIDTH_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _CTA_WIDTH_CONTAINED_PLAIN
    + _CTA_WIDTH_CONTAINED_TINT
    + _CTA_WIDTH_BLEED_PLAIN
    + _CTA_WIDTH_BLEED_TINT
    + "{% endblock %}"
)


def render_cta_width(theme: str) -> str:
    request = RequestFactory().get("/marketing/cta-width/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "CTA width",
        "bw_page_title": "CTA width, Acme",
    }
    html = engines["django"].from_string(_CTA_WIDTH_SOURCE).render(ctx, request=request)
    return _inline_css(html)


# --- the example sections (3.1.0, plan Phase 6a) ------------------------------
#
# Gate 3 of the plan's Phase 6: every section variant clears axe WCAG 2.2 AA in
# BOTH themes, the no-JS floor, and mobile-first behaviour. A catalogue is
# exactly where a11y rots fastest, because each new variant is hand-written
# markup that no existing fixture covers.
#
# The sections are rendered through the standalone examples Engine, not the
# configured one: they are package data off the template-loader path (ADR-056),
# so `engines["django"]` cannot see them by construction. The `libraries=`
# argument is load-bearing and non-obvious, exactly as in tests/test_examples.py.
#
# They are stacked into ONE fixture per theme inside a real marketing shell.
# That is deliberate: a section is used in a document, so its heading order and
# landmark nesting are only meaningful in one. Stacking also catches a section
# that is individually fine but collides with its neighbour.

# The per-section context lives in tests/test_examples.py (_SECTION_CONTEXTS)
# and is imported in render_sections below, rather than being duplicated here.


def _sections_engine():
    """The standalone engine that can see the examples tree (ADR-056)."""
    from django.template import Engine
    from django.template.backends.django import get_installed_libraries

    from brickwork import examples

    return Engine(
        dirs=[str(examples.examples_root())],
        app_dirs=True,
        libraries=get_installed_libraries(),
    )


def render_sections(theme: str) -> str:
    """Every example section, stacked in a marketing shell, in one theme."""
    from django.template import Context

    from brickwork import examples

    engine = _sections_engine()
    names = [name for name in examples.list_examples() if name.startswith("sections/")]

    # The context each section needs comes from tests/test_examples.py, the one
    # place it is already declared and kept exhaustive (a section missing from
    # _SECTION_CONTEXTS fails test_the_shipped_example_set_matches_what_the_tests_cover).
    #
    # This used to be an inline `{"features": ...} if "icon-grid" in name else {}`,
    # which silently rendered EVERY other context-taking section empty: the
    # listing variants stacked as three empty <div>s and the axe and mobile
    # gates were measuring nothing. A section that renders blank here passes
    # every gate while being completely untested, so the two lists must not be
    # allowed to drift apart again.
    from test_examples import _SECTION_CONTEXTS

    rendered = []
    for name in sorted(names):
        context = _SECTION_CONTEXTS.get(name, {})
        html = engine.get_template(name).render(Context(context))
        if not html.strip():
            raise SystemExit(f"section {name} rendered empty into the a11y fixture; it needs a context entry")
        rendered.append(html)

    request = RequestFactory().get("/sections/")
    # The stacked sections are already-rendered HTML, so they go into the shell
    # through a context variable marked safe rather than by string-building a
    # template source: the section markup is ours, but re-parsing it as template
    # source would make any literal {% or {{ in an example's prose explode.
    from django.utils.safestring import mark_safe

    source = (
        '{% extends "brickwork_marketing/shell/marketing.html" %}'
        + _MARKETING_CHROME
        + "{% block content %}{{ sections }}{% endblock %}"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Sections",
        "bw_page_title": "Example sections, Northwind",
        "sections": mark_safe("".join(rendered)),  # noqa: S308 - our own rendered templates
    }
    html = engines["django"].from_string(source).render(ctx, request=request)
    return _inline_css(html)


# --- the date-range picker example (examples/app/date-range-picker.html) ----
#
# Unlike the marketing sections above, this is a WHOLE page (it extends
# brickwork/shell/app.html directly), so it needs no host shell to be
# re-embedded into: it renders straight off _sections_engine() (a generic
# name despite the section-only docstring above; it is simply "the standalone
# engine that can see the examples tree", reused here unchanged) with the
# same shell context vars _base_context supplies elsewhere in this file.
#
# The localisation context matches tests/test_examples.py's _DRP_CONTEXT
# exactly (django.utils.dates, not a hand-written English list), imported
# rather than duplicated so the two cannot drift apart, mirroring
# render_sections' own _SECTION_CONTEXTS import above.
#
# Two fixtures per theme, mirroring render_comboboxes exactly:
#   date-range-picker-<theme>.html      the closed, no-JS floor: two real
#                                        <input type="date"> inside two real
#                                        <form method="get">, popovers absent
#                                        from the accessibility tree (native
#                                        hidden). This is what axe.spec.mjs
#                                        and the no-JS suite examine.
#   date-range-picker-js-<theme>.html   Alpine booted (the same _JS_BOOT
#                                        combobox/toasts/feedback already use)
#                                        so interactions2.spec.mjs can drive
#                                        the trigger open, select a start and
#                                        end date (reaching the two-month
#                                        mid-selection state) and exercise the
#                                        disabled-dates config live, the same
#                                        division comboboxes-js draws between
#                                        the static floor and the JS-driven
#                                        open states.
def render_date_range_picker(theme: str) -> str:
    from django.template import Context
    from test_examples import _DRP_CONTEXT

    engine = _sections_engine()
    request = RequestFactory().get("/invoices/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "bw_lang": "en",
        "nav_items": (),
        "nav_active": None,
        **_DRP_CONTEXT,
    }
    html = engine.get_template("app/date-range-picker.html").render(Context(ctx))
    return _inline_css(html)


def render_date_range_picker_js(theme: str) -> str:
    """The JS-booted leg: Alpine only (no htmx dependency in this example),
    loaded exactly like _JS_BOOT's other legs. registerBrickworkComponents is
    NOT called for bwDateRangePicker: it is not a shipped brickwork behaviour
    (the example's own header comment states this), so it never touches the
    package's Alpine registration hook; alpine:init alone is enough for its
    own inline Alpine.data() registration to run."""
    html = render_date_range_picker(theme)
    js_boot = (
        '<script type="module">\n'
        '  import Alpine from "../../node_modules/alpinejs/dist/module.esm.js";\n'
        '  import focus from "../../node_modules/@alpinejs/focus/dist/module.esm.js";\n'
        "  Alpine.plugin(focus);\n"
        "  window.Alpine = Alpine;\n"
        "  Alpine.start();\n"
        "</script>\n"
    )
    return html.replace("</body>", js_boot + "</body>")


# --- the nav renderers (#102/#82) ---------------------------------------------
#
# nav-renderers-<theme>.html   a standalone page (mirrors render_feedback's
#                              self-contained shape) composing BOTH sibling
#                              renderers over one NavItem tree: the
#                              marketing-header row ({% bw_nav_header %})
#                              inside the real .bw-marketing-header strip, and
#                              the two-tier pairing ({% bw_nav_rail %} beside
#                              a contextual {% bw_nav %} in the
#                              .bw-nav-two-tier wrapper). The request is a
#                              CHILD area's route, so axe examines the
#                              ancestor-active treatments (header underline,
#                              rail tint) plus the contextual tier's exact
#                              aria-current in both themes; every entry is a
#                              real anchor (the no-JS floor), and the rail's
#                              corner badge chip and the external glyph are
#                              both present.

_NAV_RENDERERS_SOURCE = (
    "{% load brickwork_nav %}"
    '<header class="bw-marketing-header">'
    '<div class="bw-marketing-header__inner">'
    '<div class="bw-marketing-header__brand">'
    '<nav class="bw-marketing-header__nav" aria-label="Primary">'
    "{% bw_nav_header items=items active=active %}"
    "</nav>"
    "</div>"
    "</div>"
    "</header>"
    '<main id="bw-main">'
    "<h1>Nav renderers</h1>"
    '<nav aria-label="Main navigation">'
    '<div class="bw-nav-two-tier">'
    "{% bw_nav_rail items=items active=active %}"
    "{% bw_nav items=contextual_items active=active %}"
    "</div>"
    "</nav>"
    "</main>"
)

_NAV_RENDERERS_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nav renderers (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
__BODY__
</body>
</html>
"""


def render_nav_renderers(theme: str) -> str:
    from django.urls import resolve

    from brickwork.models import NavItem
    from brickwork.services.navigation import resolve_active_item

    # A purpose-built two-tier tree: top-level areas (one with children, one
    # with a badge, one external) so every renderer affordance is on the page.
    tree = (
        NavItem(key="fx-nr-dashboard", label="Dashboard", url_name="testapp:dashboard", icon="home"),
        NavItem(
            key="fx-nr-widgets",
            label="Widgets",
            url_name="testapp:widget-list",
            icon="folder",
            children=(
                NavItem(key="fx-nr-overview", label="Overview", url_name="testapp:interactions", icon="info"),
                NavItem(key="fx-nr-activity", label="Activity", url_name="testapp:toast-demo", icon="bell"),
            ),
        ),
        NavItem(key="fx-nr-settings", label="Settings", url_name="testapp:settings-index", icon="settings", badge=2),
        NavItem(key="fx-nr-docs", label="Docs", external_url="https://example.com/docs", icon="file"),
    )
    # the CHILD area's route: the parent lights as ancestor in both compact
    # renderers, the contextual tier carries the exact aria-current
    request = RequestFactory().get("/interactions/")
    request.resolver_match = resolve("/interactions/")
    active = resolve_active_item(tree, request.resolver_match)
    ctx = {
        "request": request,
        "items": tree,
        "contextual_items": tree[1].children,
        "active": active,
    }
    body = engines["django"].from_string(_NAV_RENDERERS_SOURCE).render(ctx)
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _NAV_RENDERERS_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__BODY__", body)
    )


# --- the search + loading-button fixtures (icvoss/django-brickwork#226) -------
#
# search-<theme>.html is a standalone (non-shell) page, mirroring render_
# feedback's self-contained shape: {% bw_search %} has no dedicated demo page
# of its own yet, so the fixture composes the REAL tag directly (an unscoped
# search plus a scoped search, so both the plain no-JS floor and the scope
# chip's clear-link surface are examined) alongside a loading {% bw_button %},
# which is _button.html's own documented way of mounting _spinner.html
# (_spinner.html's own docSource: "a button's loading=True mounts this").
# Neither component had a fixture before this, each one's own docSource
# comment said so in as many words; both are exactly the silent-gap failure
# mode tests/test_a11y_fixture_coverage.py now drift-gates against the
# catalogue manifest.

_SEARCH_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Search and loading button (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Search and loading button</h1>

  <section aria-labelledby="search-heading">
    <h2 id="search-heading">Search</h2>
    __SEARCH__
  </section>

  <section aria-labelledby="search-scoped-heading">
    <h2 id="search-scoped-heading">Search, scoped</h2>
    __SEARCH_SCOPED__
  </section>

  <section aria-labelledby="loading-button-heading">
    <h2 id="loading-button-heading">Loading button</h2>
    __LOADING_BUTTON__
  </section>
</main>
</body>
</html>
"""


def _render_search_fixture() -> str:
    from django.template import Context, Template

    return Template('{% load brickwork_components %}{% bw_search action="/search/" %}').render(Context({}))


def _render_search_scoped_fixture() -> str:
    from django.template import Context, Template

    return Template('{% load brickwork_components %}{% bw_search action="/search/" scope=scope %}').render(
        Context(
            {
                "scope": {
                    "label": "Widgets",
                    "name": "scope",
                    "value": "widgets",
                    "clear_href": "/search/",
                }
            }
        )
    )


def _render_loading_button_fixture() -> str:
    from django.template import Context, Template

    return Template('{% load brickwork_components %}{% bw_button "Saving" loading=True disabled=True %}').render(
        Context({})
    )


def render_search(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _SEARCH_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__SEARCH__", _render_search_fixture())
        .replace("__SEARCH_SCOPED__", _render_search_scoped_fixture())
        .replace("__LOADING_BUTTON__", _render_loading_button_fixture())
    )


def _emit(path: Path, html: str, written: list[str], name: str | None = None) -> None:
    """Write a fixture and record its name in the same call.

    A hand-maintained ``written`` list kept beside the write calls drifted
    from what was actually written (icvoss/django-brickwork#319): the log
    reported 116 fixtures while 122 were on disk. Routing every write
    through this helper makes the two impossible to diverge, because there
    is only one way to write one. ``name`` defaults to the path's stem, but
    fragment writes record a ``fragments/...`` name distinct from their
    stem, so it can be overridden explicitly.
    """
    path.write_text(html)
    written.append(name if name is not None else path.stem)


def main() -> None:
    written: list[str] = []
    projection_css = build_projection_css()
    for theme in ("light", "dark"):
        _emit(OUT / f"list-{theme}.html", render_list(theme), written)
        _emit(OUT / f"list-menu-open-{theme}.html", render_list(theme, menu_open=True), written)
        # the topbar-primary layout (SHL-001, 0.6.0): the same list page with
        # the nav restyled as a horizontal band, so the axe gate covers the
        # bottom active marker, inline section labels, and inline switcher slot
        _emit(OUT / f"list-topbar-{theme}.html", render_list(theme, layout="topbar"), written)
        _emit(OUT / f"dashboard-{theme}.html", render_dashboard(theme), written)
        _emit(OUT / f"form-{theme}.html", render_form(theme, with_errors=False), written)
        _emit(OUT / f"form-errors-{theme}.html", render_form(theme, with_errors=True), written)
        # the 0.8.0 interaction set (floor, open floor states, lazy tab
        # active, the JS leg, and the modal's full-page floor)
        _emit(OUT / f"interactions-{theme}.html", render_interactions(theme), written)
        _emit(
            OUT / f"interactions-open-{theme}.html",
            render_interactions(theme, active_tab="details", disclosure_open=True),
            written,
        )
        _emit(
            OUT / f"interactions-tab-lazy-{theme}.html",
            render_interactions(theme, active_tab="activity"),
            written,
        )
        _emit(OUT / f"interactions-js-{theme}.html", render_interactions(theme, inject_js=True), written)
        _emit(OUT / f"interactions-modal-page-{theme}.html", render_modal_page(theme), written)
        # the 0.9.0 overlay pair (toast floors + stack, combobox floors, the
        # dismissible surfaces, and the JS legs for both pages)
        _emit(OUT / f"toasts-{theme}.html", render_toasts(theme), written)
        _emit(OUT / f"toasts-flash-{theme}.html", render_toasts(theme, flash=True), written)
        _emit(OUT / f"toasts-stack-{theme}.html", render_toast_stack(theme), written)
        _emit(OUT / f"toasts-js-{theme}.html", render_toasts(theme, inject_js=True), written)
        _emit(OUT / f"comboboxes-{theme}.html", render_comboboxes(theme), written)
        _emit(
            OUT / f"comboboxes-js-{theme}.html",
            render_comboboxes(theme, selected=True, inject_js=True),
            written,
        )
        # the 0.10.0 Tailwind projection proof (consumer utilities only)
        _emit(OUT / f"projection-{theme}.html", render_projection(theme, projection_css), written)
        # the 0.12.0 feedback set (#56/#60): skeleton, tooltip (floor + JS-open
        # state), progress (determinate + indeterminate)
        _emit(OUT / f"feedback-{theme}.html", render_feedback(theme), written)
        _emit(OUT / f"feedback-js-{theme}.html", render_feedback(theme, inject_js=True), written)
        _emit(
            OUT / f"feedback-tooltip-open-{theme}.html",
            render_feedback(theme, inject_js=True, tooltip_open=True),
            written,
        )
        # the 0.13.0 input chrome set (#57/#58): toggle, tag input, dropzone,
        # a styled date field; plus the shell's collapsed-sidebar state
        _emit(OUT / f"inputs-{theme}.html", render_inputs(theme), written)
        # bw_ranked_list (#183): populated (linked rows), empty (with
        # action), and loading skeleton variants on one page
        _emit(OUT / f"ranked-list-{theme}.html", render_ranked_list(theme), written)
        # bw_sparkline (VIZ-003/004/005/006): neutral tone, trend tone in all
        # three directions (each pairing the stroke colour with the
        # decorative glyph + hidden text COL-030 requires), and a
        # highlighted point, all on one page
        _emit(OUT / f"sparkline-{theme}.html", render_sparkline(theme), written)
        # _trend_indicator (VIZ-017): the standalone partial extracted from
        # _stat.html, in a table cell and a scorecard, all three states
        _emit(OUT / f"trend-indicator-{theme}.html", render_trend_indicator(theme), written)
        # _chart_card (chart card work): populated (real bw_chart_mount tag,
        # title/actions/legend fills), legend_position="side", loading,
        # error and empty states, all on one page
        _emit(OUT / f"chart-card-{theme}.html", render_chart_card(theme), written)
        # _data_table.html's empty-state action CTA (#185): records and
        # definition variants, both rendered with zero rows and the new
        # empty_action_href/empty_action_label passthrough
        _emit(OUT / f"data-table-empty-cta-{theme}.html", render_data_table_empty_cta(theme), written)
        # bw_theme_switch (#117): the no-JS floor (renders nothing usable,
        # the control ships the bw-theme-switch--pre-init class, icvoss/
        # django-brickwork#272, supersedes the unconditional hidden
        # attribute this shipped with through 3.11.0) and the JS leg (real
        # Alpine boot, so bwThemeSwitch's own init reveals default/brand-
        # inclusive/locked instances and axe walks the real revealed markup)
        _emit(OUT / f"theme-switch-{theme}.html", render_theme_switch(theme), written)
        _emit(OUT / f"theme-switch-js-{theme}.html", render_theme_switch(theme, inject_js=True), written)
        _emit(
            OUT / f"theme-switch-invalid-root-js-{theme}.html",
            render_theme_switch_invalid_root(theme),
            written,
        )
        # layout="compact" (#235): the no-JS floor (#272 review: the
        # pre-existing no-JS test only ever rendered layout="inline",
        # leaving the compact root's own reserved-pre-init state
        # unverified) and the disclosure's own JS leg, stamped open so axe
        # examines the revealed trigger/panel pairing and the compact
        # options' own 44px targets, not a closed disclosure
        _emit(OUT / f"theme-switch-compact-{theme}.html", render_theme_switch_compact(theme), written)
        _emit(
            OUT / f"theme-switch-compact-open-js-{theme}.html",
            render_theme_switch_compact_open(theme),
            written,
        )
        _emit(OUT / f"sidebar-collapsed-{theme}.html", render_sidebar_collapsed(theme), written)
        # the 0.14.0 slide-over + stepper + wizard set (#55/#59): the
        # slide-over's OPEN state (dialog semantics, labelling, focusable
        # content), the stepper's status pairing, and the composed wizard page
        _emit(OUT / f"slide-over-open-{theme}.html", render_slide_over_open(theme), written)
        _emit(OUT / f"stepper-{theme}.html", render_stepper(theme), written)
        _emit(OUT / f"wizard-{theme}.html", render_wizard(theme), written)
        # the 0.15.0 table bulk-selection + whole-form set (#53/#54): a
        # selectable table with the bulk-actions bar visible and a checked
        # row, and the whole-form renderer in a valid grid layout plus a
        # bound-invalid render (field + non-field errors)
        _emit(OUT / f"table-selection-{theme}.html", render_table_selection(theme), written)
        _emit(OUT / f"bw-form-{theme}.html", render_bw_form_fixture(theme), written)
        # the 1.1.0 page-templates kit (form_page, settings, console, confirm,
        # auth_signin) plus #73's POST sign-out account-menu item
        _emit(OUT / f"form-page-{theme}.html", render_form_page(theme), written)
        _emit(OUT / f"settings-{theme}.html", render_settings(theme), written)
        _emit(OUT / f"console-{theme}.html", render_console(theme), written)
        # size="sm" (ADR-060, STA-019, #218): the in-panel empty state,
        # nested inside a bw-card, exercising the demoted heading and the
        # plain action-link treatment axe never sees on the page-filling
        # console fixture above
        _emit(OUT / f"console-sm-{theme}.html", render_console(theme, size="sm"), written)
        _emit(OUT / f"confirm-{theme}.html", render_confirm(theme), written)
        _emit(OUT / f"auth-signin-{theme}.html", render_auth_signin(theme), written)
        _emit(OUT / f"account-menu-post-{theme}.html", render_account_menu_post(theme), written)
        # the 1.2.0 marketing kit (brickwork.marketing, BR-BW-MKT-002): the
        # three shipped pages, each rendered through a consumer-shaped
        # extension carrying representative content
        _emit(OUT / f"landing-{theme}.html", render_landing(theme), written)
        _emit(OUT / f"pricing-{theme}.html", render_pricing(theme), written)
        _emit(OUT / f"about-{theme}.html", render_about(theme), written)
        # the hero media_placement axis (ADR-057 section 1a, #118): "behind"
        # (no/light/dark media) and "beside", none of which landing/pricing/
        # about above ever render, so axe never examined the new CSS
        _emit(OUT / f"hero-placement-{theme}.html", render_hero_media_placement(theme), written)
        # the CTA width axis (ADR-057 section 1a, #98/#118 pattern): width="bleed"
        # (bw-cta--bleed), never rendered by any other fixture, crossed with band
        _emit(OUT / f"cta-width-{theme}.html", render_cta_width(theme), written)
        # the nav renderers (#102/#82): the marketing-header row and the
        # two-tier rail + contextual pairing, ancestor-active states lit
        _emit(OUT / f"nav-renderers-{theme}.html", render_nav_renderers(theme), written)
        # search + loading button (#226): bw_search and _spinner.html's
        # loading=True mount, neither previously rendered by any fixture
        _emit(OUT / f"search-{theme}.html", render_search(theme), written)
        # every example section (3.1.0, plan Phase 6a gate 3), stacked in a
        # real marketing shell so heading order and landmarks are meaningful
        _emit(OUT / f"sections-{theme}.html", render_sections(theme), written)
        # the date-range picker example (examples/app/date-range-picker.html):
        # the closed no-JS floor plus the Alpine-booted leg
        # interactions2.spec.mjs drives open, mid-selection and with disabled
        # dates configured, mirroring the comboboxes/comboboxes-js split.
        _emit(OUT / f"date-range-picker-{theme}.html", render_date_range_picker(theme), written)
        _emit(OUT / f"date-range-picker-js-{theme}.html", render_date_range_picker_js(theme), written)
        # bwSortable (icvoss/django-brickwork#214): the no-JS floor (real
        # move-up/move-down forms, no drag/keyboard chrome) and the JS leg
        # (Alpine-booted, drag + keyboard reorder, persistence round trip)
        _emit(OUT / f"sortable-{theme}.html", render_sortable(theme), written)
        _emit(OUT / f"sortable-js-{theme}.html", render_sortable(theme, inject_js=True), written)
        _emit(
            OUT / f"sortable-js-persist-{theme}.html",
            render_sortable(theme, inject_js=True, with_url=True),
            written,
        )
        # bwTagInput carrier takeover (icvoss/django-brickwork#237): the JS
        # leg for both the single-line and multiline floors
        _emit(OUT / f"tag-input-js-{theme}.html", render_tag_input_js(theme), written)
    FRAGMENTS.mkdir(exist_ok=True)
    _emit(FRAGMENTS / "modal-confirm.html", render_modal_fragment(), written, name="fragments/modal-confirm")
    _emit(
        FRAGMENTS / "tab-panel-activity.html",
        render_activity_fragment(),
        written,
        name="fragments/tab-panel-activity",
    )
    for intent in _TOAST_INTENTS:
        _emit(
            FRAGMENTS / f"toast-oob-{intent}.html",
            render_toast_fragment(intent, "persistent"),
            written,
            name=f"fragments/toast-oob-{intent}",
        )
    _emit(
        FRAGMENTS / "toast-oob-short.html",
        render_toast_fragment("success", "short"),
        written,
        name="fragments/toast-oob-short",
    )
    _emit(
        FRAGMENTS / "toast-oob-action.html",
        render_toast_action_fragment(),
        written,
        name="fragments/toast-oob-action",
    )
    _emit(
        FRAGMENTS / "combobox-options-green.html",
        render_combobox_options_fragment(),
        written,
        name="fragments/combobox-options-green",
    )
    _emit(
        FRAGMENTS / "sortable-reorder.html",
        render_sortable_reorder_fragment(),
        written,
        name="fragments/sortable-reorder",
    )
    print("fixtures written:", ", ".join(written))


if __name__ == "__main__":
    main()
