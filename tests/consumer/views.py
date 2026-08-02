"""Views for the V3-shaped consumer smoke harness (brickwork#61).

Three groups:

- TicketListView / SurfaceView / ReportsView: the nav destinations (Reports
  is feature-gated, see nav.py + features.py).
- TicketCreateView: the 422 form-swap loop subject (BR-BW-HTMX-003), rendered
  through {% bw_form %} (0.15.0) rather than a hand-picked per-field loop, so
  the whole-form renderer gets exercised end-to-end too.
- SurfaceView: one page composing the modal trigger, slide-over trigger, a
  selectable data table, a stepper, and a toast trigger, so the smoke leg
  would catch a cross-component integration break (#61's "second/third
  integration exercise ahead of ratification"), not just the four named
  seams. TicketConfirmView and TicketPanelView back its modal/slide-over
  triggers with real no-JS-floor routes, matching brickwork_testapp's
  InteractionConfirmView shape.
"""

from __future__ import annotations

import json

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, View

from brickwork.services.forms import is_htmx_validation_request

from .forms import TicketForm
from .models import Ticket

_STEPPER_STEPS = [
    {"label": "Details", "status": "complete"},
    {"label": "Review", "status": "current"},
    {"label": "Confirm", "status": "upcoming"},
]

_TABLE_COLUMNS = [
    {"label": "Title", "sortable": False},
    {"label": "Priority", "sortable": False},
]


class TicketListView(ListView):
    model = Ticket
    template_name = "consumer/ticket_list.html"
    context_object_name = "tickets"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Tickets"
        return ctx


class TicketCreateView(CreateView):
    """The 422 form-swap loop (BR-BW-HTMX-003, brickwork#61 seam 4).

    An htmx-driven invalid POST responds 422 with only the form partial
    re-rendered (is_htmx_validation_request -> True); a non-htmx invalid POST
    redisplays the full page at 200 (BR-BW-HTMX-001); a valid POST redirects
    at 302. Reuses {% bw_form %} (0.15.0) inside _ticket_form.html.
    """

    model = Ticket
    form_class = TicketForm
    template_name = "consumer/ticket_form.html"
    success_url = reverse_lazy("consumer:ticket-list")

    def form_valid(self, form):
        tenant = getattr(self.request, "consumer_tenant", None)
        form.instance.tenant_slug = tenant["slug"] if tenant else "default"
        return super().form_valid(form)

    def form_invalid(self, form):
        if is_htmx_validation_request(self.request):
            response = render(self.request, "consumer/_ticket_form.html", self.get_context_data(form=form))
            response.status_code = 422
            return response
        return super().form_invalid(form)


class ReportsView(TemplateView):
    """The feature-gated nav destination itself (brickwork#61 seam 3).

    Reachable directly regardless of the flag (nav visibility is display,
    never authorisation, BR-BW-NAV-005): the flag only controls whether the
    nav item appears, matching brickwork's own documented contract.
    """

    template_name = "consumer/reports.html"


class SurfaceView(TemplateView):
    """One page composing the shipped interaction/component set (brickwork#61
    "exercise the shipped surface"): a modal trigger, a slide-over trigger, a
    selectable data table, a stepper, a bw_form, and a toast trigger."""

    template_name = "consumer/surface.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tickets = Ticket.objects.all()[:5]
        ctx.update(
            {
                "title": "Component surface",
                "table_id": "surface-tickets",
                "columns": _TABLE_COLUMNS,
                "rows": [{"id": t.pk, "cells": [t.title, t.get_priority_display()]} for t in tickets],
                "steps": _STEPPER_STEPS,
                "form": TicketForm(),
            }
        )
        return ctx


class TicketConfirmView(TemplateView):
    """The modal's two documented render paths (BR-BW-HTMX-001), mirroring
    brickwork_testapp's InteractionConfirmView: an htmx GET returns the modal
    partial only; a plain GET renders it inside the full shell. POST performs
    the action: htmx POST closes the modal server-side (204 + HX-Trigger);
    plain POST redirects."""

    template_name = "consumer/interaction_confirm.html"
    MODAL_ID = "confirm-clear"

    def _is_htmx(self) -> bool:
        return self.request.headers.get("HX-Request") == "true"

    def get_template_names(self):
        if self._is_htmx():
            return ["consumer/_confirm_modal.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "title": "Clear demo tickets",
                "modal_id": self.MODAL_ID,
                "close_url": reverse("consumer:surface"),
                "backdrop_dismiss": True,
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        Ticket.objects.all().delete()
        if self._is_htmx():
            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps({"bw:modal:close": {"id": self.MODAL_ID}})
            return response
        from django.shortcuts import redirect

        return redirect("consumer:surface")


class TicketPanelView(TemplateView):
    """The slide-over's two documented render paths (BR-BW-HTMX-001), the
    slide-over analogue of TicketConfirmView above."""

    template_name = "consumer/interaction_panel.html"
    SLIDE_OVER_ID = "ticket-panel"

    def _is_htmx(self) -> bool:
        return self.request.headers.get("HX-Request") == "true"

    def get_template_names(self):
        if self._is_htmx():
            return ["consumer/_panel_slide_over.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "title": "Ticket details",
                "slide_over_id": self.SLIDE_OVER_ID,
                "close_url": reverse("consumer:surface"),
            }
        )
        return ctx


class ToastActionView(View):
    """The toast trigger's htmx endpoint (BR-BW-HTMX-007): an OOB wrapper
    plus a small main-swap acknowledgement."""

    def post(self, request, *args, **kwargs):
        return render(request, "consumer/_toast_oob.html", {"message": "Surface action recorded."})
