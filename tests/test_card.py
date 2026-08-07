"""Direct render tests for _card.html (0.5.0): regions, variants, density padding.

Covers AC-BW-070 (all five named regions render in document order; a card with
none filled stays a bare elevated surface with no empty child markup), the
class half of AC-BW-071 (the interactive variant class renders when flagged;
the elevation rule itself is asserted against the authored component CSS by
inspection), and AC-BW-072 (card padding composes with the density axis via
--bw-density-card-padding, inspected in the dist tokens).

The card is a structural composition component: its regions are named blocks
(BR-BW-TPL-001 semver-public), so a consumer fills them by extending
_card.html, and includes the extending template where the card should appear.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template import Context, Template
from django.template.loader import render_to_string

_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND = _ROOT / "frontend" / "src"
_DIST = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"

_REGION_CLASSES = [
    "bw-card__header",
    "bw-card__title",
    "bw-card__actions",
    "bw-card__body",
    "bw-card__footer",
]


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_card.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    return Template("{% extends 'brickwork/components/_card.html' %}" + blocks).render(Context(ctx))


def _frontend_css() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(_FRONTEND.glob("*.css")))


def _css_rules(css: str) -> list[tuple[str, str]]:
    """(selector, declarations) pairs; comments stripped, @media bodies flattened."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


# --- AC-BW-070: regions ----------------------------------------------------


def test_all_five_regions_render_in_document_order() -> None:
    out = _extend(
        "{% block card_header %}HEADER-SENTINEL{% endblock %}"
        "{% block card_title %}TITLE-SENTINEL{% endblock %}"
        "{% block card_actions %}ACTIONS-SENTINEL{% endblock %}"
        "{% block card_body %}BODY-SENTINEL{% endblock %}"
        "{% block card_footer %}FOOTER-SENTINEL{% endblock %}"
    )
    positions = [
        out.index("HEADER-SENTINEL"),
        out.index("TITLE-SENTINEL"),
        out.index("ACTIONS-SENTINEL"),
        out.index("BODY-SENTINEL"),
        out.index("FOOTER-SENTINEL"),
    ]
    assert positions == sorted(positions), f"card regions out of document order: {positions}"


def test_bare_card_is_an_elevated_surface_with_no_empty_child_markup() -> None:
    # AC-BW-070: no region filled -> the bw-card root only, no empty region
    # wrappers (the empty-block convention _breadcrumbs.html and the shell's
    # optional blocks already follow).
    out = _render()
    assert "bw-card" in out
    for cls in _REGION_CLASSES:
        assert cls not in out, f"bare card emitted empty region markup: {cls}"


def test_filling_one_region_emits_no_markup_for_the_others() -> None:
    out = _extend("{% block card_body %}BODY-SENTINEL{% endblock %}")
    assert "BODY-SENTINEL" in out
    for cls in ("bw-card__header", "bw-card__title", "bw-card__actions", "bw-card__footer"):
        assert cls not in out, f"unfilled region emitted markup: {cls}"


# --- AC-BW-071 (class contract): the interactive variant --------------------


def test_interactive_flag_adds_the_variant_class() -> None:
    assert "bw-card--interactive" in _render(interactive=True)


def test_card_is_not_interactive_by_default() -> None:
    assert "bw-card--interactive" not in _render()


def test_href_makes_the_card_a_link_and_interactive_by_default() -> None:
    # CMP-017: a clickable card is definitionally hoverable, so interactive
    # defaults to True whenever href is set.
    out = _render(href="/gadgets/1/")
    assert re.search(r'<a[^>]+class="[^"]*bw-card', out), "href did not render an anchor card"
    assert 'href="/gadgets/1/"' in out
    assert "bw-card--interactive" in out


def test_card_without_href_is_not_an_anchor() -> None:
    out = _render()
    assert re.search(r"<a\b", out) is None


def test_bordered_flag_adds_the_variant_class() -> None:
    assert "bw-card--bordered" in _render(bordered=True)
    assert "bw-card--bordered" not in _render()


# --- AC-BW-071 (CSS contract, by inspection of the authored component CSS) --


def test_card_css_rests_at_elevation_1_and_raises_to_2_without_transform() -> None:
    rules = _css_rules(_frontend_css())
    base = [body for sel, body in rules if "bw-card" in sel and "--interactive" not in sel]
    assert any("var(--bw-elevation-1)" in body for body in base), "no .bw-card rule rests at --bw-elevation-1"
    hover = [
        body for sel, body in rules if "bw-card--interactive" in sel and (":hover" in sel or ":focus-within" in sel)
    ]
    assert hover, "no :hover/:focus-within rule for .bw-card--interactive"
    assert any("var(--bw-elevation-2)" in body for body in hover), (
        "the interactive card hover/focus rule does not raise to --bw-elevation-2"
    )
    # MOT-010: shadow/border only, never a transform on the clickable card
    # (text-transform is typography, not motion, and stays permitted).
    for sel, body in rules:
        if "bw-card" in sel:
            assert re.search(r"(?<!text-)transform\s*:", body) is None and "scale(" not in body, (
                f"card rule {sel!r} uses a transform, breaking MOT-010's shadow/border-only rule"
            )


# --- AC-BW-072: padding composes with the density axis ----------------------


def test_density_axis_resolves_card_padding_to_the_documented_values() -> None:
    # DESIGN.md section 6.7: compact 0.75rem / comfortable 1rem / spacious 1.5rem.
    tokens = (_DIST / "tokens.css").read_text(encoding="utf-8")
    for density, value in (("compact", "0.75rem"), ("comfortable", "1rem"), ("spacious", "1.5rem")):
        blocks = re.findall(rf'\[data-density="{density}"\]\s*\{{([^}}]*)\}}', tokens)
        assert any(f"--bw-density-card-padding: {value}" in b for b in blocks), (
            f"[data-density={density}] does not set --bw-density-card-padding to {value}"
        )


def test_card_css_pads_via_the_density_token() -> None:
    rules = _css_rules(_frontend_css())
    card_bodies = [body for sel, body in rules if "bw-card" in sel]
    assert any("var(--bw-density-card-padding)" in body for body in card_bodies), (
        "no card rule composes padding from --bw-density-card-padding"
    )


def test_size_argument_maps_to_modifier_classes() -> None:
    # The card's own size arg composes WITH the density axis (a size step,
    # not an override of the density token). The modifier is emitted only when
    # supplied: the unadorned default pads straight from the density token.
    assert "bw-card--size-sm" in _render(size="sm")
    assert "bw-card--size-lg" in _render(size="lg")
    assert "bw-card--size-" not in _render()
