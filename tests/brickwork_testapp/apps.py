from __future__ import annotations

from django.apps import AppConfig


class BrickworkTestAppConfig(AppConfig):
    name = "brickwork_testapp"
    label = "brickwork_testapp"
    verbose_name = "brickwork CRUD test harness"
    default_auto_field = "django.db.models.BigAutoField"
