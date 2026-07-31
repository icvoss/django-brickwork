"""Breadcrumbs component tests (#25).

Renders the shipped _breadcrumbs.html include directly (no testapp needed). The
contract: the LAST crumb is the current page and is NEVER a link (it carries
aria-current="page" even if the caller supplied a url); intermediate crumbs link
when they carry a url and render as plain text when they do not.
"""

from __future__ import annotations

from django.template.loader import render_to_string


def _render(crumbs: list[dict]) -> str:
    return render_to_string("brickwork/components/_breadcrumbs.html", {"crumbs": crumbs})


def test_last_crumb_is_unlinked_current_page_even_with_a_url() -> None:
    html = _render(
        [
            {"label": "Home", "url": "/"},
            {"label": "Widgets", "url": "/widgets/"},
        ]
    )
    assert '<span class="bw-breadcrumbs__current" aria-current="page">Widgets</span>' in html
    # the current page is never a link, even though the crumb carries a url
    assert 'href="/widgets/"' not in html


def test_intermediate_crumb_without_url_renders_plain_text() -> None:
    html = _render(
        [
            {"label": "Home", "url": "/"},
            {"label": "Section"},
            {"label": "Current"},
        ]
    )
    assert '<span class="bw-breadcrumbs__text">Section</span>' in html
    # the unlinked intermediate crumb is not the current page
    assert html.count('aria-current="page"') == 1


def test_url_carrying_crumbs_render_links() -> None:
    html = _render(
        [
            {"label": "Home", "url": "/"},
            {"label": "Widgets", "url": "/widgets/"},
            {"label": "Alpha"},
        ]
    )
    assert '<a class="bw-breadcrumbs__link" href="/">Home</a>' in html
    assert '<a class="bw-breadcrumbs__link" href="/widgets/">Widgets</a>' in html
    assert '<span class="bw-breadcrumbs__current" aria-current="page">Alpha</span>' in html


def test_semantic_ordered_list_structure() -> None:
    html = _render([{"label": "Home", "url": "/"}, {"label": "Now"}])
    assert '<ol class="bw-breadcrumbs__list">' in html
    assert html.count('<li class="bw-breadcrumbs__item">') == 2


def test_no_crumbs_renders_nothing() -> None:
    # An empty or absent crumbs list renders NO <ol> at all, so the shell's
    # :empty suppression collapses the breadcrumbs region.
    assert "<ol" not in _render([])
    assert "<ol" not in render_to_string("brickwork/components/_breadcrumbs.html", {})
