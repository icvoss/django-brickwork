"""Settings leg that installs the brickwork_testapp.

The testapp provides real views/URLs/templates/forms so the nav active-route
resolver, the 422 HTMX form swap, and the no-JS full-page render can be exercised
end-to-end. It is kept out of the default settings leg (mirrors the icv-media
house pattern) so its routing and models never pollute a plain-install check.
"""

from tests.settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.sessions",
    "brickwork",
    "brickwork.marketing",
    "brickwork_testapp",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                "brickwork_testapp.context_processors.brickwork_context",
            ],
        },
    }
]


# ADR-101 decision 3: the logging-handler boot check (brickwork.E001) is an
# Error, so every settings module that runs system checks (makemigrations,
# migrate, check) must route the package logger to a handler. Propagation
# stays on so caplog and the root logger still see the records, and the root
# handler covers any sibling ICV package installed alongside this one.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {
        "brickwork": {"handlers": ["null"], "level": "WARNING", "propagate": True},
    },
    "root": {"handlers": ["null"]},
}
