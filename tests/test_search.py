"""Rendered-contract tests for {% bw_search %} (#155)."""

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError

_TAG = '{% bw_search action="/search/" value="invoice" %}'
_SCOPE = {
    "label": "Project: Acme",
    "name": "project",
    "value": "acme",
    "clear_href": "/search/?q=invoice",
}


def _render(source: str = _TAG, **context: object) -> str:
    return engines["django"].from_string("{% load brickwork_components %}" + source).render(context)


def test_search_is_a_get_form_no_js_floor() -> None:
    html = _render()
    assert '<form class="bw-search" method="get" action="/search/" role="search">' in html
    assert 'type="search" name="q"' in html
    assert 'value="invoice"' in html
    assert 'type="submit"' in html
    assert "hx-" not in html and "x-data" not in html


def test_search_allows_consumer_query_field_configuration() -> None:
    html = _render('{% bw_search action="/find/" name="query" placeholder="Find records" value="quarterly" %}')
    assert 'action="/find/"' in html
    assert 'name="query"' in html
    assert 'placeholder="Find records"' in html
    assert 'value="quarterly"' in html


def test_scope_renders_hidden_field_and_clear_link() -> None:
    html = _render('{% bw_search action="/search/" value="invoice" scope=scope %}', scope=_SCOPE)
    assert 'type="hidden" name="project" value="acme"' in html
    assert "Project: Acme" in html
    assert 'href="/search/?q=invoice"' in html
    assert 'aria-label="Remove Project: Acme search scope"' in html


def test_scope_clear_label_can_be_overridden() -> None:
    scope = {**_SCOPE, "clear_label": "Search every project"}
    html = _render('{% bw_search action="/search/" scope=scope %}', scope=scope)
    assert 'aria-label="Search every project"' in html


@pytest.mark.parametrize(
    "source, message",
    [
        ('{% bw_search action="" %}', "requires action="),
        ('{% bw_search action="/search/" name="" %}', "non-empty name="),
        ('{% bw_search action="/search/" scope="project" %}', "scope= must be a mapping"),
        ('{% bw_search action="/search/" scope=scope %}', "missing required keys"),
    ],
)
def test_invalid_public_arguments_fail_at_render_time(source: str, message: str) -> None:
    context = {"scope": {"label": "Project: Acme"}}
    with pytest.raises(TemplateSyntaxError, match=message):
        _render(source, **context)
