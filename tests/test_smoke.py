"""Smoke tests: the scaffold installs and imports cleanly.

These prove the empty package is a valid Django app on the 6.0 floor. Real
contract tests (token/template/navigation/interaction/JS, the WCAG axe-core
gate, the no-JS Playwright suite) land in Phase 0 per docs/specs/saas-ui/
05-verification.md.
"""

from __future__ import annotations


def test_package_imports() -> None:
    import saas_ui

    assert saas_ui.__version__


def test_app_is_installed() -> None:
    from django.apps import apps

    assert apps.is_installed("saas_ui")


def test_tokens_submodule_is_django_free() -> None:
    # The token sub-module must import without pulling in Django, so it can
    # later extract to a standalone package. Importing it here must not raise.
    import importlib

    importlib.import_module("saas_ui.tokens")


def test_conf_defaults_resolve() -> None:
    from saas_ui.conf import ui_settings

    assert ui_settings.get("theme", "default_mode") == "system"
    assert ui_settings.get("theme", "default_direction") == "ltr"
