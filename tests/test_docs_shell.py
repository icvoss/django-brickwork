"""Render tests for the docs shell (`brickwork/shell/docs.html`, ADR-091,
icvoss/django-brickwork#439).

BR-BW-PAGE-002 at docs scope: the docs shell renders a complete valid
document with nothing but its own blocks, and every block empties
gracefully. These tests mirror test_marketing.py's region coverage exactly
(the `*_region` wrapper-block idiom from #263/#434), plus the one constraint
unique to this shell and normative under ADR-091 decision 3: content
(the article) must precede the nav rail in document order.
"""

from __future__ import annotations

from django.template import Context, Template
from django.template.loader import render_to_string

_DOCS_SHELL = "brickwork/shell/docs.html"


def _render(template: str, **ctx: object) -> str:
    return render_to_string(template, ctx)


def _extend(parent: str, blocks: str, **ctx: object) -> str:
    return Template("{% extends '" + parent + "' %}" + blocks).render(Context(ctx))


def _assert_complete_document(html: str) -> None:
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert 'id="bw-main"' in html


# --- shell/docs.html: empty-graceful + chrome (BR-BW-PAGE-002 at docs scope) -


def test_the_docs_shell_with_no_blocks_filled_renders_a_complete_document() -> None:
    html = _extend(_DOCS_SHELL, "")
    _assert_complete_document(html)


def test_the_docs_shell_carries_its_own_chrome_not_another_shell_s() -> None:
    html = _extend(_DOCS_SHELL, "")
    assert "bw-docs" in html
    assert "bw-docs-layout" in html
    # never the app shell's or the marketing shell's own chrome
    assert "bw-sidebar" not in html
    assert "bw-topbar" not in html
    assert "bw-app" not in html
    assert "bw-marketing" not in html


def test_the_docs_shell_main_appears_exactly_once() -> None:
    html = _extend(_DOCS_SHELL, "")
    assert html.count('id="bw-main"') == 1


def test_the_docs_shell_content_block_lands_inside_the_main_region() -> None:
    html = _extend(_DOCS_SHELL, "{% block content %}CONTENT-SENTINEL{% endblock %}")
    main_start = html.index('id="bw-main"')
    assert main_start < html.index("CONTENT-SENTINEL")


# --- ADR-091 decision 3: source order is normative (content before nav) -----


def test_content_precedes_the_nav_rail_in_source_order() -> None:
    # The ADR's binding constraint: a docs page must emit article-then-rail so
    # the article's own heading is reachable before the rail on every
    # viewport (a real consumer accessibility defect this shell must not
    # reintroduce). `order: -1` in shell.css restores the rail to the visual
    # inline-start at the layout breakpoint; this test pins DOM order, which
    # `order` never changes.
    html = _extend(
        _DOCS_SHELL,
        "{% block content %}CONTENT-SENTINEL{% endblock %}{% block docs_nav %}NAV-SENTINEL{% endblock %}",
    )
    assert html.index("CONTENT-SENTINEL") < html.index("NAV-SENTINEL")


def test_content_precedes_the_nav_region_wrapper_itself_in_source_order() -> None:
    # Even when the rail wrapper is inspected rather than its inner block, the
    # <details> element itself must still follow the article in the DOM.
    html = _extend(
        _DOCS_SHELL,
        "{% block content %}CONTENT-SENTINEL{% endblock %}",
    )
    assert html.index("CONTENT-SENTINEL") < html.index("bw-docs-layout__nav")


# --- shell/docs.html: *_region wrapper blocks (ADR-091 decision 2) ----------


def test_filling_only_the_inner_blocks_is_unaffected_by_the_region_wrappers() -> None:
    html = _extend(
        _DOCS_SHELL,
        "{% block docs_header %}HEADER-SENTINEL{% endblock %}"
        "{% block content %}CONTENT-SENTINEL{% endblock %}"
        "{% block docs_footer %}FOOTER-SENTINEL{% endblock %}"
        "{% block docs_nav %}NAV-SENTINEL{% endblock %}",
    )
    assert '<div class="bw-docs-layout__header">' in html
    assert '<footer class="bw-docs-layout__footer">' in html
    assert '<details class="bw-docs-layout__nav">' in html
    header_start = html.index('class="bw-docs-layout__header"')
    header_sentinel = html.index("HEADER-SENTINEL")
    content_sentinel = html.index("CONTENT-SENTINEL")
    footer_start = html.index('class="bw-docs-layout__footer"')
    footer_sentinel = html.index("FOOTER-SENTINEL")
    nav_start = html.index('class="bw-docs-layout__nav"')
    nav_sentinel = html.index("NAV-SENTINEL")
    assert header_start < header_sentinel < content_sentinel < footer_start < footer_sentinel < nav_start < nav_sentinel


def test_overriding_docs_header_region_replaces_the_header_wrapper() -> None:
    html = _extend(
        _DOCS_SHELL,
        '{% block docs_header_region %}<div id="header-region-replacement">HEADER-SENTINEL</div>{% endblock %}',
    )
    assert '<div id="header-region-replacement">' in html
    assert "bw-docs-layout__header" not in html
    assert "HEADER-SENTINEL" in html


def test_overriding_docs_footer_region_replaces_the_footer_wrapper() -> None:
    html = _extend(
        _DOCS_SHELL,
        '{% block docs_footer_region %}<div id="footer-region-replacement">FOOTER-SENTINEL</div>{% endblock %}',
    )
    assert '<div id="footer-region-replacement">' in html
    assert "bw-docs-layout__footer" not in html
    assert "FOOTER-SENTINEL" in html


def test_overriding_docs_nav_region_replaces_the_nav_wrapper() -> None:
    html = _extend(
        _DOCS_SHELL,
        '{% block docs_nav_region %}<div id="nav-region-replacement">NAV-SENTINEL</div>{% endblock %}',
    )
    assert '<div id="nav-region-replacement">' in html
    assert "bw-docs-layout__nav" not in html
    assert "<details" not in html
    assert "NAV-SENTINEL" in html


def test_overriding_docs_header_region_empty_removes_the_header_and_its_chrome() -> None:
    html = _extend(
        _DOCS_SHELL,
        "{% block docs_header_region %}{% endblock %}{% block content %}CONTENT-SENTINEL{% endblock %}",
    )
    assert "bw-docs-layout__header" not in html
    assert "CONTENT-SENTINEL" in html


def test_overriding_docs_footer_region_empty_removes_the_footer_and_its_chrome() -> None:
    # The capability filling the inner block alone can never offer: the
    # <footer> element itself is gone, not merely empty.
    html = _extend(
        _DOCS_SHELL,
        "{% block content %}CONTENT-SENTINEL{% endblock %}{% block docs_footer_region %}{% endblock %}",
    )
    assert "bw-docs-layout__footer" not in html
    assert "<footer" not in html
    assert "CONTENT-SENTINEL" in html
    _assert_complete_document(html)


def test_overriding_docs_nav_region_empty_removes_the_nav_and_its_chrome() -> None:
    # The capability filling the inner block alone can never offer: the
    # <details>/<nav> landmark itself is gone, not merely empty. content still
    # renders, proving the removal is scoped to the nav region only.
    html = _extend(
        _DOCS_SHELL,
        "{% block content %}CONTENT-SENTINEL{% endblock %}{% block docs_nav_region %}{% endblock %}",
    )
    assert "bw-docs-layout__nav" not in html
    assert "<details" not in html
    assert "<nav" not in html
    assert "CONTENT-SENTINEL" in html
    _assert_complete_document(html)


# --- Accessibility: the nav rail carries a labelled landmark by default -----


def test_the_nav_rail_carries_an_aria_label_by_default() -> None:
    html = _extend(_DOCS_SHELL, "{% block docs_nav %}NAV-SENTINEL{% endblock %}")
    assert '<nav class="bw-docs-layout__nav-body" aria-label="Documentation">' in html


def test_the_docs_shell_declines_toc_version_and_feedback_regions() -> None:
    # ADR-091 decision 2: three asks are declined with reasons, not shipped as
    # empty inert seams (the icvoss/django-brickwork#438 pattern). No such
    # block names exist to fill.
    html = _extend(
        _DOCS_SHELL,
        "{% block toc %}TOC-SENTINEL{% endblock %}"
        "{% block version %}VERSION-SENTINEL{% endblock %}"
        "{% block feedback %}FEEDBACK-SENTINEL{% endblock %}",
    )
    # Django silently discards a block name the parent does not define
    # (brickwork#193): none of these sentinels render anywhere.
    assert "TOC-SENTINEL" not in html
    assert "VERSION-SENTINEL" not in html
    assert "FEEDBACK-SENTINEL" not in html
