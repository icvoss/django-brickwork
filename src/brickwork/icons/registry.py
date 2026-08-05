"""The icon registry: canonical name -> inner SVG markup, loaded from vendored art.

Seeded from a curated admin subset of Lucide (``lucide-static``, ISC; the
Feather-derived subset is MIT). Both notices are in NOTICE at the repo root. The
seed is a harvesting convenience, not a runtime dependency: only the parsed inner
markup is kept, and consumers only ever see ``{% bw_icon "name" %}``.

Design (why inner markup, not the whole file): each vendored Lucide file is a
full ``<svg width="24" height="24" ...>`` wrapper. brickwork strips that wrapper
and keeps only the inner ``<path>``/``<circle>`` content, so the ``{% bw_icon %}``
tag re-wraps it with brickwork's own size token, ``aria`` attributes and RTL
class at render time (ICO-004/007/014). The registry value is therefore the
paint content, never a fixed-size standalone icon.
"""

from __future__ import annotations

import re
from pathlib import Path

_VENDOR_DIR = Path(__file__).parent / "vendor" / "lucide"

# Canonical brickwork name -> vendored Lucide filename stem. brickwork owns this
# vocabulary (the verify-before-build finding: lucide-static ships the artwork
# under both old and new names but NO machine-readable alias map, so this table
# IS the alias safety net). Canonical names are chosen for how a consumer app
# would ask for the icon; the value resolves Lucide's own rename choice.
_SEED: dict[str, str] = {
    # actions
    "trash": "trash-2",
    "edit": "square-pen",
    "pencil": "pencil",
    "plus": "plus",
    "minus": "minus",
    "search": "search",
    "filter": "filter",
    "copy": "copy",
    "save": "save",
    "download": "download",
    "upload": "upload",
    "settings": "settings",
    "close": "x",
    "check": "check",
    # chevrons / arrows (directional ones flip under RTL, see _DIRECTIONAL)
    "chevron-down": "chevron-down",
    "chevron-up": "chevron-up",
    "chevron-left": "chevron-left",
    "chevron-right": "chevron-right",
    "chevron-forward": "chevron-right",  # logical: points to "next" in LTR
    "chevron-back": "chevron-left",  # logical: points to "previous" in LTR
    "arrow-up": "arrow-up",
    "arrow-down": "arrow-down",
    "sort": "arrow-up-down",
    # status / feedback (meaningful icons; consumer supplies a label)
    "alert-circle": "circle-alert",
    "alert-triangle": "triangle-alert",
    "info": "info",
    "success": "circle-check",
    "error": "circle-x",
    "help": "circle-help",
    # navigation / chrome
    "menu": "menu",
    "home": "home",
    "user": "user",
    "users": "users",
    "bell": "bell",
    "folder": "folder",
    "file": "file-text",
    "calendar": "calendar",
    "external-link": "external-link",
    "log-out": "log-out",
    "log-in": "log-in",
    "lock": "lock",
    "eye": "eye",
    "eye-off": "eye-off",
    "more-horizontal": "ellipsis",
    "more-vertical": "ellipsis-vertical",
    "sidebar": "panel-left",
    "spinner": "loader-circle",
    # file types (#88): per-type badges for media libraries, attachment lists
    # and file managers, in the file-badge form (file outline plus a type
    # marker) so a mixed listing reads as one family beside file/folder.
    # "document" deliberately shares the file-text artwork with "file": the
    # text-lines glyph IS the document icon, and the generic "file" seeded
    # that same artwork before the typed set existed. There is no "pdf":
    # Lucide ships no PDF glyph (no format/brand icons), so a consumer
    # wanting one merges its own via register_icons().
    "video": "file-play",
    "audio": "file-music",
    "document": "file-text",
    "image": "file-image",
    "archive": "file-archive",
    "spreadsheet": "file-spreadsheet",
}

# Icons whose meaning is direction-dependent: they flip horizontally under RTL
# (ICO-014). Symmetric icons (search, check, user) are deliberately NOT listed:
# flipping them would be wrong. chevron-forward/-back are logical-direction
# names, so they flip; the raw chevron-left/-right are physical and do not.
_DIRECTIONAL: frozenset[str] = frozenset(
    {
        "chevron-forward",
        "chevron-back",
        "external-link",
        "log-out",
        "log-in",
    }
)

# Matches the inner content of a vendored <svg>...</svg>, dropping the wrapper and
# any leading licence comment. Vendored files are trusted, pinned artefacts (not
# user input), so a targeted extraction is safe and keeps the registry values to
# paint content only.
_SVG_INNER = re.compile(r"<svg\b[^>]*>(.*)</svg>", re.DOTALL)


class IconNotFoundError(KeyError):
    """Raised when an icon name is not in the registry (ICO-013: fail loudly).

    A missing icon is a bug in the calling template, surfaced at render time with
    the offending name, never a silently-blank ``<svg>``.
    """


def _extract_inner(svg_text: str, *, name: str) -> str:
    match = _SVG_INNER.search(svg_text)
    if match is None:  # pragma: no cover - a malformed vendored file is a build bug
        raise ValueError(f"vendored SVG for {name!r} has no <svg> wrapper to strip")
    return " ".join(match.group(1).split())


def _load_seed() -> dict[str, str]:
    icons: dict[str, str] = {}
    for name, stem in _SEED.items():
        path = _VENDOR_DIR / f"{stem}.svg"
        icons[name] = _extract_inner(path.read_text(encoding="utf-8"), name=name)
    return icons


# The live registry (name -> inner SVG markup) and the directional-name set.
# Loaded once at import; a swap/merge mutates these via register_icons().
_ICONS: dict[str, str] = _load_seed()
_DIRECTIONAL_NAMES: set[str] = set(_DIRECTIONAL)


def get_icon(name: str) -> str:
    """Return the inner SVG markup for ``name``.

    Raises IconNotFoundError (ICO-013) if the name is not registered; the error
    message names the missing icon so a template typo is obvious.
    """
    try:
        return _ICONS[name]
    except KeyError as exc:
        raise IconNotFoundError(
            f"No icon named {name!r} in the brickwork registry. "
            f"Register it with brickwork.icons.register_icons() or check the name."
        ) from exc


def has_icon(name: str) -> bool:
    """Whether ``name`` is a registered icon.

    A non-raising companion to :func:`get_icon`, for callers that want to
    validate a name up front (e.g. {% bw_nav %} checking a NavItem.icon before
    the item reaches its recursive render template) rather than let the miss
    surface deep inside a render.
    """
    return name in _ICONS


def is_directional(name: str) -> bool:
    """Whether ``name`` flips horizontally under RTL (ICO-014)."""
    return name in _DIRECTIONAL_NAMES


def register_icons(mapping: dict[str, str], *, directional: tuple[str, ...] = ()) -> None:
    """Merge extra icons into the registry (ICO-002 swap, ICO-012 project add).

    ``mapping`` is name -> inner SVG markup (the paint content, matching what the
    seed stores). A project typically namespaces its own names (``"myapp-widget"``)
    to avoid colliding with the seed vocabulary. Names in ``directional`` flip
    under RTL. Re-registering an existing name overrides it (an intentional swap).
    """
    _ICONS.update(mapping)
    _DIRECTIONAL_NAMES.update(directional)


def _icon_names() -> tuple[str, ...]:
    return tuple(sorted(_ICONS))


# The registered-name contract surface. Recomputed lazily via __getattr__ so it
# reflects register_icons() calls, while still being importable as a name.
def __getattr__(attr: str) -> object:
    if attr == "ICON_NAMES":
        return _icon_names()
    raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")


ICON_NAMES: tuple[str, ...]  # populated via module __getattr__; see above
