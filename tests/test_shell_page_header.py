"""Shell page header region responsive layout (icvoss/django-brickwork#739)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_page_header_region_stacks_actions_below_sm() -> None:
    css = (_ROOT / "frontend" / "src" / "shell.css").read_text(encoding="utf-8")
    assert "@media (width < --theme(--breakpoint-sm))" in css
    assert ".bw-page-header-region" in css
    assert "flex-direction: column" in css
    assert ".bw-page-actions .bw-btn:has(.bw-btn__icon)" in css
    dist = (_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css").read_text(
        encoding="utf-8"
    )
    assert "bw-page-header-region" in dist
    assert "flex-direction:column" in dist.replace(" ", "")
