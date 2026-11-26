"""Django system checks for brickwork wiring (brickwork#101).

The number-one documented support trap (INTEGRATION.md section 3, brickwork#22)
was a silent failure: with "brickwork" in INSTALLED_APPS but
``brickwork.context_processors.theme`` missing from every DjangoTemplates
backend, the shell renders unstyled with no signal at all, and hand-mapping the
theme service's differently-named keys fails just as silently. That sat oddly
against the package's otherwise fail-fast philosophy (validate_nav_config at
import, bw_icon's exactly-one-of enforcement, unknown variants raising).

``check_theme_context_processor`` converts that rendering mystery into a named
startup message. It is registered from ``BrickworkConfig.ready()`` (apps.py),
the hook reserved for the check subsystem since Phase 0.

Why a Warning, not an Error: a consumer that uses only the component or
marketing layers (never a shell) is a legitimate install with no need for the
processor, and an Error would hard-fail its management commands. A deliberate
non-shell consumer silences the check the standard way::

    SILENCED_SYSTEM_CHECKS = ["brickwork.W001"]
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.checks import Error, Warning, register

THEME_CONTEXT_PROCESSOR = "brickwork.context_processors.theme"

_DJANGO_TEMPLATES_BACKEND = "django.template.backends.django.DjangoTemplates"


def check_theme_context_processor(app_configs, **kwargs) -> list[Warning]:
    """Warn when no DjangoTemplates backend lists the brickwork theme processor.

    Passes as soon as ANY configured DjangoTemplates backend carries
    ``brickwork.context_processors.theme`` in its context_processors; a project
    with a second (e.g. Jinja2) backend is not penalised for the extra backend.
    """
    for config in settings.TEMPLATES:
        if config.get("BACKEND") != _DJANGO_TEMPLATES_BACKEND:
            continue
        # settings.TEMPLATES is typed as list[dict[str, object]] (django-stubs has
        # no narrower shape for it, since a project's TEMPLATES entry can carry
        # arbitrary backend-specific OPTIONS); "OPTIONS" is itself an
        # object-typed value here, so it is narrowed explicitly rather than
        # chaining .get() straight through, which mypy cannot check on "object".
        options = config.get("OPTIONS", {})
        processors = options.get("context_processors", []) if isinstance(options, dict) else []
        if THEME_CONTEXT_PROCESSOR in processors:
            return []
    return [
        Warning(
            "'brickwork' is installed but no DjangoTemplates backend lists "
            f"'{THEME_CONTEXT_PROCESSOR}' in its context_processors.",
            hint=(
                "The shell reads its bw_* context variables from that processor; "
                "without it the shell renders silently unstyled (the INTEGRATION.md "
                "section 3 sharp edge, brickwork#22). Add "
                f"'{THEME_CONTEXT_PROCESSOR}' to "
                "TEMPLATES[...]['OPTIONS']['context_processors']. If this project "
                "deliberately uses only brickwork's component or marketing layers "
                "and never renders a shell, silence this check with "
                "SILENCED_SYSTEM_CHECKS = ['brickwork.W001']."
            ),
            id="brickwork.W001",
        )
    ]


E001_ID = "brickwork.E001"
_PACKAGE_LOGGER_NAME = "brickwork"


def _has_reachable_handler(logger_name: str) -> bool:
    """Return whether a handler is attached anywhere in ``logger_name``'s
    hierarchy that a record from it would actually reach, walking ancestors
    while ``propagate`` is true. ``logging.lastResort`` (the module-level
    fallback that stderr-prints WARNING+ when nothing else is configured) is
    not a configured handler and is ignored, per ADR-101 decision 3: it
    exists precisely to be invisible/unmanaged, not a substitute for a real
    handler the consumer chose.
    """
    logger = logging.getLogger(logger_name)

    current: logging.Logger | None = logger
    while current is not None:
        if any(handler is not logging.lastResort for handler in current.handlers):
            return True
        if not current.propagate:
            return False
        current = current.parent

    return False


@register()
def check_logging_handler_configured(app_configs, **kwargs):  # type: ignore[no-untyped-def]
    """Fail with an Error when no handler reaches the brickwork logger hierarchy (brickwork.E001).

    ADR-101 decision 3 and docs/STANDARDS.md section 15: a package that
    emits through logging ships a boot-time check confirming the
    consumer's LOGGING configuration actually routes it somewhere, and
    it fails as an Error, not a Warning. The failures this package logs
    (navigation warnings from `brickwork.navigation`) rely on this.
    """
    if _has_reachable_handler(_PACKAGE_LOGGER_NAME):
        return []

    logger_names = f"'{_PACKAGE_LOGGER_NAME}'"
    return [
        Error(
            "No logging handler is configured to receive records from the "
            f"{logger_names} logger (or any of its ancestors while "
            "propagate=True), so failures brickwork logs will be invisible.",
            hint=(
                "Add a handler for the 'brickwork' logger (or the root logger, "
                "if it propagates) in your LOGGING setting, e.g. "
                "LOGGING['loggers']['brickwork'] = {'handlers': [...], "
                "'level': 'WARNING', 'propagate': True}."
            ),
            id=E001_ID,
        )
    ]
