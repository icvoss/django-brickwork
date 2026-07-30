"""Django settings for the brickwork test suite (default leg).

A UI-substrate package needs real template rendering, so this carries a full
TEMPLATES block, staticfiles (for {% static %} in the shell), and i18n. The
brickwork_testapp (real views/URLs/forms for the nav-resolver and 422-form
tests) is added only in settings_seams.py, kept out of this default leg so its
routing never pollutes a plain install check (mirrors the icv-media house shape).

brickwork installs with NO django-htmx here: its core reads the HX-Request header
directly and duck-types request.htmx when present, so this proves the standalone
install path (django-htmx is an optional [htmx] extra, present in the dev deps
but deliberately not in INSTALLED_APPS).
"""

SECRET_KEY = "test-only-not-a-secret"  # noqa: S105

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "brickwork",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
            ],
        },
    }
]

STATIC_URL = "/static/"

USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "en-gb"
