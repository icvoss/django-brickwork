"""CRUD views rendering through brickwork's shell + components.

The create/edit views implement the 422 HTMX validation-swap contract
(BR-BW-HTMX-003): an htmx-driven invalid POST responds 422 with ONLY the form
section re-rendered (the hx-swap target); a non-htmx invalid POST gets a normal
full-page redisplay (itself a working page, BR-BW-HTMX-001).
"""

from __future__ import annotations

from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from brickwork.services.forms import is_htmx_validation_request

from .forms import WidgetForm
from .models import Widget

_COLUMNS = [
    {
        "label": "Name",
        "key": "name",
        "sortable": True,
        "sort_key": "name",
        "sort_key_desc": "-name",
        "next_sort": "-name",
    },
    {
        "label": "Status",
        "key": "status",
        "sortable": True,
        "sort_key": "status",
        "sort_key_desc": "-status",
        "next_sort": "status",
    },
]


class WidgetListView(ListView):
    model = Widget
    template_name = "brickwork_testapp/widget_list.html"
    context_object_name = "widgets"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        sort = self.request.GET.get("sort")
        if sort in {"name", "-name", "status", "-status"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["table_columns"] = _COLUMNS
        ctx["current_sort"] = self.request.GET.get("sort", "")
        ctx["table_rows"] = [
            {"id": w.pk, "cells": [w.name, w.get_status_display()], "url": f"/widgets/{w.pk}/edit/"}
            for w in ctx["widgets"]
        ]
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
