"""Phase 5 appearance adoption: every catalogue component is cleared or N/A.

Beautiful-defaults suite Phase 5 (icvoss/django-brickwork#540): APPEARANCE.md
must list every catalogue component between the phase5-adoption markers so no
row stays "flat only" without an explicit Adopted or N/A disposition.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APPEARANCE = _ROOT / "docs" / "APPEARANCE.md"
_MANIFEST = (
    _ROOT
    / "src"
    / "brickwork"
    / "static"
    / "brickwork"
    / "dist"
    / "catalogue-manifest.json"
)

_START = "<!-- phase5-adoption:start -->"
_END = "<!-- phase5-adoption:end -->"
_ROW = re.compile(
    r"^\|\s*(?P<name>[a-z0-9_]+)\s*\|\s*"
    r"(?P<status>Adopted|N/A \([^)]+\))\s*\|\s*"
    r"(?P<notes>.*?)\s*\|\s*$"
)
_ALLOWED_STATUS = {
    "Adopted",
    "N/A (defaults)",
    "N/A (keep lean)",
    "N/A (compose)",
    "N/A (local)",
    "N/A (deferred)",
}


def _catalogue_component_names() -> set[str]:
    man = json.loads(_MANIFEST.read_text())
    return {
        e["name"].split("/")[-1]
        for e in man["items"]
        if e.get("kind") == "component"
    }


def _phase5_component_rows() -> dict[str, str]:
    text = _APPEARANCE.read_text()
    start = text.index(_START) + len(_START)
    end = text.index(_END)
    block = text[start:end]
    # Only the "Catalogue components" table (stop at next ### heading).
    comps_heading = block.index("### Catalogue components")
    rest = block[comps_heading:]
    next_heading = rest.find("\n### ", 1)
    table = rest if next_heading < 0 else rest[:next_heading]
    rows: dict[str, str] = {}
    for line in table.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        name = m.group("name")
        status = m.group("status")
        assert status in _ALLOWED_STATUS, f"unknown status {status!r} for {name}"
        rows[name] = status
    return rows


def test_phase5_adoption_covers_every_catalogue_component() -> None:
    catalogue = _catalogue_component_names()
    rows = _phase5_component_rows()
    missing = sorted(catalogue - set(rows))
    extra = sorted(set(rows) - catalogue)
    assert not missing, f"APPEARANCE Phase 5 missing catalogue components: {missing}"
    assert not extra, f"APPEARANCE Phase 5 lists unknown components: {extra}"


def test_phase5_adoption_has_adopted_and_na_rows() -> None:
    rows = _phase5_component_rows()
    assert any(s == "Adopted" for s in rows.values())
    assert any(s.startswith("N/A") for s in rows.values())
