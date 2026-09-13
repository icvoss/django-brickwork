"""Beat Phase B P0 primitives (icvoss/django-brickwork#542)."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

_ROOT = Path(__file__).resolve().parent.parent
_DIST_CSS = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"


def _render(path: str, **ctx: object) -> str:
    return render_to_string(path, ctx)


# --- divider -----------------------------------------------------------------


def test_divider_default_is_muted_hairline() -> None:
    out = _render("brickwork/components/_divider.html")
    assert 'class="bw-divider bw-divider--tone-muted bw-divider--spacing-md"' in out
    assert 'role="separator"' in out
    assert "bw-divider__label" not in out


def test_divider_labelled_centres_label() -> None:
    out = _render("brickwork/components/_divider.html", label="Or continue with")
    assert "bw-divider--labelled" in out
    assert "Or continue with" in out
    assert 'role="separator"' not in out


def test_divider_invalid_tone_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="tone"):
        _render("brickwork/components/_divider.html", tone="loud")


def test_divider_css_ships_tone_and_spacing() -> None:
    css = _DIST_CSS.read_text(encoding="utf-8")
    assert ".bw-divider--tone-strong" in css
    assert ".bw-divider--spacing-lg" in css
    assert ".bw-divider--labelled" in css


# --- avatar ------------------------------------------------------------------


def test_avatar_initials_default() -> None:
    out = _render("brickwork/components/_avatar.html", initials="NC")
    assert "bw-avatar--size-md" in out
    assert "bw-avatar--shape-circle" in out
    assert "bw-avatar__initials" in out
    assert 'role="img"' in out
    assert 'aria-label="NC"' in out


def test_avatar_image() -> None:
    out = _render(
        "brickwork/components/_avatar.html",
        src="/static/a.jpg",
        alt="Ada Lovelace",
        size="lg",
        shape="square",
    )
    assert 'src="/static/a.jpg"' in out
    assert 'alt="Ada Lovelace"' in out
    assert "bw-avatar--size-lg" in out
    assert "bw-avatar--shape-square" in out


def test_avatar_invalid_shape_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="shape"):
        _render("brickwork/components/_avatar.html", initials="X", shape="hex")


def test_avatar_group_overflow() -> None:
    people = [{"initials": "A"}, {"initials": "B"}, {"initials": "C"}, {"initials": "D"}]
    out = Template("{% load brickwork_components %}{% bw_avatar_group avatars max=3 %}").render(
        Context({"avatars": people})
    )
    assert out.count("bw-avatar--initials") == 2
    assert "bw-avatar--overflow" in out
    assert "+2" in out


# --- chip --------------------------------------------------------------------


def test_chip_default_neutral() -> None:
    out = _render("brickwork/components/_chip.html", label="Open")
    assert "bw-chip--neutral" in out
    assert "bw-chip--size-md" in out
    assert "Open" in out
    assert "<button" not in out


def test_chip_selected_button() -> None:
    out = _render("brickwork/components/_chip.html", label="Paid", selected=True, variant="success")
    assert "bw-chip--selected" in out
    assert 'aria-pressed="true"' in out
    assert "bw-chip--success" in out


def test_chip_dismissible_mounts_bwdismissible() -> None:
    out = _render("brickwork/components/_chip.html", label="Draft", dismissible=True)
    assert 'x-data="bwDismissible()"' in out
    assert "bw-chip__close" in out
    assert "hidden" in out


def test_chip_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="variant"):
        _render("brickwork/components/_chip.html", label="X", variant="error")


def test_chip_rejects_size_lg() -> None:
    with pytest.raises(TemplateSyntaxError, match="size"):
        _render("brickwork/components/_chip.html", label="X", size="lg")


# --- button_group ------------------------------------------------------------


def test_button_group_attached_default() -> None:
    items = [{"label": "Day"}, {"label": "Week", "selected": True}, {"label": "Month"}]
    out = _render(
        "brickwork/components/_button_group.html",
        items=items,
        aria_label="Range",
    )
    assert "bw-button-group--attached" in out
    assert 'role="group"' in out
    assert "bw-btn" in out
    assert 'aria-pressed="true"' in out


def test_button_group_segmented_radiogroup() -> None:
    items = [
        {"label": "List", "selected": True},
        {"label": "Board", "href": "/board/"},
    ]
    out = _render(
        "brickwork/components/_button_group.html",
        items=items,
        variant="segmented",
        aria_label="View",
    )
    assert "bw-button-group--segmented" in out
    assert 'role="radiogroup"' in out
    assert 'role="radio"' in out
    assert 'aria-checked="true"' in out


def test_button_group_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="variant"):
        _render(
            "brickwork/components/_button_group.html",
            items=[{"label": "A"}],
            variant="stacked",
        )


# --- callout -----------------------------------------------------------------


def test_callout_default_note() -> None:
    out = _render(
        "brickwork/components/_callout.html",
        title="Note",
        body="Evaluated in the account timezone.",
    )
    assert "bw-callout--note" in out
    assert "Note" in out
    assert "Evaluated in the account timezone." in out
    assert 'role="alert"' not in out
    assert "aria-live" not in out


@pytest.mark.parametrize("variant", ["note", "info", "success", "warning", "danger", "neutral"])
def test_callout_every_variant_has_css(variant: str) -> None:
    out = _render("brickwork/components/_callout.html", title=variant.title(), variant=variant)
    assert f"bw-callout--{variant}" in out
    css = _DIST_CSS.read_text(encoding="utf-8")
    assert f".bw-callout--{variant}" in css


def test_callout_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="variant"):
        _render("brickwork/components/_callout.html", title="X", variant="tip")


# --- list_item ---------------------------------------------------------------


def test_list_item_title_and_meta() -> None:
    out = _render(
        "brickwork/components/_list_item.html",
        title="Chasing without awkwardness",
        href="/blog/chasing/",
        summary="How to write a reminder.",
        meta="14 July 2026",
        media_src="/static/blog/chasing.jpg",
        media_alt="Invoice on a desk",
    )
    assert "bw-list-item" in out
    assert 'href="/blog/chasing/"' in out
    assert "14 July 2026" in out
    assert 'alt="Invoice on a desk"' in out


def test_list_item_requires_title_in_debug() -> None:
    out = Template(
        '{% include "brickwork/components/_list_item.html" with title="" %}'
    ).render(Context({"bw_debug": True}))
    assert "data-bw-require-warn" in out


# --- marketing_footer_groups -------------------------------------------------


def test_marketing_footer_groups_slugifies_heading_ids() -> None:
    groups = [
        {
            "heading": "Product",
            "links": [{"label": "Features", "href": "/features/"}],
        },
        {
            "heading": "Company",
            "links": [{"label": "About", "href": "/about/"}],
        },
    ]
    out = _render(
        "brickwork_marketing/components/_marketing_footer_groups.html",
        groups=groups,
    )
    assert 'id="footer-product-heading"' in out
    assert 'id="footer-company-heading"' in out
    assert 'href="/features/"' in out
