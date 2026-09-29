"""Migrated craft units must match lockstep-manifest.json hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "lockstep-manifest.json"

TEMPLATES_ROOT = ROOT / "src/brickwork/templates"
MARKETING_TEMPLATES_ROOT = ROOT / "src/brickwork/marketing/templates"
FRONTEND_SRC = ROOT / "frontend/src"

# Mirrored trees where every file must be listed in the manifest. SOURCE.md
# notices are mirror-local documentation, not synced content.
MIRRORED_TREES = {
    "templates": [
        (TEMPLATES_ROOT / "brickwork", TEMPLATES_ROOT),
        (MARKETING_TEMPLATES_ROOT / "brickwork_marketing", MARKETING_TEMPLATES_ROOT),
    ],
    "frontend-js": [(FRONTEND_SRC / "js", FRONTEND_SRC)],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    assert MANIFEST.is_file(), "lockstep-manifest.json missing; run sync-from-monorepo"
    return json.loads(MANIFEST.read_text())


def _template_path(key: str) -> Path:
    """Manifest keys are namespace-prefixed, relative to the owning templates root."""
    namespace = key.split("/", 1)[0]
    root = MARKETING_TEMPLATES_ROOT if namespace == "brickwork_marketing" else TEMPLATES_ROOT
    return root / key


def test_lockstep_manifest_present_and_matches_mirror() -> None:
    data = _manifest()
    assert "tokens" in data.get("migrated_units", []) or "tokens" in data.get("units", {})
    units = data["units"]

    for name, expected in units["tokens"].items():
        path = ROOT / "src/brickwork/tokens/source" / name
        assert path.is_file(), name
        assert _sha256(path) == expected, f"token drift: {name}"

    for name, expected in units["css"].items():
        path = FRONTEND_SRC / name
        assert path.is_file(), name
        assert _sha256(path) == expected, f"css drift: {name}"


def test_lockstep_declares_templates_and_frontend_js_migrated() -> None:
    data = _manifest()
    assert {"tokens", "css-layers", "templates", "frontend-js"} <= set(data["migrated_units"])
    assert data["editorial_home"] == "icvoss/brickwork"
    assert data["units"]["templates"], "templates unit is empty"
    assert data["units"]["frontend-js"], "frontend-js unit is empty"


def test_templates_unit_matches_mirror() -> None:
    templates = _manifest()["units"]["templates"]
    namespaces = {key.split("/", 1)[0] for key in templates}
    assert namespaces == {"brickwork", "brickwork_marketing"}

    for key, expected in templates.items():
        path = _template_path(key)
        assert path.is_file(), key
        assert _sha256(path) == expected, f"template drift: {key}"


def test_frontend_js_unit_matches_mirror() -> None:
    frontend = _manifest()["units"]["frontend-js"]
    assert {"index.js", "index.css"} <= set(frontend)
    assert any(key.startswith("js/") for key in frontend)

    for key, expected in frontend.items():
        path = FRONTEND_SRC / key
        assert path.is_file(), key
        assert _sha256(path) == expected, f"frontend-js drift: {key}"


@pytest.mark.parametrize("unit", sorted(MIRRORED_TREES))
def test_no_unlisted_files_in_mirrored_trees(unit: str) -> None:
    """A file added only to the mirror is drift, so it must be in the manifest."""
    listed = set(_manifest()["units"][unit])
    for tree, key_root in MIRRORED_TREES[unit]:
        for path in tree.rglob("*"):
            if path.is_file():
                key = path.relative_to(key_root).as_posix()
                assert key in listed, f"unlisted mirror file (sync from monorepo): {key}"


def test_source_notices_present() -> None:
    for notice in (
        TEMPLATES_ROOT / "SOURCE.md",
        MARKETING_TEMPLATES_ROOT / "SOURCE.md",
        FRONTEND_SRC / "SOURCE.md",
    ):
        assert notice.is_file(), f"missing mirror notice: {notice.relative_to(ROOT)}"
