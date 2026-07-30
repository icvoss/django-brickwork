"""Smoke tests: the scaffold installs and imports cleanly.

These prove the empty package is a valid Django app on the 6.0 floor. Real
contract tests (token/template/navigation/interaction/JS, the WCAG axe-core
gate, the no-JS Playwright suite) land in Phase 0 per docs/specs/django-brickwork/
05-verification.md.
"""

from __future__ import annotations


def test_package_imports() -> None:
    import brickwork

    assert brickwork.__version__


def test_app_is_installed() -> None:
    from django.apps import apps

    assert apps.is_installed("brickwork")


def test_tokens_submodule_is_django_free() -> None:
    # The token sub-module must import without pulling in Django, so it can
    # later extract to a standalone package. Importing it here must not raise.
    import importlib

    importlib.import_module("brickwork.tokens")


def test_conf_defaults_resolve() -> None:
    # Flat BRICKWORK_* settings resolve to their documented defaults out of the
    # box (04-interfaces.md section 2). No settings are configured in
    # tests/settings.py, so these exercise the fall-through-to-default path.
    from brickwork.conf import get_setting

    assert get_setting("BRICKWORK_DEFAULT_THEME") == "light"
    assert get_setting("BRICKWORK_DEFAULT_DENSITY") == "comfortable"
    assert get_setting("BRICKWORK_DEFAULT_DIR") == "ltr"
    assert get_setting("BRICKWORK_NAV_FALLBACK") == "omit"
