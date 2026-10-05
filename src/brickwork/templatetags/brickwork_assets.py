"""``{% bw_asset_url %}``: a cache-busted static URL for brickwork's shipped assets.

icvoss/django-brickwork#723. The shell (``brickwork/shell/base.html``) links
``brickwork/dist/brickwork.css`` through a plain ``{% static %}`` URL. On a
consumer whose static storage does not hash filenames (for example whitenoise's
``CompressedStaticFilesStorage``, chosen because ``ManifestStaticFilesStorage``
double-hashes django-vite output) sitting behind a CDN or nginx that caches
``/static/`` as immutable, a brickwork upgrade ships a new stylesheet at the
SAME path and the stale copy keeps serving: the upgrade is invisible until the
cache expires or the consumer busts it by hand.

This tag layers a ``?v=<installed brickwork version>`` query onto the
``{% static %}`` URL. The query changes on every upgrade (forcing a re-fetch)
and is byte-identical between upgrades (so it stays cache-friendly, not
cache-busting on every request). It composes with ``{% static %}`` rather than
replacing it: a hashed storage still hashes the path, and the query is simply
redundant there, never harmful. A ``?`` already present in the resolved URL is
respected (the version is appended with ``&``).
"""

from __future__ import annotations

from django import template
from django.templatetags.static import static

from brickwork import __version__

register = template.Library()


@register.simple_tag
def bw_asset_url(path: str) -> str:
    """Return the ``{% static %}`` URL for ``path`` with a ``?v=<version>`` cache-buster.

    ``path`` is a static-relative path, exactly as passed to ``{% static %}``
    (for example ``"brickwork/dist/brickwork.css"``). The returned URL carries
    the installed brickwork version as a query so a long-lived ``/static/``
    cache cannot hide a package upgrade (icvoss/django-brickwork#723).
    """
    url = static(path)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={__version__}"
