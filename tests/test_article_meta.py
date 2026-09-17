"""Direct render tests for _article_meta.html (icvoss/django-brickwork#625)."""

from __future__ import annotations

from pathlib import Path

from django.template.loader import render_to_string

_ROOT = Path(__file__).resolve().parent.parent
_DIST_CSS = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_article_meta.html", ctx)


def test_article_meta_byline_matches_editorial_composition() -> None:
    out = _render(
        author_name="Amira Okonkwo",
        author_href="/journal/authors/amira-okonkwo/",
        author_initials="AO",
        published_on="12 August 2026",
        published_iso="2026-08-12",
        reading_time="8 min read",
    )
    assert 'class="bw-article-meta"' in out
    assert "bw-avatar--size-sm" in out
    assert "AO" in out
    assert 'href="/journal/authors/amira-okonkwo/"' in out
    assert "Amira Okonkwo" in out
    assert 'datetime="2026-08-12"' in out
    assert "12 August 2026" in out
    assert "8 min read" in out
    assert 'aria-hidden="true"' in out


def test_article_meta_author_without_href_is_plain_text() -> None:
    out = _render(author_name="Amira Okonkwo", published_on="12 August 2026", reading_time="8 min read")
    assert '<span class="bw-article-meta__author">Amira Okonkwo</span>' in out
    assert "bw-article-meta__author" in out
    assert "href=" not in out.split('class="bw-article-meta"', 1)[1].split("bw-article-meta__date", 1)[0]


def test_article_meta_avatar_from_src() -> None:
    out = _render(
        author_name="Amira Okonkwo",
        author_src="/media/amira.jpg",
        author_alt="Amira Okonkwo",
        published_on="12 August 2026",
        reading_time="8 min read",
    )
    assert 'src="/media/amira.jpg"' in out
    assert 'alt="Amira Okonkwo"' in out


def test_article_meta_optional_tags() -> None:
    out = _render(
        author_name="Amira Okonkwo",
        published_on="12 August 2026",
        reading_time="8 min read",
        tags=[
            {"label": "Operations", "href": "/journal/operations/"},
            {"label": "Reminders"},
        ],
    )
    assert "bw-article-meta__tags" in out
    assert 'href="/journal/operations/"' in out
    assert "Operations" in out
    assert "Reminders" in out
    assert "bw-article-meta__tag-label" in out


def test_article_meta_omits_avatar_date_reading_and_tags_when_absent() -> None:
    out = _render(author_name="Amira Okonkwo")
    assert "bw-article-meta__avatar" not in out
    assert "bw-article-meta__date" not in out
    assert "bw-article-meta__reading-time" not in out
    assert "bw-article-meta__tags" not in out
    assert "Amira Okonkwo" in out


def test_article_meta_css_ships() -> None:
    css = _DIST_CSS.read_text(encoding="utf-8")
    assert ".bw-article-meta" in css
    assert ".bw-article-meta__author" in css
    assert ".bw-article-meta__tags" in css
