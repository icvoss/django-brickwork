"""{% bw_toc %} / _toc.html contract tests (icvoss/django-brickwork#627).

The tag validates items and marks the active link with aria-current="location".
The template also accepts a bare include with the same items list.
"""

from __future__ import annotations

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

_ITEMS = [
    {"label": "Escalation order", "href": "#escalation-order"},
    {
        "label": "Changing the thresholds",
        "href": "#changing-the-thresholds",
        "children": [
            {"label": "Day offsets", "href": "#day-offsets"},
        ],
    },
    {"label": "Testing a schedule", "href": "#testing-a-schedule"},
]


def _render_tag(
    src: str = "{% bw_toc items=items active=active %}",
    **ctx: object,
) -> str:
    ctx.setdefault("items", _ITEMS)
    ctx.setdefault("active", "")
    return engines["django"].from_string("{% load brickwork_components %}" + src).render(ctx)


def test_floor_is_labelled_docs_toc_nav() -> None:
    html = _render_tag()
    assert 'class="bw-docs-toc"' in html
    assert 'class="bw-docs-toc__title"' in html
    assert 'class="bw-docs-toc__list"' in html
    assert "On this page" in html
    assert 'href="#escalation-order"' in html
    assert 'href="#day-offsets"' in html
    assert 'class="bw-docs-toc__sub"' in html


def test_active_href_marks_aria_current_location() -> None:
    html = _render_tag(active="#testing-a-schedule")
    assert 'aria-current="location"' in html
    assert html.count('aria-current="location"') == 1
    assert 'href="#testing-a-schedule" aria-current="location"' in html


def test_active_bare_id_matches_hash_href() -> None:
    html = _render_tag(active="escalation-order")
    assert 'href="#escalation-order" aria-current="location"' in html
    assert html.count('aria-current="location"') == 1


def test_active_child_marks_sub_entry() -> None:
    html = _render_tag(active="#day-offsets")
    assert 'class="bw-docs-toc__sub"' in html
    assert 'href="#day-offsets" aria-current="location"' in html


def test_custom_heading_and_heading_id() -> None:
    html = _render_tag(
        "{% bw_toc items=items heading='In this article' heading_id='article-toc' %}",
    )
    assert 'id="article-toc"' in html
    assert 'aria-labelledby="article-toc"' in html
    assert "In this article" in html


def test_empty_items_render_nothing() -> None:
    assert "<nav" not in _render_tag(items=[])
    assert "bw-docs-toc" not in _render_tag(items=[])
    assert "<nav" not in render_to_string("brickwork/components/_toc.html", {})


def test_include_path_accepts_items_and_active_href() -> None:
    html = render_to_string(
        "brickwork/components/_toc.html",
        {
            "items": [
                {"label": "Signature", "href": "#signature"},
                {"label": "Parameters", "href": "#parameters"},
            ],
            "active": "#parameters",
            "heading": "On this page",
            "heading_id": "bw-docs-toc-heading",
        },
    )
    assert 'class="bw-docs-toc"' in html
    assert 'href="#parameters" aria-current="location"' in html
    assert html.count('aria-current="location"') == 1


@pytest.mark.parametrize(
    ("src", "ctx", "needle"),
    [
        ("{% bw_toc items=items %}", {"items": "nope"}, "list/tuple"),
        ("{% bw_toc items=items %}", {"items": [{"label": "Only"}]}, "label"),
        (
            "{% bw_toc items=items %}",
            {
                "items": [
                    {
                        "label": "A",
                        "href": "#a",
                        "children": [{"label": "B", "href": "#b", "children": [{"label": "C", "href": "#c"}]}],
                    }
                ]
            },
            "one level of children",
        ),
        (
            "{% bw_toc items=items active='missing' %}",
            {},
            "matched no item",
        ),
    ],
)
def test_invalid_args_raise(src: str, ctx: dict, needle: str) -> None:
    with pytest.raises(TemplateSyntaxError, match=needle):
        _render_tag(src, **ctx)


def _on_star_attrs(html: str) -> list[tuple[str, str]]:
    from html.parser import HTMLParser

    class _Finder(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.found: list[tuple[str, str]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.found.extend((tag, name) for name, _value in attrs if name.startswith("on"))

    parser = _Finder()
    parser.feed(html)
    return parser.found


def test_plain_special_characters_are_escaped() -> None:
    attack = 'Esc"><img src=x onerror=alert(1)>'
    html = _render_tag(
        items=[{"label": attack, "href": "#x"}],
        heading='Title"><img src=x>',
        heading_id='id"><img src=x>',
    )
    assert "<img" not in html
    assert _on_star_attrs(html) == []


def test_mark_safed_heading_cannot_break_out_of_id_attribute() -> None:
    attack = mark_safe('toc" onfocus="alert(1)')
    html = _render_tag(
        "{% bw_toc items=items heading_id=heading_id %}",
        items=[{"label": "A", "href": "#a"}],
        heading_id=attack,
    )
    assert _on_star_attrs(html) == []
