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
    "{% block trigger %}"
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


# Beat Phase B primitives (#542): divider, avatar(+group), chip, button_group,
# callout, list_item. article_meta (#625) and date picker chrome (#628)
# enrolled on the same page (chrome only; owned engine stays on
# date-range-picker-*.html).
# marketing_footer_groups is covered by landing-*.html.

_PRIMITIVES_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Beat Phase B primitives (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Beat Phase B primitives</h1>
  <section aria-labelledby="divider-heading">
    <h2 id="divider-heading">Divider</h2>
    __DIVIDER__
    __DIVIDER_LABELLED__
  </section>
  <section aria-labelledby="avatar-heading">
    <h2 id="avatar-heading">Avatar</h2>
    __AVATAR__
    __AVATAR_GROUP__
  </section>
  <section aria-labelledby="chip-heading">
    <h2 id="chip-heading">Chip</h2>
    __CHIP__
    __CHIP_SELECTED__
  </section>
  <section aria-labelledby="button-group-heading">
    <h2 id="button-group-heading">Button group</h2>
    __BUTTON_GROUP__
    __BUTTON_GROUP_SEGMENTED__
  </section>
  <section aria-labelledby="callout-heading">
    <h2 id="callout-heading">Callout</h2>
    __CALLOUT__
  </section>
  <section aria-labelledby="list-item-heading">
    <h2 id="list-item-heading">List item</h2>
    __LIST_ITEM__
  </section>
  <section aria-labelledby="article-meta-heading">
    <h2 id="article-meta-heading">Article meta</h2>
    __ARTICLE_META__
  </section>
  <section aria-labelledby="date-picker-chrome-heading">
    <h2 id="date-picker-chrome-heading">Date picker chrome</h2>
    __DATE_PICKER_CHROME__
    __DATE_PICKER_CHROME_RANGE__
  </section>
</main>
</body>
</html>
"""


def render_primitives(theme: str) -> str:
    from django.utils.safestring import mark_safe

    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    from django.template import Context, Template

    divider = render_to_string("brickwork/components/_divider.html", {})
    divider_labelled = render_to_string(
        "brickwork/components/_divider.html",
        {"label": "Or continue with", "tone": "strong"},
    )
    avatar = render_to_string("brickwork/components/_avatar.html", {"initials": "NC"})
    avatar_group = Template("{% load brickwork_components %}{% bw_avatar_group avatars max=3 size='md' %}").render(
        Context(
            {
                "avatars": [
                    {"initials": "A"},
                    {"initials": "B"},
                    {"initials": "C"},
                    {"initials": "D"},
                ]
            }
        )
    )
    chip = render_to_string("brickwork/components/_chip.html", {"label": "Open"})
    chip_selected = render_to_string(
        "brickwork/components/_chip.html",
        {"label": "Paid", "selected": True, "variant": "success"},
    )
    button_group = render_to_string(
        "brickwork/components/_button_group.html",
        {
            "items": [{"label": "Day"}, {"label": "Week", "selected": True}, {"label": "Month"}],
            "aria_label": "Date range",
        },
    )
    button_group_seg = render_to_string(
        "brickwork/components/_button_group.html",
        {
            "items": [{"label": "List", "selected": True}, {"label": "Board"}],
            "variant": "segmented",
            "aria_label": "View mode",
        },
    )
    callout = render_to_string(
        "brickwork/components/_callout.html",
        {
            "title": "Note",
            "body": "Reminder schedules use the account timezone.",
            "variant": "note",
        },
    )
    list_item = render_to_string(
        "brickwork/components/_list_item.html",
        {
            "title": "Chasing without the awkwardness",
            "href": "/blog/chasing/",
            "summary": "How to write a reminder that gets paid.",
            "meta": "14 July 2026",
        },
    )
    article_meta = render_to_string(
        "brickwork/components/_article_meta.html",
        {
            "author_name": "Amira Okonkwo",
            "author_href": "/journal/authors/amira-okonkwo/",
            "author_initials": "AO",
            "published_on": "12 August 2026",
            "published_iso": "2026-08-12",
            "reading_time": "8 min read",
            "tags": [
                {"label": "Operations", "href": "/journal/operations/"},
                {"label": "Reminders"},
            ],
        },
    )
    date_picker_chrome = render_to_string(
        "brickwork/components/_date_picker_chrome.html",
        {
            "label": "Date raised",
            "id": "bw-dpc-a11y",
            "fields": mark_safe(
                '<div class="bw-date-picker-chrome__field">'
                '<input type="date" class="bw-input" id="id_a11y_raised" name="raised" '
                'aria-labelledby="bw-dpc-a11y-label">'
                '<button type="button" class="bw-date-picker-chrome__trigger" '
                'aria-label="Choose date">Open</button>'
                "</div>"
            ),
            "panel": mark_safe("<p>Calendar engine slot</p>"),
        },
    )
    date_picker_chrome_range = render_to_string(
        "brickwork/components/_date_picker_chrome.html",
        {
            "label": "Date range",
            "id": "bw-dpc-a11y-range",
            "range": True,
            "panel_open": True,
            "panel_label": "Choose dates",
            "fields": mark_safe(
                '<div class="bw-date-picker-chrome__field">'
                '<input type="date" class="bw-input" aria-label="Start date">'
                '<button type="button" class="bw-date-picker-chrome__trigger" '
                'aria-label="Choose start date">Open</button>'
                "</div>"
                '<span class="bw-date-picker-chrome__separator" aria-hidden="true">-</span>'
                '<div class="bw-date-picker-chrome__field">'
                '<input type="date" class="bw-input" aria-label="End date">'
                '<button type="button" class="bw-date-picker-chrome__trigger" '
                'aria-label="Choose end date">Open</button>'
                "</div>"
            ),
            "panel": mark_safe("<p>Range calendar engine slot</p>"),
        },
    )
    return (
        _PRIMITIVES_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__DIVIDER__", divider)
        .replace("__DIVIDER_LABELLED__", divider_labelled)
        .replace("__AVATAR__", avatar)
        .replace("__AVATAR_GROUP__", avatar_group)
        .replace("__CHIP__", chip)
        .replace("__CHIP_SELECTED__", chip_selected)
        .replace("__BUTTON_GROUP__", button_group)
        .replace("__BUTTON_GROUP_SEGMENTED__", button_group_seg)
        .replace("__CALLOUT__", callout)
        .replace("__LIST_ITEM__", list_item)
        .replace("__ARTICLE_META__", article_meta)
        .replace("__DATE_PICKER_CHROME__", date_picker_chrome)
        .replace("__DATE_PICKER_CHROME_RANGE__", date_picker_chrome_range)
    )


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

  <section aria-labelledby="input-group-heading">
    <h2 id="input-group-heading">Input group</h2>
    __INPUT_GROUP__
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


def _render_input_group_fixture() -> str:
    """Currency prefix + search-icon prefix around real bw-input controls (#624)."""
    from django import forms
    from django.template import Context, Template
    from django.utils.safestring import mark_safe

    class _AmountForm(forms.Form):
        amount = forms.DecimalField(label="Amount", max_digits=10, decimal_places=2)

    field = _AmountForm()["amount"]
    amount = Template(
        "{% load brickwork_forms %}"
        '<div class="bw-field">'
        '<label class="bw-field__label" for="{{ field.id_for_label }}">{{ field.label }}</label>'
        '<div class="bw-field__control">'
        "{% bw_field_widget field as amount_widget %}"
        '{% include "brickwork/components/_input_group.html" with prefix="£" field=amount_widget %}'
        "</div></div>"
    ).render(Context({"field": field}))
    domain_control = mark_safe(  # noqa: S308 (fixture-authored trusted markup)
        '<input class="bw-input" type="text" id="id_domain" name="domain" value="acme">'
    )
    domain = render_to_string(
        "brickwork/components/_input_group.html",
        {"prefix_icon": "search", "suffix": ".example", "field": domain_control},
    )
    return (
        f"{amount}"
        f'<div class="bw-field" style="margin-block-start:1rem">'
        f'<label class="bw-field__label" for="id_domain">Domain</label>'
        f'<div class="bw-field__control">{domain}</div></div>'
    )


def render_inputs(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _INPUTS_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__TOGGLE__", _render_toggle_fixture())
        .replace("__TAG_INPUT__", _render_tag_input_fixture())
        .replace("__DROPZONE__", _render_dropzone_fixture())
        .replace("__DATE_FIELD__", _render_date_field_fixture())
        .replace("__INPUT_GROUP__", _render_input_group_fixture())
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

  <section aria-labelledby="ranked-list-secondary-heading">
    <h2 id="ranked-list-secondary-heading">With secondary column and caption</h2>
    __RANKED_LIST_SECONDARY__
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

_RANKED_LIST_SECONDARY_ROWS = [
    {
        "label": "Organic",
        "amount": 4000,
        "value": "4,000",
        "secondary": "50%",
        "secondary_text": "Revenue: £12.50",
        "href": "/channels/organic/",
    },
    {
        "label": "Paid search",
        "amount": 3000,
        "value": "3,000",
        "secondary": "37.5%",
        "secondary_text": "Revenue: £8.00",
    },
    {
        "label": "Email",
        "amount": 1000,
        "value": "1,000",
        "secondary": "12.5%",
    },
]


def _render_ranked_list_fixture(**ctx: object) -> str:
    from django.template import Context, Template

    return Template(
        "{% load brickwork_components %}"
        "{% bw_ranked_list rows=rows basis=basis label=label loading=loading "
        "empty_heading=empty_heading empty_body=empty_body "
        "empty_action_href=empty_action_href empty_action_label=empty_action_label "
        "caption=caption secondary_caption=secondary_caption %}"
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
                "caption": "",
                "secondary_caption": "",
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
            "__RANKED_LIST_SECONDARY__",
            _render_ranked_list_fixture(
                rows=_RANKED_LIST_SECONDARY_ROWS,
                basis="total",
                label="Revenue by channel",
                caption="Showing the top 3",
                secondary_caption="Share of total",
            ),
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


# card-<theme>.html (appearance suite, icvoss/django-brickwork#535): bare
# include defaults, inverse header recipe, elevated surface, and an
# extend-and-include filler with root modifiers, so axe covers recipe chrome
# and CSS-only axes on package-default light/dark.

_CARD_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Card (__THEME__)</title>
__CSS__
<style>
  .bw-card-gallery { display: grid; gap: 1.5rem; }
  @media (min-width: 48rem) {
    .bw-card-gallery { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  .bw-card-gallery > section { margin: 0; }
  .bw-card-gallery h2 { font-size: 0.875rem; margin-block: 0 0.5rem; }
</style>
</head>
<body class="bw-body">
<main>
  <h1>Card</h1>
  <div class="bw-card-gallery">
  __CARD_SECTIONS__
  </div>
</main>
</body>
</html>
"""

# 1x1 PNG (light grey) as a stable offline media fixture asset.
_CARD_MEDIA_SRC = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='360'%3E"
    "%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E"
    "%3Cstop stop-color='%2364748b'/%3E%3Cstop offset='1' stop-color='%2394a3b8'/%3E"
    "%3C/linearGradient%3E%3C/defs%3E"
    "%3Crect width='640' height='360' fill='url(%23g)'/%3E%3C/svg%3E"
)


def _card_section(heading_id: str, heading: str, html: str) -> str:
    return f'<section aria-labelledby="{heading_id}"><h2 id="{heading_id}">{heading}</h2>{html}</section>'


def render_card(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    from django.template import Context, Template

    sections: list[str] = []
    sections.append(
        _card_section(
            "card-default",
            "Default",
            render_to_string(
                "brickwork/components/_card.html",
                {"title": "Members", "body": "Twelve active seats across the workspace."},
            ),
        )
    )
    for surface in ("raised", "tint", "inverse", "muted"):
        sections.append(
            _card_section(
                f"card-surface-{surface}",
                f"Surface {surface}",
                render_to_string(
                    "brickwork/components/_card.html",
                    {
                        "title": surface.title(),
                        "body": f"surface={surface}",
                        "surface": surface,
                    },
                ),
            )
        )
    for elevation in ("0", "2", "3"):
        sections.append(
            _card_section(
                f"card-elevation-{elevation}",
                f"Elevation {elevation}",
                render_to_string(
                    "brickwork/components/_card.html",
                    {
                        "title": f"Elevation {elevation}",
                        "body": f"elevation={elevation}",
                        "elevation": elevation,
                    },
                ),
            )
        )
    for size in ("sm", "md", "lg"):
        sections.append(
            _card_section(
                f"card-size-{size}",
                f"Size {size}",
                render_to_string(
                    "brickwork/components/_card.html",
                    {"title": f"Size {size}", "body": f"size={size}", "size": size},
                ),
            )
        )
    for radius in ("sm", "xl", "none"):
        sections.append(
            _card_section(
                f"card-radius-{radius}",
                f"Radius {radius}",
                render_to_string(
                    "brickwork/components/_card.html",
                    {
                        "title": f"Radius {radius}",
                        "body": f"radius={radius}",
                        "radius": radius,
                    },
                ),
            )
        )
    for recipe in ("plain", "bordered", "muted", "inverse", "accent"):
        sections.append(
            _card_section(
                f"card-header-{recipe}",
                f"Header {recipe}",
                render_to_string(
                    "brickwork/components/_card.html",
                    {
                        "title": f"Header {recipe}",
                        "body": f"header_recipe={recipe}",
                        "header_recipe": recipe,
                    },
                ),
            )
        )
    sections.append(
        _card_section(
            "card-header-action",
            "Header action",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Workspace",
                    "body": "Title with an include-path header action.",
                    "header_recipe": "bordered",
                    "action_label": "Edit",
                    "action_href": "/edit/",
                },
            ),
        )
    )
    # Inverse header + ghost action: site galleries hit this pairing; axe must
    # cover it so muted ghost ink on inverse fill cannot regress past AA.
    sections.append(
        _card_section(
            "card-header-inverse-action",
            "Header inverse action",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Members",
                    "body": "Inverse header with an include-path ghost action.",
                    "header_recipe": "inverse",
                    "action_label": "Add member",
                    "action_href": "/members/new/",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-footer-muted",
            "Footer muted",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Members",
                    "body": "Invite colleagues and manage roles.",
                    "header_recipe": "inverse",
                    "footer_recipe": "muted",
                    "caption": "Updated today",
                    "elevation": "2",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-footer-plain",
            "Footer plain",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Notes",
                    "body": "Plain footer chrome with a caption.",
                    "footer_recipe": "plain",
                    "caption": "Last saved 2 minutes ago",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-footer-actions",
            "Footer actions (extends)",
            Template(
                "{% extends 'brickwork/components/_card.html' %}"
                "{% load brickwork_components %}"
                "{% block body %}<p class='bw-card__body'>Confirm before publishing.</p>{% endblock %}"
                "{% block footer %}<div class='bw-card__footer bw-card__footer--actions'>"
                "{% bw_button 'Cancel' variant='ghost' size='sm' %}"
                "{% bw_button 'Publish' size='sm' %}"
                "</div>{% endblock %}"
            ).render(Context({"title": "Publish changes", "header_recipe": "bordered", "footer_recipe": "actions"})),
        )
    )
    sections.append(
        _card_section(
            "card-media-bleed",
            "Media bleed",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Coastal studio",
                    "body": "Bleed media covers the top radius.",
                    "media_recipe": "bleed",
                    "media_src": _CARD_MEDIA_SRC,
                    "media_alt": "",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-media-inset",
            "Media inset",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Inset media",
                    "body": "Inset media sits inside the card padding.",
                    "media_recipe": "inset",
                    "media_src": _CARD_MEDIA_SRC,
                    "media_alt": "",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-media-icon",
            "Media icon",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Team",
                    "body": "Icon media for emblem cards.",
                    "media_recipe": "icon",
                    "media_icon": "users",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-linked",
            "Linked interactive",
            render_to_string(
                "brickwork/components/_card.html",
                {
                    "title": "Invoice #1042",
                    "body": "Whole-card link; header actions suppressed.",
                    "href": "/invoices/1042/",
                    "action_label": "Should not render",
                    "action_href": "/nope/",
                },
            ),
        )
    )
    sections.append(
        _card_section(
            "card-extends-muted",
            "Extends filler with muted header",
            Template(
                "{% extends 'brickwork/components/_card.html' %}"
                "{% block header %}<div class='bw-card__header'>"
                "<h2 class='bw-card__title'>Custom header</h2></div>{% endblock %}"
                "{% block body %}<p class='bw-card__body'>Body copy for the extends path.</p>{% endblock %}"
            ).render(Context({"header_recipe": "muted", "elevation": "2"})),
        )
    )
    return (
        _CARD_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__CARD_SECTIONS__", "\n".join(sections))
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
# size="sm" with its action link (STA-001/002, CHT-008). It also covers
# _chart_data_table.html in all three of CHT-013's data_table_mode values,
# each rendered through the chart_data_table block as a SIBLING of the
# role="img" mount (the CHT-012 placement contract): the hidden mode puts the
# clip-pattern table (present in the accessibility tree, absent visually)
# under axe, the toggle mode brings the native <details> disclosure under the
# keyboard and no-JS legs, and the visible mode puts the table's own contrast
# and hairlines under axe.

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

  <section aria-labelledby="chart-card-table-hidden-heading">
    <h2 id="chart-card-table-hidden-heading">Fallback table, hidden</h2>
    __CHART_CARD_TABLE_HIDDEN__
  </section>

  <section aria-labelledby="chart-card-table-toggle-heading">
    <h2 id="chart-card-table-toggle-heading">Fallback table, toggle</h2>
    __CHART_CARD_TABLE_TOGGLE__
  </section>

  <section aria-labelledby="chart-card-table-visible-heading">
    <h2 id="chart-card-table-visible-heading">Fallback table, visible</h2>
    __CHART_CARD_TABLE_VISIBLE__
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


def _render_chart_data_table(mode: str) -> str:
    """CHT-012's fallback table at one of CHT-013's three modes, with a real
    three-column, three-row series: a one-row table would exercise neither the
    row-header contract past its first cell nor the wrapper's overflow."""
    from django.template import Context, Template

    return Template(
        "{% load brickwork_components %}"
        "{% bw_chart_data_table caption=caption columns=columns rows=rows "
        "data_table_mode=mode toggle_label=toggle_label %}"
    ).render(
        Context(
            {
                "caption": "Revenue by month and channel",
                "columns": ["Month", "Direct", "Referral"],
                "rows": [
                    ["January", "120", "45"],
                    ["February", "150", "60"],
                    ["March", "180", "75"],
                ],
                "mode": mode,
                "toggle_label": "View as table",
            }
        )
    )


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
        .replace(
            "__CHART_CARD_TABLE_HIDDEN__",
            _render_chart_card_fixture(
                title="Revenue by month",
                mount=mark_safe(mount),  # noqa: S308
                data_table=_render_chart_data_table("hidden"),
            ),
        )
        .replace(
            "__CHART_CARD_TABLE_TOGGLE__",
            _render_chart_card_fixture(
                title="Revenue by month",
                mount=mark_safe(mount),  # noqa: S308
                data_table=_render_chart_data_table("toggle"),
            ),
        )
        .replace(
            "__CHART_CARD_TABLE_VISIBLE__",
            _render_chart_card_fixture(
                title="Revenue by month",
                mount=mark_safe(mount),  # noqa: S308
                data_table=_render_chart_data_table("visible"),
            ),
        )
    )


# --- the bw_gauge fixtures (icvoss/django-brickwork VIZ-007 to VIZ-010) -----
#
# gauge-<theme>.html covers: a plain determinate ring (default accent),
# threshold_bands resolving each of the three non-accent tokens (danger,
# warning, success), and the sm/lg size modifiers, so axe sees every
# threshold colour class and every size the component ships, not merely the
# default md/accent case.

_GAUGE_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gauge (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Gauge</h1>

  <section aria-labelledby="gauge-default-heading">
    <h2 id="gauge-default-heading">Default (accent)</h2>
    __GAUGE_DEFAULT__
  </section>

  <section aria-labelledby="gauge-thresholds-heading">
    <h2 id="gauge-thresholds-heading">Threshold bands</h2>
    __GAUGE_THRESHOLD_DANGER__
    __GAUGE_THRESHOLD_WARNING__
    __GAUGE_THRESHOLD_SUCCESS__
  </section>

  <section aria-labelledby="gauge-sizes-heading">
    <h2 id="gauge-sizes-heading">Sizes</h2>
    __GAUGE_SMALL__
    __GAUGE_LARGE__
  </section>
</main>
</body>
</html>
"""

_GAUGE_BANDS = [
    {"max": 50, "token": "danger"},
    {"max": 80, "token": "warning"},
    {"max": 100, "token": "success"},
]


def _render_gauge_fixture(**ctx: object) -> str:
    from django.template import Context, Template

    return Template(
        "{% load brickwork_components %}"
        "{% bw_gauge value=value min=min max=max label=label size=size threshold_bands=threshold_bands %}"
    ).render(
        Context(
            {
                "value": 0,
                "min": 0,
                "max": 100,
                "label": "",
                "size": "md",
                "threshold_bands": None,
                **ctx,
            }
        )
    )


def render_gauge(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _GAUGE_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__GAUGE_DEFAULT__", _render_gauge_fixture(value=73, label="Storage used"))
        .replace(
            "__GAUGE_THRESHOLD_DANGER__",
            _render_gauge_fixture(value=30, label="CPU load, danger band", threshold_bands=_GAUGE_BANDS),
        )
        .replace(
            "__GAUGE_THRESHOLD_WARNING__",
            _render_gauge_fixture(value=65, label="CPU load, warning band", threshold_bands=_GAUGE_BANDS),
        )
        .replace(
            "__GAUGE_THRESHOLD_SUCCESS__",
            _render_gauge_fixture(value=95, label="CPU load, success band", threshold_bands=_GAUGE_BANDS),
        )
        .replace("__GAUGE_SMALL__", _render_gauge_fixture(value=42, label="Small gauge", size="sm"))
        .replace("__GAUGE_LARGE__", _render_gauge_fixture(value=88, label="Large gauge", size="lg"))
    )


# --- the _scorecard and _stat_comparison fixtures (VIZ-011/012, VIZ-019/020) -
#
# scorecard-<theme>.html covers: the shared dashboard grid (_scorecard.html,
# CHT-026) arranging real pre-rendered _stat.html cards across the span=2/3/4
# modifiers plus an untagged (span=1) item, so axe walks the grid's own
# markup AND every card it arranges; and _stat_comparison.html's sm/md/lg
# sizes each paired with a different trend direction, so axe sees every
# trend colour class and every size the component ships, not merely the
# default md/up case.

_SCORECARD_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scorecard and stat comparison (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Scorecard and stat comparison</h1>

  <section aria-labelledby="scorecard-grid-heading">
    <h2 id="scorecard-grid-heading">Scorecard grid</h2>
    __SCORECARD_GRID__
  </section>

  <section aria-labelledby="stat-comparison-heading">
    <h2 id="stat-comparison-heading">Stat comparison</h2>
    __STAT_COMPARISON_SM__
    __STAT_COMPARISON_MD__
    __STAT_COMPARISON_LG__
  </section>
</main>
</body>
</html>
"""


def _render_stat_comparison_fixture(**ctx: object) -> str:
    return render_to_string("brickwork/components/_stat_comparison.html", ctx)


def render_scorecard(theme: str) -> str:
    from django.utils.safestring import mark_safe

    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    items = [
        {
            "content": mark_safe(  # noqa: S308 (fixture-authored trusted markup)
                render_to_string(
                    "brickwork/components/_stat.html",
                    {"label": "Revenue", "value": "£12,400", "trend": "up", "trend_label": "14% up"},
                )
            ),
            "span": 2,
        },
        {
            "content": mark_safe(  # noqa: S308 (fixture-authored trusted markup)
                render_to_string(
                    "brickwork/components/_stat.html",
                    {"label": "Churn", "value": "4.2%", "trend": "down", "trend_label": "1.1pt worse"},
                )
            ),
            "span": "3",
        },
        {
            "content": mark_safe(  # noqa: S308 (fixture-authored trusted markup)
                render_to_string(
                    "brickwork/components/_stat.html",
                    {"label": "Signups", "value": "318", "trend": "flat", "trend_label": "unchanged"},
                )
            ),
            "span": 4,
        },
        {
            "content": mark_safe(  # noqa: S308 (fixture-authored trusted markup)
                render_to_string("brickwork/components/_stat.html", {"label": "Uptime", "value": "99.98%"})
            ),
        },
    ]
    scorecard_grid = render_to_string("brickwork/components/_scorecard.html", {"items": items})
    return (
        _SCORECARD_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__SCORECARD_GRID__", scorecard_grid)
        .replace(
            "__STAT_COMPARISON_SM__",
            _render_stat_comparison_fixture(
                label="Revenue",
                current="12,400",
                previous="10,900",
                period_label="vs last month",
                trend="up",
                trend_label="14% up",
                size="sm",
            ),
        )
        .replace(
            "__STAT_COMPARISON_MD__",
            _render_stat_comparison_fixture(current="987", previous="1,234"),
        )
        .replace(
            "__STAT_COMPARISON_LG__",
            _render_stat_comparison_fixture(
                label="Churn",
                current="4.2%",
                previous="3.1%",
                period_label="vs last quarter",
                trend="down",
                trend_label="1.1pt worse",
                size="lg",
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


# --- token specimen (THM-016, icvoss/django-brickwork#268) -------------------
#
# token-specimen-<theme>.html covers the no-JS floor: dual light/dark panes,
# load-bearing rows, contrast-pair chips, and the live swatch var() wiring.
# The PE script that fills resolved values is stripped for file:// (same
# pattern as marketing-overlay nojs); unit tests cover the script itself.

_TOKEN_SPECIMEN_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Token specimen (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Token specimen</h1>
  __SPECIMEN__
</main>
</body>
</html>
"""

_TOKEN_SPECIMEN_SCRIPT_TAG = re.compile(
    r'<script src="[^"]*token-specimen\.js"[^>]*></script>',
    re.IGNORECASE,
)


def _render_token_specimen_fixture() -> str:
    from django.template import Context, Template

    html = Template("{% load brickwork_theming %}{% bw_token_specimen %}").render(Context({}))
    return _TOKEN_SPECIMEN_SCRIPT_TAG.sub("", html)


def render_token_specimen(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _TOKEN_SPECIMEN_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__SPECIMEN__", _render_token_specimen_fixture())
    )


# --- preview frame (ILL-026, icvoss/django-brickwork#269) --------------------
#
# preview-frame-<theme>.html covers the surface-guarded viewport with a live
# component render, plus the card-scale and scrollable modifiers.

_PREVIEW_FRAME_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Preview frame (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Preview frame</h1>
  <section aria-labelledby="preview-frame-full-heading">
    <h2 id="preview-frame-full-heading">Full scale</h2>
    __PREVIEW_FULL__
  </section>
  <section aria-labelledby="preview-frame-card-heading">
    <h2 id="preview-frame-card-heading">Card scale</h2>
    __PREVIEW_CARD__
  </section>
</main>
</body>
</html>
"""


def _render_preview_frame_fixture(**ctx: object) -> str:
    return render_to_string("brickwork/components/_preview_frame.html", ctx)


def render_preview_frame(theme: str) -> str:
    from django.utils.safestring import mark_safe

    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    full = _render_preview_frame_fixture(
        content=mark_safe(
            '<div class="bw-alert bw-alert--info" role="status">'
            '<div class="bw-alert__body"><p class="bw-alert__title">Live render</p>'
            '<p class="bw-alert__message">Surface-guarded against --bw-color-surface.</p></div></div>'
        ),
        caption="Info alert inside the frame",
    )
    # Card scale applies a CSS transform; interactive controls inside would
    # measure below the 24x24 tap-target floor even when the unscaled control
    # is compliant. Specimen content here is non-interactive on purpose.
    card = _render_preview_frame_fixture(
        content=mark_safe('<span class="bw-badge">Card scale</span>'),
        scale="card",
        caption="Card-scale badge",
    )
    return (
        _PREVIEW_FRAME_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__PREVIEW_FULL__", full)
        .replace("__PREVIEW_CARD__", card)
    )


# --- proof collage (icvoss/django-brickwork#572) -----------------------------

_PROOF_COLLAGE_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Proof collage (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Proof collage</h1>
  __COLLAGE__
  __PAGE__
</main>
</body>
</html>
"""


def render_proof_collage(theme: str) -> str:
    from django.utils.safestring import mark_safe

    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    collage = render_to_string(
        "brickwork_marketing/components/_proof_collage.html",
        {
            "heading": "Kit collage",
            "lede": "Live package pieces as visual proof.",
            "layout": "collage",
            # Collage tiles always wrap at card scale, so specimen content
            # stays non-interactive (scaled buttons fail the 24x24 sweep).
            "items": [
                {
                    "label": "Chip",
                    "content": mark_safe('<span class="bw-badge">Get started</span>'),
                },
                {
                    "label": "Status",
                    "content": mark_safe('<span class="bw-badge">Shipped</span>'),
                },
                {
                    "label": "Callout",
                    "content": mark_safe(
                        '<div class="bw-alert bw-alert--info" role="status">'
                        '<div class="bw-alert__body"><p class="bw-alert__title">Live</p></div></div>'
                    ),
                },
            ],
        },
    )
    page = render_to_string(
        "brickwork_marketing/components/_proof_collage.html",
        {
            "heading": "Page as proof",
            "layout": "page",
            "items": [
                {
                    "content": mark_safe(
                        "<section><h2>Pricing</h2>"
                        '<p class="bw-prose">A composed marketing band.</p>'
                        '<span class="bw-badge">Choose plan</span></section>'
                    )
                }
            ],
        },
    )
    return (
        _PROOF_COLLAGE_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__COLLAGE__", collage)
        .replace("__PAGE__", page)
    )


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
    "{% block body %}"
    '<form id="fx-slide-over-form"><label for="fx-slide-over-input">Widget name'
    '<input id="fx-slide-over-input" name="name" data-bw-autofocus></label></form>'
    "{% endblock %}"
    '{% block footer %}<footer class="bw-slide-over__footer">'
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
    '{% include "brickwork_marketing/components/_marketing_footer_groups.html" with groups=footer_groups %}'
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
        "footer_groups": [
            {
                "heading": "Product",
                "links": [
                    {"label": "Features", "href": "#features"},
                    {"label": "Pricing", "href": "#pricing"},
                ],
            },
            {
                "heading": "Company",
                "links": [
                    {"label": "About", "href": "#about"},
                    {"label": "Contact", "href": "#contact"},
                ],
            },
        ],
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


# --- marketing mobile-nav toggle (#263) ---------------------------------------
#
# landing/pricing/about intentionally omit the toggle so the coarse-pointer
# and no-JS marketing-header assertions keep measuring a permanently visible
# nav/actions row. This fixture is the coverage vehicle for
# component/mobile_nav_toggle: it composes the documented marketing_nav_region
# include pattern so the a11y gate sees the trigger and the sibling collapse
# CSS at every theme.

_MOBILE_NAV_TOGGLE_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    "{% load brickwork_components i18n %}"
    "{% block marketing_nav_region %}"
    '{% include "brickwork_marketing/components/_mobile_nav_toggle.html" %}'
    '<nav class="bw-site-header__nav" aria-label="{% translate \'Primary\' %}">'
    "{% block marketing_nav %}"
    '<a href="#features">Features</a>'
    '<a href="#pricing">Pricing</a>'
    '<a href="#about">About</a>'
    "{% endblock %}"
    "</nav>"
    "{% endblock %}"
    "{% block marketing_actions %}"
    '<a href="#signin">Sign in</a>'
    '{% bw_button "Get started" href="#start" variant="primary" size="sm" %}'
    "{% endblock %}"
    "{% block content %}"
    "<h1>Mobile nav toggle</h1>"
    "<p>Coverage fixture for the package-owned marketing mobile-nav toggle.</p>"
    "{% endblock %}"
    "{% block footer_legal %}&copy; 2026 Acme Ltd. All rights reserved.{% endblock %}"
)


def render_mobile_nav_toggle(theme: str) -> str:
    request = RequestFactory().get("/marketing/mobile-nav/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Mobile nav toggle",
        "bw_page_title": "Mobile nav toggle, Acme",
    }
    html = engines["django"].from_string(_MOBILE_NAV_TOGGLE_SOURCE).render(ctx, request=request)
    return _inline_css(html)


# --- marketing header overlay (ADR-105, icvoss/django-brickwork#565) ---------
#
# Default landing fixtures keep the sticky solid header. These fixtures cover
# BR-BW-MKT-006: no-JS opaque overlay floor, enhanced light/dark context ink,
# and scrolled frost. Attribute stamps are author-literal so axe examines the
# enhanced states without depending on file:// script resolution; the PE
# script behaviour is asserted separately by a11y/marketing_overlay.spec.mjs.

_OVERLAY_JS = (ROOT / "src/brickwork/static/brickwork/js/marketing-overlay.js").read_text(encoding="utf-8")
_OVERLAY_SCRIPT_TAG = re.compile(
    r'<script src="[^"]*marketing-overlay\.js"[^>]*></script>',
    re.IGNORECASE,
)


def _inline_overlay_script(html: str, *, inject: bool) -> str:
    """Drop or inline the shell's marketing-overlay.js for file:// fixtures."""
    if inject:
        return _OVERLAY_SCRIPT_TAG.sub(f"<script>{_OVERLAY_JS}</script>", html)
    return _OVERLAY_SCRIPT_TAG.sub("", html)


def _overlay_shell_source(
    *,
    attrs: str = "",
    hero_context: str = "dark",
    band_context: str = "light",
) -> str:
    return (
        '{% extends "brickwork_marketing/shell/marketing.html" %}'
        "{% load brickwork_components i18n %}"
        "{% block marketing_header_modifiers %}bw-site-header--overlay{% endblock %}"
        f"{{% block marketing_header_attrs %}}{attrs}{{% endblock %}}"
        "{% block brand_wordmark %}Acme{% endblock %}"
        "{% block marketing_nav %}"
        '<a href="#features">Features</a>'
        '<a href="#pricing">Pricing</a>'
        '<a href="#about">About</a>'
        "{% endblock %}"
        "{% block marketing_actions %}"
        '<a href="#signin">Sign in</a>'
        '{% bw_button "Get started" href="#start" variant="primary" size="sm" %}'
        "{% endblock %}"
        "{% block content %}"
        f'<section data-bw-nav-context="{hero_context}" '
        'style="background: oklch(0.18 0.02 265); color: oklch(0.98 0.002 265);'
        ' padding-block: 6rem; min-block-size: 100vh;">'
        "<h1>Full-bleed under the nav</h1>"
        "<p>Package-owned overlay chrome clears this copy.</p>"
        "</section>"
        f'<section data-bw-nav-context="{band_context}" '
        'style="padding-block: 6rem; min-block-size: 100vh;'
        ' background: oklch(0.98 0.002 265); color: oklch(0.2 0.02 265);">'
        "<h2>Light band</h2>"
        "<p>Context flips when this band sits under the header.</p>"
        "</section>"
        "{% endblock %}"
        "{% block footer_legal %}&copy; 2026 Acme Ltd. All rights reserved.{% endblock %}"
    )


def render_marketing_overlay(theme: str, *, state: str = "nojs") -> str:
    """state: nojs | dark | light-scrolled | dark-scrolled | js-boot."""
    attrs = ""
    inject = False
    if state == "dark":
        attrs = ' data-bw-overlay-ready data-bw-nav-context="dark" data-bw-scrolled="false"'
    elif state == "light-scrolled":
        attrs = ' data-bw-overlay-ready data-bw-nav-context="light" data-bw-scrolled="true"'
    elif state == "dark-scrolled":
        attrs = ' data-bw-overlay-ready data-bw-nav-context="dark" data-bw-scrolled="true"'
    elif state == "js-boot":
        attrs = ' data-bw-nav-context="dark"'
        inject = True
    request = RequestFactory().get(f"/marketing/overlay/{state}/")
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Overlay",
        "bw_page_title": f"Overlay {state}, Acme",
    }
    html = engines["django"].from_string(_overlay_shell_source(attrs=attrs)).render(ctx, request=request)
    return _inline_overlay_script(_inline_css(html), inject=inject)


# --- the hero media_placement axis (ADR-057 section 1a, icvoss/django-brickwork#118) ---
#
# None of landing/pricing/about above ever passes media_placement, so they all
# render the "below" default: the "behind", "beside" and "above" CSS this
# option adds (.bw-hero--media-behind, .bw-hero--media-beside,
# .bw-hero--media-above in frontend/src/marketing.css) had no fixture
# rendering it, so axe was never actually examining it and the
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
# alongside the placement axis itself. An "above" hero closes the set
# (icvoss/django-brickwork#201): media stacked visually above the copy.
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
_HERO_PLACEMENT_ABOVE = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Above" heading="Media stacked above the copy"'
    ' lede="Visual order only: document and tab order stay copy then media."'
    ' primary_cta=primary_cta media=beside_media media_placement="above" %}'
)
# eyebrow_marker="rule" (#659): leading accent dash before the overline.
# Stacked last so existing nth() selectors against --media-behind stay stable.
# Composes with decoration (#645) and media_placement="beside".
_HERO_PLACEMENT_EYEBROW_MARKER = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="With marker" heading="Accent rule before the overline"'
    ' lede="eyebrow_marker rule draws via component ::before; decoration still hangs behind."'
    ' primary_cta=primary_cta media=beside_media media_placement="beside"'
    ' decoration=decoration_mark eyebrow_marker="rule" %}'
)
# Presence hero (#672): sentence-tone eyebrow, subheading, meta_items,
# start-aligned actions, circular portrait beside the copy.
_HERO_PLACEMENT_PRESENCE = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Independent consultant" eyebrow_tone="sentence"'
    ' heading="Nigel Copley"'
    ' subheading="Strategy and delivery for product teams."'
    ' lede="A quieter supporting paragraph under the positioning line."'
    ' primary_cta=primary_cta media=beside_media media_placement="beside"'
    ' media_shape="circle" meta_items=meta_items align="start" %}'
)

_HERO_PLACEMENT_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _HERO_PLACEMENT_BEHIND_NO_MEDIA
    + _HERO_PLACEMENT_BEHIND_LIGHT_MEDIA
    + _HERO_PLACEMENT_BEHIND_DARK_MEDIA
    + _HERO_PLACEMENT_BESIDE
    + _HERO_PLACEMENT_ABOVE
    + _HERO_PLACEMENT_EYEBROW_MARKER
    + _HERO_PLACEMENT_PRESENCE
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
    decoration_mark = mark_safe(  # noqa: S308 - our own fixture markup
        '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
        '<circle cx="32" cy="32" r="28" fill="currentColor"/>'
        "</svg>"
    )
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
        "decoration_mark": decoration_mark,
        "meta_items": ["Est. 2019", "Available for projects"],
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

_CTA_WIDTH_SECTION_SHELL = '{% include "brickwork_marketing/components/_section.html" with width="bleed" band="tint" %}'

_CTA_WIDTH_SOURCE = (
    '{% extends "brickwork_marketing/shell/marketing.html" %}'
    + _MARKETING_CHROME
    + "{% block content %}"
    + _CTA_WIDTH_CONTAINED_PLAIN
    + _CTA_WIDTH_CONTAINED_TINT
    + _CTA_WIDTH_BLEED_PLAIN
    + _CTA_WIDTH_BLEED_TINT
    + _CTA_WIDTH_SECTION_SHELL
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


# --- marketing sustainment primitives (BR-BW-MKT-007..009, #570/#571) ---------
#
# Three primitives shipped with no dedicated fixture: soft-stage atmosphere
# under the overlay header (BR-BW-MKT-007 composing with BR-BW-MKT-006),
# product-shot chrome inside a hero media slot at both media_placement values
# it supports (BR-BW-MKT-008), and section reveal motion (BR-BW-MKT-009).
# render_sections already stacks the example sections that exercise each of
# these once, but that fixture never composes soft-stage with the overlay
# header (the two features interact: BR-BW-MKT-007 rule 3), and never shows
# the product shot at both "beside" and "below". These fixtures close that gap
# rather than duplicate render_sections' own coverage.


_SOFT_STAGE_OVERLAY_HERO = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Invoicing" heading="Atmosphere under the overlay header"'
    ' lede="Soft-stage is the first-band atmosphere under an overlay header, not a second shell."'
    " primary_cta=primary_cta secondary_cta=secondary_cta"
    ' align="center" atmosphere="soft-stage" %}'
)


def render_soft_stage_overlay(theme: str) -> str:
    """BR-BW-MKT-007 rule 3: soft-stage composes with the overlay header (BR-BW-MKT-006).

    Reuses the overlay shell shape from render_marketing_overlay, but with a
    soft-stage hero as the first band rather than the plain full-bleed
    section that fixture uses, so BOTH clearance mechanisms are exercised
    together on the same document. The soft-stage hero here is the default
    "below" media placement on the ordinary surface, so its ink follows the
    page theme: the header's own data-bw-nav-context is stamped to match
    theme (BR-BW-MKT-006 rule 4), not hard-coded to "dark". A hard-coded
    "dark" here rendered the light-theme header ink near-white on a
    near-white band, which axe reports as incomplete gradient-backed
    contrast rather than a violation. _hero.html's root <section> has no
    attrs passthrough to also stamp data-bw-nav-context on the band itself
    (the marking _overlay_shell_source's own hand-authored bands do); that
    is moot for this fixture regardless, since it is the no-JS static
    export (inject=False) where marketing-overlay.js's band scan never
    runs, so only the header's own stamped attribute is ever examined.
    """
    hero_context = "dark" if theme == "dark" else "light"
    request = RequestFactory().get("/marketing/soft-stage-overlay/")
    source = (
        '{% extends "brickwork_marketing/shell/marketing.html" %}'
        "{% load brickwork_components %}"
        "{% block marketing_header_modifiers %}bw-site-header--overlay{% endblock %}"
        f'{{% block marketing_header_attrs %}} data-bw-overlay-ready data-bw-nav-context="{hero_context}" data-bw-scrolled="false"{{% endblock %}}'
        "{% block brand_wordmark %}Acme{% endblock %}"
        "{% block marketing_nav %}"
        '<a href="#features">Features</a>'
        '<a href="#pricing">Pricing</a>'
        '<a href="#about">About</a>'
        "{% endblock %}"
        "{% block marketing_actions %}"
        '<a href="#signin">Sign in</a>'
        '{% bw_button "Get started" href="#start" variant="primary" size="sm" %}'
        "{% endblock %}"
        "{% block content %}" + _SOFT_STAGE_OVERLAY_HERO + "{% endblock %}"
        "{% block footer_legal %}&copy; 2026 Acme Ltd. All rights reserved.{% endblock %}"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Soft-stage under overlay",
        "bw_page_title": "Soft-stage under overlay, Acme",
        "primary_cta": {"label": "Start free trial", "url": "#start"},
        "secondary_cta": {"label": "Book a demo", "url": "#demo"},
    }
    html = engines["django"].from_string(source).render(ctx, request=request)
    return _inline_overlay_script(_inline_css(html), inject=False)


_HERO_BLEED_SOFT_STAGE_HERO = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Invoicing" heading="A stage that runs edge to edge"'
    ' lede="width=bleed composes with atmosphere=soft-stage: the wash-and-grid'
    ' layer now spans the full viewport instead of stopping at the marketing rail."'
    " primary_cta=primary_cta secondary_cta=secondary_cta"
    ' align="center" width="bleed" atmosphere="soft-stage" %}'
)


def render_hero_bleed_soft_stage(theme: str) -> str:
    """icvoss/django-brickwork#710: width="bleed" composed with atmosphere="soft-stage".

    Mirrors render_soft_stage_overlay's shell shape exactly (same overlay
    header, same clearance mechanism, BR-BW-MKT-006) so this fixture also
    proves width="bleed" composes with the overlay's own first-child
    clearance padding, which targets .bw-hero directly and is unaffected
    by the bleed axis's inline-size escape. No other fixture composes
    width="bleed" with atmosphere="soft-stage": render_soft_stage_overlay
    exercises soft-stage alone (the default "contained" width), and
    render_cta_width exercises width="bleed" on _cta.html/_section.html,
    never on the hero. a11y/marketing_bleed.spec.mjs proves the escape
    live (bounding-box width against the viewport), which axe cannot:
    axe checks contrast and semantics, not layout geometry.
    """
    hero_context = "dark" if theme == "dark" else "light"
    request = RequestFactory().get("/marketing/hero-bleed-soft-stage/")
    source = (
        '{% extends "brickwork_marketing/shell/marketing.html" %}'
        "{% load brickwork_components %}"
        "{% block marketing_header_modifiers %}bw-site-header--overlay{% endblock %}"
        f'{{% block marketing_header_attrs %}} data-bw-overlay-ready data-bw-nav-context="{hero_context}" data-bw-scrolled="false"{{% endblock %}}'
        "{% block brand_wordmark %}Acme{% endblock %}"
        "{% block marketing_nav %}"
        '<a href="#features">Features</a>'
        '<a href="#pricing">Pricing</a>'
        '<a href="#about">About</a>'
        "{% endblock %}"
        "{% block marketing_actions %}"
        '<a href="#signin">Sign in</a>'
        '{% bw_button "Get started" href="#start" variant="primary" size="sm" %}'
        "{% endblock %}"
        "{% block content %}" + _HERO_BLEED_SOFT_STAGE_HERO + "{% endblock %}"
        "{% block footer_legal %}&copy; 2026 Acme Ltd. All rights reserved.{% endblock %}"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Hero bleed with soft-stage",
        "bw_page_title": "Hero bleed with soft-stage, Acme",
        "primary_cta": {"label": "Start free trial", "url": "#start"},
        "secondary_cta": {"label": "Book a demo", "url": "#demo"},
    }
    html = engines["django"].from_string(source).render(ctx, request=request)
    return _inline_overlay_script(_inline_css(html), inject=False)


_SOFT_STAGE_MEDIA_BEHIND_HERO = (
    '{% include "brickwork_marketing/components/_hero.html" with'
    ' eyebrow="Invoicing" heading="Copy stays on top of the stage and the media"'
    ' lede="Soft-stage composes with media_placement=behind: copy and its scrim'
    ' must still paint above both the decorative stage and the media."'
    " primary_cta=primary_cta secondary_cta=secondary_cta"
    ' media=behind_media media_placement="behind" atmosphere="soft-stage" %}'
)


def render_soft_stage_media_behind(theme: str) -> str:
    """BR-BW-MKT-007 rule 3 x ADR-057 media_placement="behind": soft-stage's
    decorative .bw-stage layer must not repaint over .bw-hero__media, which
    must in turn not repaint over .bw-hero__copy and its scrim. No other
    fixture composes soft-stage with "behind": render_soft_stage_overlay
    above only exercises the default "below" placement, and
    render_hero_media_placement exercises "behind" without atmosphere.
    marketing_stacking.spec.mjs proves the stacking order live with
    elementFromPoint, which axe cannot: axe checks contrast and semantics,
    not paint order.
    """
    from django.utils.safestring import mark_safe

    request = RequestFactory().get("/marketing/soft-stage-media-behind/")
    behind_media = mark_safe(  # noqa: S308 - our own fixture markup
        '<svg viewBox="0 0 480 320" aria-hidden="true" focusable="false">'
        '<rect width="480" height="320" fill="#050506"/>'
        '<circle cx="240" cy="160" r="90" fill="#121214"/>'
        "</svg>"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Soft-stage with media behind",
        "bw_page_title": "Soft-stage with media behind, Acme",
        "primary_cta": {"label": "Start free trial", "url": "#start"},
        "secondary_cta": {"label": "Book a demo", "url": "#demo"},
        "behind_media": behind_media,
    }
    source = (
        '{% extends "brickwork_marketing/shell/marketing.html" %}'
        + _MARKETING_CHROME
        + "{% block content %}"
        + _SOFT_STAGE_MEDIA_BEHIND_HERO
        + "{% endblock %}"
    )
    html = engines["django"].from_string(source).render(ctx, request=request)
    return _inline_css(html)


_PRODUCT_SHOT_BESIDE_HERO = (
    '{% extends "brickwork_marketing/components/_hero.html" %}'
    "{% block media %}"
    '<div class="bw-hero__media">'
    '{% include "brickwork_marketing/components/_product_shot.html" with content=shot_media window="light" %}'
    "</div>"
    "{% endblock %}"
)
_PRODUCT_SHOT_BELOW_HERO = (
    '{% extends "brickwork_marketing/components/_hero.html" %}'
    "{% block media %}"
    '<div class="bw-hero__media">'
    '{% include "brickwork_marketing/components/_product_shot.html" with content=shot_media %}'
    "</div>"
    "{% endblock %}"
)


def render_product_shot_placement(theme: str) -> str:
    """BR-BW-MKT-008: the product shot inside a hero media slot, both the
    "beside" placement the spec names explicitly and the "below" default.
    """
    from django.utils.safestring import mark_safe

    request = RequestFactory().get("/marketing/product-shot-placement/")
    shot_media = mark_safe(  # noqa: S308 - our own fixture markup
        '<svg viewBox="0 0 480 320" aria-hidden="true" focusable="false">'
        '<rect width="480" height="320" fill="var(--bw-color-surface-sunken)"/>'
        '<rect x="24" y="24" width="240" height="16" rx="8" fill="var(--bw-color-border)"/>'
        '<rect x="24" y="60" width="160" height="16" rx="8" fill="var(--bw-color-border)"/>'
        "</svg>"
    )
    beside = (
        engines["django"]
        .from_string(_PRODUCT_SHOT_BESIDE_HERO)
        .render(
            {
                "eyebrow": "Invoicing",
                "heading": "Beside: a true two-column row",
                "lede": "The product shot fills the media column from 48rem up.",
                "primary_cta_label": "Start free trial",
                "primary_cta_href": "#start",
                "media_placement": "beside",
                "shot_media": shot_media,
            }
        )
    )
    below = (
        engines["django"]
        .from_string(_PRODUCT_SHOT_BELOW_HERO)
        .render(
            {
                "eyebrow": "Invoicing",
                "heading": "Below: the media_placement default",
                "lede": "Omitting media_placement stacks the shot after the copy, the shipped column-flex layout.",
                "primary_cta_label": "Start free trial",
                "primary_cta_href": "#start",
                "shot_media": shot_media,
            }
        )
    )
    source = (
        '{% extends "brickwork_marketing/shell/marketing.html" %}'
        + _MARKETING_CHROME
        + "{% block content %}{{ beside }}{{ below }}{% endblock %}"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Product shot placement",
        "bw_page_title": "Product shot placement, Acme",
        "beside": mark_safe(beside),  # noqa: S308 - our own rendered template
        "below": mark_safe(below),  # noqa: S308 - our own rendered template
    }
    html = engines["django"].from_string(source).render(ctx, request=request)
    return _inline_css(html)


_REVEAL_SECTION = (
    '{% include "brickwork_marketing/components/_feature_grid.html" with'
    ' heading="Everything the chasing needs" items=features columns=3 %}'
)


def render_marketing_reveal(theme: str) -> str:
    """BR-BW-MKT-009: reveal="enter" on a section wrapping a feature grid.

    The static export IS the resting state (no-JS floor): a11y/marketing_
    reveal.spec.mjs proves the reduced-motion computed style separately.
    """
    request = RequestFactory().get("/marketing/reveal/")
    features = [
        {
            "icon": "bell",
            "heading": "Automatic reminders",
            "body": "Chase on your schedule, not when you remember.",
        },
        {
            "icon": "calendar",
            "heading": "Late-payment prediction",
            "body": "Know which accounts slip before they do.",
        },
        {
            "icon": "check",
            "heading": "Reconciliation",
            "body": "Payments matched to invoices automatically.",
        },
    ]
    source = (
        '{% extends "brickwork_marketing/shell/marketing.html" %}' + _MARKETING_CHROME + "{% block content %}"
        '<section class="bw-section bw-section--reveal-enter">'
        '<div class="bw-section__inner">' + _REVEAL_SECTION + "</div>"
        "</section>"
        "{% endblock %}"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "title": "Section reveal",
        "bw_page_title": "Section reveal, Acme",
        "features": features,
    }
    html = engines["django"].from_string(source).render(ctx, request=request)
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
#                              inside the real .bw-site-header strip, and
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
    '<header class="bw-site-header">'
    '<div class="bw-site-header__inner">'
    '<div class="bw-site-header__brand">'
    '<nav class="bw-site-header__nav" aria-label="Primary">'
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


# --- app shell three-region layout (brickwork#700 / #701 / #702 / #703) -------
#
# app-regions-<theme>.html  extends shell/app.html with layout="regions", an
#                           icon-density rail (link + menu_trigger), a
#                           contextual sidebar {% bw_nav %}, and a filled
#                           topbar so axe sees the full-width topbar + sibling
#                           rail + sibling sidebar landmarks together. Empty
#                           suppression is covered by the unit tests; this
#                           fixture is the populated happy path.

_APP_REGIONS_SOURCE = (
    "{% extends 'brickwork/shell/app.html' %}"
    "{% load brickwork_nav %}"
    "{% block page_title %}App regions{% endblock %}"
    "{% block rail %}"
    "{% bw_nav_rail items=rail_items active=active density='icons' %}"
    "{% endblock %}"
    "{% block sidebar %}"
    "{% bw_nav items=contextual_items active=active %}"
    "{% endblock %}"
    "{% block mobile_nav %}"
    "{% bw_nav items=rail_items active=active %}"
    "{% endblock %}"
    "{% block topbar_search %}"
    '<input type="search" aria-label="Search" placeholder="Search">'
    "{% endblock %}"
    "{% block content %}"
    "<h1>Regions shell</h1>"
    "<p>Three-region app shell fixture.</p>"
    "{% endblock %}"
)


def render_app_regions(theme: str) -> str:
    from brickwork.models import NavItem

    rail_items = (
        NavItem(key="fx-ar-home", label="Home", href="/", icon="home"),
        NavItem(
            key="fx-ar-channels",
            label="Channels",
            menu_trigger=True,
            icon="folder",
            children=(NavItem(key="fx-ar-email", label="Email", href="/email/"),),
        ),
        NavItem(key="fx-ar-settings", label="Settings", href="/settings/", icon="settings"),
    )
    contextual_items = (
        NavItem(key="fx-ar-overview", label="Overview", href="/"),
        NavItem(key="fx-ar-activity", label="Activity", href="/activity/"),
    )
    request = RequestFactory().get("/")
    ctx = {
        "request": request,
        "layout": "regions",
        "bw_theme": theme,
        "rail_items": rail_items,
        "contextual_items": contextual_items,
        "active": rail_items[0],
    }
    html = engines["django"].from_string(_APP_REGIONS_SOURCE).render(ctx, request=request)
    return _inline_css(html)


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


# --- version switcher (icvoss/django-brickwork#414) --------------------------
#
# version-switch-<theme>.html is a standalone page mirroring render_search:
# {% bw_version_switch %} is a private render target with no demo page of its
# own, so the fixture composes the REAL tag directly (current latest plus an
# older deprecated entry) so axe sees the disclosure, aria-current marking,
# and status text.

_VERSION_SWITCH_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Version switch (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Version switch</h1>
  <section aria-labelledby="version-switch-heading">
    <h2 id="version-switch-heading">Documentation version</h2>
    __VERSION_SWITCH__
  </section>
</main>
</body>
</html>
"""


def _render_version_switch_fixture() -> str:
    from django.template import Context, Template

    return Template("{% load brickwork_components %}{% bw_version_switch versions=versions current=current %}").render(
        Context(
            {
                "versions": [
                    {"label": "3.31.0", "href": "/docs/3.31.0/", "status": "latest"},
                    {"label": "3.30.0", "href": "/docs/3.30.0/"},
                    {"label": "3.28.0", "href": "/docs/3.28.0/", "status": "deprecated"},
                ],
                "current": "3.31.0",
            }
        )
    )


def render_version_switch(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _VERSION_SWITCH_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__VERSION_SWITCH__", _render_version_switch_fixture())
    )


# --- docs on-this-page toc (icvoss/django-brickwork#627) --------------------
#
# toc-<theme>.html is a standalone page mirroring render_version_switch:
# {% bw_toc %} reuses .bw-docs-toc chrome with nested __sub entries and an
# active aria-current="location" marker.

_TOC_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Table of contents (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Table of contents</h1>
  <section aria-labelledby="toc-fixture-heading">
    <h2 id="toc-fixture-heading">On this page control</h2>
    __TOC__
  </section>
</main>
</body>
</html>
"""


def _render_toc_fixture() -> str:
    from django.template import Context, Template

    return Template(
        "{% load brickwork_components %}{% bw_toc items=items active=active heading_id='bw-docs-toc-heading' %}"
    ).render(
        Context(
            {
                "items": [
                    {
                        "label": "Escalation order",
                        "href": "#escalation-order",
                        "children": [
                            {"label": "Changing the thresholds", "href": "#changing-the-thresholds"},
                        ],
                    },
                    {"label": "Testing a schedule change", "href": "#testing-a-schedule"},
                    {"label": "Recovery by stage", "href": "#recovery-by-stage"},
                ],
                "active": "#changing-the-thresholds",
            }
        )
    )


def render_toc(theme: str) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    return (
        _TOC_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace("__TOC__", _render_toc_fixture())
    )


# --- the code display content primitive (icvoss/django-brickwork#259) -------
#
# code-display-<theme>.html is a standalone (non-shell) page, mirroring
# render_search's self-contained shape: _code.html has no dedicated demo
# page of its own beyond the sections-*.html stack (which renders it via the
# new sections/content/code.html example, one line per snippet only, per
# that file's own header comment on Django's tag-tokenizer constraint). This
# fixture instead renders the REAL template directly with genuinely
# multi-line, real source text (a Python string carries no such tokenizer
# limit), so the axe gate examines the shape the component actually exists
# for: a plain panel (no header), a filename+language panel, and a
# copyable panel, each with several real lines of code. The JS leg
# (code-display-js-<theme>.html) boots Alpine for real so bwCodeCopy's own
# init() reveals the copy control, proving the no-JS floor (the button
# never renders visible without it) and the enhanced control (it does, once
# JS runs) are both genuinely different observed states, not merely
# asserted ones.

_CODE_DISPLAY_PAGE = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Code display (__THEME__)</title>
__CSS__
</head>
<body class="bw-body">
<main>
  <h1>Code display</h1>

  <section aria-labelledby="code-plain-heading">
    <h2 id="code-plain-heading">Plain panel, no header</h2>
    __CODE_PLAIN__
  </section>

  <section aria-labelledby="code-labelled-heading">
    <h2 id="code-labelled-heading">Filename and language</h2>
    __CODE_LABELLED__
  </section>

  <section aria-labelledby="code-copyable-heading">
    <h2 id="code-copyable-heading">Copyable</h2>
    __CODE_COPYABLE__
  </section>
</main>
__JS_BOOT__
</body>
</html>
"""

_CODE_DISPLAY_PLAIN_SNIPPET = """due_date - 7d   first reminder, friendly
due_date        due today
due_date + 3d   overdue, cc the account owner
due_date + 14d  final notice before escalation"""

_CODE_DISPLAY_PYTHON_SNIPPET = """def next_reminder(invoice):
    \"\"\"Return the next reminder stage for an overdue invoice.\"\"\"
    days_overdue = (today() - invoice.due_date).days
    if days_overdue >= 14:
        return Stage.FINAL_NOTICE
    if days_overdue >= 3:
        return Stage.OVERDUE
    return Stage.DUE_TODAY"""

_CODE_DISPLAY_TS_SNIPPET = """import { nextReminder, Stage } from "./reminders";

test("escalates after 14 days", () => {
  const invoice = { dueDate: daysAgo(15) };
  expect(nextReminder(invoice)).toBe(Stage.FinalNotice);
});"""


def _render_code_display_fixture(*, filename: str, language: str, code: str, copyable: bool = False) -> str:
    return render_to_string(
        "brickwork/components/_code.html",
        {
            "filename": filename,
            "language": language,
            "label": "Reminder schedule" if not filename else "",
            "code": code,
            "copyable": copyable,
        },
    )


def render_code_display(theme: str, *, inject_js: bool = False) -> str:
    css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
    page = (
        _CODE_DISPLAY_PAGE.replace("__THEME__", theme)
        .replace("__CSS__", f"<style>{css}</style>")
        .replace(
            "__CODE_PLAIN__",
            _render_code_display_fixture(filename="", language="", code=_CODE_DISPLAY_PLAIN_SNIPPET),
        )
        .replace(
            "__CODE_LABELLED__",
            _render_code_display_fixture(
                filename="billing/reminders.py", language="Python", code=_CODE_DISPLAY_PYTHON_SNIPPET
            ),
        )
        .replace(
            "__CODE_COPYABLE__",
            _render_code_display_fixture(
                filename="billing/reminders.test.ts",
                language="TypeScript",
                code=_CODE_DISPLAY_TS_SNIPPET,
                copyable=True,
            ),
        )
    )
    return page.replace("__JS_BOOT__", _JS_BOOT if inject_js else "")


# --- the docs shell (ADR-091, icvoss/django-brickwork#439) ---------------
#
# shell/docs.html is a new shell this branch adds: the [article | rail]
# two-column layout, article-then-rail in source order with CSS `order: -1`
# restoring the rail visually at --bw-breakpoint-lg (the shell's own normative
# rule, see its header comment). This fixture exercises the real contract
# rather than an empty page: a populated article (docs_header, long-form
# content wrapped in .bw-prose with a heading hierarchy, a code block and a
# list, docs_footer) plus a real {% bw_nav %} rail in docs_nav, since the
# package ships no docs nav component and a consumer composes the existing
# nav mechanism there (the shell's own docSource, "the mechanism is the
# package's own {% bw_nav %}"). The layout CSS is not overridden or
# suppressed here, so the axe gate's multi-breakpoint sweep genuinely
# observes the source-order/visual-order split the shell's header calls out
# as the one constraint bought with a real consumer defect.
_DOCS_SOURCE = (
    '{% extends "brickwork/shell/docs.html" %}'
    "{% load brickwork_components brickwork_nav %}"
    "{% block page_title %}Configuring widget filters{% endblock %}"
    "{% block docs_header %}"
    "<h1>Configuring widget filters</h1>"
    '<p class="bw-prose__lede">How the filter bar resolves query parameters'
    " into the records table, and the options available to a consumer"
    " composing their own filter set.</p>"
    "{% endblock %}"
    "{% block content %}"
    '<div class="bw-prose">'
    "<p>Every list page ships a filter bar backed by a plain Django form:"
    " each bound field becomes one query parameter, and the records table"
    " re-renders from the resolved queryset on every request.</p>"
    "<h2>Declaring the filter form</h2>"
    "<p>A filter form is a normal <code>forms.Form</code> subclass. Nothing"
    " about it is brickwork-specific until it is passed to the filter bar"
    " include:</p>"
    "<pre><code>class WidgetFilterForm(forms.Form):\n"
    "    status = forms.ChoiceField(\n"
    "        choices=STATUS_CHOICES,\n"
    "        required=False,\n"
    "    )\n"
    "    q = forms.CharField(required=False)</code></pre>"
    "<p>Bind it from the request's query string in the view, then include the"
    " filter bar with the bound instance:</p>"
    "<h2>Behaviour worth knowing</h2>"
    "<ul>"
    "<li>An empty field is dropped from the query string entirely rather than"
    " kept as an empty parameter.</li>"
    "<li>The clear link resets to the bare list URL, not to the form's"
    " initial values.</li>"
    "<li>Sortable columns compose with the filter set: the sort parameter is"
    " preserved across a filter change.</li>"
    "</ul>"
    "<h3>Common mistakes</h3>"
    "<p>Passing an unbound form renders the filter bar with no applied"
    " filters, which is easy to miss in review because the bar still renders"
    " correctly, just against an empty query.</p>"
    "</div>"
    "{% endblock %}"
    "{% block docs_footer %}"
    '<p><a href="/widgets/">&larr; Back to widgets</a></p>'
    "{% endblock %}"
    "{% block docs_nav %}"
    "{% bw_nav items=docs_nav_items active=docs_nav_active labels='wrap' %}"
    "{% endblock %}"
)


_DOCS_SITE_CHROME_HEADER_INCLUDE = '{% include "brickwork/components/_site_header.html" %}'

_DOCS_SITE_CHROME_FOOTER_INCLUDE = '{% include "brickwork/components/_site_footer.html" %}'


def render_docs_with_site_chrome(theme: str) -> str:
    """The docs shell WITH package shared site chrome (ADR-113 / #448).

    Overrides docs_site_*_region so the package includes supply the landmark
    (no nested .bw-docs-site-header). Shares the same populated article/rail
    body as render_docs so the only variable under test is the site chrome.
    """
    from django.urls import resolve

    from brickwork.models import NavContext, NavItem
    from brickwork.services.navigation import resolve_active_item, visible_items

    tree = (
        NavItem(
            key="fx-docs-chrome-getting-started",
            label="Getting started",
            section_header=True,
            children=(
                NavItem(key="fx-docs-chrome-dashboard", label="Dashboard", url_name="testapp:dashboard"),
                NavItem(key="fx-docs-chrome-widgets", label="Widgets", url_name="testapp:widget-list"),
            ),
        ),
    )
    request = RequestFactory().get("/widgets/")
    request.resolver_match = resolve("/widgets/")
    nav_context = NavContext(request=request)
    items = visible_items(tree, nav_context)
    active = resolve_active_item(items, request.resolver_match)
    source = (
        '{% extends "brickwork/shell/docs.html" %}'
        "{% load brickwork_components brickwork_nav %}"
        "{% block page_title %}Configuring widget filters{% endblock %}"
        "{% block docs_site_header_region %}" + _DOCS_SITE_CHROME_HEADER_INCLUDE + "{% endblock %}"
        "{% block docs_header %}<h1>Configuring widget filters</h1>{% endblock %}"
        '{% block content %}<div class="bw-prose"><p>Every list page ships a'
        " filter bar backed by a plain Django form.</p></div>{% endblock %}"
        '{% block docs_footer %}<p><a href="/widgets/">&larr; Back to widgets</a></p>{% endblock %}'
        "{% block docs_nav %}{% bw_nav items=docs_nav_items active=docs_nav_active labels='wrap' %}{% endblock %}"
        "{% block docs_site_footer_region %}" + _DOCS_SITE_CHROME_FOOTER_INCLUDE + "{% endblock %}"
    )
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "docs_nav_items": items,
        "docs_nav_active": active,
    }
    html = engines["django"].from_string(source).render(ctx, request=request)
    return _inline_css(html)


def render_docs(theme: str) -> str:
    from django.urls import resolve

    from brickwork.models import NavContext, NavItem
    from brickwork.services.navigation import resolve_active_item, visible_items

    # A real docs sidebar shape: section headers grouping topic pages, one
    # active leaf (Widgets, matching the /widgets/ request below and the
    # article content, which documents the widget filter bar) so the rail's
    # active-state treatment is examined alongside the two-column layout.
    # Built the same way render_list builds its own nav context: a real
    # NavItem tree resolved through visible_items + resolve_active_item,
    # never a hand-rolled active flag.
    tree = (
        NavItem(
            key="fx-docs-getting-started",
            label="Getting started",
            section_header=True,
            children=(
                NavItem(key="fx-docs-dashboard", label="Dashboard", url_name="testapp:dashboard"),
                NavItem(key="fx-docs-widgets", label="Widgets", url_name="testapp:widget-list"),
            ),
        ),
        NavItem(
            key="fx-docs-filters",
            label="Filtering",
            section_header=True,
            children=(
                NavItem(key="fx-docs-widget-create", label="Creating a widget", url_name="testapp:widget-create"),
                NavItem(key="fx-docs-settings", label="Settings", url_name="testapp:settings-index"),
            ),
        ),
        NavItem(
            key="fx-docs-interactions",
            label="Interactions",
            section_header=True,
            children=(
                NavItem(key="fx-docs-toasts", label="Toasts", url_name="testapp:toast-demo"),
                NavItem(key="fx-docs-comboboxes", label="Comboboxes", url_name="testapp:combobox-demo"),
            ),
        ),
    )
    request = RequestFactory().get("/widgets/")
    request.resolver_match = resolve("/widgets/")
    nav_context = NavContext(request=request)
    items = visible_items(tree, nav_context)
    active = resolve_active_item(items, request.resolver_match)
    ctx = {
        "request": request,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
        "docs_nav_items": items,
        "docs_nav_active": active,
    }
    html = engines["django"].from_string(_DOCS_SOURCE).render(ctx, request=request)
    return _inline_css(html)


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
        # Beat Phase B P0 primitives (#542)
        _emit(OUT / f"primitives-{theme}.html", render_primitives(theme), written)
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
        # _card appearance suite (#535): default, inverse header recipe,
        # elevated surface, extends filler with root modifiers
        _emit(OUT / f"card-{theme}.html", render_card(theme), written)
        # _chart_card (chart card work): populated (real bw_chart_mount tag,
        # title/actions/legend fills), legend_position="side", loading,
        # error and empty states, all on one page
        _emit(OUT / f"chart-card-{theme}.html", render_chart_card(theme), written)
        # bw_gauge (VIZ-007 to VIZ-010): the default accent ring, all three
        # threshold_bands colours, and the sm/lg size modifiers, all on one
        # page
        _emit(OUT / f"gauge-{theme}.html", render_gauge(theme), written)
        # _scorecard (VIZ-011/012) and _stat_comparison (VIZ-019/020): the
        # shared dashboard grid arranging real _stat.html cards across every
        # span= modifier, plus the comparison tile's sm/md/lg sizes each
        # paired with a different trend direction, all on one page
        _emit(OUT / f"scorecard-{theme}.html", render_scorecard(theme), written)
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
        # bw_token_specimen (#268): load-bearing dual-pane specimen, no-JS floor
        _emit(OUT / f"token-specimen-{theme}.html", render_token_specimen(theme), written)
        # _preview_frame (#269): surface-guarded live-render container
        _emit(OUT / f"preview-frame-{theme}.html", render_preview_frame(theme), written)
        _emit(OUT / f"proof-collage-{theme}.html", render_proof_collage(theme), written)
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
        # package-owned marketing mobile-nav toggle (#263): marketing_nav_region
        # include pattern; landing/pricing/about omit it so coarse-pointer nav
        # assertions keep a permanently visible header row
        _emit(OUT / f"mobile-nav-toggle-{theme}.html", render_mobile_nav_toggle(theme), written)
        # marketing header overlay (ADR-105 / #565): no-JS opaque floor plus
        # statically stamped enhanced light/dark and scrolled states for axe
        _emit(
            OUT / f"marketing-overlay-{theme}.html",
            render_marketing_overlay(theme, state="nojs"),
            written,
        )
        _emit(
            OUT / f"marketing-overlay-dark-{theme}.html",
            render_marketing_overlay(theme, state="dark"),
            written,
        )
        _emit(
            OUT / f"marketing-overlay-light-scrolled-{theme}.html",
            render_marketing_overlay(theme, state="light-scrolled"),
            written,
        )
        _emit(
            OUT / f"marketing-overlay-dark-scrolled-{theme}.html",
            render_marketing_overlay(theme, state="dark-scrolled"),
            written,
        )
        _emit(
            OUT / f"marketing-overlay-js-{theme}.html",
            render_marketing_overlay(theme, state="js-boot"),
            written,
        )
        # the hero media_placement axis (ADR-057 section 1a, #118): "behind"
        # (no/light/dark media) and "beside", none of which landing/pricing/
        # about above ever render, so axe never examined the new CSS
        _emit(OUT / f"hero-placement-{theme}.html", render_hero_media_placement(theme), written)
        # the CTA width axis (ADR-057 section 1a, #98/#118 pattern): width="bleed"
        # (bw-cta--bleed), never rendered by any other fixture, crossed with band
        _emit(OUT / f"cta-width-{theme}.html", render_cta_width(theme), written)
        # soft-stage atmosphere composing with the overlay header (BR-BW-MKT-007
        # rule 3 / BR-BW-MKT-006), never composed together by any other fixture
        _emit(OUT / f"soft-stage-overlay-{theme}.html", render_soft_stage_overlay(theme), written)
        # hero width="bleed" composing with atmosphere="soft-stage" under the
        # overlay header (icvoss/django-brickwork#710): the geometry proof is
        # a11y/marketing_bleed.spec.mjs, never rendered by any other fixture
        _emit(
            OUT / f"hero-bleed-soft-stage-{theme}.html",
            render_hero_bleed_soft_stage(theme),
            written,
        )
        # soft-stage atmosphere composing with media_placement="behind"
        # (BR-BW-MKT-007 rule 3, ADR-057 section 1a): the stacking order
        # marketing_stacking.spec.mjs proves live, never rendered by any
        # other fixture
        _emit(
            OUT / f"soft-stage-media-behind-{theme}.html",
            render_soft_stage_media_behind(theme),
            written,
        )
        # product-shot chrome (BR-BW-MKT-008) inside a hero media slot at both
        # "beside" and the "below" default, never rendered by any other fixture
        _emit(OUT / f"product-shot-placement-{theme}.html", render_product_shot_placement(theme), written)
        # section reveal motion (BR-BW-MKT-009): the resting-state (no-JS) export;
        # the reduced-motion computed-style proof is a11y/marketing_reveal.spec.mjs
        _emit(OUT / f"marketing-reveal-{theme}.html", render_marketing_reveal(theme), written)
        # the nav renderers (#102/#82): the marketing-header row and the
        # two-tier rail + contextual pairing, ancestor-active states lit
        _emit(OUT / f"nav-renderers-{theme}.html", render_nav_renderers(theme), written)
        # three-region app shell (#700/#701/#702/#703): full-width topbar +
        # sibling icon rail (with menu trigger) + contextual sidebar
        _emit(OUT / f"app-regions-{theme}.html", render_app_regions(theme), written)
        # search + loading button (#226): bw_search and _spinner.html's
        # loading=True mount, neither previously rendered by any fixture
        _emit(OUT / f"search-{theme}.html", render_search(theme), written)
        # version switcher (#414): bw_version_switch current-version disclosure
        _emit(OUT / f"version-switch-{theme}.html", render_version_switch(theme), written)
        # docs on-this-page toc (#627): bw_toc nested entries + aria-current
        _emit(OUT / f"toc-{theme}.html", render_toc(theme), written)
        # the docs shell (ADR-091, #439): a populated two-column docs page
        # (real article content in .bw-prose, a real {% bw_nav %} rail),
        # never rendered by any other fixture before this shell existed
        _emit(OUT / f"docs-{theme}.html", render_docs(theme), written)
        # the docs shell WITH site-wide chrome filled (#448 item 1):
        # docs_site_header/docs_site_footer, the seam outside <main> no
        # other docs fixture exercises
        _emit(OUT / f"docs-with-site-chrome-{theme}.html", render_docs_with_site_chrome(theme), written)
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
        # the code display content primitive (#259): a plain panel, a
        # filename+language panel and a copyable panel, each with real
        # multi-line source, plus the JS leg proving bwCodeCopy's own
        # init() reveals the copy control that the no-JS floor ships hidden
        _emit(OUT / f"code-display-{theme}.html", render_code_display(theme), written)
        _emit(OUT / f"code-display-js-{theme}.html", render_code_display(theme, inject_js=True), written)
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
