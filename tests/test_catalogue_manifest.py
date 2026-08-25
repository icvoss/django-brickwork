"""Catalogue manifest tests (plan decision D8, W0.2 of the interface-system
delivery plan).

``services/catalogue_manifest.py`` reads the shipped ``catalogue-manifest.json``
(generated from the real shipped template and examples trees by
``scripts/generate_catalogue_manifest.py``) and exposes it as typed Python.
These tests cover:

1. **Manifest shape**: the typed reader's accessors match the raw JSON, and
   the documented counts hold (5 shells, 39 components, 26 sections, 16
   archetypes: verified against the 3.7.0 tree, docs/CATALOGUE.md ss5).
2. **Manifest-vs-reality drift**: regenerating the manifest from the current
   template and examples trees produces byte-identical output to the
   committed file, exactly the same drift discipline
   ``test_template_manifest.py`` applies to ``template-manifest.json``.
3. **The vocabulary gate (D4/O1)**: "family" never leaks into a package API
   identifier by construction, because this manifest is data, not code; this
   file asserts the JSON itself carries no key or value shaped like a
   template tag, CSS class or token name.
4. **The two Wave 0 scoping decisions hold** (docs/CATALOGUE.md ss7/ss8):
   no item carries render-input data, and ``families`` carries shipped
   counts only, never a status or wave field.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from brickwork.services.catalogue_manifest import (
    families,
    item,
    items,
    items_by_kind,
    manifest,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DIST = _REPO_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"


def _load_generator():
    """Import scripts/generate_catalogue_manifest.py without touching sys.path.

    Mirrors ``test_template_manifest.py``'s own ``_load_generator``: the
    generator lives in scripts/, not the installed package, so it is not
    importable by dotted name.
    """
    spec = importlib.util.spec_from_file_location(
        "generate_catalogue_manifest", _REPO_ROOT / "scripts" / "generate_catalogue_manifest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_generator = _load_generator()
build_manifest = _generator.build_manifest


# ---------------------------------------------------------------------------
# 1. Manifest shape
# ---------------------------------------------------------------------------


def test_counts_match_the_documented_wave_0_baseline() -> None:
    # ROADMAP.md / the delivery plan's W0.2 exit criteria: 5 shells, 39
    # components, 42 examples (16 archetypes + 26 sections). Verified
    # directly against the repo, not copied from the plan: docs/CATALOGUE.md
    # ss5 records the same verification.
    counts = manifest()["counts"]
    assert counts == {"shells": 5, "components": 39, "sections": 26, "archetypes": 16}


def test_items_covers_every_shell_component_section_and_archetype() -> None:
    assert len(items()) == 5 + 39 + 26 + 16 == 86


def test_items_by_kind_filters_correctly() -> None:
    assert len(items_by_kind("shell")) == 5
    assert len(items_by_kind("component")) == 39
    assert len(items_by_kind("section")) == 26
    assert len(items_by_kind("archetype")) == 16


def test_item_returns_a_known_shell() -> None:
    entry = item("shell/app")
    assert entry is not None
    assert entry["kind"] == "shell"
    assert entry["templatePath"] == "brickwork/shell/app.html"
    assert entry["family"] is None


def test_item_returns_none_for_an_unknown_name() -> None:
    assert item("not-a-real-item") is None


def test_a_tag_consumed_component_records_tag_consumption() -> None:
    # _button.html is never {% include %}d directly (brickwork skill: "call
    # the tag, never include the partial"), so its usage is only detectable
    # via the {% bw_button %} call, and its own consumption must say "tag".
    entry = item("component/button")
    assert entry is not None
    assert entry["consumption"] == "tag"
    assert "app/dashboard.html" in entry["usedByArchetypes"]


def test_an_include_consumed_component_records_include_consumption() -> None:
    entry = item("component/data_table")
    assert entry is not None
    assert entry["consumption"] == "include"


def test_a_marketing_component_is_used_by_both_archetypes_and_sections() -> None:
    # _hero.html is composed by the marketing archetypes directly AND by the
    # sections/hero/* examples, so both usage buckets must be populated.
    entry = item("component/hero")
    assert entry is not None
    assert entry["usedByArchetypes"], "expected at least one archetype using the hero component"
    assert entry["usedBySections"], "expected at least one section using the hero component"


def test_sections_requiring_context_match_the_documented_shape() -> None:
    # docs/CATALOGUE.md ss7: exactly the sections whose content is a list of
    # dicts a template cannot build inline.
    section_names = {
        entry["name"].removeprefix("examples/") for entry in items_by_kind("section") if entry["requiresContext"]
    }
    assert section_names == {
        "sections/features/icon-grid.html",
        "sections/pricing/three-tier.html",
        "sections/stats/inline-band.html",
        "sections/listing/card-grid.html",
        "sections/listing/compact-table.html",
        "sections/listing/media-list.html",
    }


def test_most_sections_render_from_empty_context() -> None:
    section_items = items_by_kind("section")
    empty_context = [entry for entry in section_items if not entry["requiresContext"]]
    assert len(empty_context) == 20  # 26 sections total, 6 need context


def test_archetypes_are_scoped_to_their_shipped_family() -> None:
    families_seen = {entry["family"] for entry in items_by_kind("archetype") if entry["family"]}
    assert families_seen == {"Product applications", "Transactional journeys", "Marketing and public web"}


def test_base_archetype_carries_no_family() -> None:
    # examples/base.html is a raw document skeleton, tied to no one family.
    entry = item("examples/base.html")
    assert entry is not None
    assert entry["family"] is None


def test_sections_carry_no_family() -> None:
    # A section lives under its TYPE (hero, cta, ...), reusable across
    # several families, not scoped to one (docs/CATALOGUE.md ss5).
    assert all(entry["family"] is None for entry in items_by_kind("section"))


def test_manifest_escape_hatch_matches_typed_accessors() -> None:
    raw = manifest()
    assert [entry["name"] for entry in raw["items"]] == [entry["name"] for entry in items()]
    assert [entry["name"] for entry in raw["families"]] == [entry["name"] for entry in families()]


def test_items_are_cached_and_immutable() -> None:
    first = items()
    second = items()
    assert first is second, "items() should be lru_cache'd (read once per process)"
    assert isinstance(first, tuple)


# ---------------------------------------------------------------------------
# 2. Manifest-vs-reality drift
# ---------------------------------------------------------------------------


def test_committed_manifest_matches_a_fresh_regeneration() -> None:
    """The generator is the ONLY thing that may write catalogue-manifest.json.

    A source edit that adds/removes/moves a shell, component or example
    without re-running the generator fails here, exactly as an un-rebuilt
    template-manifest.json fails ``test_template_manifest.py``'s equivalent
    check.
    """
    committed = json.loads(_DIST.joinpath("catalogue-manifest.json").read_text(encoding="utf-8"))
    fresh = build_manifest()
    assert fresh == committed, (
        "catalogue-manifest.json is stale: run "
        "'DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:. "
        "python scripts/generate_catalogue_manifest.py' and commit the result."
    )


# ---------------------------------------------------------------------------
# 3. The vocabulary gate (D4/O1): family is data, never a package identifier
# ---------------------------------------------------------------------------


def test_no_item_name_or_template_path_carries_the_word_family() -> None:
    # O1: "family" is a catalogue data VALUE, never part of a package
    # identifier (a name, a template path, a doc pointer). This does not
    # forbid the word appearing as a family VALUE itself (family names like
    # "Product applications" are expected); it forbids it leaking into the
    # identifier-shaped fields any package code could import or reference.
    for entry in items():
        for identifier_field in ("name", "templatePath", "docSource"):
            value = entry.get(identifier_field, "")
            assert "family" not in value.lower(), f"{identifier_field}={value!r} on {entry['name']} carries 'family'"


def test_no_item_carries_primitive_or_pattern_in_an_identifier_field() -> None:
    # The same D4 vocabulary gate also names "primitive" and "pattern".
    for entry in items():
        for identifier_field in ("name", "templatePath", "docSource"):
            value = entry.get(identifier_field, "").lower()
            assert "primitive" not in value, f"{identifier_field} on {entry['name']} carries 'primitive'"
            assert "pattern" not in value, f"{identifier_field} on {entry['name']} carries 'pattern'"


# ---------------------------------------------------------------------------
# 4. The two Wave 0 scoping decisions (docs/CATALOGUE.md ss7 / ss8)
# ---------------------------------------------------------------------------


def test_no_item_carries_render_input_data() -> None:
    # docs/CATALOGUE.md ss7: render inputs are deliberately deferred. No item
    # may carry a "context"/"fixture"/"renderInput"-shaped field.
    forbidden_keys = {"context", "fixture", "renderinput", "renderinputs", "rendercontext"}
    for entry in items():
        keys = {key.lower() for key in entry}
        overlap = keys & forbidden_keys
        assert not overlap, f"{entry['name']} carries a forbidden render-input key: {overlap}"


def test_families_carry_shipped_counts_only_no_status_or_wave() -> None:
    # docs/CATALOGUE.md ss8: family status/wave is roadmap truth and is
    # deliberately excluded. Only package-truth shipped counts ship.
    for entry in families():
        assert set(entry.keys()) == {"name", "archetypeCount", "sectionCount"}


def test_families_only_lists_families_with_shipped_coverage() -> None:
    family_names = {entry["name"] for entry in families()}
    assert family_names == {"Product applications", "Transactional journeys", "Marketing and public web"}
    # Data-heavy operations, Documentation, and Editorial and publishing are
    # named in INTERFACE-SYSTEM.md's required-archetype table but have no
    # shipped archetype yet, so they are correctly absent here.
    assert "Data-heavy operations" not in family_names
    assert "Documentation" not in family_names
    assert "Editorial and publishing" not in family_names
