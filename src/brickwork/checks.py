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

from django.conf import settings
from django.core.checks import Warning

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
        processors = config.get("OPTIONS", {}).get("context_processors", [])
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
