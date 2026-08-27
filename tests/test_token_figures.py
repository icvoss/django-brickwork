"""The quoted-figure helper must report the ref it measured, not the tree it ran in.

The counts themselves are gated elsewhere (``test_positioning.py`` checks the
shipped manifest against ``docs/POSITIONING.md``). What is tested here is the
property that helper exists for: a figure produced without its ref, or read
from the working tree instead of the requested ref, is the defect it prevents.

The fixture is two real refs whose counts genuinely differ on every axis. A
helper that ignored its argument and read the checkout would agree with at
most one of them, so it fails rather than passing by coincidence (#286: the
fixture must be able to express the violation).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from token_figures import figures  # noqa: E402

# Two refs, chosen because #297 (the chart token vocabulary) moved every count
# between them. Pinned as shas rather than branch names so the fixture cannot
# drift into agreement as main advances.
_BEFORE = "a1c2330"
_AFTER = "fc9ebc3"


def _available(ref: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{ref}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


_needs_history = pytest.mark.skipif(
    not (_available(_BEFORE) and _available(_AFTER)),
    reason="shallow clone: the two pinned refs are not present",
)


@_needs_history
def test_the_two_pinned_refs_really_do_differ() -> None:
    """Guard the fixture itself: if these agree, every test below is vacuous."""
    before, after = figures(_BEFORE), figures(_AFTER)
    for key in ("unique", "overridable", "contrast_pairs"):
        assert before[key] != after[key], (
            f"{key} is equal at {_BEFORE} and {_AFTER}, so this fixture can no "
            "longer catch a helper that ignores its ref argument"
        )


@_needs_history
@pytest.mark.parametrize("ref", [_BEFORE, _AFTER])
def test_figures_report_the_ref_they_were_asked_for(ref: str) -> None:
    """The ref travels with the numbers; that is the whole point of the helper."""
    result = figures(ref)
    assert result["ref"] == ref
    assert result["sha"], "no sha resolved, so the figure carries no provenance"
    assert ref.startswith(result["sha"]) or result["sha"].startswith(ref)


@_needs_history
def test_figures_read_the_requested_ref_not_the_working_tree() -> None:
    """The defect this helper exists to prevent, asserted directly.

    Every wrong token figure this project has published was a correct
    measurement of the wrong tree. If ``figures()`` ever reads the checkout
    instead of the ref, one of these two must come back with the other's
    numbers.
    """
    before, after = figures(_BEFORE), figures(_AFTER)
    assert before["unique"] == 337
    assert before["overridable"] == 268
    assert after["unique"] == 352
    assert after["overridable"] == 283


@_needs_history
def test_an_unknown_ref_fails_loudly_rather_than_falling_back() -> None:
    """A silent fallback to the working tree is the failure mode to avoid."""
    with pytest.raises(SystemExit):
        figures("definitely-not-a-ref")
