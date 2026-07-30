"""Theme-attribute resolution: turn a request into shell axis attributes.

``resolve_theme_attributes`` returns the ``data-theme`` / ``data-density`` /
``dir`` (and optional logo URL) that the shell renders on <html>. It reads the
documented BRICKWORK_DEFAULT_* settings, then lets a host-injected
``theme_resolver`` override per request (e.g. a per-user preference, or a
per-tenant brand). brickwork NEVER reads a named request attribute for tenant
identity itself (BR-BW-NAV-004 applied here); the resolver is the host's hook.

BRD-009: the resolver may also return a ``logo`` URL, so per-tenant runtime logo
swapping works without brickwork assuming where the logo lives.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from brickwork.conf import get_setting

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest


class ThemeAttributes(TypedDict, total=False):
    """The axis attributes the shell renders. `logo` is optional (BRD-009)."""

    theme: str  # "light" | "dark"
    density: str  # "compact" | "comfortable" | "spacious"
    dir: str  # "ltr" | "rtl"
    logo: str  # optional per-tenant logo URL


def resolve_theme_attributes(
    request: HttpRequest,
    *,
    theme_resolver: Callable[[HttpRequest], ThemeAttributes] | None = None,
) -> ThemeAttributes:
    """Resolve the shell's theme/density/direction (+ optional logo) for a request.

    Starts from the documented BRICKWORK_DEFAULT_* settings, then merges whatever a
    host-injected ``theme_resolver`` returns (a partial dict is fine: only the
    keys it sets override). The resolver is the sole place a host expresses
    per-user or per-tenant theming; brickwork reads no request attribute itself.
    """
    attrs: ThemeAttributes = {
        "theme": get_setting("BRICKWORK_DEFAULT_THEME"),
        "density": get_setting("BRICKWORK_DEFAULT_DENSITY"),
        "dir": get_setting("BRICKWORK_DEFAULT_DIR"),
    }
    if theme_resolver is not None:
        override = theme_resolver(request) or {}
        attrs.update({k: v for k, v in override.items() if v is not None})
    return attrs
