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


def render_console(theme: str) -> str:
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


def main() -> None:
    written = []
    projection_css = build_projection_css()
    for theme in ("light", "dark"):
        (OUT / f"list-{theme}.html").write_text(render_list(theme))
        (OUT / f"list-menu-open-{theme}.html").write_text(render_list(theme, menu_open=True))
        # the topbar-primary layout (SHL-001, 0.6.0): the same list page with
        # the nav restyled as a horizontal band, so the axe gate covers the
        # bottom active marker, inline section labels, and inline switcher slot
        (OUT / f"list-topbar-{theme}.html").write_text(render_list(theme, layout="topbar"))
        (OUT / f"dashboard-{theme}.html").write_text(render_dashboard(theme))
        (OUT / f"form-{theme}.html").write_text(render_form(theme, with_errors=False))
        (OUT / f"form-errors-{theme}.html").write_text(render_form(theme, with_errors=True))
        # the 0.8.0 interaction set (floor, open floor states, lazy tab
        # active, the JS leg, and the modal's full-page floor)
        (OUT / f"interactions-{theme}.html").write_text(render_interactions(theme))
        (OUT / f"interactions-open-{theme}.html").write_text(
            render_interactions(theme, active_tab="details", disclosure_open=True)
        )
        (OUT / f"interactions-tab-lazy-{theme}.html").write_text(render_interactions(theme, active_tab="activity"))
        (OUT / f"interactions-js-{theme}.html").write_text(render_interactions(theme, inject_js=True))
        (OUT / f"interactions-modal-page-{theme}.html").write_text(render_modal_page(theme))
        # the 0.9.0 overlay pair (toast floors + stack, combobox floors, the
        # dismissible surfaces, and the JS legs for both pages)
        (OUT / f"toasts-{theme}.html").write_text(render_toasts(theme))
        (OUT / f"toasts-flash-{theme}.html").write_text(render_toasts(theme, flash=True))
        (OUT / f"toasts-stack-{theme}.html").write_text(render_toast_stack(theme))
        (OUT / f"toasts-js-{theme}.html").write_text(render_toasts(theme, inject_js=True))
        (OUT / f"comboboxes-{theme}.html").write_text(render_comboboxes(theme))
        (OUT / f"comboboxes-js-{theme}.html").write_text(render_comboboxes(theme, selected=True, inject_js=True))
        # the 0.10.0 Tailwind projection proof (consumer utilities only)
        (OUT / f"projection-{theme}.html").write_text(render_projection(theme, projection_css))
        # the 0.12.0 feedback set (#56/#60): skeleton, tooltip (floor + JS-open
        # state), progress (determinate + indeterminate)
        (OUT / f"feedback-{theme}.html").write_text(render_feedback(theme))
        (OUT / f"feedback-js-{theme}.html").write_text(render_feedback(theme, inject_js=True))
        (OUT / f"feedback-tooltip-open-{theme}.html").write_text(
            render_feedback(theme, inject_js=True, tooltip_open=True)
        )
        # the 0.13.0 input chrome set (#57/#58): toggle, tag input, dropzone,
        # a styled date field; plus the shell's collapsed-sidebar state
        (OUT / f"inputs-{theme}.html").write_text(render_inputs(theme))
        (OUT / f"sidebar-collapsed-{theme}.html").write_text(render_sidebar_collapsed(theme))
        # the 0.14.0 slide-over + stepper + wizard set (#55/#59): the
        # slide-over's OPEN state (dialog semantics, labelling, focusable
        # content), the stepper's status pairing, and the composed wizard page
        (OUT / f"slide-over-open-{theme}.html").write_text(render_slide_over_open(theme))
        (OUT / f"stepper-{theme}.html").write_text(render_stepper(theme))
        (OUT / f"wizard-{theme}.html").write_text(render_wizard(theme))
        # the 0.15.0 table bulk-selection + whole-form set (#53/#54): a
        # selectable table with the bulk-actions bar visible and a checked
        # row, and the whole-form renderer in a valid grid layout plus a
        # bound-invalid render (field + non-field errors)
        (OUT / f"table-selection-{theme}.html").write_text(render_table_selection(theme))
        (OUT / f"bw-form-{theme}.html").write_text(render_bw_form_fixture(theme))
        # the 1.1.0 page-templates kit (form_page, settings, console, confirm,
        # auth_signin) plus #73's POST sign-out account-menu item
        (OUT / f"form-page-{theme}.html").write_text(render_form_page(theme))
        (OUT / f"settings-{theme}.html").write_text(render_settings(theme))
        (OUT / f"console-{theme}.html").write_text(render_console(theme))
        (OUT / f"confirm-{theme}.html").write_text(render_confirm(theme))
        (OUT / f"auth-signin-{theme}.html").write_text(render_auth_signin(theme))
        (OUT / f"account-menu-post-{theme}.html").write_text(render_account_menu_post(theme))
        # the 1.2.0 marketing kit (brickwork.marketing, BR-BW-MKT-002): the
        # three shipped pages, each rendered through a consumer-shaped
        # extension carrying representative content
        (OUT / f"landing-{theme}.html").write_text(render_landing(theme))
        (OUT / f"pricing-{theme}.html").write_text(render_pricing(theme))
        (OUT / f"about-{theme}.html").write_text(render_about(theme))
        # the nav renderers (#102/#82): the marketing-header row and the
        # two-tier rail + contextual pairing, ancestor-active states lit
        (OUT / f"nav-renderers-{theme}.html").write_text(render_nav_renderers(theme))
        written += [
            f"list-{theme}",
            f"list-menu-open-{theme}",
            f"list-topbar-{theme}",
            f"dashboard-{theme}",
            f"form-{theme}",
            f"form-errors-{theme}",
            f"interactions-{theme}",
            f"interactions-open-{theme}",
            f"interactions-tab-lazy-{theme}",
            f"interactions-js-{theme}",
            f"interactions-modal-page-{theme}",
            f"toasts-{theme}",
            f"toasts-flash-{theme}",
            f"toasts-stack-{theme}",
            f"toasts-js-{theme}",
            f"comboboxes-{theme}",
            f"comboboxes-js-{theme}",
            f"projection-{theme}",
            f"feedback-{theme}",
            f"feedback-js-{theme}",
            f"feedback-tooltip-open-{theme}",
            f"inputs-{theme}",
            f"sidebar-collapsed-{theme}",
            f"slide-over-open-{theme}",
            f"stepper-{theme}",
            f"wizard-{theme}",
            f"table-selection-{theme}",
            f"bw-form-{theme}",
            f"form-page-{theme}",
            f"settings-{theme}",
            f"console-{theme}",
            f"confirm-{theme}",
            f"auth-signin-{theme}",
            f"account-menu-post-{theme}",
            f"landing-{theme}",
            f"pricing-{theme}",
            f"about-{theme}",
            f"nav-renderers-{theme}",
        ]
    FRAGMENTS.mkdir(exist_ok=True)
    (FRAGMENTS / "modal-confirm.html").write_text(render_modal_fragment())
    (FRAGMENTS / "tab-panel-activity.html").write_text(render_activity_fragment())
    written += ["fragments/modal-confirm", "fragments/tab-panel-activity"]
    for intent in _TOAST_INTENTS:
        (FRAGMENTS / f"toast-oob-{intent}.html").write_text(render_toast_fragment(intent, "persistent"))
        written.append(f"fragments/toast-oob-{intent}")
    (FRAGMENTS / "toast-oob-short.html").write_text(render_toast_fragment("success", "short"))
    (FRAGMENTS / "toast-oob-action.html").write_text(render_toast_action_fragment())
    (FRAGMENTS / "combobox-options-green.html").write_text(render_combobox_options_fragment())
    written += ["fragments/toast-oob-short", "fragments/toast-oob-action", "fragments/combobox-options-green"]
    print("fixtures written:", ", ".join(written))


if __name__ == "__main__":
    main()
