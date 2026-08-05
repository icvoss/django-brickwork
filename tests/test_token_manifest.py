"""Token contract manifest tests (brickwork#39).

``services/token_manifest.py`` reads the shipped ``token-manifest.json`` (generated
from the annotated DTCG source) and exposes the load-bearing brand set and the full
overridable vocabulary as typed Python, so a consumer never hard-codes token names
semver could move. These tests pin the manifest's shape and guard against drift
between the manifest and what tokens.css actually emits.
"""

from __future__ import annotations

import re
from pathlib import Path

from brickwork.services.token_manifest import (
    is_overridable,
    load_bearing,
    manifest,
    overridable_names,
)

_DIST = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist"

# The core seven every brand authors, plus the conditional / authored-per-theme
# entries (surface-inverse, fg-on-accent, info) the manifest also carries.
_CORE_SEVEN = {
    "--bw-color-surface",
    "--bw-color-fg",
    "--bw-color-border",
    "--bw-color-accent",
    "--bw-color-danger",
    "--bw-color-warning",
    "--bw-color-success",
}


def test_load_bearing_returns_the_core_seven_plus_conditional_entries() -> None:
    names = {entry["name"] for entry in load_bearing()}
    assert names >= _CORE_SEVEN, f"missing core load-bearing names: {_CORE_SEVEN - names}"
    assert "--bw-color-surface-inverse" in names
    assert "--bw-color-info" in names
    assert "--bw-color-fg-on-accent" in names
    assert len(names) == 10, f"expected 7 core + surface-inverse/info/fg-on-accent, got {sorted(names)}"


def test_fg_on_accent_carries_the_contrast_constraint() -> None:
    entries = {entry["name"]: entry for entry in load_bearing()}
    fg_on_accent = entries["--bw-color-fg-on-accent"]
    assert fg_on_accent["contrastPair"] == "--bw-color-accent"
    assert fg_on_accent["minContrast"] == 4.5
    assert fg_on_accent.get("authoredPerTheme") is True


def test_conditional_entries_are_marked_conditional() -> None:
    entries = {entry["name"]: entry for entry in load_bearing()}
    assert entries["--bw-color-surface-inverse"].get("conditional") is True
    info = entries["--bw-color-info"]
    assert info.get("conditional") is True
    assert info.get("collapsesTo") == "--bw-color-accent"


def test_load_bearing_is_cached_and_immutable() -> None:
    first = load_bearing()
    second = load_bearing()
    assert first is second, "load_bearing() should be lru_cache'd (read once per process)"
    assert isinstance(first, tuple)


def test_overridable_names_excludes_primitives() -> None:
    names = overridable_names()
    assert names, "expected a non-empty overridable vocabulary"
    assert not any(name.startswith("--bw-primitive-") for name in names), (
        "primitives must never appear in the overridable vocabulary (build-time input only, 0.11.0)"
    )


def test_overridable_names_includes_canonical_component_names() -> None:
    # 0.11.0 tier re-grammar: the canonical --bw-component-* names must be
    # present; the old un-infixed / dual names must not.
    names = overridable_names()
    assert "--bw-component-button-radius" in names
    assert "--bw-component-icon-size-md" in names
    assert "--bw-button-radius" not in names
    assert "--bw-icon-size-md" not in names
    assert "--bw-size-icon-md" not in names


def test_overridable_names_includes_the_012_feedback_component_tokens() -> None:
    # 0.12.0 (#56/#60): the three new component tokens must be present in the
    # overridable vocabulary under their canonical --bw-component-* names.
    names = overridable_names()
    assert "--bw-component-tooltip-max-width" in names
    assert "--bw-component-progress-track-height" in names
    assert "--bw-component-stat-tile-sparkline-height" in names


def test_overridable_names_includes_the_marketing_logo_height_token() -> None:
    # #83: the marketing brand-slot logo cap must be overridable under its
    # canonical component-tier name.
    names = overridable_names()
    assert "--bw-component-logo-height" in names


def test_is_overridable_true_for_accent_false_for_primitive() -> None:
    assert is_overridable("--bw-color-accent") is True
    assert is_overridable("--bw-primitive-gray-0") is False


def test_is_overridable_false_for_unknown_name() -> None:
    assert is_overridable("--bw-not-a-real-token") is False


def test_manifest_escape_hatch_matches_typed_accessors() -> None:
    raw = manifest()
    assert set(raw["overridable"]) == overridable_names()
    assert [entry["name"] for entry in raw["loadBearing"]] == [entry["name"] for entry in load_bearing()]


def test_overridable_set_matches_names_actually_emitted_in_tokens_css() -> None:
    """The manifest's overridable vocabulary must not drift from what tokens.css
    emits under :root as a CANONICAL declaration (excluding the 0.10.0 courtesy
    alias block, which re-declares old names the manifest deliberately excludes)."""
    css = (_DIST / "tokens.css").read_text()
    canonical_css = css.split("courtesy aliases", 1)[0]
    emitted = set(re.findall(r"^\s*(--bw-[a-z0-9-]+):", canonical_css, re.M))
    # tokens.css also emits primitives-free component/colour/etc tokens under
    # data-density and data-theme blocks that are theme/density variants of
    # names already counted once under :root; the manifest vocabulary is a
    # name-level (not per-block) set, so comparing against the unique name set
    # emitted anywhere in the canonical section is the correct comparison.
    manifest_names = overridable_names()
    assert manifest_names <= emitted, f"manifest names never emitted by tokens.css: {manifest_names - emitted}"
