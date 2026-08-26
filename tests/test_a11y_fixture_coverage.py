"""Drift gate: every shipped catalogue-manifest item is covered by the a11y
gate's fixtures (icvoss/django-brickwork#226).

The blocking a11y gate (axe, keyboard, browser no-JS) runs over whatever
``.html`` files land in ``a11y/fixtures/``. Two of the four catalogue kinds
get there by an EXPLICIT, hand-maintained enumeration
(``a11y/generate_fixtures.py``'s own per-theme write calls in ``main()``,
extended by hand for every new surface since 0.8.0): a new component that
never gets a write call is silently invisible to the entire gate, and it has
happened twice (a visual surface shipped pre-3.6.0, then ``theme_switch`` in
the W0.4 slice, both caught only in review, not by any test). The other two
kinds (``archetype``, ``section``) are already immune: ``archetype`` fixtures
come from ``a11y/generate_archetype_fixtures.py``'s auto-discovery off
``items_by_kind("archetype")`` (W0.3, ``tests/test_archetype_harness.py``
already gates its own enrolment), and ``section`` fixtures come from
``render_sections`` walking every ``sections/*`` example
(``tests/test_examples.py`` already gates that walk's own exhaustiveness).

**Coverage mechanism, chosen over both a hand-written registry and a text
parse of ``generate_fixtures.py``.** ``tests/test_positioning.py`` already
states, for this exact file, that a second regex over its source would be "the
kind of parallel, ungrounded re-derivation this module's docstring warns
against"; the same reasoning applies here even more directly, since a coverage
GATE that could itself silently drift from what the generator actually renders
would be worse than no gate at all. Instead, this file imports the real
generator (``importlib.util.spec_from_file_location``, the same mechanism
``tests/test_catalogue_manifest.py``'s own ``_load_generator()`` uses for
``scripts/generate_catalogue_manifest.py``) and runs its real ``main()``,
with ``django.template.engine.Engine.find_template`` instrumented to record
every template name it resolves. ``Engine.find_template`` is the single
choke point BOTH ``{% extends %}`` (via ``ExtendsNode.find_template``) and
``{% include %}``/inclusion-tag/``get_template()``/``render_to_string`` (via
``Engine.get_template``) funnel through, on every ``Engine`` instance, so this
observes exactly what the axe gate's own fixtures actually load, with no
second list to fall out of sync: a shell or component's ``templatePath`` is
"covered" if and only if the real generator run genuinely resolved it.
``OUT``/``FRAGMENTS`` are monkeypatched to ``tmp_path`` before ``main()``
runs, so this never touches or depends on the real (gitignored, generated)
``a11y/fixtures/`` directory, and ``build_projection_css`` is stubbed to
return ``""`` so the run needs no Node subprocess: ``render_projection``
composes raw Tailwind utility classes over ``tokens.css`` only, no catalogue
shell/component/section template, so skipping it costs no coverage.

This test module needs ``brickwork_testapp`` installed (the generator imports
``brickwork_testapp.forms``/``nav``/``views``), so, like
``tests/test_integration.py``, it is collected only under the ``settings_seams``
leg (``tests/conftest.py``'s ``pytest_ignore_collect``), and
``.github/workflows/ci.yml``'s ``settings_seams`` step runs it alongside that
file.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest
from django.template.engine import Engine

from brickwork.services._catalogue_manifest import items_by_kind, manifest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GENERATOR_PATH = _REPO_ROOT / "a11y" / "generate_fixtures.py"
_ARCHETYPE_GENERATOR_PATH = _REPO_ROOT / "a11y" / "generate_archetype_fixtures.py"

# Legitimate exclusions: an item that genuinely cannot have a fixture, with a
# one-line justification each. Empty today: every shell/component/section is
# coverable (component/search and component/spinner, the two items this test
# found with no fixture, are now covered by the search-<theme>.html fixture
# generate_fixtures.py's own #226 section adds, rather than excused here).
_ALLOWLIST: dict[str, str] = {}


def _load_module(path: Path, name: str) -> types.ModuleType:
    """Import a script module by file path (never by dotted name: neither
    ``a11y/`` nor ``scripts/`` is a package on ``sys.path``). Mirrors
    ``tests/test_catalogue_manifest.py``'s own ``_load_generator()``."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _traced_template_names(tmp_path: Path) -> set[str]:
    """Run the real fixture generator once, instrumented, and return every
    template name ``Engine.find_template`` resolved along the way.

    ``find_template`` is patched at the CLASS level (``Engine.find_template``),
    not on one instance, because the generator uses several distinct ``Engine``
    objects: the configured ``engines["django"]`` backend's engine, plus the
    standalone examples-tree engines ``_sections_engine()``/``_example_engine()``
    build for rendering package-data templates off the loader path (ADR-056).
    A single class-level patch covers all of them; the original is always
    restored, even if the generator raises.
    """
    loaded: set[str] = set()
    original_find_template = Engine.find_template

    def _recording_find_template(self, name, dirs=None, skip=None):
        loaded.add(name)
        return original_find_template(self, name, dirs=dirs, skip=skip)

    generator = _load_module(_GENERATOR_PATH, "a11y_generate_fixtures")
    generator.OUT = tmp_path / "fixtures"
    generator.OUT.mkdir(parents=True, exist_ok=True)
    generator.FRAGMENTS = generator.OUT / "fragments"
    # render_projection composes raw Tailwind utility classes over tokens.css
    # only (no shell/component/section template), so stubbing the Node build
    # this feeds costs no coverage and keeps this test dependency-free.
    generator.build_projection_css = lambda: ""

    Engine.find_template = _recording_find_template
    try:
        generator.main()
    finally:
        Engine.find_template = original_find_template

    return loaded


@pytest.fixture(scope="session")
def traced_template_names(tmp_path_factory: pytest.TempPathFactory) -> set[str]:
    """Session-scoped: the generator run is real Django rendering across every
    hand-maintained fixture (~0.3s locally), reused by both the coverage test
    and the fault-injection negative test below rather than repeated twice."""
    return _traced_template_names(tmp_path_factory.mktemp("a11y-coverage-trace"))


# ---------------------------------------------------------------------------
# 1. Shell and component coverage: every manifest templatePath was genuinely
#    resolved by the real generator run.
# ---------------------------------------------------------------------------


def _uncovered_shell_and_component_items(loaded_template_names: set[str]) -> list[str]:
    uncovered = []
    for kind in ("shell", "component"):
        for entry in items_by_kind(kind):
            if entry["name"] in _ALLOWLIST:
                continue
            if entry["templatePath"] not in loaded_template_names:
                uncovered.append(entry["name"])
    return uncovered


def test_every_shell_and_component_has_an_a11y_fixture(traced_template_names: set[str]) -> None:
    uncovered = _uncovered_shell_and_component_items(traced_template_names)
    assert not uncovered, (
        f"the following catalogue-manifest shells/components are not rendered by any "
        f"a11y/generate_fixtures.py fixture: {uncovered}. Add a fixture that renders "
        "each one (a new standalone page mirroring render_search/render_feedback/"
        "render_inputs is the usual shape), or add a one-line justification to this "
        "file's _ALLOWLIST if a fixture is genuinely not possible for this item."
    )


def test_no_allowlist_entry_is_stale() -> None:
    """The reverse direction: an allowlisted item that is not in the manifest
    at all (renamed, removed) would mean the allowlist itself has drifted."""
    known_names = {entry["name"] for entry in items_by_kind("shell")} | {
        entry["name"] for entry in items_by_kind("component")
    }
    stale = sorted(name for name in _ALLOWLIST if name not in known_names)
    assert not stale, f"_ALLOWLIST names items no longer in the catalogue manifest: {stale}"


# ---------------------------------------------------------------------------
# 2. Section coverage: render_sections walks every sections/* example, and
#    tests/test_examples.py already gates that walk's own exhaustiveness
#    (test_the_shipped_example_set_matches_what_the_tests_cover). This test
#    re-asserts the same invariant from this gate's own angle: every manifest
#    section name was genuinely resolved by the traced generator run.
# ---------------------------------------------------------------------------


def test_every_section_has_an_a11y_fixture(traced_template_names: set[str]) -> None:
    uncovered = [
        entry["name"]
        for entry in items_by_kind("section")
        if entry["name"] not in _ALLOWLIST and entry["name"].removeprefix("examples/") not in traced_template_names
    ]
    assert not uncovered, (
        f"the following catalogue-manifest sections are not rendered into the "
        f"sections-<theme>.html fixture: {uncovered}. This should be structurally "
        "impossible (render_sections walks every sections/* example via "
        "brickwork.examples.list_examples()); if this fails, tests/test_examples.py's "
        "own exhaustiveness gate should also be failing, check there first."
    )


# ---------------------------------------------------------------------------
# 3. Archetype coverage: covered BY CONSTRUCTION via auto-discovery, not by
#    re-listing archetype names here. a11y/generate_archetype_fixtures.py's
#    own discover_archetypes() walks items_by_kind("archetype") directly, the
#    same mechanism tests/test_archetype_harness.py's enrolment gate already
#    proves. This asserts that mechanism exists and is genuinely wired to the
#    shipped manifest, rather than duplicating the harness's own render tests.
# ---------------------------------------------------------------------------


def test_archetype_fixtures_are_auto_discovered_from_the_manifest() -> None:
    archetype_generator = _load_module(_ARCHETYPE_GENERATOR_PATH, "a11y_generate_archetype_fixtures")
    discovered = archetype_generator.discover_archetypes()
    manifest_names = {entry["name"] for entry in items_by_kind("archetype")}

    assert set(discovered.values()) == manifest_names, (
        "a11y/generate_archetype_fixtures.py's discover_archetypes() has drifted from "
        'items_by_kind("archetype"); it should read that manifest directly with no '
        "hand-maintained archetype list of its own (this is what makes archetype "
        "coverage immune to the silent-gap failure mode this file otherwise gates)."
    )
    assert len(discovered) == manifest()["counts"]["archetypes"]


# ---------------------------------------------------------------------------
# 4. Fault injection (pinned negative test): a manifest item the real fixture
#    set does not cover must fail the coverage check, not pass it silently.
# ---------------------------------------------------------------------------


def test_an_uncovered_item_fails_the_coverage_check(traced_template_names: set[str]) -> None:
    """Proves _uncovered_shell_and_component_items actually rejects a genuine
    gap, rather than trivially passing regardless of input (a coverage check
    that always reports "nothing missing" would pass
    test_every_shell_and_component_has_an_a11y_fixture for the wrong reason).

    Injects one fake item into a COPY of the real manifest data (never
    mutates the shared, lru_cache'd manifest reader: brickwork.services.
    _catalogue_manifest.items()/items_by_kind() are read by other tests in
    this same process, and lru_cache means a real mutation would leak across
    tests), with a templatePath guaranteed absent from the traced set.
    """
    real_items = items_by_kind("component")
    fake_item = {
        "name": "component/nonexistent-widget-226",
        "kind": "component",
        "family": None,
        "templatePath": "brickwork/components/_nonexistent_widget_226.html",
        "docSource": "brickwork/components/_nonexistent_widget_226.html",
        "consumption": "include",
        "usedByArchetypes": [],
        "usedBySections": [],
    }
    assert fake_item["templatePath"] not in traced_template_names, (
        "fixture bug: the injected fake item's templatePath collided with a real "
        "traced template name, which would make this negative test vacuous"
    )

    injected_items = tuple(real_items) + (fake_item,)

    def _uncovered_with_injection() -> list[str]:
        uncovered = []
        for entry in injected_items:
            if entry["name"] in _ALLOWLIST:
                continue
            if entry["templatePath"] not in traced_template_names:
                uncovered.append(entry["name"])
        return uncovered

    uncovered = _uncovered_with_injection()
    assert uncovered == ["component/nonexistent-widget-226"], (
        f"expected only the injected fake item to be reported uncovered, got {uncovered}: "
        "the coverage check did not react to the injected gap"
    )
