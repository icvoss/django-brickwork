"""Tests for the brickwork system checks (brickwork#101).

The top documented support trap (#22, INTEGRATION.md section 3) was a silent
failure: brickwork installed but brickwork.context_processors.theme missing
from every DjangoTemplates backend renders the shell unstyled with no signal.
brickwork.W001 names it at startup instead. Every test here overrides TEMPLATES
explicitly so the assertions hold identically under all three settings legs
(default, seams, consumer).
"""

from __future__ import annotations

from django.core.checks import Warning, run_checks
from django.core.checks.registry import registry as check_registry
from django.test import override_settings

from brickwork.checks import THEME_CONTEXT_PROCESSOR, check_theme_context_processor

_DJANGO_BACKEND = "django.template.backends.django.DjangoTemplates"
_JINJA_BACKEND = "django.template.backends.jinja2.Jinja2"


def _templates(*backends: dict) -> list[dict]:
    return list(backends)


def _django_backend(processors: list[str] | None = None) -> dict:
    options: dict = {}
    if processors is not None:
        options["context_processors"] = processors
    return {"BACKEND": _DJANGO_BACKEND, "APP_DIRS": True, "DIRS": [], "OPTIONS": options}


def test_missing_processor_returns_w001() -> None:
    with override_settings(TEMPLATES=_templates(_django_backend(["django.template.context_processors.request"]))):
        result = check_theme_context_processor(None)
    assert len(result) == 1
    assert isinstance(result[0], Warning)
    assert result[0].id == "brickwork.W001"
    assert THEME_CONTEXT_PROCESSOR in result[0].msg


def test_present_processor_passes() -> None:
    with override_settings(TEMPLATES=_templates(_django_backend([THEME_CONTEXT_PROCESSOR]))):
        assert check_theme_context_processor(None) == []


def test_backend_without_options_or_processors_returns_w001() -> None:
    # A DjangoTemplates backend with no OPTIONS (or no context_processors key)
    # must not crash the check; it simply cannot list the processor.
    with override_settings(TEMPLATES=_templates(_django_backend())):
        result = check_theme_context_processor(None)
    assert [w.id for w in result] == ["brickwork.W001"]


def test_any_django_backend_listing_the_processor_passes() -> None:
    # Passing on ANY DjangoTemplates backend: a project with a second backend
    # (or a first backend without the processor) is not penalised as long as
    # one carries it.
    with override_settings(
        TEMPLATES=_templates(
            _django_backend(["django.template.context_processors.request"]),
            _django_backend([THEME_CONTEXT_PROCESSOR]),
        )
    ):
        assert check_theme_context_processor(None) == []


def test_non_django_backends_do_not_count() -> None:
    # A Jinja2-only project cannot render brickwork's Django templates at all;
    # the check still warns rather than treating the foreign backend as wiring.
    with override_settings(
        TEMPLATES=_templates({"BACKEND": _JINJA_BACKEND, "APP_DIRS": False, "DIRS": [], "OPTIONS": {}})
    ):
        result = check_theme_context_processor(None)
    assert [w.id for w in result] == ["brickwork.W001"]


def test_check_is_registered_with_django() -> None:
    # BrickworkConfig.ready() must register the check so `manage.py check`
    # actually runs it; a correct check function that never registers is the
    # silent failure all over again.
    assert check_theme_context_processor in check_registry.registered_checks


def test_run_checks_end_to_end_emits_and_clears_w001() -> None:
    # Through Django's own runner, not just the function in isolation.
    with override_settings(TEMPLATES=_templates(_django_backend([]))):
        ids = [message.id for message in run_checks()]
    assert "brickwork.W001" in ids
    with override_settings(TEMPLATES=_templates(_django_backend([THEME_CONTEXT_PROCESSOR]))):
        ids = [message.id for message in run_checks()]
    assert "brickwork.W001" not in ids
