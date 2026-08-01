from __future__ import annotations

from django.urls import path

from . import views

app_name = "testapp"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("widgets/", views.WidgetListView.as_view(), name="widget-list"),
    path("widgets/new/", views.WidgetCreateView.as_view(), name="widget-create"),
    path("widgets/<int:pk>/edit/", views.WidgetUpdateView.as_view(), name="widget-edit"),
    # a nested/section route so the active-route resolver has a tree to walk
    path("settings/", views.WidgetListView.as_view(), name="settings-index"),
    # the 0.8.0 interaction set: the composed page, the modal's no-JS floor
    # route (its htmx fragment path branches on HX-Request in the view), and
    # the lazy tab-panel endpoint
    path("interactions/", views.InteractionsView.as_view(), name="interactions"),
    path("interactions/confirm/", views.InteractionConfirmView.as_view(), name="interaction-confirm"),
    path("interactions/panels/activity/", views.LazyActivityPanelView.as_view(), name="interaction-panel-activity"),
    # the 0.9.0 overlay pair: the toast demo page and its delivery endpoint
    # (OOB wrapper on the htmx branch, messages alert floor on the plain
    # branch), and the combobox demo page with its server filter endpoint
    path("toasts/", views.ToastDemoView.as_view(), name="toast-demo"),
    path("toasts/action/", views.ToastActionView.as_view(), name="toast-action"),
    path("comboboxes/", views.ComboboxDemoView.as_view(), name="combobox-demo"),
    path("comboboxes/options/colour/", views.ComboboxColourOptionsView.as_view(), name="combobox-colour-options"),
]
