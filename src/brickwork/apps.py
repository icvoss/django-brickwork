"""Django app configuration for brickwork.

The ``AppConfig.ready()`` hook is where any system checks for the token/template
contracts are registered. Navigation duplicate-key validation is enforced by the
consuming project calling ``validate_nav_config()`` at import time
(BR-BW-NAV-002), not from ``ready()``, since brickwork ships no nav config of its
own. Kept minimal in the scaffold; populated as the check subsystem lands in
Phase 0.
"""

from __future__ import annotations

from django.apps import AppConfig


class BrickworkConfig(AppConfig):
    name = "brickwork"
    verbose_name = "brickwork UI substrate"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # Phase 0: register system checks (token/template/nav contract guards)
        # here. Intentionally empty until the check subsystem lands; an install
        # imports cleanly with no models.
        pass
