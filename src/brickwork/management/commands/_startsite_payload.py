"""The payload every ``startsite`` starter shares (ADR-095, icvoss/django-brickwork#470).

Kept separate from ``startsite.py`` so the command module stays orchestration
only (parse arguments, write files, report), matching the "thin command"
convention every management command in the ecosystem follows. Every constant
or function here yields the literal text of one emitted file.

What lives here is what both starters emit identically: the brand token file,
``manage.py``, ``wsgi.py``, the settings module (parameterised by the starter's
own app), the ``.gitignore``, and the ownership banner that prefixes every
copied example page. What differs per starter lives beside it, in
``_startsite_public_site.py`` and ``_startsite_data_app.py``, and is selected
through ``_startsite_starters.py``.

Nothing in this module is supported surface in its own right (ADR-095 section
3): the command that writes these files is governed; the files it writes are
plain, owned copies from the moment they land in a consumer's tree, and this
module is simply where their starting text lives.

Emitted pages embed real ``brickwork.examples.read_example()`` source, never a
hand-retyped copy, so the emitted page can never drift from what the installed
package actually ships (ADR-095 section 3, "the payload already ships"). A
short banner is prepended to each, in the voice ``examples/base.html`` already
uses, naming the file as emitted, owned output.
"""

from __future__ import annotations

from brickwork import __version__, examples

# --- Brand tokens ------------------------------------------------------
#
# The seven load-bearing tokens per theme (docs/DESIGN.md section 2) plus
# --bw-color-fg-on-accent, authored per theme rather than derived (the
# documented fg-on-accent trap, docs/BRANDING.md). These exact literal
# values are proven at 4.5:1 in both themes by
# tests/test_startsite.py::test_brand_css_fg_on_accent_is_contrast_valid,
# which re-validates them through the real render_brand_css() service (the
# same mechanism a dynamic per-tenant theme builder uses) rather than
# asserting contrast by eye. Placeholder hues only: a starting point the
# consumer edits, not a brand.

LIGHT_TOKENS = {
    "--bw-color-surface": "oklch(0.99 0.003 90)",
    "--bw-color-fg": "oklch(0.24 0.02 270)",
    "--bw-color-border": "oklch(0.90 0.008 270)",
    "--bw-color-accent": "oklch(0.55 0.20 265)",
    "--bw-color-danger": "oklch(0.55 0.19 25)",
    "--bw-color-success": "oklch(0.56 0.14 150)",
    "--bw-color-warning": "oklch(0.68 0.15 75)",
    "--bw-color-fg-on-accent": "oklch(0.99 0 0)",
}

DARK_TOKENS = {
    "--bw-color-surface": "oklch(0.22 0.015 270)",
    "--bw-color-fg": "oklch(0.93 0.01 90)",
    "--bw-color-border": "oklch(0.34 0.015 270)",
    "--bw-color-accent": "oklch(0.68 0.17 265)",
    "--bw-color-danger": "oklch(0.65 0.18 25)",
    "--bw-color-success": "oklch(0.66 0.13 150)",
    "--bw-color-warning": "oklch(0.72 0.14 80)",
    # The fg-on-accent flip (docs/BRANDING.md, brickwork#35): this theme's
    # accent is a LIGHT colour, so its safe foreground is dark ink, not the
    # white the light theme above uses. Never copy the light value here.
    "--bw-color-fg-on-accent": "oklch(0.16 0.02 270)",
}

#: Where the emitted brand stylesheet lives, relative to the project root, and
#: the ``{% static %}`` name the emitted pages link it by. One definition so the
#: two cannot drift apart.
BRAND_CSS_PATH = "static/brand.css"
BRAND_CSS_STATIC_NAME = "brand.css"


def brand_css() -> str:
    """Render the emitted brand stylesheet from the literal token values above.

    Uses the real ``render_brand_css`` service (validate=True), so a future
    edit to the placeholder values that breaks the fg-on-accent contrast
    check, or names an unknown token, fails the command loudly at emission
    time rather than shipping a broken starting point. This is the same
    mechanism a dynamic per-tenant theme builder uses (docs/BRANDING.md);
    the starter's brand.css is a one-time emission, not a call the emitted
    project itself makes at runtime.
    """
    from brickwork.services.brand_css import render_brand_css

    banner = (
        "/*\n"
        f" * {BRAND_CSS_PATH} -- emitted by `manage.py startsite`.\n"
        " *\n"
        " * This file is yours from the moment it was written (ADR-095). It is not\n"
        " * brickwork's brand: it is a starting point with placeholder values, proven\n"
        " * to pass the fg-on-accent contrast check brickwork enforces, nothing more.\n"
        " * Edit every value here. docs/BRANDING.md (in the installed django-brickwork\n"
        " * package) covers the load-bearing token set and the fg-on-accent trap this\n"
        " * file's --bw-color-fg-on-accent values already satisfy.\n"
        " *\n"
        " * Loaded AFTER brickwork's own tokens.css (see head_extra in each page),\n"
        " * which is what lets these overrides win the cascade.\n"
        " */\n\n"
    )
    return banner + render_brand_css(LIGHT_TOKENS, DARK_TOKENS, validate=True)


# --- Settings ------------------------------------------------------------

_SETTINGS_TEMPLATE = '''"""Settings for the project `manage.py startsite` emitted (ADR-095).

This file is yours from the moment it was written. It is not governed by
django-brickwork's versioning: edit it freely, the way you would any other
Django settings module. It wires exactly what a brickwork-based project needs
to run with populated example pages; everything past that (a production
database, allowed hosts, a secret key from the environment, deployment
settings) is this project's own to add.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Replace this before deploying anywhere reachable. A placeholder is fine for
# `runserver` on your own machine.
SECRET_KEY = "django-insecure-startsite-placeholder-change-me"  # noqa: S105

DEBUG = True

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
__BRICKWORK_APPS__
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                # Without this, the shell renders structurally correct and
                # completely unstyled with no error (brickwork's top
                # documented support trap, brickwork.W001). It is wired here
                # so `manage.py check` is clean out of the box.
                "brickwork.context_processors.theme",
            ],
        },
    },
]

WSGI_APPLICATION = "mysite.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
'''


def settings_py(*, app: str, marketing: bool) -> str:
    """Render the emitted settings module for one starter.

    ``app`` is the starter's own Django app (``pages`` or ``invoices``);
    ``marketing`` adds ``brickwork.marketing`` alongside ``brickwork`` for a
    starter whose pages extend the marketing shell. The marketing kit is a
    second, opt-in app (ADR-055): a starter that has no marketing page does
    not install it, so its output stays byte-identical to a bare
    ``brickwork`` install.
    """
    lines = [
        "    # The UI substrate.",
        '    "brickwork",',
    ]
    if marketing:
        lines += [
            "    # brickwork.marketing is the opt-in marketing kit (added alongside",
            "    # brickwork, never in place of it): this starter's landing page extends",
            "    # its shell.",
            '    "brickwork.marketing",',
        ]
    lines += [f'    "{app}",']
    return _SETTINGS_TEMPLATE.replace("__BRICKWORK_APPS__", "\n".join(lines))


def requirements_txt() -> str:
    """The emitted project's one dependency, pinned to the brickwork that wrote it.

    The pin is the version of the installed package that emitted the project,
    so the project is recorded as working against exactly what it was
    generated from. The consumer owns it from there (docs/QUICKSTART.md:
    "You own the pin"). Django is not listed: django-brickwork depends on it.
    """
    return f"# Emitted by `manage.py startsite`. Yours to edit.\ndjango-brickwork=={__version__}\n"


GITIGNORE = """# Emitted by `manage.py startsite`. Yours to edit.
__pycache__/
*.pyc
db.sqlite3
staticfiles/
.venv/
"""

WSGI_PY = '''"""WSGI entrypoint for the project `manage.py startsite` emitted."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = get_wsgi_application()
'''

MANAGE_PY = '''#!/usr/bin/env python
"""Django's manage.py, for the project `manage.py startsite` emitted."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Could not import Django. Are you sure it is installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''

# --- Page templates --------------------------------------------------------
#
# Each is the real, installed brickwork.examples source, prefixed with a
# banner in examples/base.html's own voice. Reading the source through
# brickwork.examples.read_example() (rather than retyping it here) means the
# emitted page can never disagree with what the installed package actually
# ships (ADR-095 section 3): a pin bump that changes the example changes what
# the NEXT `startsite` run emits, with nothing here to fall out of sync.

_BANNER = """{{% comment %}}
{path} -- emitted by `manage.py startsite` from brickwork's own
{source} example.

This file is yours from the moment it was written (ADR-095). It carries no
semver guarantee: django-brickwork's governed surface is the shell it
extends, the components it includes, and the --bw-* tokens it uses, not this
page. Edit it however this project needs; a later brickwork release will
never reach back into it.
{{% endcomment %}}
{{% load static %}}
{{% block head_extra %}}
  {{{{ block.super }}}}
  <link rel="stylesheet" href="{{% static '{brand}' %}}">
{{% endblock %}}
"""


def emitted_page(source_name: str, emitted_path: str) -> str:
    """Prepend the ownership banner to a copied example, after its {% extends %}.

    {% extends %} must be the first tag in a Django template, so the banner
    cannot simply be prepended to the source text: it is inserted as a
    second {% comment %} block on the line immediately after the extends
    line, ahead of the example's own leading comment. The same insertion
    carries a head_extra override linking the emitted brand.css AFTER
    brickwork's own stylesheet (docs/BRANDING.md: load order is load-bearing
    and fails silently), with {{ block.super }} so it never has to know
    whether the shell adds anything of its own to that block.
    """
    return emitted_page_from_source(examples.read_example(source_name), source_name, emitted_path)


def emitted_page_from_source(source: str, source_name: str, emitted_path: str) -> str:
    """As :func:`emitted_page`, for example source a starter has already adjusted."""
    extends_line, _, rest = source.partition("\n")
    banner = _BANNER.format(path=emitted_path, source=source_name, brand=BRAND_CSS_STATIC_NAME)
    return f"{extends_line}\n{banner}{rest}"
