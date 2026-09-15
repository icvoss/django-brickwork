"""Render tests for marketing ``_portrait.html`` and ``_bio.html`` (#116)."""

from __future__ import annotations

from django.template import Context, Template
from django.utils.safestring import mark_safe


def _include(path: str, **ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template("{% include '" + path + "' with " + keys + " %}").render(Context(ctx))


_PORTRAIT = "brickwork_marketing/components/_portrait.html"
_BIO = "brickwork_marketing/components/_bio.html"
_IMAGE = mark_safe('<img src="/static/ada.jpg" alt="Ada Lovelace">')


def test_portrait_renders_name_role_body_and_constrained_image() -> None:
    html = _include(
        _PORTRAIT,
        name="Ada Lovelace",
        role="Analytical Engine",
        body="Notes on the Jacquard loom.",
        image=_IMAGE,
        align="start",
    )
    assert "bw-portrait--align-start" in html
    assert "bw-portrait__name" in html
    assert "Ada Lovelace" in html
    assert "bw-portrait__image" in html
    assert 'alt="Ada Lovelace"' in html
    assert "bw-portrait__actions" not in html


def test_portrait_align_end_and_flat_ctas() -> None:
    html = _include(
        _PORTRAIT,
        name="Ada Lovelace",
        image=_IMAGE,
        align="end",
        primary_cta_label="Book a conversation",
        primary_cta_href="/contact/",
        secondary_cta_label="Read more",
        secondary_cta_href="/writing/",
    )
    assert "bw-portrait--align-end" in html
    assert "bw-btn--primary" in html
    assert "bw-btn--secondary" in html
    assert "/contact/" in html


def test_portrait_dict_cta_wins_over_flat() -> None:
    html = _include(
        _PORTRAIT,
        name="Ada",
        primary_cta={"label": "Dict CTA", "url": "/dict/"},
        primary_cta_label="Flat CTA",
        primary_cta_href="/flat/",
    )
    assert "Dict CTA" in html
    assert "/dict/" in html
    assert "Flat CTA" not in html


def test_portrait_empty_collapses() -> None:
    html = Template("{% include '" + _PORTRAIT + "' %}").render(Context({}))
    assert "bw-portrait" not in html
    assert html.strip() == ""


def test_bio_renders_compact_strip_with_profile_link() -> None:
    html = _include(
        _BIO,
        name="Ada Lovelace",
        role="Staff writer",
        body="Writes about computation.",
        image=_IMAGE,
        profile_label="More from Ada",
        profile_href="/authors/ada/",
    )
    assert "bw-bio" in html
    assert "bw-bio__name" in html
    assert "bw-bio__profile-link" in html
    assert "/authors/ada/" in html
    assert "<h2" not in html


def test_bio_dict_profile_wins_over_flat() -> None:
    html = _include(
        _BIO,
        name="Ada",
        profile={"label": "Profile", "url": "/profile/"},
        profile_label="Flat",
        profile_href="/flat/",
    )
    assert "Profile" in html
    assert "/profile/" in html
    assert "Flat" not in html


def test_bio_empty_collapses() -> None:
    html = Template("{% include '" + _BIO + "' %}").render(Context({}))
    assert "bw-bio" not in html
    assert html.strip() == ""
