"""Root URLconf for the consumer smoke leg (settings_consumer.py).

Separate from tests/urls.py (the default/seams leg's URLconf) so the
consumer app's routes never leak into either existing leg.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("consumer.urls")),
]
