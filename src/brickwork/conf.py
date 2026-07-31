"""Settings access for brickwork.

Configuration is a small set of flat, namespaced ``BRICKWORK_*`` settings in the
consumer's Django settings (README Open Question 3, resolved: the ``BRICKWORK_*``
prefix uses the brand-neutral package name as the slug, not an ``ICV_*`` shape,
since this is not an ``icv-*`` package). This module centralises defaults and
validation so there is one home for them rather than scattered
``getattr(settings, ...)`` calls. The exact settings are documented in
docs/specs/django-brickwork/04-interfaces.md section 2.

Every setting has a working default; nothing requires configuration for the
package to function out of the box with a single, unbranded default theme.

Tenancy and permissions are NEVER read from a named request attribute here: the
navigation resolver takes host-injected callables (permission_checker,
feature_checker, visibility_policy) so the package stays tenancy-agnostic
(request.tenant vs request.merchant diverge across consumers, with zero
convergence in the five-app audit). See 04-interfaces.md.
"""

from __future__ import annotations

from typing import Any, Final

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Flat setting name -> (default value, allowed values or None for free-form).
# Mirrors the table in 04-interfaces.md section 2 exactly.
_SETTINGS: Final[dict[str, tuple[Any, tuple[Any, ...] | None]]] = {
    "BRICKWORK_DEFAULT_THEME": ("light", ("light", "dark")),
    "BRICKWORK_DEFAULT_DENSITY": ("comfortable", ("compact", "comfortable", "spacious")),
    "BRICKWORK_DEFAULT_DIR": ("ltr", ("ltr", "rtl")),
    "BRICKWORK_NAV_FALLBACK": ("omit", ("omit", "disabled")),
    # Optional dotted path to a Callable[[HttpRequest], ThemeAttributes] used by
    # the brickwork.context_processors.theme processor for per-user/per-tenant
    # theming. None (default) = no resolver, defaults-only theming. Free-form.
    "BRICKWORK_THEME_RESOLVER": (None, None),
}


def get_setting(name: str) -> Any:
    """Return a ``BRICKWORK_*`` setting, falling back to its documented default.

    Raises ImproperlyConfigured if the setting name is not one brickwork defines,
    or if the configured value is outside the documented allowed set. Validating
    here (rather than at each use site) makes a misconfiguration a loud, early
    failure instead of a silently-wrong render.
    """
    try:
        default, allowed = _SETTINGS[name]
    except KeyError as exc:  # pragma: no cover - defensive; not a public path
        raise ImproperlyConfigured(f"{name} is not a brickwork setting") from exc

    value = getattr(settings, name, default)
    if allowed is not None and value not in allowed:
        raise ImproperlyConfigured(f"{name}={value!r} is not one of the allowed values {allowed}.")
    return value
