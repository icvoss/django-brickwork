"""The token contract manifest: the load-bearing brand set and its constraints.

brickwork#39. The manifest (``static/brickwork/dist/token-manifest.json``) is
generated from the annotated DTCG source by the token build, so it can never
drift from the shipped tokens. This module reads it and exposes it as typed
Python, so a consumer building a theming UI (or the ``render_brand_css`` emitter,
brickwork#40) enumerates the editable brand set, its constraints, and the full
overridable ``--bw-*`` vocabulary without hard-coding token names that semver
could move.

Public surface (semver-stable names):
- ``load_bearing()`` -> the load-bearing brand set as ``LoadBearingToken`` entries.
- ``overridable_names()`` -> the full frozenset of overridable ``--bw-*`` names.
- ``is_overridable(name)`` -> membership test against that set.
- ``manifest()`` -> the whole parsed manifest dict (escape hatch).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import TypedDict

_MANIFEST_RESOURCE = "static/brickwork/dist/token-manifest.json"


class LoadBearingToken(TypedDict, total=False):
    """One entry in the load-bearing set (brickwork#39).

    ``name`` is the ``--bw-*`` custom-property name. The optional keys carry the
    constraint metadata: ``conditional`` (author only when the default does not
    fit, e.g. surface-inverse / info), ``authoredPerTheme`` (the value legitimately
    differs light vs dark and cannot be derived, e.g. fg-on-accent),
    ``contrastPair`` + ``minContrast`` (must meet a contrast ratio against the
    named token), and ``collapsesTo`` (a three-role brand may point this token at
    the named one, e.g. info -> accent).
    """

    name: str
    conditional: bool
    authoredPerTheme: bool
    contrastPair: str
    minContrast: float
    collapsesTo: str


@lru_cache(maxsize=1)
def manifest() -> dict:
    """The whole parsed token manifest (cached; read once per process)."""
    raw = files("brickwork").joinpath(_MANIFEST_RESOURCE).read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def load_bearing() -> tuple[LoadBearingToken, ...]:
    """The load-bearing brand set: the tokens a brand authors, with constraints.

    A brand overrides these (~7 core plus the conditional and authored-per-theme
    ones) and inherits every derived token. Returned as an immutable tuple in the
    manifest's order.
    """
    return tuple(manifest()["loadBearing"])


@lru_cache(maxsize=1)
def overridable_names() -> frozenset[str]:
    """Every overridable ``--bw-*`` custom-property name (semantic + component).

    Excludes primitives and the raw font/space ramps a brand should not target.
    This is the vocabulary a brand override, and ``render_brand_css`` validation,
    are checked against.
    """
    return frozenset(manifest()["overridable"])


def is_overridable(name: str) -> bool:
    """Whether ``name`` (a ``--bw-*`` custom property) is in the overridable set."""
    return name in overridable_names()
