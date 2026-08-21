"""Template contract manifest tests (CHK-BLD-005, BR-BW-TPL-001, BR-BW-VER-001).

``services/template_manifest.py`` reads the shipped ``template-manifest.json``
(generated from the real shipped template tree by
``scripts/generate_template_manifest.py``) and exposes every semver-public
block/partial name as typed Python. These tests cover four things, each
independent of the others:

1. **Manifest shape**: the typed reader's accessors match the raw JSON, and
   the deprecated ``empty_state_action`` entry is represented correctly.
2. **Manifest-vs-reality drift**: regenerating the manifest from the current
   template tree produces byte-identical output to the committed file. This
   is the same drift discipline ``test_tokens.py`` applies to the compiled
   token artefacts, and what the CI ``test`` job's manifest-regeneration step
   gates on (mirroring the ``frontend-build`` job's token drift gate).
3. **The rename-detection gate**: ``check_contract_stability`` compares the
   committed baseline (``tests/template_contract_baseline.json``) against a
   manifest and fails, with an instructive message, when a name disappears
   without a covering deprecation. This is the actual point of this file: it
   is what makes a silent block rename impossible to land, where before this
   change ``AC-BW-010`` only checked that a block was documented, never that
   its name was stable.
4. **What the gate deliberately allows**: adding a new name is never a
   violation (additive is MINOR), and a name that is both still present and
   listed under ``deprecated`` in the current manifest is never a violation
   (that is the BR-BW-VER-001 parallel-support shape working as intended).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from brickwork.services.template_manifest import (
    block_names,
    blocks,
    declared_in,
    deprecation,
    is_deprecated,
    manifest,
    partial_names,
    partials,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DIST = _REPO_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"
_BASELINE_PATH = _REPO_ROOT / "tests" / "template_contract_baseline.json"


def _load_generator():
    """Import scripts/generate_template_manifest.py without touching sys.path.

    The generator lives in scripts/, not the installed package, so it is not
    importable by dotted name; loading it directly by file path keeps this
    test file's own imports ruff-clean (no path mutation ahead of an import).
    """
    spec = importlib.util.spec_from_file_location(
        "generate_template_manifest", _REPO_ROOT / "scripts" / "generate_template_manifest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_generator = _load_generator()
build_manifest = _generator.build_manifest
check_contract_stability = _generator.check_contract_stability


# ---------------------------------------------------------------------------
# 1. Manifest shape
# ---------------------------------------------------------------------------


def test_block_names_includes_a_shell_block_and_a_component_block() -> None:
    names = block_names()
    assert "content" in names  # declared independently by every shell
    assert "card_header" in names  # declared by _card.html


def test_partial_names_includes_a_tag_consumed_and_an_include_consumed_partial() -> None:
    names = partial_names()
    assert "btn_inner" in names  # _button.html, tag-consumed
    assert "table_rows" in names  # _data_table.html, include-consumed


def test_declared_in_returns_every_declaring_template_for_a_shared_block_name() -> None:
    # "content" has no common ancestor that declares it (shell/base.html does
    # not), so every shell that offers it as its own extension point appears.
    owners = declared_in("content")
    assert "brickwork/shell/app.html" in owners
    assert "brickwork/shell/auth.html" in owners
    assert "brickwork/shell/centred.html" in owners
    assert "brickwork_marketing/shell/marketing.html" in owners


def test_declared_in_returns_a_single_template_for_a_partial() -> None:
    assert declared_in("btn_inner") == ["brickwork/components/_button.html"]


def test_declared_in_returns_empty_list_for_an_unknown_name() -> None:
    assert declared_in("not_a_real_block_or_partial") == []


def test_empty_state_action_is_deprecated_and_superseded_by_action() -> None:
    assert is_deprecated("empty_state_action") is True
    entry = deprecation("empty_state_action")
    assert entry is not None
    assert entry["declaredIn"] == "brickwork/components/_empty_state.html"
    assert entry["supersededBy"] == "action"
    assert entry["removedAt"] == "4.0.0"


def test_empty_state_action_still_ships_alongside_its_replacement() -> None:
    # Deprecated is not the same as removed: BR-BW-VER-001 parallel support
    # means both the old and new block are still in the live block set.
    names = block_names()
    assert "empty_state_action" in names
    assert "action" in names


def test_a_non_deprecated_name_returns_not_deprecated() -> None:
    assert is_deprecated("content") is False
    assert deprecation("content") is None


def test_manifest_escape_hatch_matches_typed_accessors() -> None:
    raw = manifest()
    assert [entry["name"] for entry in raw["blocks"]] == [entry["name"] for entry in blocks()]
    assert [entry["name"] for entry in raw["partials"]] == [entry["name"] for entry in partials()]


def test_blocks_and_partials_are_cached_and_immutable() -> None:
    first = blocks()
    second = blocks()
    assert first is second, "blocks() should be lru_cache'd (read once per process)"
    assert isinstance(first, tuple)


# ---------------------------------------------------------------------------
# 2. Manifest-vs-reality drift
# ---------------------------------------------------------------------------


def test_committed_manifest_matches_a_fresh_regeneration_from_the_template_tree() -> None:
    """The generator is the ONLY thing that may write template-manifest.json.

    A source edit that adds/renames/removes a block or partial without
    re-running the generator (``python scripts/generate_template_manifest.py``)
    fails here, exactly as an un-rebuilt token artefact fails the
    ``frontend-build`` CI job's ``git diff --exit-code`` check.
    """
    committed = json.loads(_DIST.joinpath("template-manifest.json").read_text(encoding="utf-8"))
    fresh = build_manifest()
    assert fresh == committed, (
        "template-manifest.json is stale: run "
        "'DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:. "
        "python scripts/generate_template_manifest.py' and commit the result."
    )


def test_every_declared_block_and_partial_name_is_a_valid_python_identifier_shape() -> None:
    # Django's own {% block %}/{% partialdef %} grammar only accepts a single
    # bare word (see defaulttags.partialdef_func / loader_tags.do_block), so
    # this is a sanity check on the generator's extraction, not a new rule.
    for entry in blocks():
        assert entry["name"].isidentifier(), entry["name"]
    for entry in partials():
        assert entry["name"].isidentifier(), entry["name"]


# ---------------------------------------------------------------------------
# 3 & 4. The rename-detection gate: what it catches, and what it allows
# ---------------------------------------------------------------------------


@pytest.fixture
def baseline() -> dict:
    return json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def current() -> dict:
    return json.loads(_DIST.joinpath("template-manifest.json").read_text(encoding="utf-8"))


def test_the_committed_baseline_matches_the_committed_manifest_with_no_violations(
    baseline: dict, current: dict
) -> None:
    """The gate itself must be green against the repo as it stands.

    If this fails, either the manifest was regenerated without updating the
    baseline in the same PR, or the baseline drifted for some other reason;
    either way it is a real finding, not a fixture problem.
    """
    assert check_contract_stability(baseline, current) == []


def test_removing_a_block_with_no_deprecation_entry_fails_with_an_instructive_message(
    baseline: dict, current: dict
) -> None:
    current["blocks"] = [entry for entry in current["blocks"] if entry["name"] != "trigger_meta"]

    violations = check_contract_stability(baseline, current)

    assert len(violations) == 1
    message = violations[0]
    assert "trigger_meta" in message
    assert "BR-BW-TPL-001" in message
    assert "BR-BW-VER-001" in message
    # The message must name the concrete paths forward, not just "this broke".
    assert "deprecate" in message.lower()
    assert "MAJOR" in message


def test_renaming_a_block_fails_the_same_way_as_removing_it(baseline: dict, current: dict) -> None:
    # A rename is a removal of the old name plus an addition of a new one;
    # the gate only needs to catch the removal half, since the addition half
    # is never a violation on its own (checked below).
    current["blocks"] = [entry for entry in current["blocks"] if entry["name"] != "modal_title"]
    current["blocks"].append(
        {"name": "dialog_title", "declaredIn": ["brickwork/components/_modal.html"], "consumption": ["extend"]}
    )

    violations = check_contract_stability(baseline, current)

    assert len(violations) == 1
    assert "modal_title" in violations[0]


def test_removing_a_partial_with_no_deprecation_entry_fails(baseline: dict, current: dict) -> None:
    current["partials"] = [entry for entry in current["partials"] if entry["name"] != "sort_link"]

    violations = check_contract_stability(baseline, current)

    assert len(violations) == 1
    assert "sort_link" in violations[0]
    assert "partial" in violations[0]


def test_adding_a_new_block_is_never_a_violation(baseline: dict, current: dict) -> None:
    current["blocks"].append(
        {"name": "brand_new_block", "declaredIn": ["brickwork/components/_card.html"], "consumption": ["include"]}
    )

    assert check_contract_stability(baseline, current) == []


def test_adding_a_new_partial_is_never_a_violation(baseline: dict, current: dict) -> None:
    current["partials"].append(
        {
            "name": "brand_new_partial",
            "declaredIn": "brickwork/components/_tabs.html",
            "inline": False,
            "consumption": "tag",
        }
    )

    assert check_contract_stability(baseline, current) == []


def test_a_name_still_present_and_marked_deprecated_is_never_a_violation(baseline: dict, current: dict) -> None:
    # This is the steady-state shape for empty_state_action right now: present
    # in both blocks and deprecated, in both the baseline and the current
    # manifest. Confirms the gate does not flag ordinary parallel support.
    assert "empty_state_action" in baseline["deprecated"]
    assert any(entry["name"] == "empty_state_action" for entry in current["deprecated"])
    assert any(entry["name"] == "empty_state_action" for entry in current["blocks"])

    assert check_contract_stability(baseline, current) == []


def test_dropping_a_deprecated_name_at_a_major_still_requires_a_baseline_update(baseline: dict, current: dict) -> None:
    # Simulates the 4.0.0 removal BR-BW-TPL-001's own deprecation note
    # promises: empty_state_action drops out of the LIVE manifest entirely
    # (both blocks and deprecated). The gate still fires, because the
    # baseline was not updated in this simulated change: a major-version
    # removal is a deliberate, acknowledged act (update the baseline in the
    # same PR as the bump), never a change that passes just because a prior
    # deprecation entry existed.
    current["blocks"] = [entry for entry in current["blocks"] if entry["name"] != "empty_state_action"]
    current["deprecated"] = [entry for entry in current["deprecated"] if entry["name"] != "empty_state_action"]

    violations = check_contract_stability(baseline, current)

    assert len(violations) == 1
    assert "empty_state_action" in violations[0]
