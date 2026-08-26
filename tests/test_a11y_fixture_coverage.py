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
import re
import types
from collections.abc import Iterable
from pathlib import Path

import pytest
from django.template.engine import Engine

from brickwork.services._catalogue_manifest import items_by_kind, manifest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GENERATOR_PATH = _REPO_ROOT / "a11y" / "generate_fixtures.py"
_ARCHETYPE_GENERATOR_PATH = _REPO_ROOT / "a11y" / "generate_archetype_fixtures.py"
_POSITIONING = _REPO_ROOT / "docs" / "POSITIONING.md"
_README = _REPO_ROOT / "README.md"

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


def _traced_generator_run(tmp_path: Path) -> tuple[set[str], set[str]]:
    """Run the real fixture generator once, instrumented, and return
    (every template name ``Engine.find_template`` resolved, every top-level
    fixture filename actually written to ``generator.OUT``).

    ``find_template`` is patched at the CLASS level (``Engine.find_template``),
    not on one instance, because the generator uses several distinct ``Engine``
    objects: the configured ``engines["django"]`` backend's engine, plus the
    standalone examples-tree engines ``_sections_engine()``/``_example_engine()``
    build for rendering package-data templates off the loader path (ADR-056).
    A single class-level patch covers all of them; the original is always
    restored, even if the generator raises.

    The second element is the mechanical source of truth for the documented
    hand-maintained fixture count (icvoss/django-brickwork#226 review, "B5"):
    counting the files this SAME real run actually wrote is the only way that
    cannot drift from what the axe gate loads, unlike a hand count of
    ``generator.OUT / f"..."`` write-call sites in the generator's source
    (which is exactly what produced the wrong 52/104 figure this fixes). Only
    top-level ``.html`` files count, mirroring what the axe gate itself globs
    (``fragments/`` are OOB HTML snippets injected into an already-loaded page
    via htmx, never loaded directly by Playwright as their own document).
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

    written = {path.name for path in generator.OUT.glob("*.html")}
    return loaded, written


@pytest.fixture(scope="session")
def traced_generator_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[set[str], set[str]]:
    """Session-scoped: the generator run is real Django rendering across every
    hand-maintained fixture (~0.3s locally), reused by the coverage tests, the
    fault-injection negative test and the fixture-count gate below rather than
    repeated four times."""
    return _traced_generator_run(tmp_path_factory.mktemp("a11y-coverage-trace"))


@pytest.fixture(scope="session")
def traced_template_names(traced_generator_run: tuple[set[str], set[str]]) -> set[str]:
    return traced_generator_run[0]


@pytest.fixture(scope="session")
def traced_fixture_filenames(traced_generator_run: tuple[set[str], set[str]]) -> set[str]:
    return traced_generator_run[1]


# ---------------------------------------------------------------------------
# 1. Shell and component coverage: every manifest templatePath was genuinely
#    resolved by the real generator run.
# ---------------------------------------------------------------------------


def _uncovered_shell_and_component_items(
    loaded_template_names: set[str], items: Iterable[dict] | None = None
) -> list[str]:
    """Which of ``items`` (default: the real shell + component manifest
    entries) has no ``templatePath`` in ``loaded_template_names``.

    ``items`` is a parameter, not a hard-coded ``items_by_kind`` call, so the
    fault-injection negative test below can drive this SAME function with an
    injected fake item rather than duplicating its loop: a helper that only
    the gate itself ever calls could rot to always-returning-``[]`` with
    nothing to catch it.
    """
    if items is None:
        items = [entry for kind in ("shell", "component") for entry in items_by_kind(kind)]
    uncovered = []
    for entry in items:
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


def _now_covered_allowlist_entries(loaded_template_names: set[str], allowlist: dict[str, str]) -> list[str]:
    """Which allowlisted names now HAVE a fixture, i.e. the allowlist entry
    is stale in the other direction: it was excused as uncoverable, but a
    fixture rendering its templatePath exists now.

    Parameterised on ``allowlist`` (rather than reading the module-level
    ``_ALLOWLIST`` directly) for the same reason
    ``_uncovered_shell_and_component_items`` takes an ``items`` parameter:
    the fault-injection test below drives this exact function with an
    injected fake entry, so a future rot to always-returning-``[]`` is
    caught rather than silently trusted.
    """
    all_items = {entry["name"]: entry for kind in ("shell", "component") for entry in items_by_kind(kind)}
    now_covered = []
    for name in allowlist:
        entry = all_items.get(name)
        if entry is None:
            # Not this test's concern: test_no_allowlist_entry_is_stale already
            # catches a name absent from the manifest entirely.
            continue
        if entry["templatePath"] in loaded_template_names:
            now_covered.append(name)
    return sorted(now_covered)


def test_no_allowlist_entry_is_now_covered(traced_template_names: set[str]) -> None:
    """Bidirectional staleness: an allowlisted item that a fixture now
    genuinely renders must fail here, telling the maintainer to remove the
    now-unnecessary excuse rather than let it sit alongside a real fixture."""
    now_covered = _now_covered_allowlist_entries(traced_template_names, _ALLOWLIST)
    assert not now_covered, (
        f"the following _ALLOWLIST entries are now covered by a real a11y fixture: "
        f"{now_covered}. Remove them from _ALLOWLIST; the excuse no longer applies."
    )


def test_a_now_covered_allowlist_entry_fails_the_staleness_check(traced_template_names: set[str]) -> None:
    """Proves _now_covered_allowlist_entries actually rejects a stale excuse,
    rather than trivially passing regardless of input. _ALLOWLIST is empty
    today, so this is pure future-proofing (Concern (b), #226 review): inject
    a fake allowlist entry naming a component genuinely covered by a real
    fixture (bw_search itself, resolved by search-<theme>.html), and assert
    the real check reports it as now-covered.
    """
    search_entry = next(entry for entry in items_by_kind("component") if entry["name"] == "component/search")
    assert search_entry["templatePath"] in traced_template_names, (
        "fixture bug: component/search's templatePath was not traced by the real generator "
        "run, which would make this positive-injection test vacuous"
    )

    fake_allowlist = {**_ALLOWLIST, "component/search": "fake justification injected by a test"}

    now_covered = _now_covered_allowlist_entries(traced_template_names, fake_allowlist)
    assert now_covered == ["component/search"], (
        f"expected only the injected fake allowlist entry to be reported as now-covered, got "
        f"{now_covered}: the staleness check did not react to the injected stale entry"
    )


# ---------------------------------------------------------------------------
# 2. Section coverage: render_sections walks every sections/* example, and
#    tests/test_examples.py already gates that walk's own exhaustiveness
#    (test_the_shipped_example_set_matches_what_the_tests_cover). This test
#    re-asserts the same invariant from this gate's own angle: every manifest
#    section name was genuinely resolved by the traced generator run.
# ---------------------------------------------------------------------------


def test_every_section_has_an_a11y_fixture(traced_template_names: set[str]) -> None:
    sections = items_by_kind("section")
    not_prefixed = [entry["name"] for entry in sections if not entry["name"].startswith("examples/")]
    assert not not_prefixed, (
        f"the following catalogue-manifest sections do not start with 'examples/': {not_prefixed}. "
        "This test strips that prefix before comparing against traced template names "
        "(sections/*.html templates are resolved without it); a section name that does not "
        "carry the prefix would silently compare wrong and never be reported as uncovered."
    )
    uncovered = [
        entry["name"]
        for entry in sections
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

    Drives the REAL ``_uncovered_shell_and_component_items`` (the same
    function ``test_every_shell_and_component_has_an_a11y_fixture`` calls),
    passing it an injected items iterable rather than duplicating its loop: a
    parallel copy of the loop here would stay green even if the real helper
    rotted to always-returning-``[]``, which is exactly the rot this test
    exists to catch.

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

    uncovered = _uncovered_shell_and_component_items(traced_template_names, injected_items)
    assert uncovered == ["component/nonexistent-widget-226"], (
        f"expected only the injected fake item to be reported uncovered, got {uncovered}: "
        "the coverage check did not react to the injected gap"
    )


# ---------------------------------------------------------------------------
# 5. Fixture-count gate: the hand-maintained fixture count documented in
#    README.md and docs/POSITIONING.md must match how many top-level fixture
#    files the real generator run actually wrote (icvoss/django-brickwork#226
#    review, "B5"). A prior review round hand-counted the generator's
#    ``OUT / f"..."`` write-call sites in source and reached two different
#    totals (51 and 52 per theme); neither a source count nor a doc count is
#    the ground truth, only counting the real output is. This closes the
#    dispute class permanently: the documented number can now only ever be
#    RIGHT here, because it is asserted against the same traced run that
#    also gates coverage above, not re-derived by a second mechanism.
# ---------------------------------------------------------------------------

_A11Y_ROW_RE = re.compile(r"(?m)^\|\s*A11y gate\s*\|\s*(?P<value>[^|]+?)\s*\|\s*(?P<note>.*?)\s*\|$")
_README_A11Y_LINE_RE = re.compile(
    r"axe-core WCAG 2\.2 AA scan across (?P<total>\d+) documents \((?P<hand>\d+) hand-maintained fixtures"
)


def test_documented_hand_maintained_fixture_count_matches_the_real_generator_output(
    traced_fixture_filenames: set[str],
) -> None:
    """The mechanical count: top-level ``.html`` files the real, traced
    ``a11y/generate_fixtures.py`` run wrote, excluding ``fragments/*`` (OOB
    HTML snippets, never their own axe-scanned document) and excluding
    ``archetypes/`` (a different generator, ``a11y/generate_archetype_fixtures.py``,
    gated separately by ``test_a11y_gate_archetype_fixture_count_matches_the_shipped_manifest``
    in ``tests/test_positioning.py``). This count is per THEME PAIR already
    doubled: every fixture is written once per theme in the same run.
    """
    hand_maintained_total = len(traced_fixture_filenames)
    assert hand_maintained_total % 2 == 0, (
        f"traced fixture file count {hand_maintained_total} is odd; every fixture is written "
        "once per theme (light and dark), so the total should always be even"
    )
    per_theme = hand_maintained_total // 2
    archetype_total = manifest()["counts"]["archetypes"] * 2
    documented_total = hand_maintained_total + archetype_total

    positioning_text = _POSITIONING.read_text(encoding="utf-8")
    row_match = _A11Y_ROW_RE.search(positioning_text)
    assert row_match is not None, "docs/POSITIONING.md has no '| A11y gate | ... |' row; has section 5 changed shape?"
    value, note = row_match.group("value"), row_match.group("note")

    leading_int = re.match(r"(\d+)", value)
    assert leading_int is not None, f"A11y gate value cell {value!r} does not start with an integer"
    assert int(leading_int.group(1)) == documented_total, (
        f"docs/POSITIONING.md's 'A11y gate' row claims {leading_int.group(1)} documents, but the "
        f"real traced generator run wrote {hand_maintained_total} hand-maintained fixtures + "
        f"{archetype_total} archetype fixtures = {documented_total}. Update the row to match."
    )
    assert f"{hand_maintained_total} hand-maintained ({per_theme} fixtures x light and dark)" in note, (
        f"docs/POSITIONING.md's 'A11y gate' row note does not state "
        f"'{hand_maintained_total} hand-maintained ({per_theme} fixtures x light and dark)'; "
        f"got: {note!r}"
    )

    readme_text = _README.read_text(encoding="utf-8")
    readme_match = _README_A11Y_LINE_RE.search(readme_text)
    assert readme_match is not None, (
        "README.md has no 'axe-core WCAG 2.2 AA scan across <n> documents (<n> hand-maintained "
        "fixtures...' sentence; has its accessibility paragraph changed shape?"
    )
    assert int(readme_match.group("total")) == documented_total, (
        f"README.md claims {readme_match.group('total')} documents, but the real traced "
        f"generator run proves {documented_total}. Update README.md to match."
    )
    assert int(readme_match.group("hand")) == hand_maintained_total, (
        f"README.md claims {readme_match.group('hand')} hand-maintained fixtures, but the real "
        f"traced generator run wrote {hand_maintained_total}. Update README.md to match."
    )
