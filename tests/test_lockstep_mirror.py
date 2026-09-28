"""Migrated craft units must match lockstep-manifest.json hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "lockstep-manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lockstep_manifest_present_and_matches_mirror() -> None:
    assert MANIFEST.is_file(), "lockstep-manifest.json missing; run sync-from-monorepo"
    data = json.loads(MANIFEST.read_text())
    assert "tokens" in data.get("migrated_units", []) or "tokens" in data.get("units", {})
    units = data["units"]

    for name, expected in units["tokens"].items():
        path = ROOT / "src/brickwork/tokens/source" / name
        assert path.is_file(), name
        assert _sha256(path) == expected, f"token drift: {name}"

    for name, expected in units["css"].items():
        path = ROOT / "frontend/src" / name
        assert path.is_file(), name
        assert _sha256(path) == expected, f"css drift: {name}"
