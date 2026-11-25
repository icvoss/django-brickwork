"""Rendered-contract tests for {% bw_command %} (icvoss/django-brickwork#156)."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import mark_safe

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_ITEMS = (
    {"label": "Dashboard", "href": "/app/", "group": "Navigation", "hint": "Home"},
    {"label": "Settings", "url": "/settings/", "group": "Navigation"},
    {"label": "New project", "href": "/projects/new/", "group": "Actions", "keywords": "create"},
)


def _render(source: str = "", **context: object) -> str:
    if not source:
        source = "{% bw_command items=items action='/search/' %}"
    return engines["django"].from_string("{% load brickwork_components %}" + source).render(context)


def test_command_uses_kit_cmdk_chrome_and_alpine_hook() -> None:
    html = _render(items=_ITEMS)
    assert 'class="bw-cmdk"' in html
    assert 'class="bw-cmdk__scrim"' in html
    assert 'class="bw-cmdk__panel"' in html
    assert 'class="bw-cmdk__input"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'aria-hidden="true"' in html
    assert 'x-data="bwCommand(' in html
    assert 'x-trap.inert.noscroll="isOpen"' in html
    assert "data-bw-open" not in html  # closed until JS opens it


def test_items_render_grouped_with_href_and_url_alias() -> None:
    html = _render(items=_ITEMS)
    assert "bw-cmdk__group-label" in html
    assert "Navigation" in html
    assert "Actions" in html
    assert 'data-bw-href="/app/"' in html
    assert 'data-bw-href="/settings/"' in html
    assert 'data-bw-href="/projects/new/"' in html
    assert 'data-bw-keywords="create"' in html
    assert "Home" in html


def test_action_ships_a_hidden_search_row_tied_to_bw_search_surface() -> None:
    html = _render(items=_ITEMS)
    assert "data-bw-command-search" in html
    assert "data-bw-command-search-template" in html
    assert "bwCommand(" in html and "/search/" in html
    assert "name:" in html and "'q'" in html.replace("\\u0027", "'").replace("&#x27;", "'")


def test_without_action_there_is_no_search_row() -> None:
    html = _render("{% bw_command items=items %}", items=_ITEMS)
    assert "data-bw-command-search" not in html


def test_empty_items_still_render_the_palette_shell() -> None:
    html = _render("{% bw_command %}")
    assert 'class="bw-cmdk"' in html
    assert "bw-cmdk__empty" in html


@pytest.mark.parametrize(
    "source, message, context",
    [
        ('{% bw_command items="nope" %}', "list or tuple", {}),
        ("{% bw_command items=items %}", "mappings", {"items": ["x"]}),
        ("{% bw_command items=items %}", 'non-empty "label"', {"items": [{"href": "/x/"}]}),
        ("{% bw_command items=items %}", "href", {"items": [{"label": "X"}]}),
        ('{% bw_command items=items name="" %}', "non-empty name=", {"items": _ITEMS}),
    ],
)
def test_invalid_public_arguments_fail_at_render_time(source: str, message: str, context: dict) -> None:
    with pytest.raises(TemplateSyntaxError, match=message):
        _render(source, **context)


ATTACK = mark_safe('a" onclick="alert(1)')


def _on_star_attrs(html: str) -> list[tuple[str, str]]:
    class _Finder(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.found: list[tuple[str, str]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.found.extend((tag, name) for name, _value in attrs if name.startswith("on"))

    parser = _Finder()
    parser.feed(html)
    return parser.found


def test_consumer_supplied_item_values_cannot_break_out_of_attributes() -> None:
    items = (
        {
            "label": "Safe",
            "href": ATTACK,
            "hint": ATTACK,
            "keywords": ATTACK,
            "group": ATTACK,
        },
    )
    html = _render("{% bw_command items=items %}", items=items)
    assert _on_star_attrs(html) == []


def test_bundle_registers_bw_command() -> None:
    bundle = _DIST_JS.read_text()
    assert 'Alpine.data("bwCommand"' in bundle or "bwCommand" in bundle
    assert "bw:command:open" in bundle
    assert "bw:command:close" in bundle
    assert "bw:command:select" in bundle
