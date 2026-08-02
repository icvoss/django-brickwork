"""Theme-attribute resolution: turn a request into shell axis attributes.

``resolve_theme_attributes`` returns the ``data-theme`` / ``data-density`` /
``dir`` (and optional logo URL and brand slug) that the shell renders on
<html>. It reads the documented BRICKWORK_DEFAULT_* settings, then lets a
host-injected ``theme_resolver`` override per request (e.g. a per-user
preference, or a per-tenant brand). brickwork NEVER reads a named request
attribute for tenant identity itself (BR-BW-NAV-004 applied here); the
resolver is the host's hook.

BRD-009: the resolver may also return a ``logo`` URL, so per-tenant runtime logo
swapping works without brickwork assuming where the logo lives.

0.10.0 (03-services amendment): ``brand`` is the fourth axis. A non-empty
brand renders as ``data-bw-brand`` on the shell root <html> so brand
stylesheets can scope to ``[data-bw-brand=...]`` at :root, where the derived
color-mix tokens compute. This is the first-class version of the site-level
shell/base.html override icvlocal carried from 0.6.0 (BR-BW-TPL-002 demand
evidence, resolved here).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, TypedDict

from django.core.exceptions import ImproperlyConfigured

from brickwork.conf import get_setting

# The brand-CSS emitter (brickwork#40) lives in its own module but is re-exported
# here so ``brickwork.services.tokens`` stays the single public token-services
# entry point (docs/BRANDING.md points consumers at this path).
from brickwork.services.brand_css import BrandValidationError, render_brand_css

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest

__all__ = [
    "BrandValidationError",
    "ThemeAttributes",
    "render_brand_css",
    "resolve_theme_attributes",
]


class ThemeAttributes(TypedDict, total=False):
    """The axis attributes the shell renders. `logo` is optional (BRD-009)."""

    theme: str  # "light" | "dark"
    density: str  # "compact" | "comfortable" | "spacious"
    dir: str  # "ltr" | "rtl"
    logo: str  # optional per-tenant logo URL
    brand: str  # "" = no brand; else an attribute-safe slug (0.10.0)


# Brand slugs flow into the data-bw-brand attribute on the shell root <html>
# and into consumers' [data-bw-brand=...] stylesheet scopes, so they are
# constrained to the same conservative id-safe token the interaction tags use
# (the tabs id-safety precedent) rather than escaped into something a selector
# cannot address.
_BRAND_SLUG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def resolve_theme_attributes(
    request: HttpRequest,
    *,
    theme_resolver: Callable[[HttpRequest], ThemeAttributes] | None = None,
) -> ThemeAttributes:
    """Resolve the shell's theme/density/direction/brand (+ optional logo) for a request.

    Starts from the documented BRICKWORK_DEFAULT_* settings, then merges whatever a
    host-injected ``theme_resolver`` returns (a partial dict is fine: only the
    keys it sets override). The resolver is the sole place a host expresses
    per-user or per-tenant theming; brickwork reads no request attribute itself.

    ``brand`` (0.10.0): a resolver result that carries a ``brand`` key wins
    (including an explicit ``""`` to suppress the default); otherwise
    ``BRICKWORK_DEFAULT_BRAND`` applies. A non-empty brand must be an
    attribute-safe slug (``[A-Za-z][A-Za-z0-9_-]*``); anything else raises
    ImproperlyConfigured here at resolve time, mirroring the tabs id-safety
    precedent, so a bad slug is a loud failure rather than a broken
    ``[data-bw-brand=...]`` selector.
    """
    attrs: ThemeAttributes = {
        "theme": get_setting("BRICKWORK_DEFAULT_THEME"),
        "density": get_setting("BRICKWORK_DEFAULT_DENSITY"),
        "dir": get_setting("BRICKWORK_DEFAULT_DIR"),
        "brand": get_setting("BRICKWORK_DEFAULT_BRAND"),
    }
    if theme_resolver is not None:
        override = theme_resolver(request) or {}
        attrs.update({k: v for k, v in override.items() if v is not None})
    brand = attrs.get("brand", "")
    if brand and not _BRAND_SLUG_RE.match(brand):
        raise ImproperlyConfigured(f"brickwork brand {brand!r} is not an attribute-safe slug ([A-Za-z][A-Za-z0-9_-]*).")
    return attrs
