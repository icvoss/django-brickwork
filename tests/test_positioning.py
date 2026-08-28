"""Drift gate for docs/POSITIONING.md section 5, "The full verified numbers"
(icvoss/django-brickwork#240).

That table is the canonical claims source the consuming site's marketing copy
anchors to (`docs/POSITIONING.md`'s own scope statement). It had rotted
silently once already: written at 3.7.0, still claiming 3.7.0 numbers at
3.10.0, worst on the component count (39 claimed, 40 shipped once
bw_theme_switch landed in 3.9.0). This module parses the ACTUAL markdown
table out of the doc (row label -> value cell, not a hand-copied literal), so
either side of a future edit that leaves the other behind fails loudly here
rather than rotting again.

Every source read in this file is the shipped artefact or importable code
exactly as a consumer would resolve it, mirroring the existing manifest
drift tests' own convention:
- the catalogue manifest via ``brickwork.services._catalogue_manifest``
  (``importlib.resources`` under the hood, same as a real consumer), never
  by re-running ``scripts/generate_catalogue_manifest.py``: this must be able
  to fail if the wheel's shipped JSON goes stale even when the generator
  would still produce the right thing.
- the token manifest via ``brickwork.services.token_manifest``, same reasoning.
- ``brickwork.__version__`` via a real import, never a string copied from
  ``pyproject.toml``.
- template tag registrations via importing the six ``templatetags`` modules
  and inspecting each ``Library``'s own ``tags``/``filters`` mappings.
- Alpine registrations by parsing the ``Alpine.data("...", ...)`` calls out
  of ``frontend/src/js/index.js``, the single registration point named in
  that file's own module docstring.

Rows this file does NOT gate (icons, logical-property counts, the test
function count) are cheap to compute but not cheap to keep honest inside
pytest without re-implementing a second parallel counting mechanism with no
independent source to check it against, or without shelling out to Node.
docs/POSITIONING.md marks each of those rows "dated" rather than "gated" in
its own table for exactly this reason; this file must never silently start
asserting one of them as a tautology (deriving both sides from the same
expression proves nothing).
"""

from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path

import brickwork
from brickwork.services._catalogue_manifest import manifest as catalogue_manifest
from brickwork.services.token_manifest import manifest as token_manifest_data

_REPO_ROOT = Path(__file__).resolve().parent.parent
_POSITIONING = _REPO_ROOT / "docs" / "POSITIONING.md"

# ---------------------------------------------------------------------------
# Markdown table parsing: row label -> value cell, from the ACTUAL doc text.
# ---------------------------------------------------------------------------

_SECTION_5_HEADING_RE = re.compile(r"(?m)^## \d+\. The full verified numbers")
_NEXT_HEADING_RE = re.compile(r"(?m)^## \d+\. ")
_TABLE_ROW_RE = re.compile(r"^\|\s*(?P<label>[^|]+?)\s*\|\s*(?P<value>[^|]+?)\s*\|\s*(?P<note>.*?)\s*\|$")


def _section_5_text() -> str:
    """The text of the "full verified numbers" section, found by title rather
    than by section number: renumbering the document (inserting or removing an
    earlier section) must not break this gate, only retitling the section
    should.
    """
    text = _POSITIONING.read_text(encoding="utf-8")
    start = _SECTION_5_HEADING_RE.search(text)
    assert start is not None, (
        "docs/POSITIONING.md has no '## <n>. The full verified numbers' heading; has the section been renamed?"
    )
    end = _NEXT_HEADING_RE.search(text, start.end())
    assert end is not None, "docs/POSITIONING.md has no heading after the full verified numbers section"
    return text[start.end() : end.start()]


def _parse_table(section_text: str) -> dict[str, tuple[str, str]]:
    """Every ``| Fact | Value | Note |`` row as ``{fact: (value, note)}``.

    Skips the header row and the ``|---|---|---|`` separator row (neither
    parses as a real fact/value pair, and both would otherwise pollute the
    returned mapping with junk keys).
    """
    rows: dict[str, tuple[str, str]] = {}
    for line in section_text.splitlines():
        match = _TABLE_ROW_RE.match(line.strip())
        if match is None:
            continue
        label = match.group("label").strip()
        if label in {"Fact", "---"} or set(label) <= {"-"}:
            continue
        rows[label] = (match.group("value").strip(), match.group("note").strip())
    return rows


def _table_rows() -> dict[str, tuple[str, str]]:
    return _parse_table(_section_5_text())


def _leading_int(value: str) -> int:
    """The leading integer of a value cell, e.g. "40" -> 40, "19 total" -> 19."""
    match = re.match(r"(\d+)", value)
    assert match is not None, f"value cell {value!r} does not start with an integer"
    return int(match.group(1))


# ---------------------------------------------------------------------------
# Sanity: the table exists and every row this file inspects is present.
# ---------------------------------------------------------------------------


def test_section_5_table_is_parseable_and_non_empty() -> None:
    rows = _table_rows()
    assert rows, "parsed zero rows from docs/POSITIONING.md section 5; has the table format changed?"
    assert "Version" in rows


# The rows this file's other tests treat as gated, i.e. cross-checked against
# a real shipped artefact rather than merely hand-counted. Kept as a literal
# list here, independent of the note text, so the assertion below is not
# tautological: it reads the "Gated" marker from the parsed table and checks
# it against this list, rather than deriving both sides from the same string.
_GATED_ROW_LABELS = (
    "Components",
    "Shells",
    "Sections",
    "Archetypes",
    "Template tag registrations",
    "Tokens",
    "Alpine components",
    "Examples",
    "A11y gate",
    "Version",
)


def test_gated_rows_carry_a_visible_gated_marker_in_their_note() -> None:
    """Every row this file treats as gated must still say so in the doc.

    Guards against a silent relabelling (e.g. "Gated" -> "Dated") that would
    otherwise leave the table claiming a row is merely dated while this file
    keeps enforcing it as gated, which is a correctness statement the reader
    can no longer verify by reading the table alone.
    """
    rows = _table_rows()
    for label in _GATED_ROW_LABELS:
        _value, note = rows[label]
        assert re.search(r"\*\*[A-Za-z ]*[Gg]ated\*\*", note), (
            f"{label!r} row is treated as gated by this test file but its note "
            f"no longer carries a visible Gated marker: {note!r}"
        )


# ---------------------------------------------------------------------------
# Gated rows: catalogue manifest kind counts and the core/marketing split.
# ---------------------------------------------------------------------------


def test_components_row_matches_the_shipped_catalogue_manifest() -> None:
    manifest = catalogue_manifest()
    items = manifest["items"]
    components = [item for item in items if item["kind"] == "component"]
    marketing = [item for item in components if "brickwork_marketing" in item["templatePath"]]
    core_count = len(components) - len(marketing)

    value, note = _table_rows()["Components"]
    assert _leading_int(value) == len(components) == manifest["counts"]["components"]
    assert f"{core_count} core" in note
    assert f"{len(marketing)} marketing" in note


def test_shells_row_matches_the_shipped_catalogue_manifest() -> None:
    manifest = catalogue_manifest()
    value, _note = _table_rows()["Shells"]
    assert _leading_int(value) == manifest["counts"]["shells"]


def test_sections_row_matches_the_shipped_catalogue_manifest() -> None:
    manifest = catalogue_manifest()
    value, _note = _table_rows()["Sections"]
    assert _leading_int(value) == manifest["counts"]["sections"]


def test_archetypes_row_matches_the_shipped_catalogue_manifest() -> None:
    manifest = catalogue_manifest()
    value, _note = _table_rows()["Archetypes"]
    assert _leading_int(value) == manifest["counts"]["archetypes"]


def test_examples_row_matches_the_shipped_catalogue_manifest() -> None:
    manifest = catalogue_manifest()
    total = manifest["counts"]["sections"] + manifest["counts"]["archetypes"]

    value, note = _table_rows()["Examples"]
    assert _leading_int(value) == total
    assert f"{manifest['counts']['archetypes']} archetype pages" in note
    assert f"{manifest['counts']['sections']} sections" in note


def test_a11y_gate_archetype_fixture_count_matches_the_shipped_manifest() -> None:
    """Only the archetype half of the a11y-gate row is cheaply gateable here.

    The 122 hand-maintained fixtures (61 fixtures x light and dark) are no
    longer merely hand-counted from a11y/generate_fixtures.py's source: this
    file still deliberately does not re-parse that script (a second regex
    over its source would be exactly the kind of parallel, ungrounded
    re-derivation this module's docstring warns against), but
    tests/test_a11y_fixture_coverage.py's
    test_documented_hand_maintained_fixture_count_matches_the_real_generator_output
    counts the real files the traced generator run writes and gates this
    exact number against that count, so it is covered end to end even
    though the mechanism lives in the other file. (A prior review round
    hand-counted the generator's write-call sites and reached 52/104,
    which the real traced run disproved: it was 51/102, per
    icvoss/django-brickwork#226 review "B5". #244 then added a tag-input
    fixture pair to the same generator, moving the real count to 52/104,
    which coincided with that original hand count but for a different
    reason: one more fixture landed for real, rather than the hand count
    being right all along. #235 then added a theme-switch compact-layout
    fixture pair, moving the real count to 53/106. #183 then added a
    ranked-list fixture pair, moving the real count to 54/108. #272's own
    review round then added a no-JS-floor compact fixture
    (theme-switch-compact-<theme>.html, the pre-existing no-JS coverage
    only ever rendered layout="inline"), moving the real count to 55/110.
    #185 then added the _data_table.html empty-state action CTA fixture,
    moving the real count to 56/112. The chart card work then added a
    chart-card fixture pair, covering the real {% bw_chart_mount %} tag's
    accessible-name pairing plus the card's loading, error and empty
    states, moving the real count to 57/114. The sparkline work then added
    a sparkline fixture pair, covering the neutral and trend tones, the
    highlight marker and the no-JS floor, moving the real count to 60/120.
    The trend indicator work (VIZ-017) then added a trend-indicator fixture
    trio (up/down/flat), which this docstring never recorded a step for; the
    scorecard/stat-comparison work then added a scorecard fixture, covering
    the shared dashboard grid's span= modifiers plus the comparison tile's
    sm/md/lg sizes, moving the real count to 61/122.)
    The archetype half is different: it is walked from the SAME shipped
    manifest every other gated row already reads, so it is genuinely free
    to check here.
    """
    manifest = catalogue_manifest()
    archetype_count = manifest["counts"]["archetypes"]

    value, note = _table_rows()["A11y gate"]
    assert _leading_int(value) == 122 + (archetype_count * 2)
    assert f"{archetype_count} catalogue archetypes x light and dark" in note


# ---------------------------------------------------------------------------
# Gated row: token manifest overridable count.
# ---------------------------------------------------------------------------


def test_tokens_row_overridable_count_matches_the_shipped_token_manifest() -> None:
    manifest = token_manifest_data()
    overridable_count = len(manifest["overridable"])

    value, note = _table_rows()["Tokens"]
    assert f"{overridable_count} overridable" in note, (
        f"the shipped token-manifest.json carries {overridable_count} overridable names; "
        "docs/POSITIONING.md section 5's Tokens row note is stale"
    )
    # The load-bearing set and its unconditional subset are equally cheap to
    # check against the same shipped manifest.
    load_bearing = manifest["loadBearing"]
    unconditional = [entry for entry in load_bearing if not entry.get("conditional")]
    assert f"{len(load_bearing)} load-bearing" in note
    assert f"{len(unconditional)} unconditional" in note


# ---------------------------------------------------------------------------
# Gated row: Alpine.data() registrations, parsed from the single registration
# point (frontend/src/js/index.js's own module docstring names it as such).
# ---------------------------------------------------------------------------

_ALPINE_DATA_CALL_RE = re.compile(r'Alpine\.data\(\s*"(\w+)"')


def test_alpine_components_row_matches_the_registration_point() -> None:
    index_js = (_REPO_ROOT / "frontend" / "src" / "js" / "index.js").read_text(encoding="utf-8")
    registered = _ALPINE_DATA_CALL_RE.findall(index_js)
    assert registered, "found zero Alpine.data(...) calls in frontend/src/js/index.js; has it moved?"

    value, note = _table_rows()["Alpine components"]
    assert _leading_int(value) == len(registered)
    for name in registered:
        assert name in note, f"{name} is registered in index.js but not named in the Alpine components row note"


# ---------------------------------------------------------------------------
# Gated row: template tag registrations, introspected from the real Library
# objects the six templatetags modules build at import time.
# ---------------------------------------------------------------------------

_TEMPLATETAGS_MODULES = (
    "brickwork.templatetags.brickwork_components",
    "brickwork.templatetags.brickwork_forms",
    "brickwork.templatetags.brickwork_icons",
    "brickwork.templatetags.brickwork_interactions",
    "brickwork.templatetags.brickwork_nav",
    "brickwork.templatetags.brickwork_theming",
)


def test_template_tag_registrations_row_matches_the_real_libraries() -> None:
    total_tags = 0
    total_filters = 0
    for module_name in _TEMPLATETAGS_MODULES:
        module = importlib.import_module(module_name)
        total_tags += len(module.register.tags)
        total_filters += len(module.register.filters)
    grand_total = total_tags + total_filters

    value, note = _table_rows()["Template tag registrations"]
    assert _leading_int(value) == grand_total
    assert f"{total_filters} `filter`" in note
    # The Library API exposes tags as one mapping (inclusion_tag and
    # simple_tag both register through it), so the inclusion/simple split in
    # the note is cross-checked against a source-level decorator count
    # instead of the runtime registry, which cannot distinguish the two tag
    # kinds once registered.
    inclusion_tag_count = 0
    simple_tag_count = 0
    for module_name in _TEMPLATETAGS_MODULES:
        source = inspect.getsource(importlib.import_module(module_name))
        inclusion_tag_count += len(re.findall(r"register\.inclusion_tag\(", source))
        simple_tag_count += len(re.findall(r"register\.simple_tag\b", source))
    assert inclusion_tag_count + simple_tag_count == total_tags
    assert f"{inclusion_tag_count} `inclusion_tag`" in note
    assert f"{simple_tag_count} `simple_tag`" in note


# ---------------------------------------------------------------------------
# Gated row: version, against the real import (never a string copied from
# pyproject.toml).
# ---------------------------------------------------------------------------


def test_version_row_matches_the_real_package_version() -> None:
    value, note = _table_rows()["Version"]
    assert value == brickwork.__version__
    assert "pyproject.toml" in note
    assert "__init__.py" in note
