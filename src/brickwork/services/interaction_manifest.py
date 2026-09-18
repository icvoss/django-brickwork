"""The interaction contract manifest: Alpine names, events, HTMX target IDs.

icvoss/django-brickwork#229 (Option C). The manifest
(``static/brickwork/dist/interaction-manifest.json``) is generated from the
real JS registration / dispatch sites and the shipped template tree by
``scripts/generate_interaction_manifest.py``, so it can never drift from what
actually ships. This module reads it and exposes it as typed Python, so a
consumer (or a future AST codemod driven by BR-BW-VER-001) enumerates the
three remaining versioned interaction surfaces without hard-coding names that
semver could move.

Public surface (semver-stable names):
- ``alpine_names()`` -> frozenset of ``Alpine.data(...)`` registration names.
- ``event_names()`` -> frozenset of dispatched ``bw:...`` event names.
- ``htmx_target_ids()`` -> frozenset of package-owned HTMX target IDs.
- ``manifest()`` -> the whole parsed manifest dict (escape hatch).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import TypedDict

_MANIFEST_RESOURCE = "static/brickwork/dist/interaction-manifest.json"


class AlpineEntry(TypedDict):
    """One ``Alpine.data("Name")`` registration in the interaction contract."""

    name: str


class EventEntry(TypedDict):
    """One dispatched ``bw:...`` event name in the interaction contract."""

    name: str


class HtmxTargetEntry(TypedDict):
    """One package-owned HTMX swap-target id (BR-BW-HTMX-005)."""

    id: str


@lru_cache(maxsize=1)
def manifest() -> dict:
    """The whole parsed interaction manifest (cached; read once per process)."""
    raw = files("brickwork").joinpath(_MANIFEST_RESOURCE).read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def alpine_components() -> tuple[AlpineEntry, ...]:
    """Every Alpine registration, in registration (manifest) order."""
    return tuple(manifest()["alpineComponents"])


@lru_cache(maxsize=1)
def events() -> tuple[EventEntry, ...]:
    """Every dispatched event name, in name-sorted order."""
    return tuple(manifest()["events"])


@lru_cache(maxsize=1)
def htmx_targets() -> tuple[HtmxTargetEntry, ...]:
    """Every package-owned HTMX target id, in name-sorted order."""
    return tuple(manifest()["htmxTargets"])


@lru_cache(maxsize=1)
def alpine_names() -> frozenset[str]:
    """Every semver-public Alpine.data registration name."""
    return frozenset(entry["name"] for entry in alpine_components())


@lru_cache(maxsize=1)
def event_names() -> frozenset[str]:
    """Every semver-public ``bw:...`` event name."""
    return frozenset(entry["name"] for entry in events())


@lru_cache(maxsize=1)
def htmx_target_ids() -> frozenset[str]:
    """Every semver-public package-owned HTMX target id (BR-BW-HTMX-005)."""
    return frozenset(entry["id"] for entry in htmx_targets())
