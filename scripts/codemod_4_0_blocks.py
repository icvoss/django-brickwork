#!/usr/bin/env python3
"""Codemod: rename deprecated 3.4.0 template block fills to their 4.0.0 names.

Help text for owned consumers migrating onto django-brickwork 4.0.0. Not a
substitute for the clean break: the package no longer declares the old
block names, so unmigrated fills are silently discarded by Django.

Renames (old → new), scoped to ``{% block … %}`` / ``{% endblock … %}``:

  card_header → header
  card_title → title
  card_actions → actions
  card_body → body
  card_footer → footer
  modal_title / modal_body / modal_footer → title / body / footer
  slide_over_title / slide_over_body / slide_over_footer → title / body / footer
  alert_body → body
  tooltip_trigger → trigger
  empty_state_action → action

Empty-state only (the same word means the opposite on other templates):

  On templates that extend ``_empty_state.html``:
    title → heading
    description → body

Usage::

  python scripts/codemod_4_0_blocks.py path/to/templates [--write]

Default is dry-run (prints planned renames). Pass ``--write`` to apply.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Generic prefixed renames (safe across the package's own templates).
_PREFIXED: list[tuple[str, str]] = [
    ("empty_state_action", "action"),
    ("tooltip_trigger", "trigger"),
    ("slide_over_title", "title"),
    ("slide_over_body", "body"),
    ("slide_over_footer", "footer"),
    ("modal_title", "title"),
    ("modal_body", "body"),
    ("modal_footer", "footer"),
    ("alert_body", "body"),
    ("card_header", "header"),
    ("card_title", "title"),
    ("card_actions", "actions"),
    ("card_body", "body"),
    ("card_footer", "footer"),
]

_EMPTY_STATE_EXTENDS = re.compile(r"""\{%\s*extends\s+["']brickwork/components/_empty_state\.html["']\s*%\}""")
_BLOCK_OPEN = re.compile(r"\{%\s*block\s+(\w+)\s*%\}")
_BLOCK_CLOSE = re.compile(r"\{%\s*endblock(?:\s+(\w+))?\s*%\}")


def _rename_prefixed(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    out = text
    for old, new in _PREFIXED:
        open_pat = re.compile(rf"(\{{%\s*block\s+){old}(\s*%\}})")
        close_pat = re.compile(rf"(\{{%\s*endblock\s+){old}(\s*%\}})")
        opens = len(open_pat.findall(out))
        closes = len(close_pat.findall(out))
        if opens or closes:
            out = open_pat.sub(rf"\1{new}\2", out)
            out = close_pat.sub(rf"\1{new}\2", out)
            notes.append(f"{old} → {new} ({opens} open, {closes} named close)")
    return out, notes


def _rename_empty_state_locals(text: str) -> tuple[str, list[str]]:
    """title→heading and description→body only inside empty_state extenders."""
    if not _EMPTY_STATE_EXTENDS.search(text):
        return text, []
    notes: list[str] = []
    out = text
    for old, new in (("title", "heading"), ("description", "body")):
        open_pat = re.compile(rf"(\{{%\s*block\s+){old}(\s*%\}})")
        close_pat = re.compile(rf"(\{{%\s*endblock\s+){old}(\s*%\}})")
        opens = len(open_pat.findall(out))
        closes = len(close_pat.findall(out))
        if opens or closes:
            out = open_pat.sub(rf"\1{new}\2", out)
            out = close_pat.sub(rf"\1{new}\2", out)
            notes.append(f"empty_state {old} → {new} ({opens} open, {closes} named close)")
    return out, notes


def transform(text: str) -> tuple[str, list[str]]:
    out, notes = _rename_prefixed(text)
    out2, notes2 = _rename_empty_state_locals(out)
    return out2, notes + notes2


def iter_templates(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(p for p in root.rglob("*.html") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="Template file or directory to scan")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply renames in place (default is dry-run)",
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"path not found: {args.path}", file=sys.stderr)
        return 2

    changed = 0
    for path in iter_templates(args.path):
        original = path.read_text(encoding="utf-8")
        updated, notes = transform(original)
        if not notes:
            continue
        changed += 1
        print(f"{path}:")
        for note in notes:
            print(f"  {note}")
        if args.write and updated != original:
            path.write_text(updated, encoding="utf-8")
            print("  wrote")
        elif not args.write:
            print("  (dry-run; pass --write to apply)")

    if changed == 0:
        print("no deprecated block fills found")
    elif not args.write:
        print(f"\n{changed} file(s) would change; re-run with --write to apply")
    else:
        print(f"\n{changed} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
