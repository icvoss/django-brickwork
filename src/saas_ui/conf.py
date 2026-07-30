"""Settings access for saas_ui.

All configuration lives under a single namespaced ``SAAS_UI`` dict in the
consumer's settings (per open-question 3, resolved: ``SAAS_UI_*`` prefix with
the package name as the slug). This module wraps access so defaults, validation
and deprecation warnings have one home, rather than scattered
``getattr(settings, ...)`` calls.

Tenancy and permissions are NEVER read from a named request attribute here:
the navigation resolver takes host-injected callables (visibility_policy) so
the package stays tenancy-agnostic (request.tenant vs request.merchant diverge
across consumers). See docs/specs/saas-ui/04-interfaces.md.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

DEFAULTS: dict[str, dict[str, Any]] = {
    "shell": {
        "layout": "sidebar",
        "sidebar_collapsible": True,
        "content_width": "fluid",
    },
    "theme": {
        "default_mode": "system",
        "default_density": "comfortable",
        "default_direction": "ltr",
    },
    "navigation": {
        "policy": None,  # dotted path to a host NavigationPolicy, or None
    },
}


class UISettings:
    """Read-through accessor over the consumer's ``SAAS_UI`` settings dict."""

    def get(self, section: str, key: str, default: Any = None) -> Any:
        user = getattr(settings, "SAAS_UI", {})
        return user.get(section, {}).get(key, DEFAULTS.get(section, {}).get(key, default))


ui_settings = UISettings()
