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
import subprocess
from pathlib import Path

import django

django.setup()

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
