"""Vendored @bwui artefacts must match the npm pins when node_modules is present."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"
PACKAGE_JSON = ROOT / "package.json"
PIN = DIST / "bwui-pin.json"
TOKENS_NM = ROOT / "node_modules" / "@bwui" / "tokens"
CSS_NM = ROOT / "node_modules" / "@bwui" / "css"

TOKEN_FILES = ("tokens.css", "tailwind-theme.css", "tokens.js")
CSS_FILES = ("brickwork.css",)


def _pins() -> dict:
    pkg = json.loads(PACKAGE_JSON.read_text())
    deps = pkg.get("dependencies", {})
    return {
        "tokens": deps["@bwui/tokens"],
        "css": deps["@bwui/css"],
    }


def test_package_json_pins_exact_bwui_versions() -> None:
    pins = _pins()
    for name, version in pins.items():
        assert version and not version.startswith("^"), f"{name} pin must be exact, got {version!r}"
        assert version.count(".") >= 2, f"{name} pin looks like a range: {version!r}"


def test_bwui_pin_file_matches_package_json() -> None:
    assert PIN.is_file(), "missing bwui-pin.json (run npm run build)"
    recorded = json.loads(PIN.read_text())
    pins = _pins()
    assert recorded["tokens"] == pins["tokens"]
    assert recorded["css"] == pins["css"]
    for name in (*TOKEN_FILES, *CSS_FILES):
        assert name in recorded["vendored"]


@pytest.mark.skipif(not TOKENS_NM.is_dir(), reason="npm deps not installed")
def test_vendored_tokens_match_installed_package() -> None:
    for name in TOKEN_FILES:
        shipped = DIST / name
        published = TOKENS_NM / "dist" / name
        assert published.is_file(), f"missing {published}"
        assert shipped.read_bytes() == published.read_bytes(), f"drift vs @bwui/tokens: {name}"


@pytest.mark.skipif(not CSS_NM.is_dir(), reason="npm deps not installed")
def test_vendored_css_is_minified_from_installed_package() -> None:
    published = CSS_NM / "dist" / "brickwork.css"
    shipped = DIST / "brickwork.css"
    assert published.is_file()
    assert shipped.is_file()
    assert shipped.stat().st_size > 0
    # Minify changes bytes; the published source must still be the input.
    assert b".bw-badge--neutral" in published.read_bytes()
    assert b".bw-badge--neutral" in shipped.read_bytes()
