from __future__ import annotations

from django.apps import AppConfig


class ConsumerAppConfig(AppConfig):
    """A second, V3-shaped consumer fixture (brickwork#61).

    Distinct from brickwork_testapp (the CRUD harness in settings_seams.py):
    this app is deliberately shaped like a real brownfield multi-tenant
    adopter, exercising the four seams named in #61 (multi-host shell
    branching, a BRICKWORK_THEME_RESOLVER tenant resolver, a waffle-style
    feature_checker gating nav, and the 422 form-swap loop) plus a page that
    composes the wider interaction/component set, so the smoke leg catches a
    cross-component integration break, not just the four named seams.
    """

    name = "consumer"
    label = "consumer"
    verbose_name = "brickwork V3-shaped consumer smoke harness"
    default_auto_field = "django.db.models.BigAutoField"
