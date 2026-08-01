"""Render brickwork pages to standalone HTML fixtures for the axe + no-JS suite.

Renders the testapp's real pages (list, dashboard, form, form-with-errors)
through the full shell, with list and dashboard routed through the shipped
0.5.0 page patterns, in both light and dark themes, inlines the compiled
brickwork.css, and writes self-contained HTML files under a11y/fixtures/.
Playwright then loads each file:// and runs axe-core (WCAG 2.2 AA) plus a
no-JS assertion.

Rendering the REAL pages (not a hand-written sample) means the a11y gate tests
exactly what a consumer ships, and it catches a contrast regression from a bad
token or a missing aria wiring on any shipped component.

Run: DJANGO_SETTINGS_MODULE=tests.settings_seams PYTHONPATH=src:tests \
     python a11y/generate_fixtures.py
"""

from __future__ import annotations

import re
from pathlib import Path

import django

django.setup()

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
            # route through patterns/list.html, exactly as the view does, so
            # the axe gate examines the fully-composed pattern page
            # (AC-BW-077): populated filter bar, table card, badges, titled
            # alert, definition table, selected row. columns/rows/table_id/
            # empty_* feed the pattern's own default table card.
            "base_parent": "brickwork/patterns/list.html",
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
    return _inline_css(render_to_string("brickwork_testapp/widget_list.html", ctx, request=request))


def render_dashboard(theme: str) -> str:
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/dashboard/")
    request.resolver_match = resolve("/dashboard/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            # route through patterns/dashboard.html, exactly as the view does:
            # three stat tiles (up + down deltas so the glyph + accessible-text
            # pairing is examined in both themes, BR-BW-TPL-007), the content
            # card, and the recent-activity table card (AC-BW-077).
            "base_parent": "brickwork/patterns/dashboard.html",
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
    return _inline_css(render_to_string("brickwork_testapp/dashboard.html", ctx, request=request))


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
        # the nav entry and the modal's close_url both lead back to the page
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
            "close_url": "/interactions/",
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
        "close_url": "/interactions/",
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
        '{% load brickwork_interactions %}{% bw_toast message intent=intent duration="persistent" id=toast_id %}'
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
        '{% bw_toast message intent="info" duration="persistent" '
        'action_label="View widgets" action_url="#toast-action-target" id="toast-with-action" %}'
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


def main() -> None:
    written = []
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
