"""Render tests for marketing ``_directory.html`` (#647)."""

from __future__ import annotations

from django.template import Context, Template
from django.utils.safestring import mark_safe


def _include(**ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template("{% include 'brickwork_marketing/components/_directory.html' with " + keys + " %}").render(
        Context(ctx)
    )


def test_directory_with_items_renders_ordered_entries() -> None:
    html = _include(
        heading="Packages",
        items=[
            {
                "number": "01",
                "icon": "folder",
                "heading": "django-brickwork",
                "url": "/packages/django-brickwork/",
                "body": "The professional UI substrate.",
                "version": "3.34.0",
                "status": "Stable",
                "install": "pip install django-brickwork",
            },
            {
                "heading": "django-icv-core",
                "body": "Shared model base and helpers.",
            },
        ],
    )
    assert "bw-directory-section" in html
    assert "<ol" in html and "bw-directory" in html
    assert "bw-directory__number" in html
    assert "01" in html
    assert "2" in html  # loop counter for the second item
    assert 'href="/packages/django-brickwork/"' in html
    assert "bw-directory__link" in html
    assert "django-brickwork" in html
    assert "django-icv-core" in html
    assert "3.34.0" in html
    assert "Stable" in html
    assert "<code" in html and "pip install django-brickwork" in html
    assert "bw-directory__item--mark" in html
    assert "bw-directory__item--meta" in html


def test_directory_empty_items_renders_intro_alone() -> None:
    html = _include(heading="Packages", lede="Public packages only.")
    assert "bw-directory-section__heading" in html
    assert "Packages" in html
    assert "Public packages only." in html
    assert "<ol" not in html
    assert "bw-directory__item" not in html


def test_directory_fully_empty_renders_nothing() -> None:
    html = Template("{% include 'brickwork_marketing/components/_directory.html' %}").render(Context({}))
    assert "bw-directory" not in html


def test_directory_omits_absent_optional_fields() -> None:
    html = _include(items=[{"heading": "Solo entry", "body": "Just a title and body."}])
    assert "bw-directory__mark" not in html
    assert "bw-directory__meta" not in html
    assert "bw-directory__link" not in html
    assert "<a " not in html
    assert "Solo entry" in html


def test_directory_logo_preferred_over_icon() -> None:
    logo = mark_safe('<img src="/logo.svg" alt="">')
    html = _include(
        items=[
            {
                "heading": "With logo",
                "icon": "folder",
                "logo": logo,
            }
        ]
    )
    assert 'src="/logo.svg"' in html
    assert "bw-directory__icon" not in html


def test_directory_title_without_url_is_plain_text() -> None:
    html = _include(items=[{"heading": "Unlinked", "url": ""}])
    # Empty url is falsy: no anchor.
    assert "bw-directory__link" not in html
    assert "Unlinked" in html
