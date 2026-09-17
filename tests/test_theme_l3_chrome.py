"""Phase E: L3 kit chrome reads theme tokens; northline-material moves them.

Source-wiring half of #600. Computed-style half lives in
a11y/theme_l3_chrome.spec.mjs (Playwright probe on a white canvas).
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_COMPONENTS = (_ROOT / "frontend" / "src" / "components.css").read_text(encoding="utf-8")
_PACK = (_ROOT / "docs" / "examples" / "brand-pack" / "northline-material" / "tokens.css").read_text(encoding="utf-8")
_DEFAULTS = (_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "tokens.css").read_text(encoding="utf-8")


def _rules(css: str) -> list[tuple[str, str]]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


def _bodies(selector: str) -> list[str]:
    return [body for sel, body in _rules(_COMPONENTS) if sel == selector]


def _decl_value(css: str, name: str) -> str | None:
    """First custom-property value for *name* in a :root-like block."""
    pattern = re.compile(rf"{re.escape(name)}\s*:\s*([^;]+);")
    match = pattern.search(css)
    return match.group(1).strip() if match else None


def test_button_chrome_reads_radius_and_elevation_tokens() -> None:
    base = _bodies(".bw-btn")
    assert base, "missing .bw-btn"
    assert "var(--bw-component-button-radius)" in base[0]
    # Exact selector pair for resting filled elevation (not :hover / :active).
    elev = [
        body
        for sel, body in _rules(_COMPONENTS)
        if re.sub(r"\s+", "", sel) == ".bw-btn--primary:not(.bw-btn--disabled),.bw-btn--danger:not(.bw-btn--disabled)"
    ]
    assert elev, "missing primary/danger elevation rule"
    assert "var(--bw-component-button-elevation)" in elev[0]
    secondary = [
        body
        for sel, body in _rules(_COMPONENTS)
        if re.sub(r"\s+", "", sel) == ".bw-btn--secondary:not(.bw-btn--disabled)"
    ]
    assert secondary, "missing secondary elevation rule"
    assert "var(--bw-component-button-elevation)" in secondary[0]


def test_card_chrome_reads_l3_radius_elevation_and_surface_tokens() -> None:
    card = _bodies(".bw-card")
    assert card, "missing .bw-card"
    body = card[0]
    assert "var(--bw-radius-lg)" in body
    assert "var(--bw-elevation-1)" in body
    assert "var(--bw-color-surface)" in body
    raised = _bodies(".bw-card--surface-raised")
    assert raised and "var(--bw-color-surface-raised)" in raised[0]


def test_modal_chrome_reads_surface_radius_and_elevation_tokens() -> None:
    floor = _bodies(".bw-modal__panel")
    assert floor, "missing .bw-modal__panel"
    assert "var(--bw-color-surface-raised)" in floor[0]
    assert "var(--bw-radius-xl)" in floor[0]
    assert "var(--bw-elevation-2)" in floor[0]
    open_panel = [
        body
        for sel, body in _rules(_COMPONENTS)
        if ".bw-modal__panel" in sel and ("bw-modal--open" in sel or "data-bw-open" in sel)
    ]
    assert open_panel, "missing open modal panel rule"
    assert "var(--bw-elevation-4)" in open_panel[0]


def test_northline_material_differs_from_defaults_on_gate_axes() -> None:
    """Torture pack must actually change the axes card/modal/button read."""
    for name in (
        "--bw-radius-md",
        "--bw-radius-lg",
        "--bw-radius-xl",
        "--bw-elevation-1",
        "--bw-elevation-2",
        "--bw-elevation-4",
        "--bw-color-surface-raised",
    ):
        pack_val = _decl_value(_PACK, name)
        default_val = _decl_value(_DEFAULTS, name)
        assert pack_val, f"northline-material missing {name}"
        assert default_val, f"defaults missing {name}"
        assert pack_val != default_val, f"{name} torture value equals package default"


def test_component_button_radius_aliases_radius_md() -> None:
    assert "var(--bw-radius-md)" in _DEFAULTS
    assert re.search(
        r"--bw-component-button-radius\s*:\s*var\(--bw-radius-md\)",
        _DEFAULTS,
    ), "button radius must track --bw-radius-md so L3 md moves buttons"
