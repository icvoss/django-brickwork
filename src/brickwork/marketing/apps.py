"""Django app configuration for brickwork.marketing.

BR-BW-MKT-001: this sub-app is an OPT-IN addition to a consumer's
``INSTALLED_APPS``, alongside (never in place of) ``brickwork`` itself. It
ships templates and static assets only: no models, no migrations, no views,
and no URLs. It exists purely as the Django-native template/static discovery
seam (``APP_DIRS``) that makes the marketing surface an install decision
rather than a default: a consumer who never adds this app to
``INSTALLED_APPS`` gets output byte-identical to a bare ``brickwork`` install.

Its templates live under their own ``brickwork_marketing/`` namespace (never
the core ``brickwork/`` tree), so the two version and override independently
and a marketing template never shadows a core one (BR-BW-MKT-001,
BR-BW-TPL-002).
"""

from __future__ import annotations

from django.apps import AppConfig


class MarketingConfig(AppConfig):
    name = "brickwork.marketing"
    label = "brickwork_marketing"
    verbose_name = "brickwork marketing kit"
    default_auto_field = "django.db.models.BigAutoField"
