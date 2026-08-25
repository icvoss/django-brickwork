"""Ready-made context processor wiring the theme service to the shell.

The shell (``brickwork/shell/base.html``) reads the ``<html>`` axis attributes
from the context variables ``bw_theme`` / ``bw_density`` / ``bw_dir`` /
``bw_lang`` / ``bw_brand`` / ``bw_page_title``. ``resolve_theme_attributes``
returns the service-shaped dict ``{theme, density, dir, brand}`` (plus an
optional ``logo``), which does NOT match those names and carries no language. A consumer that drops the
service output straight into context therefore gets a silently unstyled shell
(brickwork#22).

Add this processor to ``TEMPLATES[...]["OPTIONS"]["context_processors"]`` and the
shell is wired with no hand mapping::

    "context_processors": [
        ...,
        "brickwork.context_processors.theme",
    ],

To express per-user or per-tenant theming, set ``BRICKWORK_THEME_RESOLVER`` to a
dotted path to a ``Callable[[HttpRequest], ThemeAttributes]`` (the same resolver
shape ``resolve_theme_attributes`` accepts); the processor imports and applies it.
``bw_lang`` comes from Django's active language (``get_language()``), so the
shell's ``<html lang>`` follows ``LocaleMiddleware``/``i18n_patterns`` with no
extra wiring. The consumer still owns ``bw_page_title`` (set it per view).

``bw_theme_locked_axes`` (icvoss/django-brickwork#117): the space-separated
subset of ``theme``/``density``/``dir``/``brand`` the resolver's OWN return
value asserted for this request, distinct from a value that merely fell back
to a ``BRICKWORK_DEFAULT_*`` setting. ``{% bw_theme_switch %}`` reads this to
decide, per axis, whether a real server preference exists (the axis renders
read-only, since a client-side default must never clobber it, SHL-003 applied
to this axis) or none does (the axis is a free client toggle). Computed by
calling the resolver a second time and inspecting its raw keys: the resolver
is documented as a pure function of ``request`` (BRANDING.md recipe 3), so a
second call carries no observable side effect beyond the one extra call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import get_language

from brickwork.conf import get_setting
from brickwork.services.tokens import resolve_theme_attributes

if TYPE_CHECKING:
    from django.http import HttpRequest


_LOCKABLE_AXES = ("theme", "density", "dir", "brand")


def theme(request: HttpRequest) -> dict:
    """Map the theme service output onto the ``bw_*`` names the shell reads.

    Returns ``bw_theme`` / ``bw_density`` / ``bw_dir`` (from
    ``resolve_theme_attributes``, honouring a ``BRICKWORK_THEME_RESOLVER`` if
    set), ``bw_lang`` (the active language), ``bw_debug`` (``settings.DEBUG``;
    gates the shell's dev-only registration detector, brickwork#87), ``bw_logo``
    when the resolver supplied one, ``bw_brand`` when the resolved brand is
    non-empty (0.10.0: rendered as ``data-bw-brand`` on the shell root <html>),
    and ``bw_theme_locked_axes`` (icvoss/django-brickwork#117: the axes a
    resolver itself asserted this request, read by ``{% bw_theme_switch %}``).
    Does NOT set ``bw_page_title`` (view-owned).
    """
    resolver_path = get_setting("BRICKWORK_THEME_RESOLVER")
    theme_resolver = import_string(resolver_path) if resolver_path else None

    attrs = resolve_theme_attributes(request, theme_resolver=theme_resolver)

    context = {
        "bw_theme": attrs.get("theme"),
        "bw_density": attrs.get("density"),
        "bw_dir": attrs.get("dir"),
        "bw_lang": get_language() or "en",
        "bw_debug": settings.DEBUG,
    }
    if attrs.get("logo"):
        context["bw_logo"] = attrs["logo"]
    if attrs.get("brand"):
        context["bw_brand"] = attrs["brand"]

    # A second, side-effect-free call: resolve_theme_attributes() merges the
    # resolver's return value with the BRICKWORK_DEFAULT_* set and discards
    # which keys came from which, so the ONLY way to see the resolver's own
    # assertion is to ask it directly (BRANDING.md recipe 3 documents the
    # resolver as a pure function of request, so this carries no observable
    # side effect beyond the one extra call).
    locked = ()
    if theme_resolver is not None:
        raw = theme_resolver(request) or {}
        locked = tuple(axis for axis in _LOCKABLE_AXES if raw.get(axis))
    context["bw_theme_locked_axes"] = " ".join(locked)
    return context
