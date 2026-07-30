"""Minimal Django settings for the brickwork test suite.

Phase 0 will add a testapp and richer configuration (theme axes, a nav policy,
the accessibility/no-JS browser suite runs against a separate settings module).
The scaffold suite only needs the app to install and import cleanly.
"""

SECRET_KEY = "test-only-not-a-secret"

# brickwork installs with NO django-htmx: its core only reads the HX-Request
# header directly and duck-types request.htmx when present. This settings
# module deliberately omits django_htmx to prove the standalone install path.
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "brickwork",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

MIDDLEWARE = []

USE_TZ = True
USE_I18N = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {},
    }
]
