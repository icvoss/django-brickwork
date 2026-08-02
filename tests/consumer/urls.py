from __future__ import annotations

from django.urls import path

from . import views

app_name = "consumer"

urlpatterns = [
    path("tickets/", views.TicketListView.as_view(), name="ticket-list"),
    path("tickets/new/", views.TicketCreateView.as_view(), name="ticket-create"),
    path("surface/", views.SurfaceView.as_view(), name="surface"),
    path("reports/", views.ReportsView.as_view(), name="reports"),
    path("surface/confirm/", views.TicketConfirmView.as_view(), name="surface-confirm"),
    path("surface/panel/", views.TicketPanelView.as_view(), name="surface-panel"),
    path("surface/toast/", views.ToastActionView.as_view(), name="surface-toast"),
]
