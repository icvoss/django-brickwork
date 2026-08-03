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
