from __future__ import annotations

from django.urls import path

from . import views

app_name = "testapp"

urlpatterns = [
    path("widgets/", views.WidgetListView.as_view(), name="widget-list"),
    path("widgets/new/", views.WidgetCreateView.as_view(), name="widget-create"),
    path("widgets/<int:pk>/edit/", views.WidgetUpdateView.as_view(), name="widget-edit"),
    # a nested/section route so the active-route resolver has a tree to walk
    path("settings/", views.WidgetListView.as_view(), name="settings-index"),
]
