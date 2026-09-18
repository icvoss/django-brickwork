"""Interaction contract manifest tests (icvoss/django-brickwork#229).

``services/interaction_manifest.py`` reads the shipped
``interaction-manifest.json`` (generated from ``frontend/src/js/`` and the
shipped template tree by ``scripts/generate_interaction_manifest.py``) and
exposes Alpine names, event names and HTMX target IDs as typed Python. These
tests cover:

1. **Manifest shape**: the typed reader's accessors match the raw JSON, and
   the #228 backfill names (``bwThemeSwitch``, ``bw:theme-switch:change``)
   are present.
2. **Manifest-vs-reality drift**: regenerating the manifest from the current
   sources produces byte-identical output to the committed file, mirroring
   ``test_template_manifest.py`` and the token artefact drift gate.
3. **Extraction invariants**: Alpine names are valid identifiers; events use
   the ``bw:`` namespace; HTMX targets are the stable BR-BW-HTMX-005 mount
   points (non-empty, package-prefixed).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from brickwork.services.interaction_manifest import (
    alpine_components,
    alpine_names,
    event_names,
    events,
    htmx_target_ids,
    htmx_targets,
    manifest,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DIST = _REPO_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"


def _load_generator():
    """Import scripts/generate_interaction_manifest.py without touching sys.path."""
    spec = importlib.util.spec_from_file_location(
        "generate_interaction_manifest",
        _REPO_ROOT / "scripts" / "generate_interaction_manifest.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_generator = _load_generator()
build_manifest = _generator.build_manifest


# ---------------------------------------------------------------------------
# 1. Manifest shape
# ---------------------------------------------------------------------------


def test_alpine_names_include_theme_switch_and_a_core_overlay() -> None:
    names = alpine_names()
    assert "bwThemeSwitch" in names
    assert "bwModal" in names
    assert "bwSlideOver" in names


def test_event_names_include_theme_switch_change_and_modal_pair() -> None:
    names = event_names()
    assert "bw:theme-switch:change" in names
    assert "bw:modal:open" in names
    assert "bw:modal:close" in names


def test_htmx_targets_include_the_three_stable_mount_points() -> None:
    ids = htmx_target_ids()
    assert ids == frozenset({"bw-modal-root", "bw-slide-over-root", "bw-toast-region"})


def test_manifest_escape_hatch_matches_typed_accessors() -> None:
    raw = manifest()
    assert [entry["name"] for entry in raw["alpineComponents"]] == [entry["name"] for entry in alpine_components()]
    assert [entry["name"] for entry in raw["events"]] == [entry["name"] for entry in events()]
    assert [entry["id"] for entry in raw["htmxTargets"]] == [entry["id"] for entry in htmx_targets()]


def test_accessors_are_cached_and_immutable() -> None:
    first = alpine_components()
    second = alpine_components()
    assert first is second
    assert isinstance(first, tuple)


# ---------------------------------------------------------------------------
# 2. Manifest-vs-reality drift
# ---------------------------------------------------------------------------


def test_committed_manifest_matches_a_fresh_regeneration() -> None:
    """The generator is the ONLY thing that may write interaction-manifest.json."""
    committed = json.loads(_DIST.joinpath("interaction-manifest.json").read_text(encoding="utf-8"))
    fresh = build_manifest()
    assert fresh == committed, (
        "interaction-manifest.json is stale: run "
        "'python scripts/generate_interaction_manifest.py' and commit the result."
    )


# ---------------------------------------------------------------------------
# 3. Extraction invariants
# ---------------------------------------------------------------------------


def test_every_alpine_name_is_a_valid_identifier() -> None:
    for name in alpine_names():
        assert name.isidentifier(), name
        assert name.startswith("bw"), name


def test_every_event_name_uses_the_bw_namespace() -> None:
    for name in event_names():
        assert name.startswith("bw:"), name


def test_every_htmx_target_is_a_package_prefixed_literal() -> None:
    for target_id in htmx_target_ids():
        assert target_id.startswith("bw-"), target_id
        assert "{{" not in target_id
