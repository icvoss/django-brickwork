#!/usr/bin/env python3
"""Fail if the tagged commit still carries unconsumed changelog fragments.

Run at release time, against the commit being tagged (icvoss/django-brickwork#375):

    python scripts/check_no_leftover_fragments.py

``scripts/assemble_changelog.py`` DELETES every fragment it consumes, so a
fragment still present at ``changelog.d/`` at tag time is proof the assembler
either never ran or ran against an earlier commit than the one being tagged.
This is deliberately a state check, not a history check: ``publish.yml`` fires
on a tag push, where the commit history leading to the tag may have been
squashed or rebased, so "was there a consuming commit" is not reliably
answerable from history. Whether ``changelog.d/`` is clean AT THE TAGGED
COMMIT is answerable, and is exactly the fact that matters.

This complements, and does not replace, the existing CHANGELOG heading check
in ``publish.yml``'s ``resolve`` job. That check alone is satisfiable by a
hand-written ``## [<version>]`` heading with no fragment ever having been
assembled into it, which is exactly what shipped v3.13.0 without naming four
capabilities (icvoss/django-brickwork#361): ``scripts/assemble_changelog.py``
never ran, and the release commit hand-inserted the heading above content
already sitting under ``## [Unreleased]``. A leftover-fragment check cannot
see a capability that never wrote a fragment in the first place (that is
DELIVERABLE 1's job, the PR-time gate), but it does catch the specific
failure of fragments existing and being ignored, which is what happened here:
14 fragments were present at the v3.13.0 tag and none had been consumed.

Deliberately dependency-free (stdlib only) so it runs in CI with no install
step beyond the checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAGMENT_DIR = REPO_ROOT / "changelog.d"


def leftover_fragments() -> list[Path]:
    """Return every consumable fragment still present, sorted for stable output."""
    return sorted(path for path in FRAGMENT_DIR.glob("*.md") if path.name != "README.md")


def main() -> int:
    leftover = leftover_fragments()
    if not leftover:
        print("changelog.d/ holds no leftover fragments. Clean to release.")
        return 0

    names = "\n".join(f"  - {path.name}" for path in leftover)
    print(
        "ERROR: changelog.d/ still holds unconsumed fragment(s) at the tagged "
        "commit:\n"
        f"{names}\n\n"
        "scripts/assemble_changelog.py deletes every fragment it consumes, so "
        "a fragment still present here means either the assembler never ran "
        "for this release, or it ran against a commit earlier than the one "
        "being tagged. See RELEASING.md, 'Pre-tag checklist': run "
        "'python scripts/assemble_changelog.py <version>', review the "
        "generated CHANGELOG section by hand, commit, and re-tag.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
