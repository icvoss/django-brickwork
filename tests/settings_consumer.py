"""Settings leg that installs the V3-shaped consumer harness (tests/consumer/).

A SECOND, richer consumer app alongside brickwork_testapp/settings_seams.py
(brickwork#61): proves the four brownfield-adopter seams (multi-host shell
branching, a BRICKWORK_THEME_RESOLVER tenant resolver, a waffle-style
feature_checker gating nav, and the 422 form-swap loop) plus a page composing
the wider interaction/component set. Kept out of both the default leg and the
settings_seams leg (mirrors the icv-media house pattern brickwork_testapp
already follows) so its routing, models, and middleware never pollute either
existing leg.

ALLOWED_HOSTS carries both simulated tenant hosts (tests/consumer/tenants.py)
plus the Django test client's default testserver, so a test can address
either host by name via the Django test client's ``SERVER_NAME`` /
``Host`` header without a real DNS entry.
"""

from tests.settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.sessions",
    "brickwork",
    "consumer",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "consumer.middleware.TenantHostMiddleware",
]

ALLOWED_HOSTS = [
    "testserver",
    "localhost",
    "127.0.0.1",
    "acme.example.com",
    "globex.example.com",
    # an unmapped host used to prove tenant_for_host's fallback degrades
    # gracefully rather than raising (brickwork#61 seam 1); a genuinely
    # unknown host is out of ALLOWED_HOSTS's own concern, which is a
    # separate, orthogonal check to the tenant-resolution fallback below.
    "unmapped.example.com",
]

ROOT_URLCONF = "tests.urls_consumer"

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
                "brickwork.context_processors.theme",
                "consumer.context_processors.consumer_context",
            ],
            # brickwork#80: run the whole consumer smoke leg with the dev aid a
            # real adopter is told to use, so a shipped template whose
            # optional-by-design variable resolution regresses to a
            # string_if_invalid bypass (|default on a genuinely undefined
            # variable) fails this leg instead of leaking markers in the field.
            "string_if_invalid": "INVALID_VARIABLE: %s",
        },
    }
]

# The tenant theme resolver (brickwork#61 seam 2): reads the request host
# (already resolved onto request.consumer_tenant by TenantHostMiddleware, but
# independently correct even without it, see theme_resolver.py) and returns
# per-tenant theme/density/dir/brand, proving the
# brickwork.context_processors.theme mapping onto the shell bw_* vars.
BRICKWORK_THEME_RESOLVER = "consumer.theme_resolver.resolve_tenant_theme"
