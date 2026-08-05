"""brickwork icon registry: a name -> SVG mapping that is the public API contract.

The registry maps a stable, brand-neutral icon *name* (``"trash"``,
``"chevron-down"``) to the inner SVG markup that renders it. The name vocabulary
is the versioned public contract (BR-BW-VER-001 applies to icon names exactly as
it does to token and template-block names); the vendored Lucide artwork behind
each name is a pinned, swappable implementation detail (ICO-001/002).

Consumers only ever reference an icon by name via ``{% bw_icon "name" %}``; they
never author raw inline SVG and no request/DB string ever reaches ``|safe``
(ICO-003, injection-safe by construction). A team may swap the whole set by
supplying their own registry keyed to the same names (ICO-002), or merge a
namespaced project icon in (ICO-012), without changing a single call site.

Public surface:

- ``get_icon(name)`` -> the inner SVG markup for a registered name.
- ``is_directional(name)`` -> whether the icon flips under RTL (ICO-014).
- ``register_icons(mapping, *, directional=())`` -> merge extra icons in.
- ``IconNotFoundError`` -> raised on an unknown name (ICO-013, fail loudly). A
  ``BrickworkError`` and ``LookupError``, deliberately NOT a ``KeyError``, so
  Django's template-partials machinery cannot mask it (brickwork#74).
- ``ICON_NAMES`` -> the sorted tuple of registered names (the contract surface).
"""

from __future__ import annotations

from . import registry as _registry
from .registry import (
    IconNotFoundError,
    get_icon,
    is_directional,
    register_icons,
)

__all__ = [
    "ICON_NAMES",
    "IconNotFoundError",
    "get_icon",
    "is_directional",
    "register_icons",
]


def __getattr__(attr: str) -> object:
    # Re-export ICON_NAMES lazily so it reflects register_icons() calls rather
    # than freezing the seed set at import time (registry.ICON_NAMES is itself a
    # module-__getattr__ computed value).
    if attr == "ICON_NAMES":
        return _registry.ICON_NAMES
    raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")


ICON_NAMES: tuple[str, ...]  # populated via module __getattr__; see above
