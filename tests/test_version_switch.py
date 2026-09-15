"""{% bw_version_switch %} contract tests (icvoss/django-brickwork#414).

The tag renders a native <details> of plain version links in a labelled
<nav>, with the viewed version named on the trigger and marked
aria-current="true" in the panel. It is navigation, not a menu: no ARIA
menu roles, no Alpine upgrade. Status labels (latest / deprecated) are
visible text.
"""

from __future__ import annotations

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import mark_safe

_VERSIONS = [
    {"label": "3.31.0", "href": "/docs/3.31.0/guides/reminders/", "status": "latest"},
    {"label": "3.30.0", "href": "/docs/3.30.0/guides/reminders/"},
    {"label": "3.28.0", "href": "/docs/3.28.0/guides/reminders/", "status": "deprecated"},
]


def _render(
    src: str = "{% bw_version_switch versions=versions current=current %}",
    **ctx: object,
) -> str:
    ctx.setdefault("versions", _VERSIONS)
    ctx.setdefault("current", "3.31.0")
    return engines["django"].from_string("{% load brickwork_components %}" + src).render(ctx)


def test_floor_is_a_details_disclosure_of_version_links() -> None:
    html = _render()
    assert '<details class="bw-version-switch"' in html
    assert "<summary" in html
    assert 'href="/docs/3.31.0/guides/reminders/"' in html
    assert 'href="/docs/3.30.0/guides/reminders/"' in html
    assert html.count("bw-version-switch__item-label") == 3
    assert html.count('href="/docs/') == 3


def test_no_aria_menu_semantics() -> None:
    html = _render()
    assert 'role="menu"' not in html
    assert 'role="menuitem"' not in html
    assert "aria-haspopup" not in html
    assert "aria-expanded" not in html


def test_trigger_names_the_current_version() -> None:
    html = _render()
    assert 'class="bw-version-switch__label">3.31.0</span>' in html
    assert 'aria-label="Documentation version: 3.31.0"' in html


def test_current_version_carries_aria_current() -> None:
    html = _render()
    assert "bw-version-switch__item--current" in html
    assert 'aria-current="true"' in html
    assert html.count('aria-current="true"') == 1


def test_status_labels_are_visible_text() -> None:
    html = _render()
    assert "Latest" in html
    assert "Deprecated" in html
    assert "bw-version-switch__status" in html


def test_placement_end_modifier() -> None:
    html = _render("{% bw_version_switch versions=versions current=current placement='end' %}")
    assert "bw-version-switch--end" in html


def test_custom_landmark_label() -> None:
    html = _render("{% bw_version_switch versions=versions current=current label='API version' %}")
    assert 'aria-label="API version: 3.31.0"' in html
    assert 'aria-label="API version"' in html


@pytest.mark.parametrize(
    ("src", "ctx", "needle"),
    [
        ("{% bw_version_switch versions=versions current='' %}", {}, "non-empty current="),
        ("{% bw_version_switch versions=versions current='9.9.9' %}", {}, "exactly one version label"),
        ("{% bw_version_switch versions=versions current=current %}", {"versions": []}, "non-empty list/tuple"),
        (
            "{% bw_version_switch versions=versions current=current %}",
            {"versions": [{"label": "3.31.0"}]},
            "label",
        ),
        (
            "{% bw_version_switch versions=versions current=current %}",
            {"versions": [{"label": "3.31.0", "href": "/x/", "status": "beta"}]},
            "status must be one of",
        ),
        (
            "{% bw_version_switch versions=versions current=current placement='middle' %}",
            {},
            "placement must be one of",
        ),
    ],
)
def test_invalid_args_raise(src: str, ctx: dict, needle: str) -> None:
    with pytest.raises(TemplateSyntaxError, match=needle):
        _render(src, **ctx)


def _on_star_attrs(html: str) -> list[tuple[str, str]]:
    """Return every live on* attribute name (not escaped text inside values)."""
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
    attack = '3.0"><img src=x onerror=alert(1)>'
    html = _render(
        "{% bw_version_switch versions=versions current=current label=label %}",
        versions=[{"label": attack, "href": "/docs/"}],
        current=attack,
        label='Docs"><img src=x>',
    )
    assert "<img" not in html
    assert _on_star_attrs(html) == []


def test_mark_safed_values_cannot_break_out_of_aria_attributes() -> None:
    # Attribute position must not honour SafeData (#349). Text position may
    # still render trusted markup; the gate is that no live on* attribute lands.
    attack = mark_safe('3.0" onfocus="alert(1)')
    html = _render(
        "{% bw_version_switch versions=versions current=current label=label %}",
        versions=[{"label": "3.31.0", "href": "/docs/"}],
        current="3.31.0",
        label=attack,
    )
    assert _on_star_attrs(html) == []
    assert "onfocus=" not in html.split(">", 1)[0]  # not on the opening details tag
