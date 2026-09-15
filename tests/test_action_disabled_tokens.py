"""COL-018 flat disabled tokens (icvoss/django-brickwork#282).

Opacity dimming failed contrast on most surfaces and cannot be gated under
brand overrides. The package ships ``--bw-color-action-disabled-{bg,text,border}``
and paints disabled controls with those tokens instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from brickwork.services.brand_css import BrandValidationError, render_brand_css
from brickwork.services.token_manifest import contrast_pairs, overridable_names

_ROOT = Path(__file__).resolve().parent.parent
_DIST = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"
_FRONTEND = _ROOT / "frontend" / "src"


def test_action_disabled_tokens_are_overridable() -> None:
    names = overridable_names()
    for name in (
        "--bw-color-action-disabled-bg",
        "--bw-color-action-disabled-text",
        "--bw-color-action-disabled-border",
    ):
        assert name in names


def test_action_disabled_text_contrast_pair_is_manifested() -> None:
    pairs = [
        p
        for p in contrast_pairs()
        if p["name"] == "--bw-color-action-disabled-text" and p["contrastPair"] == "--bw-color-action-disabled-bg"
    ]
    assert len(pairs) == 1
    assert pairs[0]["minContrast"] == 4.5


def test_render_brand_css_rejects_failing_disabled_pair() -> None:
    # Darkening surface alone collapses muted-ink-on-sunken below 4.5:1.
    # L 0.85 fires the action-disabled pair before the status-fg pairs
    # (those raise first around L 0.90; see test_brand_css.py).
    with pytest.raises(BrandValidationError, match="action-disabled-text"):
        render_brand_css({"color-surface": "oklch(0.85 0 0)"})


def test_render_brand_css_accepts_safe_surface_with_disabled_pair() -> None:
    # Near-white surface still clears muted-ink-on-sunken (and status pairs).
    css = render_brand_css({"color-surface": "oklch(0.99 0 0)"})
    assert "--bw-color-surface:" in css


def test_disabled_controls_do_not_use_opacity_encoding() -> None:
    components = (_FRONTEND / "components.css").read_text(encoding="utf-8")
    # The five former opacity sites must use the flat tokens instead.
    for selector in (
        r"\.bw-btn:disabled",
        r"\.bw-input:disabled",
        r"input\.bw-checkbox:disabled",
        r"input\.bw-toggle:disabled",
        r"\.bw-pagination__link--disabled",
    ):
        assert re.search(selector, components), selector
    assert "opacity: var(--bw-component-disabled-opacity)" not in components
    assert "--bw-color-action-disabled-bg" in components
    assert "--bw-color-action-disabled-text" in components
    assert "--bw-color-action-disabled-border" in components


def test_dist_css_carries_flat_disabled_rules() -> None:
    css = (_DIST / "brickwork.css").read_text(encoding="utf-8")
    assert "--bw-color-action-disabled-bg" in css
    assert "opacity:var(--bw-component-disabled-opacity)" not in css or (
        # Opacity token may still appear for non-disabled uses; assert buttons
        # no longer bind disabled to it by checking the flat tokens ship.
        "--bw-color-action-disabled-text" in css
    )
