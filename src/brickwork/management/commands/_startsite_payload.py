"""The file payload the ``startsite`` command writes (ADR-095, icvoss/django-brickwork#470).

Kept separate from ``startsite.py`` so the command module stays orchestration
only (parse arguments, write files, report), matching the "thin command"
convention every management command in the ecosystem follows. Every constant
here is the literal text of one emitted file.

Nothing in this module is supported surface in its own right (ADR-095 section
3): the command that writes these files is governed; the files it writes are
plain, owned copies from the moment they land in a consumer's tree, and this
module is simply where their starting text lives.

Two of the three pages embed real ``brickwork.examples.read_example()`` source
(``app/dashboard.html``, ``docs/home.html``, ``marketing/landing.html``), never
a hand-retyped copy, so the emitted page can never drift from what the
installed package actually ships (ADR-095 section 3, "the payload already
ships"). A short banner is prepended to each, in the voice
``examples/base.html`` already uses, naming the file as emitted, owned output.
"""

from __future__ import annotations

from brickwork import examples

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
        " * static/pages/brand.css -- emitted by `manage.py startsite`.\n"
        " *\n"
        " * This file is yours from the moment it was written (ADR-095). It is not\n"
        " * brickwork's brand: it is a starting point with placeholder values, proven\n"
        " * to pass the fg-on-accent contrast check brickwork enforces, nothing more.\n"
        " * Edit every value here. docs/BRANDING.md (in the installed django-brickwork\n"
        " * package) covers the load-bearing token set and the fg-on-accent trap this\n"
        " * file's --bw-color-fg-on-accent values already satisfy.\n"
        " *\n"
        " * Loaded AFTER brickwork's own tokens.css (see head_extra in base.html),\n"
        " * which is what lets these overrides win the cascade.\n"
        " */\n\n"
    )
    return banner + render_brand_css(LIGHT_TOKENS, DARK_TOKENS, validate=True)


# --- Settings ------------------------------------------------------------

SETTINGS_PY = '''"""Settings for the project `manage.py startsite` emitted (ADR-095).

This file is yours from the moment it was written. It is not governed by
django-brickwork's versioning: edit it freely, the way you would any other
Django settings module. It wires exactly what a brickwork-based project needs
to run and look designed; everything past that (a real database, allowed
hosts, a secret key from the environment, deployment settings) is this
project's own to add.
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
    # The UI substrate. brickwork.marketing is the opt-in marketing kit
    # (added alongside brickwork, never in place of it); this project uses
    # both, since one of its three pages is the marketing landing page.
    "brickwork",
    "brickwork.marketing",
    "pages",
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

# --- urls.py ---------------------------------------------------------------

URLS_PY = '''"""URLconf for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Wires the three starting pages this
command generated; add your own routes here as the project grows.
"""

from django.urls import path

from pages import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("app/", views.dashboard, name="dashboard"),
    path("docs/", views.docs_home, name="docs-home"),
]
'''

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

# --- nav.py ------------------------------------------------------------

NAV_PY = '''"""Navigation config for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Validated at import via
validate_nav_config (brickwork's own documented pattern, docs/INTEGRATION.md
section 2), so a bad nav tree fails at startup, never at first render.

nav_items / nav_active is a convention the shipped example pages use, not a
brickwork contract: no shell reads a nav variable from context, they expose
blocks a page fills with {% bw_nav %}. This file follows that convention
because the emitted dashboard and docs pages do; it is not an API you must
keep.
"""

from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

NAV = (
    NavItem(key="dashboard", label="Dashboard", url_name="dashboard", icon="folder"),
    NavItem(key="docs", label="Docs", url_name="docs-home", icon="file"),
)

validate_nav_config(NAV)
'''

# --- views.py ------------------------------------------------------------

VIEWS_PY = '''"""Views for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Each view supplies exactly the context
its page template needs; see that template's own leading comment (copied
from the brickwork example it started from) for the full contract. Extend or
replace these however this project needs.
"""

from django.shortcuts import render
from django.urls import resolve

from brickwork.services.navigation import resolve_active_item

from .nav import NAV


def landing(request):
    """The marketing landing page (from brickwork's examples/marketing/landing.html)."""
    logos = [
        {"src": "https://placehold.co/120x32?text=Acme", "alt": "Acme"},
        {"src": "https://placehold.co/120x32?text=Globex", "alt": "Globex"},
        {"src": "https://placehold.co/120x32?text=Initech", "alt": "Initech"},
    ]
    features = [
        {
            "icon": "folder",
            "heading": "Organise everything",
            "body": "Keep every project, file and conversation in one searchable place.",
        },
        {
            "icon": "users",
            "heading": "Built for teams",
            "body": "Invite your team and share context without a single lost thread.",
        },
        {
            "icon": "settings",
            "heading": "Configured your way",
            "body": "Every workspace is different. Set it up the way your team works.",
        },
    ]
    stats = [
        {"value": "2,400+", "label": "Teams onboarded"},
        {"value": "99.98%", "label": "Uptime last quarter"},
        {"value": "4.8/5", "label": "Average review score"},
    ]
    return render(
        request,
        "pages/landing.html",
        {"logos": logos, "features": features, "stats": stats},
    )


def dashboard(request):
    """The app dashboard (from brickwork's examples/app/dashboard.html)."""
    activity_columns = [
        {"label": "Item", "sortable": False},
        {"label": "Status", "sortable": False},
        {"label": "Updated", "sortable": False},
    ]
    activity_rows = [
        {"id": "row-1", "cells": ["Quarterly report", "Complete", "2 hours ago"]},
        {"id": "row-2", "cells": ["Client onboarding", "In progress", "Yesterday"]},
        {"id": "row-3", "cells": ["Budget review", "Complete", "3 days ago"]},
    ]
    active = resolve_active_item(NAV, resolve(request.path))
    return render(
        request,
        "pages/dashboard.html",
        {
            "activity_columns": activity_columns,
            "activity_rows": activity_rows,
            "nav_items": NAV,
            "nav_active": active,
        },
    )


def docs_home(request):
    """The docs home page (from brickwork's examples/docs/home.html)."""
    active = resolve_active_item(NAV, resolve(request.path))
    return render(
        request,
        "pages/docs_home.html",
        {
            "nav_items": NAV,
            "nav_active": active,
            # No search view is scaffolded by startsite; point this at your
            # own search endpoint once you build one.
            "docs_search_action": "/docs/search/",
            "has_published_docs": True,
        },
    )
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
  <link rel="stylesheet" href="{{% static 'pages/brand.css' %}}">
{{% endblock %}}
"""


def _emitted_page(source_name: str, emitted_path: str) -> str:
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
    source = examples.read_example(source_name)
    extends_line, _, rest = source.partition("\n")
    banner = _BANNER.format(path=emitted_path, source=source_name)
    return f"{extends_line}\n{banner}{rest}"


def landing_html() -> str:
    return _emitted_page("marketing/landing.html", "pages/templates/pages/landing.html")


def dashboard_html() -> str:
    return _emitted_page("app/dashboard.html", "pages/templates/pages/dashboard.html")


def docs_home_html() -> str:
    return _emitted_page("docs/home.html", "pages/templates/pages/docs_home.html")


# --- Project README ---------------------------------------------------------

README_MD = """# This project was started with `manage.py startsite`

Everything in this directory is yours from the moment it was written
(ADR-095 in django-brickwork). There is no update command and no upgrade
path: this is a one-time emission, not a framework that reaches back into
your files later. Edit anything here however your project needs.

## What you have

- `mysite/settings.py`: brickwork and brickwork.marketing installed, the
  theme context processor wired, static files configured.
- `pages/nav.py`: a real navigation config, validated at import.
- `pages/views.py`: three views, each supplying the context its page needs.
- `pages/templates/pages/`: three real pages, copied from brickwork's own
  example pages (a marketing landing page, an app dashboard, a docs home).
- `static/pages/brand.css`: placeholder brand tokens, contrast-verified,
  ready for you to replace with your own brand.

## Next steps

1. `python manage.py runserver` and look at the three pages.
2. Edit `static/pages/brand.css` with your real brand colours. Re-verify
   `--bw-color-fg-on-accent` at 4.5:1 against your new accent in each theme;
   see BRANDING.md in the installed django-brickwork package.
3. Edit `pages/nav.py`, `pages/views.py` and the page templates: none of
   it is generated again, so there is nothing to lose by changing it.
4. Read INTEGRATION.md in the installed django-brickwork package for the
   rest of the seams (forms, htmx, the chrome/body boundary) as you build
   past these three pages.
"""
