"""Django app configuration for saas_ui.

The AppConfig.ready() hook is where navigation validation runs (duplicate-key
detection raises at startup per BR-SUI-NAV-*), and where any system checks for
the token/template contracts are registered. Kept minimal in the scaffold;
populated as the navigation and check subsystems land in Phase 0.
"""

from __future__ import annotations

from django.apps import AppConfig


class SaasUiConfig(AppConfig):
    name = "saas_ui"
    verbose_name = "SaaS UI substrate"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # Phase 0: register system checks (token/template/nav contract guards)
        # and run navigation duplicate-key validation here. Intentionally empty
        # in the scaffold so an install imports cleanly with no models.
        pass
