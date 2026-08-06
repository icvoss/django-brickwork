#!/usr/bin/env python3
"""Assemble changelog.d/ fragments into a dated CHANGELOG.md section.

Run in a release PR (icvoss/django-brickwork#113):

    python scripts/assemble_changelog.py 2.0.0

Reads every ``changelog.d/<slug>.<type>.md`` fragment, groups the entries into
Added / Changed / Fixed / Removed, inserts a dated ``## [<version>]`` section
above the most recent existing release section, and deletes the fragments it
consumed. The generated section is a STARTING POINT to be edited by hand: a
release usually wants a summary paragraph no fragment can write.

Deliberately dependency-free (stdlib only) so it runs in any checkout without
an install step, and deliberately not wired into CI: assembling a changelog is
a judgement call made once per release, not a gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAGMENT_DIR = REPO_ROOT / "changelog.d"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Order is the Keep a Changelog house order, not alphabetical: a reader wants
# new capability first and removals last.
SECTIONS = ("added", "changed", "fixed", "removed")

FRAGMENT_RE = re.compile(r"^(?P<slug>.+)\.(?P<type>added|changed|fixed|removed)\.md$")


def collect_fragments() -> tuple[dict[str, list[str]], list[Path]]:
    """Return ({type: [entry bodies]}, [consumed paths]), sorted for stability."""
    grouped: dict[str, list[str]] = {section: [] for section in SECTIONS}
    consumed: list[Path] = []

    for path in sorted(FRAGMENT_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        match = FRAGMENT_RE.match(path.name)
        if not match:
            raise SystemExit(
                f"{path.name}: not a valid fragment name. Expected "
                f"<slug>.<type>.md where <type> is one of {', '.join(SECTIONS)}. "
                f"See changelog.d/README.md."
            )
        body = path.read_text(encoding="utf-8").strip()
        if not body:
            raise SystemExit(f"{path.name}: fragment is empty.")
        grouped[match.group("type")].append(body)
        consumed.append(path)

    return grouped, consumed


def render_section(version: str, grouped: dict[str, list[str]], date: str) -> str:
    lines = [f"## [{version}] - {date}", ""]
    for section in SECTIONS:
        entries = grouped[section]
        if not entries:
            continue
        lines.append(f"### {section.capitalize()}")
        lines.append("")
        # A blank line between entries: fragments are usually multi-line
        # paragraphs, and Keep a Changelog reads better spaced than dense.
        lines.append("\n\n".join(entries))
        lines.append("")
    return "\n".join(lines)


def insert_section(changelog_text: str, section: str) -> str:
    """Insert the new section directly above the first existing release heading.

    Anchors on the first ``## [`` heading that is not ``[Unreleased]``, so the
    Unreleased placeholder (kept for anything landing after this release) stays
    at the top where a reader expects it.
    """
    lines = changelog_text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("## [") and not line.startswith("## [Unreleased]"):
            return "".join(lines[:index]) + section + "\n" + "".join(lines[index:])
    raise SystemExit("CHANGELOG.md: found no existing '## [<version>]' heading to insert above.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="the version being released, e.g. 2.0.0")
    parser.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="release date as YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--keep-fragments",
        action="store_true",
        help="do not delete the consumed fragments (for a dry run)",
    )
    args = parser.parse_args()

    grouped, consumed = collect_fragments()
    if not consumed:
        print("No fragments in changelog.d/. Nothing to assemble.", file=sys.stderr)
        return 1

    section = render_section(args.version, grouped, args.date)
    CHANGELOG.write_text(
        insert_section(CHANGELOG.read_text(encoding="utf-8"), section),
        encoding="utf-8",
    )

    if not args.keep_fragments:
        for path in consumed:
            path.unlink()

    counts = ", ".join(f"{len(grouped[s])} {s}" for s in SECTIONS if grouped[s])
    print(f"Wrote [{args.version}] - {args.date} to CHANGELOG.md ({counts}).")
    print(f"Consumed {len(consumed)} fragment(s). Review and edit the section by hand before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
