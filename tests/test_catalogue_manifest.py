"""Catalogue manifest tests (plan decision D8, W0.2 of the interface-system
delivery plan).

``services/_catalogue_manifest.py`` (underscore-prefixed: an INTERNAL reader,
not public API, see its own module docstring for why) reads the shipped
``catalogue-manifest.json`` (generated from the real shipped template and
examples trees by ``scripts/generate_catalogue_manifest.py``) and exposes it
as typed Python for this repo's own in-package consumers. These tests cover:

1. **Manifest shape**: the typed reader's accessors match the raw JSON, and
   the documented counts hold (5 shells, 40 components, 26 sections, 16
   archetypes: verified against the tree post-W0.1/W0.4 merge,
   docs/CATALOGUE.md ss5).
2. **Manifest-vs-reality drift**: regenerating the manifest from the current
   template and examples trees produces byte-identical output (canonical
   bytes, not a parsed-dict comparison) to the committed file.
3. **The vocabulary gate (D4/O1)**: "family" never leaks into a public
   package API identifier. This covers both the shipped JSON (a data value
   only, never a key/value shaped like a template tag, CSS class or token
   name) and the exported identifiers of every PUBLIC ``brickwork.services``
   module (excluding this file's own internal, underscore-prefixed reader,
   which is deliberately exempt, see point 1 above): this second half is
   exactly the surface a prior review round found the vocabulary gate had
   missed.
4. **The two Wave 0 scoping decisions hold** (docs/CATALOGUE.md ss7/ss8):
   no item carries render-input data, and ``families`` carries shipped
   counts only, never a status or wave field.
5. **``_requires_context``'s node-tree walk**, unit-tested directly against
   hand-built template strings (not the shipped examples tree, which only
   ever exercises the shapes it happens to contain): the RHS and scope rules
   a ``{% with %}``/``{% firstof ... as %}`` binding must satisfy before the
   name it defines counts as "local" rather than context-sourced (PR#233
   review: a with-binding that copies an external context variable through
   to an include kwarg was a reproducible false negative in an earlier
   version of this detector).
"""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
from pathlib import Path

import pytest
from django.template import Engine

import brickwork.services
from brickwork.services._catalogue_manifest import (
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
write_manifest = _generator.write_manifest
_requires_context = _generator._requires_context


# ---------------------------------------------------------------------------
# 1. Manifest shape
# ---------------------------------------------------------------------------


def test_counts_match_the_documented_wave_0_baseline() -> None:
    # ROADMAP.md / the delivery plan's W0.2 exit criteria set the original
    # baseline at 5 shells, 39 components, 42 examples (16 archetypes + 26
    # sections). W0.4 (icvoss/django-brickwork#228) shipped a 40th
    # component, bw_theme_switch/_theme_switch.html, after that baseline was
    # written; the count below is verified directly against the repo
    # post-merge, not copied from the plan: docs/CATALOGUE.md ss5 records
    # the same verification.
    counts = manifest()["counts"]
    assert counts == {"shells": 5, "components": 40, "sections": 26, "archetypes": 16}


def test_items_covers_every_shell_component_section_and_archetype() -> None:
    assert len(items()) == 5 + 40 + 26 + 16 == 87


def test_items_by_kind_filters_correctly() -> None:
    assert len(items_by_kind("shell")) == 5
    assert len(items_by_kind("component")) == 40
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


def test_committed_manifest_matches_a_fresh_regeneration_byte_for_byte(tmp_path: Path) -> None:
    """The generator is the ONLY thing that may write catalogue-manifest.json.

    Exercises the generator's OWN write path (``write_manifest``, the exact
    function ``main()`` calls) into a temp file, then compares raw bytes
    (``read_bytes``) against the committed file. This deliberately does NOT
    re-implement the serialisation with its own ``json.dumps(...)``
    expression: a duplicated expression cannot see a divergence if the
    writer's own serialisation ever changes (``separators``,
    ``ensure_ascii``, the trailing-newline convention), and would still
    normalise and pass against CRLF-committed content, silently defeating
    the point of this test. Comparing bytes written through the real code
    path is the only way this test can actually catch that class of drift.
    This is stricter than ``test_template_manifest.py``'s equivalent check
    (parsed dicts) by design: D8 makes this manifest's own doc pointers and
    ordering part of what a consumer reads directly off disk, so canonical
    bytes is the truer gate for it specifically, not a claim this file makes
    about the sibling test.
    """
    committed_bytes = _DIST.joinpath("catalogue-manifest.json").read_bytes()
    fresh_path = tmp_path / "catalogue-manifest.json"
    write_manifest(fresh_path)
    fresh_bytes = fresh_path.read_bytes()
    assert fresh_bytes == committed_bytes, (
        "catalogue-manifest.json is stale: run "
        "'DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:. "
        "python scripts/generate_catalogue_manifest.py' and commit the result."
    )


# ---------------------------------------------------------------------------
# 3. The vocabulary gate (D4/O1): family is data, never a package identifier
# ---------------------------------------------------------------------------

# Stems, not whole words: "famil" (not "family") also matches the plural
# "families", the natural spelling for a function/collection name (exactly
# the shape "families()" itself takes). "primitive" and "pattern" already
# match their own plurals as substrings, so they need no shortening. Checked
# against the shipped tree for false positives (a legitimate identifier that
# happens to contain "famil"): none found; the only two "famil" hits in the
# whole source tree are the prose words "familiar"/"shadcn-familiar" inside
# docstrings, which this gate never inspects (it only reads exported names).
_FORBIDDEN_VOCABULARY = ("famil", "primitive", "pattern")


def test_no_item_name_or_template_path_carries_the_word_family() -> None:
    # O1: "family" is a catalogue data VALUE, never part of a package
    # identifier (a name, a template path, a doc pointer). This does not
    # forbid the word appearing as a family VALUE itself (family names like
    # "Product applications" are expected); it forbids it leaking into the
    # identifier-shaped fields any package code could import or reference.
    for entry in items():
        for identifier_field in ("name", "templatePath", "docSource"):
            value = entry.get(identifier_field, "")
            assert "famil" not in value.lower(), f"{identifier_field}={value!r} on {entry['name']} carries 'family'"


def test_no_item_carries_primitive_or_pattern_in_an_identifier_field() -> None:
    # The same D4 vocabulary gate also names "primitive" and "pattern".
    for entry in items():
        for identifier_field in ("name", "templatePath", "docSource"):
            value = entry.get(identifier_field, "").lower()
            assert "primitive" not in value, f"{identifier_field} on {entry['name']} carries 'primitive'"
            assert "pattern" not in value, f"{identifier_field} on {entry['name']} carries 'pattern'"


def _assert_module_exports_no_forbidden_vocabulary(module: object) -> None:
    """One module's exported names, and their TypedDict/class fields, are clean.

    Shared by the package module itself (``brickwork.services``) and every
    public child module, so both are held to exactly the same check: an
    ``__all__`` re-export from ``services/__init__.py`` is exactly as public
    as a name defined directly in a child module, and O1 does not
    distinguish where a forbidden identifier is DEFINED from where it is
    RE-EXPORTED, only whether it is reachable as public API.
    """
    exported_names = getattr(module, "__all__", None) or [name for name in vars(module) if not name.startswith("_")]
    for name in exported_names:
        lowered = name.lower()
        for word in _FORBIDDEN_VOCABULARY:
            assert word not in lowered, f"{module.__name__}.{name} is public and carries {word!r} (O1)"
        attr = getattr(module, name, None)
        annotations = getattr(attr, "__annotations__", None)
        if not annotations:
            continue
        for field_name in annotations:
            field_lowered = field_name.lower()
            for word in _FORBIDDEN_VOCABULARY:
                assert word not in field_lowered, (
                    f"{module.__name__}.{name}.{field_name} is a public field and carries {word!r} (O1)"
                )


def test_no_public_services_module_exports_a_family_primitive_or_pattern_name() -> None:
    """The vocabulary gate over Python identifiers, not just JSON (D4/O1).

    A prior review round found this manifest's own service reader shipped
    ``FamilyEntry``/``families()`` as PUBLIC Python identifiers, which O1
    forbids (a package API identifier may never carry "family", "primitive"
    or "pattern"). The fix was making that reader internal
    (``services/_catalogue_manifest.py``, excluded here by construction: an
    underscore-prefixed module is not part of the public surface this test
    walks), but the gate that should have caught it in the first place only
    ever checked the shipped JSON, never Python identifiers. This walks the
    ``brickwork.services`` PACKAGE MODULE ITSELF (a prior round of this gate
    checked only its child modules via ``pkgutil.iter_modules``, which lists
    submodules but never the package module ``__init__.py`` belongs to, so a
    future ``from ._catalogue_manifest import families`` re-export sitting
    directly in ``services/__init__.py`` would have passed silently) plus
    every PUBLIC child module under it (``services/__init__.py``'s own
    docstring: "the public Python API surface"), and asserts none of their
    exported names, module-level or class/TypedDict attribute, carries any
    of the three forbidden words.
    """
    _assert_module_exports_no_forbidden_vocabulary(brickwork.services)

    checked_modules: list[str] = []
    for module_info in pkgutil.iter_modules(brickwork.services.__path__):
        if module_info.name.startswith("_"):
            continue  # internal module, not public API, out of scope by design
        module = importlib.import_module(f"brickwork.services.{module_info.name}")
        checked_modules.append(module.__name__)
        _assert_module_exports_no_forbidden_vocabulary(module)
    assert checked_modules, "expected at least one public brickwork.services module to check"


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


# ---------------------------------------------------------------------------
# 5. _requires_context's node-tree walk, unit-tested against hand-built
#    template strings (PR#233 review round)
# ---------------------------------------------------------------------------
#
# The shipped examples tree only ever exercises whatever with/firstof/include
# shapes it happens to contain today (currently: exactly one, base.html's
# firstof-plus-include), so a regression in the RHS/scope rules that does not
# happen to change base.html's own verdict would pass the drift test and
# every other check in this file with nothing to catch it. These tests call
# the detector directly against template strings built for the purpose, so
# each rule is pinned independently of what the shipped tree happens to ship.
#
# A bare ``Engine()`` (no ``app_dirs``, no ``libraries``) is enough: every
# template string below uses only Django's built-in tags (``with``,
# ``firstof``, ``for``, ``if``, ``include``), never a brickwork ``{% load %}``
# tag, so this does not need ``test_examples.py``'s ``_example_engine()``
# machinery (that exists for RENDERING a real shipped example; this only
# compiles a node tree and never renders it).

_engine = Engine()

# (case name, template source, expected _requires_context() result). The
# include target names a real shipped component path so the shape matches
# what the generator actually walks in the wild; nothing here renders these
# templates, so the target need not resolve on any loader path.
_REQUIRES_CONTEXT_CASES: list[tuple[str, str, bool]] = [
    (
        "with_binding_wrapping_external_name_feeding_include_kwarg",
        "{% with heading=external_heading %}"
        '{% include "brickwork/components/_page_header.html" with title=heading %}'
        "{% endwith %}",
        True,
    ),
    (
        "with_binding_wrapping_literal_feeding_include_kwarg",
        '{% with heading="Fixed heading" %}'
        '{% include "brickwork/components/_page_header.html" with title=heading %}'
        "{% endwith %}",
        False,
    ),
    (
        "with_binding_out_of_scope_for_a_sibling_include",
        '{% with x="literal" %}{{ x }}{% endwith %}{% include "brickwork/components/_page_header.html" with title=x %}',
        True,
    ),
    (
        "nested_if_inherits_enclosing_context_requirement",
        '{% if flag %}{% include "brickwork/components/_page_header.html" with title=external_var %}{% endif %}',
        True,
    ),
    (
        "firstof_asvar_with_a_literal_fallback_feeding_include_kwarg",
        "{% firstof bw_toast_position 'top-end' as resolved %}"
        '{% include "brickwork/components/_toast_region.html" with placement=resolved %}',
        False,
    ),
    (
        "firstof_asvar_with_no_literal_argument_feeding_include_kwarg",
        '{% firstof a b as resolved %}{% include "brickwork/components/_toast_region.html" with placement=resolved %}',
        True,
    ),
    (
        "base_html_real_shape_firstof_plus_include",
        "{% firstof bw_toast_position 'top-end' as bw_toast_position_resolved %}"
        '{% include "brickwork/components/_toast_region.html" with placement=bw_toast_position_resolved %}',
        False,
    ),
]


@pytest.mark.parametrize(
    ("name", "source", "expected"), _REQUIRES_CONTEXT_CASES, ids=[case[0] for case in _REQUIRES_CONTEXT_CASES]
)
def test_requires_context_rhs_and_scope_rules(name: str, source: str, expected: bool) -> None:
    """Pins the RHS/scope rules a with/firstof binding must satisfy.

    ``with_binding_wrapping_external_name_feeding_include_kwarg`` is the
    PR#233 review's exact false-negative repro: an earlier version of the
    detector treated every ``{% with %}``-bound name as local regardless of
    what its own right-hand side needed, so this shape (a with-binding
    copying an external, context-sourced variable straight through to an
    include kwarg) read as ``requiresContext: False`` while genuinely
    needing context, with nothing at render time to catch a wrong False.

    ``with_binding_wrapping_literal_feeding_include_kwarg`` is the control:
    the same shape, but the with-binding's own right-hand side is a literal,
    so it is correctly safe.

    ``with_binding_out_of_scope_for_a_sibling_include`` pins that a
    ``{% with %}`` binding is scoped to its own block: a name bound inside
    one with-block does not make an unrelated include OUTSIDE that block
    treat the same name as local, matching Django's real
    ``WithNode.render()`` push/pop scoping.

    ``nested_if_inherits_enclosing_context_requirement`` pins that scope is
    inherited through arbitrary nesting (an ``{% if %}`` here) via
    ``Node.child_nodelists``, not just at the top level of a template.

    ``firstof_asvar_with_a_literal_fallback_feeding_include_kwarg`` and
    ``firstof_asvar_with_no_literal_argument_feeding_include_kwarg`` pin
    firstof's own RHS rule, deliberately ANY rather than with's ALL:
    ``FirstOfNode.render()`` never fails regardless of its arguments
    (``ignore_failures=True`` per argument, ``asvar`` always assigned), so
    one literal argument is enough to guarantee a context-independent
    fallback, but with every argument bare and context-sourced, none is.

    ``base_html_real_shape_firstof_plus_include`` pins the exact shape
    ``examples/base.html`` ships (``{% firstof bw_toast_position 'top-end'
    as bw_toast_position_resolved %}`` then passing the resolved name into
    ``_toast_region.html``'s ``placement`` kwarg), the one case the shipped
    examples tree already exercises and the reason this detector was
    refined in the first place (icvoss/django-brickwork#232 follow-up).
    """
    template = _engine.from_string(source)
    assert _requires_context(template.nodelist, source) is expected, (
        f"{name}: expected requiresContext={expected} for:\n{source}"
    )
