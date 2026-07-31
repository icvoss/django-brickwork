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

from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from brickwork.services.forms import is_htmx_validation_request

from .forms import WidgetFilterForm, WidgetForm
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
            from django.shortcuts import render

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
