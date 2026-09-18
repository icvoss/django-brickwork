"""Guard that ``import brickwork`` resolves under this tree when editable.

A shared ``.venv`` in the primary checkout can hold an editable ``.pth`` that
points at whichever worktree last ran ``pip install -e .``. Probes then run
another branch's code with no error and no marker
(icvoss/django-brickwork#354).

Installed-wheel testing (the publish gate) legitimately resolves from
``site-packages``; that path is not under the repo root, so this guard skips
rather than failing the artefact check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import brickwork

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_brickwork_import_resolves_under_this_tree_when_editable() -> None:
    origin = Path(brickwork.__file__).resolve()
    if "site-packages" in origin.parts:
        pytest.skip(
            "brickwork is installed from a wheel (site-packages); "
            "editable worktree path check does not apply "
            "(icvoss/django-brickwork#354)"
        )
    assert origin.is_relative_to(_REPO_ROOT), (
        f"import brickwork resolved outside this tree: {origin}\n"
        f"expected under: {_REPO_ROOT}\n"
        "Use a per-worktree virtualenv and reinstall with "
        '`pip install -e ".[dev]"` from this tree, then confirm with '
        "`import brickwork; print(brickwork.__file__)` "
        "(icvoss/django-brickwork#354)."
    )
