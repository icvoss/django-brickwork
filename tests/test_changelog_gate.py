"""The changelog gate's opt-out marker must be a decision, not a mention.

``scripts/check_changelog_fragment_required.py`` waives its fragment
requirement when a PR body carries the opt-out marker. That waiver used to be
a substring test, so a PR body that merely DISCUSSED the marker (this file's
own subject, or a PR quoting the failure message the gate prints) silently
waived the gate (icvoss/django-brickwork#380).

The script had no tests at all, which is why the gap between its docstring
("the exact line") and its check (``in``) survived. These pin the behaviour.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_changelog_fragment_required.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_changelog_fragment_required", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = _load()
opt_out_requested = module.opt_out_requested
MARKER = module.OPT_OUT_MARKER


@pytest.mark.parametrize(
    "body",
    [
        MARKER,
        f"{MARKER}\n",
        f"Refactor only, no behaviour change.\n\n{MARKER}\n",
        f"{MARKER}   ",
        f"  {MARKER}",
        f"line one\r\n{MARKER}\r\nline three",
    ],
)
def test_the_marker_alone_on_a_line_waives_the_gate(body: str) -> None:
    # The escape hatch must keep working: this is the whole point of the
    # marker, and a fix that broke it would be worse than the defect.
    assert opt_out_requested(body) is True


@pytest.mark.parametrize(
    "body",
    [
        # The reported defect: prose ABOUT the gate waived the gate.
        f"This PR fixes the '{MARKER}' opt-out so it matches whole lines.",
        # Quoting the gate's own failure message, which names the marker.
        f"CI said: opt out by adding the exact line '{MARKER}' to the PR body.",
        # Marker embedded in a longer token or sentence.
        f"see {MARKER}-discussion in the linked issue",
        f"{MARKER} is what you would add if this were a refactor, but it is not",
        "an ordinary PR body naming no marker at all",
        "",
    ],
)
def test_a_mere_mention_does_not_waive_the_gate(body: str) -> None:
    assert opt_out_requested(body) is False


def test_the_defect_is_actually_reproduced_by_the_old_substring_check() -> None:
    """Teeth: the prose cases must be ones the OLD check got wrong.

    Without this, the negative assertions above could all be strings the
    substring test also rejected, and the parametrised cases would pass
    against the unfixed script. Each of these is a body the old
    ``MARKER in body`` waived and the new check refuses, so the test suite
    would have failed before the fix and passes after it.
    """
    regressions = [
        f"This PR fixes the '{MARKER}' opt-out so it matches whole lines.",
        f"CI said: opt out by adding the exact line '{MARKER}' to the PR body.",
        f"see {MARKER}-discussion in the linked issue",
    ]
    for body in regressions:
        assert MARKER in body, "the old substring check must have waived this body"
        assert opt_out_requested(body) is False, "the new check must refuse it"
