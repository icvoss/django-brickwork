"""Brickwork Theme level checker (ADR-110 / Phase C)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from brickwork.services.brand_css import BrandValidationError, render_brand_css
from brickwork.services.theme_profile import (
    L1_REQUIRED,
    L2_FONTS,
    L3_RADIUS,
    check_theme_level,
    infer_theme_level,
    kit_owned_present,
    parse_level,
    recommended_tokens_for_level,
)

_REPO = Path(__file__).resolve().parent.parent
_PACK = _REPO / "docs" / "examples" / "brand-pack"

_CUSTOM_PROP_RE = re.compile(r"(--bw-[a-z0-9-]+)\s*:")


def _names_from_tokens_css(path: Path) -> frozenset[str]:
    return frozenset(_CUSTOM_PROP_RE.findall(path.read_text(encoding="utf-8")))


_L1_COLOURS = {
    # Near package defaults so derived status pairs stay AA under validate=True.
    "--bw-color-surface": "oklch(1 0 0)",
    "--bw-color-fg": "oklch(0.205 0.005 265)",
    "--bw-color-border": "oklch(0.90 0.01 240)",
    "--bw-color-accent": "oklch(0.42 0.11 330)",
    "--bw-color-danger": "oklch(0.55 0.18 25)",
    "--bw-color-success": "oklch(0.56 0.13 155)",
    "--bw-color-warning": "oklch(0.70 0.14 75)",
    "--bw-color-fg-on-accent": "oklch(1 0 0)",
}

_L2_FONTS_VALUES = {
    "--bw-font-family-sans": '"Source Sans 3", system-ui, sans-serif',
    "--bw-font-family-display": '"Source Serif 4", Georgia, serif',
    "--bw-font-family-mono": '"IBM Plex Mono", ui-monospace, monospace',
}


def test_infer_empty_is_l0() -> None:
    assert infer_theme_level([]) == "L0"


def test_infer_colours_only_is_l1() -> None:
    assert infer_theme_level(L1_REQUIRED) == "L1"


def test_infer_colours_plus_fonts_is_l2() -> None:
    assert infer_theme_level(L1_REQUIRED | L2_FONTS) == "L2"


def test_infer_l3_via_radius() -> None:
    names = L1_REQUIRED | L2_FONTS | L3_RADIUS
    assert infer_theme_level(names) == "L3"


def test_infer_l3_via_surface_raised_alone() -> None:
    names = L1_REQUIRED | L2_FONTS | {"--bw-color-surface-raised"}
    assert infer_theme_level(names) == "L3"


def test_infer_l4_via_space_1() -> None:
    names = L1_REQUIRED | L2_FONTS | L3_RADIUS | {"--bw-space-1"}
    assert infer_theme_level(names) == "L4"


def test_infer_l4_via_density_default_flag() -> None:
    names = L1_REQUIRED | L2_FONTS | L3_RADIUS
    assert infer_theme_level(names, has_density_default=True) == "L4"


def test_infer_l4_via_density_tokens() -> None:
    names = L1_REQUIRED | L2_FONTS | L3_RADIUS | {"--bw-density-card-padding"}
    assert infer_theme_level(names) == "L4"


def test_colours_only_claiming_l3_fails() -> None:
    report = check_theme_level("L3", L1_REQUIRED)
    assert report.ok is False
    assert report.evidenced == "L1"
    assert report.claimed == "L3"
    assert "--bw-radius-sm" in report.missing_for_claim
    assert "evidenced L1" in report.message


def test_l2_claim_ok_for_northline_shape() -> None:
    report = check_theme_level("L2", L1_REQUIRED | L2_FONTS)
    assert report.ok is True
    assert report.evidenced == "L2"


def test_kit_owned_does_not_evidence_level() -> None:
    names = L1_REQUIRED | {"--bw-z-modal", "--bw-duration-fast", "--bw-opacity-muted"}
    assert infer_theme_level(names) == "L1"
    kit = kit_owned_present(names)
    assert "--bw-z-modal" in kit
    report = check_theme_level("L1", names)
    assert report.ok is True
    assert report.kit_owned == kit


def test_short_token_names_normalise() -> None:
    short = [
        "color-surface",
        "color-fg",
        "color-border",
        "color-accent",
        "color-danger",
        "color-success",
        "color-warning",
        "color-fg-on-accent",
    ]
    assert infer_theme_level(short) == "L1"


def test_parse_level() -> None:
    assert parse_level("l3") == "L3"
    with pytest.raises(ValueError, match="unknown theme level"):
        parse_level("L9")


def test_recommended_tokens_nest() -> None:
    assert recommended_tokens_for_level("L1") < recommended_tokens_for_level("L2")
    assert "--bw-space-1" in recommended_tokens_for_level("L4")


def test_render_brand_css_accepts_l3_material_values() -> None:
    """Emitter already validates L2 to L4 overridable values (Phase C sibling)."""
    css = render_brand_css(
        {
            **_L1_COLOURS,
            **_L2_FONTS_VALUES,
            "--bw-radius-sm": "0.5rem",
            "--bw-radius-md": "0.875rem",
            "--bw-radius-lg": "1.25rem",
            "--bw-elevation-1": "0 2px 4px 0 oklch(0 0 0 / 0.08)",
            "--bw-elevation-2": "0 6px 12px -2px oklch(0 0 0 / 0.14)",
            "--bw-elevation-3": "0 16px 28px -6px oklch(0 0 0 / 0.18)",
            "--bw-color-surface-raised": "oklch(1 0.002 240)",
        }
    )
    assert "--bw-radius-md:" in css
    assert "--bw-elevation-2:" in css
    assert "--bw-font-family-sans:" in css


def test_render_brand_css_still_rejects_unknown_names() -> None:
    with pytest.raises(BrandValidationError, match="unknown brickwork token"):
        render_brand_css({**_L1_COLOURS, "--bw-not-a-token": "0.5rem"})


@pytest.mark.parametrize(
    ("slug", "claimed", "density_default"),
    [
        ("northline", "L2", False),
        ("harbour", "L2", False),
        ("folio", "L2", False),
        ("northline-material", "L3", False),
        ("northline-dense", "L4", True),
    ],
)
def test_example_packs_evidence_their_claimed_level(slug: str, claimed: str, density_default: bool) -> None:
    names = _names_from_tokens_css(_PACK / slug / "tokens.css")
    report = check_theme_level(claimed, names, has_density_default=density_default)  # type: ignore[arg-type]
    assert report.ok, report.message
    assert report.evidenced == claimed
