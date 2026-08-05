"""Django app configuration for brickwork.

The ``AppConfig.ready()`` hook is where system checks for the wiring contracts
are registered (see checks.py). Navigation duplicate-key validation is enforced
by the consuming project calling ``validate_nav_config()`` at import time
(BR-BW-NAV-002), not from ``ready()``, since brickwork ships no nav config of
its own.
"""

from __future__ import annotations

from django.apps import AppConfig
from django.core import checks


class BrickworkConfig(AppConfig):
    name = "brickwork"
    verbose_name = "brickwork UI substrate"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # The missing-theme-context-processor check (brickwork#101): the top
        # documented support trap (#22) used to fail silently; the check names
        # it at startup instead. Imported here, not at module top, so the app
        # config stays importable before Django is fully set up.
        from brickwork.checks import check_theme_context_processor

        checks.register(check_theme_context_processor, checks.Tags.templates)
