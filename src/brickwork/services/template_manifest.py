"""The template contract manifest: every semver-public block and partial name.

BR-BW-TPL-001 makes every named ``{% block %}`` in a shipped shell/component
and every ``{% partialdef %}`` in a shipped component part of this package's
versioned public contract. The manifest
(``static/brickwork/dist/template-manifest.json``) is generated from the real
shipped template tree by ``scripts/generate_template_manifest.py``, so it can
never drift from what actually ships. This module reads it and exposes it as
typed Python, so a consumer (or a future third-party experience pack, per
ADR-077's section contract tier) enumerates the block/partial surface, which
template declares a given name, its consumption mode, and its deprecation
status, without hard-coding names that semver could move.

Public surface (semver-stable names):
- ``block_names()`` -> the full frozenset of semver-public block names.
- ``partial_names()`` -> the full frozenset of semver-public partial names.
- ``declared_in(name)`` -> the template path(s) declaring a block name, or the
  single template path declaring a partial name.
- ``is_deprecated(name)`` -> whether a block or partial name is deprecated.
- ``deprecation(name)`` -> the ``DeprecatedEntry`` for a deprecated name, or
  ``None``.
- ``manifest()`` -> the whole parsed manifest dict (escape hatch).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import TypedDict

_MANIFEST_RESOURCE = "static/brickwork/dist/template-manifest.json"


class BlockEntry(TypedDict):
    """One named ``{% block %}`` in the shipped template contract.

    ``declaredIn`` is a list, not a single template: Django inheritance lets
    sibling leaf templates each declare the same-named override point off a
    shared ancestor that does not itself declare it (e.g. ``content``,
    declared independently by every shell). ``consumption`` is the set of
    consumption modes across every declaring template (almost always a single
    value): ``"tag"`` (the template is an inclusion_tag's private render
    target, never a consumer call site), ``"extend"`` (a consumer opens
    ``{% extends %}`` on this template directly and fills the block), or
    ``"include"`` (the template is filled via ``{% include %}`` with context;
    extending it to override a block, where documented, is a secondary
    escape hatch, not the primary consumption path).
    """

    name: str
    declaredIn: list[str]
    consumption: list[str]


class PartialEntry(TypedDict):
    """One named ``{% partialdef %}`` in the shipped template contract.

    Unlike a block, a partial name is declared in exactly one template (Django
    itself enforces this: a duplicate ``{% partialdef %}`` name in one
    template is a ``TemplateSyntaxError``, and this package's own templates
    never repeat a partial name across files), so ``declaredIn`` is a single
    path. ``inline`` mirrors the ``{% partialdef name inline %}`` argument:
    whether the partial also renders immediately where it is defined.
    """

    name: str
    declaredIn: str
    inline: bool
    consumption: str


class DeprecatedEntry(TypedDict):
    """A block or partial name kept for BR-BW-VER-001 parallel support.

    ``supersededBy`` names the replacement; both render until ``removedAt``
    (a MAJOR version). A consumer migrating away from a deprecated name fills
    only the superseding one.
    """

    kind: str
    name: str
    declaredIn: str
    supersededBy: str
    removedAt: str
    note: str


@lru_cache(maxsize=1)
def manifest() -> dict:
    """The whole parsed template manifest (cached; read once per process)."""
    raw = files("brickwork").joinpath(_MANIFEST_RESOURCE).read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def blocks() -> tuple[BlockEntry, ...]:
    """Every semver-public block, in manifest (name-sorted) order."""
    return tuple(manifest()["blocks"])


@lru_cache(maxsize=1)
def partials() -> tuple[PartialEntry, ...]:
    """Every semver-public partial, in manifest (name-sorted) order."""
    return tuple(manifest()["partials"])


@lru_cache(maxsize=1)
def deprecated() -> tuple[DeprecatedEntry, ...]:
    """Every deprecated block/partial name still shipping under parallel support."""
    return tuple(manifest()["deprecated"])


@lru_cache(maxsize=1)
def block_names() -> frozenset[str]:
    """Every semver-public block name (BR-BW-TPL-001)."""
    return frozenset(entry["name"] for entry in blocks())


@lru_cache(maxsize=1)
def partial_names() -> frozenset[str]:
    """Every semver-public partial name (BR-BW-TPL-001)."""
    return frozenset(entry["name"] for entry in partials())


@lru_cache(maxsize=1)
def _blocks_by_name() -> dict[str, BlockEntry]:
    return {entry["name"]: entry for entry in blocks()}


@lru_cache(maxsize=1)
def _partials_by_name() -> dict[str, PartialEntry]:
    return {entry["name"]: entry for entry in partials()}


@lru_cache(maxsize=1)
def _deprecated_by_name() -> dict[str, DeprecatedEntry]:
    return {entry["name"]: entry for entry in deprecated()}


def declared_in(name: str) -> list[str]:
    """The template path(s) declaring ``name``.

    Returns a block's full ``declaredIn`` list, a partial's single
    ``declaredIn`` path wrapped in a one-element list, or an empty list for an
    unknown name.
    """
    block = _blocks_by_name().get(name)
    if block is not None:
        return list(block["declaredIn"])
    partial = _partials_by_name().get(name)
    if partial is not None:
        return [partial["declaredIn"]]
    return []


def is_deprecated(name: str) -> bool:
    """Whether ``name`` (a block or partial name) is deprecated."""
    return name in _deprecated_by_name()


def deprecation(name: str) -> DeprecatedEntry | None:
    """The deprecation entry for ``name``, or ``None`` if it is not deprecated."""
    return _deprecated_by_name().get(name)
