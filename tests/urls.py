"""Root URLconf for the brickwork test suite.

The default leg has no URLs of its own (brickwork ships no views). The
brickwork_testapp's routes (list/create/edit, used by the nav-resolver and
422-form tests) are included only under settings_seams.py, so the default suite
stays route-free. Defined as an empty list here so ROOT_URLCONF always resolves.
"""

from __future__ import annotations

from django.apps import apps
from django.urls import include, path

urlpatterns: list = []

# When the testapp is installed (settings_seams leg), mount its routes so the
# resolver/form tests have real URL names to reverse and post to.
if apps.is_installed("brickwork_testapp"):
    urlpatterns += [path("", include("brickwork_testapp.urls"))]
