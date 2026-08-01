"""CRUD + dashboard views rendering through brickwork's shell and patterns.

The list and dashboard pages route through the shipped 0.5.0 page patterns
(patterns/list.html, patterns/dashboard.html) via the base_parent context var
the shared testapp base extends, proving the patterns against real content.
The create/edit views implement the 422 HTMX validation-swap contract
(BR-BW-HTMX-003): an htmx-driven invalid POST responds 422 with ONLY the form
section re-rendered (the hx-swap target); a non-htmx invalid POST gets a normal
full-page redisplay (itself a working page, BR-BW-HTMX-001).
"""

from __future__ import annotations

import json

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView, View

from brickwork.services.forms import is_htmx_validation_request

from .forms import COLOUR_CHOICES, SKILL_OPTIONS, ComboDemoForm, WidgetFilterForm, WidgetForm
from .models import Widget

# The minimal sortable-column contract (#23): only label + sortable + sort_key.
# The template derives the descending key and the next-click toggle from
# sort_key + the shared current_sort, so a consumer no longer computes
# sort_key_desc / next_sort by hand.
_COLUMNS = [
    {"label": "Name", "sortable": True, "sort_key": "name"},
    {"label": "Status", "sortable": True, "sort_key": "status"},
]

# The dashboard's recent-activity table: plain columns, no sorting.
_ACTIVITY_COLUMNS = [
    {"label": "Name", "sortable": False},
    {"label": "Status", "sortable": False},
]


def _widget_counts() -> dict:
    """One aggregate for the stat tiles and the list page's facts table."""
    return Widget.objects.aggregate(
        total=Count("pk"),
        active=Count("pk", filter=Q(status="active")),
        draft=Count("pk", filter=Q(status="draft")),
    )


class WidgetListView(ListView):
    model = Widget
    template_name = "brickwork_testapp/widget_list.html"
    context_object_name = "widgets"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        # The filter bar's no-JS floor is a plain GET form (TBL-003): the view
        # reads the same params whether the request came from a full-page
        # navigation or an htmx swap.
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        status = self.request.GET.get("status")
        if status in {"draft", "active", "archived"}:
            qs = qs.filter(status=status)
        sort = self.request.GET.get("sort")
        if sort in {"name", "-name", "status", "-status"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Route the page through the shipped list pattern; the pattern's
        # page_header default is wired from title/description.
        ctx["base_parent"] = "brickwork/patterns/list.html"
        ctx["title"] = "Widgets"
        ctx["description"] = "Everything in the harness."
        ctx["filter_form"] = WidgetFilterForm(self.request.GET or None)
        # The pattern's list_body default (patterns/_table_card.html) reads
        # columns/rows/table_id/current_sort/empty_* straight from context.
        ctx["table_id"] = "widgets-table"
        ctx["columns"] = _COLUMNS
        ctx["current_sort"] = self.request.GET.get("sort", "")
        ctx["rows"] = [
            {"id": w.pk, "cells": [w.name, w.get_status_display()], "url": f"/widgets/{w.pk}/edit/"}
            for w in ctx["widgets"]
        ]
        ctx["empty_heading"] = "No widgets yet"
        ctx["empty_body"] = "Create your first widget to get started."
        # The definition-variant facts table on the list page (one aggregate,
        # not three counts).
        counts = _widget_counts()
        ctx["summary_facts"] = [
            {"label": "Total widgets", "value": counts["total"]},
            {"label": "Active", "value": counts["active"]},
            {"label": "Draft", "value": counts["draft"]},
        ]
        return ctx


class DashboardView(TemplateView):
    """The dashboard page: three stat tiles fed by real aggregates plus the
    widgets table as the recent-activity region (patterns/dashboard.html)."""

    template_name = "brickwork_testapp/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        recent = Widget.objects.order_by("-created_at")[:5]
        ctx.update(
            {
                "base_parent": "brickwork/patterns/dashboard.html",
                "title": "Dashboard",
                "description": "The workspace at a glance.",
                "stats": _widget_counts(),
                # the pattern's dashboard_activity default reads these from context
                "table_id": "activity-table",
                "columns": _ACTIVITY_COLUMNS,
                "rows": [
                    {"id": w.pk, "cells": [w.name, w.get_status_display()], "url": f"/widgets/{w.pk}/edit/"}
                    for w in recent
                ],
                "empty_heading": "No activity yet",
                "empty_body": "Create a widget to see it appear here.",
            }
        )
        return ctx


class _WidgetFormMixin:
    model = Widget
    form_class = WidgetForm
    template_name = "brickwork_testapp/widget_form.html"
    success_url = reverse_lazy("testapp:widget-list")

    def form_invalid(self, form):
        # On an htmx submission, re-render ONLY the form partial with 422 so htmx
        # swaps the form section in place (BR-BW-HTMX-003). Otherwise fall back to
        # the full-page redisplay (a working no-JS page).
        if is_htmx_validation_request(self.request):
            response = render(
                self.request,
                "brickwork_testapp/_widget_form.html",
                self.get_context_data(form=form),
            )
            response.status_code = 422
            return response
        return super().form_invalid(form)


class WidgetCreateView(_WidgetFormMixin, CreateView):
    pass


class WidgetUpdateView(_WidgetFormMixin, UpdateView):
    pass


# --- the 0.8.0 interaction set (04-interfaces section 4b) -------------------
#
# One page composes all four components with real content (a consuming-project
# shape): an actions dropdown, three tabs (one htmx-lazy), a modal opened from
# a trigger with its no-JS floor route registered, and a single-open disclosure
# group. Shared constants live here so the a11y fixture generator renders the
# exact same composition (no fixture drift).

INTERACTION_TAB_KEYS = ("overview", "details", "activity")

INTERACTION_TABS = [
    {"key": "overview", "label": "Overview"},
    {"key": "details", "label": "Details", "badge": 3},
    {"key": "activity", "label": "Activity"},
]

# The danger item's url is the modal's no-JS floor route: the same action a
# JS-enabled user reaches through the modal trigger below. The querystring on
# the first two keeps their urls unique on the page (the fixture generator
# rewires them for file:// runs).
INTERACTION_DROPDOWN_ITEMS = [
    {"label": "New widget", "url": "/widgets/new/?via=dropdown", "icon": "plus"},
    {"label": "Draft widgets", "url": "/widgets/?status=draft", "icon": "filter"},
    {"divider": True},
    {
        "label": "Reset demo data",
        "url": "/interactions/confirm/",
        "icon": "trash",
        "intent": "danger",
        "attrs": {"data-demo-action": "reset"},
    },
]

# Every tab panel body shares one fixed min-block-size so switching tabs (and
# the lazy panel's skeleton -> content swap) never shifts the layout below the
# tabs region (BR-BW-HTMX-009, AC-BW-094).
_PANEL_WRAP = '<div class="itx-panel-body" style="min-block-size: 10rem">{}</div>'

_OVERVIEW_PANEL = mark_safe(  # noqa: S308 - static harness markup, no user input
    _PANEL_WRAP.format(
        "<p>The workspace at a glance: two widgets, one active, one draft. "
        "This panel is server-rendered and visible whenever the overview tab "
        "is the server-selected tab.</p>"
    )
)

_DETAILS_PANEL = mark_safe(  # noqa: S308 - static harness markup, no user input
    _PANEL_WRAP.format(
        "<p>Alpha is active and Beta is a draft. Three fields changed this "
        "week, which is what the tab badge counts.</p>"
    )
)

# The lazy panel's placeholder: a skeleton sized to the incoming content class
# so the htmx swap reserves its space (BR-BW-HTMX-009).
_ACTIVITY_SKELETON = mark_safe(  # noqa: S308 - static harness markup, no user input
    _PANEL_WRAP.format('<div class="bw-skeleton" style="block-size: 8rem" aria-hidden="true"></div>')
)

_DISCLOSURE_ITEMS = [
    {
        "label": "What is brickwork?",
        "content": mark_safe(  # noqa: S308 - static harness markup
            "<p>The building blocks to build beautiful interfaces: a shell, "
            "navigation, forms, and the interaction set this page composes.</p>"
        ),
    },
    {
        "label": "Does it need JavaScript?",
        "content": mark_safe(  # noqa: S308 - static harness markup
            "<p>No. Every component ships a server-rendered no-JS floor; Alpine only upgrades what already works.</p>"
        ),
        "meta": mark_safe('<span class="itx-meta">no-JS</span>'),  # noqa: S308
    },
    {
        "label": "How do accordions group?",
        "content": mark_safe(  # noqa: S308 - static harness markup
            "<p>Disclosures sharing a name attribute form a native single-open "
            "accordion: opening one closes its siblings with no script.</p>"
        ),
    },
]


def interactions_context(active_tab: str | None, *, disclosure_open: bool = False) -> dict:
    """The interactions page context, shared with a11y/generate_fixtures.py.

    The view owns the server-selected tab (04-interfaces 4b): an unknown or
    missing ?tab falls back to the first tab. When the lazy tab is the active
    one its content is server-rendered inline (the no-JS floor renders the
    active panel full-page, AC-BW-085) and the lazy wiring is omitted.
    """
    from django.template.loader import render_to_string

    active = active_tab if active_tab in INTERACTION_TAB_KEYS else "overview"
    activity_is_active = active == "activity"
    # _activity_panel.html carries its own itx-panel-body wrapper so the
    # server-rendered inline case and the htmx swap response are byte-equal
    # content in an identically sized container (BR-BW-HTMX-009).
    activity_panel = (
        mark_safe(render_to_string("brickwork_testapp/_activity_panel.html"))  # noqa: S308
        if activity_is_active
        else _ACTIVITY_SKELETON
    )
    items = [dict(item) for item in _DISCLOSURE_ITEMS]
    items[0]["open"] = disclosure_open
    return {
        "title": "Interactions",
        "description": "The 0.8.0 interaction set composed with real content.",
        "tabs": INTERACTION_TABS,
        "active_tab": active,
        "dropdown_items": INTERACTION_DROPDOWN_ITEMS,
        "overview_panel": _OVERVIEW_PANEL,
        "details_panel": _DETAILS_PANEL,
        "activity_panel": activity_panel,
        "activity_lazy_url": "" if activity_is_active else "/interactions/panels/activity/",
        "disclosure_items": items,
    }


class InteractionsView(TemplateView):
    """The interactions page: all four 0.8.0 components on one real page."""

    template_name = "brickwork_testapp/interactions.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(interactions_context(self.request.GET.get("tab")))
        return ctx


class InteractionConfirmView(TemplateView):
    """The modal's two documented render paths, one consumer partial
    (04-interfaces 4b "Two render paths, one partial", BR-BW-HTMX-001).

    GET with HX-Request renders the consumer's modal partial only (the htmx
    path swaps it into #bw-modal-root and bwModal opens it); a plain GET
    renders the same partial inside a full page extending the shell, so with
    no JavaScript the modal is simply a page. POST performs the action: an
    htmx POST is answered 204 with the documented HX-Trigger server-close
    header; a plain POST redirects (POST -> redirect -> full page).
    """

    template_name = "brickwork_testapp/interaction_confirm.html"

    MODAL_ID = "confirm-reset"

    def _is_htmx(self) -> bool:
        # brickwork's own duck-typing rule: read the HX-Request header
        # directly, no django-htmx dependency required.
        return self.request.headers.get("HX-Request") == "true"

    def get_template_names(self):
        if self._is_htmx():
            return ["brickwork_testapp/_confirm_modal.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "title": "Reset demo data",
                "modal_id": self.MODAL_ID,
                "close_url": reverse("testapp:interactions"),
                "backdrop_dismiss": True,
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        Widget.objects.all().delete()
        if self._is_htmx():
            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps({"bw:modal:close": {"id": self.MODAL_ID}})
            return response
        return redirect("testapp:interactions")


class LazyActivityPanelView(TemplateView):
    """The lazy tab panel endpoint: returns the panel content partial only
    (the hx-get="... " hx-trigger="intersect once" hx-target="this" swap, CBH-014)."""

    template_name = "brickwork_testapp/_activity_panel.html"


# --- the 0.9.0 overlay pair (04-interfaces section 4b) ----------------------
#
# Two demo pages in consuming-project shape: the toast page (server-delivered
# feedback whose no-JS floor is the messages alert banner, plus the dismissible
# alert/badge instances) and the combobox page (native select floors under one
# form, with the server filter endpoint and the 422 selection-survival path).

TOAST_INTENTS = ("success", "info", "warning", "danger")
TOAST_DURATIONS = ("short", "normal", "long", "persistent")

_TOAST_MESSAGE = "Demo data saved."


class ToastDemoView(TemplateView):
    """The toast demo page: the shell's one #bw-toast-region, the delivery
    form, the messages alert floor, and the dismissible alert/badge instances."""

    template_name = "brickwork_testapp/toasts.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"title": "Toasts", "description": "Server-delivered feedback, floor first."})
        return ctx


class ToastActionView(View):
    """The toast delivery endpoint, one action with the two documented paths
    (04-interfaces 4b). An htmx POST answers 200 with the OOB toast wrapper
    (hx-swap-oob="afterbegin:#bw-toast-region", the only creation path,
    BR-BW-HTMX-007) plus the ordinary main-swap content; a plain POST queues a
    django.contrib.messages flash and redirects, so the same feedback renders
    as the _alert.html banner floor (STA-008): the toast is the enhanced form
    of a flash message, never the only form."""

    def post(self, request, *args, **kwargs):
        intent = request.POST.get("intent", "success")
        if intent not in TOAST_INTENTS:
            intent = "success"
        duration = request.POST.get("duration", "normal")
        if duration not in TOAST_DURATIONS:
            duration = "normal"
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "brickwork_testapp/_toast_oob.html",
                {"intent": intent, "duration": duration, "message": _TOAST_MESSAGE},
            )
        messages.success(request, _TOAST_MESSAGE)
        return redirect("testapp:toast-demo")


class ComboboxDemoView(FormView):
    """The combobox demo page: two combobox instances over native select
    floors (single server-filter mode + multiple client mode) in one form.
    An invalid htmx POST re-renders ONLY the form partial with 422
    (BR-BW-HTMX-003) so the combobox rehydrates its selection from the
    re-rendered floor controls; a plain invalid POST redisplays the full page."""

    template_name = "brickwork_testapp/comboboxes.html"
    form_class = ComboDemoForm
    success_url = reverse_lazy("testapp:combobox-demo")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "title": "Comboboxes",
                "description": "Filterable selection over a native select floor.",
                "skill_options": SKILL_OPTIONS,
            }
        )
        return ctx

    def form_invalid(self, form):
        if is_htmx_validation_request(self.request):
            response = render(
                self.request,
                "brickwork_testapp/_combobox_form.html",
                self.get_context_data(form=form),
            )
            response.status_code = 422
            return response
        return super().form_invalid(form)


class ComboboxColourOptionsView(TemplateView):
    """The server filter endpoint (CBH-019): returns the consumer's option-list
    partial only, filtered by ?q, for the debounced hx-get targeting the stable
    bw-listbox-id_colour listbox id (BR-BW-HTMX-005)."""

    template_name = "brickwork_testapp/_combobox_options.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip().lower()
        ctx["listbox_id"] = "bw-listbox-id_colour"
        ctx["options"] = [(value, label) for value, label in COLOUR_CHOICES if q in label.lower()]
        return ctx
