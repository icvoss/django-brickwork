#!/usr/bin/env python3
"""Print the shipped token counts together with the git ref they came from.

Run from the repo root:

    python scripts/token_figures.py            # defaults to origin/main
    python scripts/token_figures.py fc9ebc3    # any ref

This exists for figures QUOTED INTO PROSE: pull request bodies, issue
comments, review notes, release notes. The counts that gate CI are already
derived from the shipped manifests by ``tests/test_positioning.py``, so this
duplicates none of that machinery and is not a second source of truth for
them; it reads the same artefacts and reports what they say.

Why it reads a git ref rather than the working tree: every token figure this
project has published wrongly was a correct measurement of the wrong tree,
taken in a worktree that was behind, mid-edit, or on another branch, then
quoted as a fact about main. Reading through ``git show`` makes that
impossible, and printing the ref alongside the numbers means a figure cannot
be copied out of this output without its provenance travelling with it. The
ref is part of the figure, not a footnote to it.

What this does NOT do: it cannot stop anyone measuring by hand against a
stale checkout, which is how every wrong figure got published in the first
place. It removes the reason to, by being less work than writing a one-off
script, and it makes the resulting number self-describing. That is an easier
path rather than a guarantee, and a tool that claimed more than it delivers
would be the same defect it exists to catch.

Counts reported:

- ``unique --bw-*``: distinct custom-property names in the compiled
  ``tokens.css``. Higher than the overridable count because it includes
  names emitted only inside theme, density, or alias blocks.
- ``overridable``: the length of ``token-manifest.json``'s ``overridable``
  array, the figure ``docs/POSITIONING.md``'s section 5 table is gated
  against.
- ``load-bearing`` and ``unconditional``: the manifest's ``loadBearing``
  entries, and the subset that carry no ``conditional`` flag.
- ``contrastPairs``: declared foreground/background pairs that
  ``render_brand_css()`` validates a brand override against.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

_MANIFEST = "src/brickwork/static/brickwork/dist/token-manifest.json"
_TOKENS_CSS = "src/brickwork/static/brickwork/dist/tokens.css"
_BW_NAME = re.compile(r"--bw-[a-zA-Z0-9_-]+")


def _show(ref: str, path: str) -> str:
    """Read ``path`` as it exists at ``ref``, never from the working tree."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot read {path} at {ref}: {result.stderr.strip()}")
    return result.stdout


def figures(ref: str) -> dict[str, object]:
    """Return the token counts at ``ref``, with the resolved sha alongside."""
    resolved = subprocess.run(
        ["git", "rev-parse", "--short", ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if resolved.returncode != 0:
        raise SystemExit(f"not a git ref: {ref}")

    manifest = json.loads(_show(ref, _MANIFEST))
    load_bearing = manifest["loadBearing"]
    return {
        "ref": ref,
        "sha": resolved.stdout.strip(),
        "unique": len(set(_BW_NAME.findall(_show(ref, _TOKENS_CSS)))),
        "overridable": len(manifest["overridable"]),
        "load_bearing": len(load_bearing),
        "unconditional": len([e for e in load_bearing if not e.get("conditional")]),
        "contrast_pairs": len(manifest.get("contrastPairs", [])),
    }


def main() -> None:
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    f = figures(ref)
    print(f"measured at {f['ref']} ({f['sha']})")
    print(f"  unique --bw-*   {f['unique']}")
    print(f"  overridable     {f['overridable']}")
    print(f"  load-bearing    {f['load_bearing']} ({f['unconditional']} unconditional)")
    print(f"  contrast pairs  {f['contrast_pairs']}")


if __name__ == "__main__":
    main()
