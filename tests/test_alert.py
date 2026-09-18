"""Direct render tests for _alert.html's block naming (STA-008/009, ADR-077 SS4).

Covers the deprecated `alert_body` block dual-shipped alongside its concise
successor `body` (BR-BW-VER-001 parallel support): both must render, and an
unfilled body block emits no extra markup.
"""

from __future__ import annotations

from django.template import Context, Template


def _extend(blocks: str, **ctx: object) -> str:
    source = "{% extends 'brickwork/components/_alert.html' %}{% load i18n brickwork_icons %}" + blocks
    return Template(source).render(Context(ctx))


def test_body_block_renders() -> None:
    out = _extend("{% block body %}BODY-SENTINEL{% endblock %}")
    assert "BODY-SENTINEL" in out


def test_deprecated_alert_body_block_still_renders_alone() -> None:
    out = _extend("{% block alert_body %}LEGACY-SENTINEL{% endblock %}")
    assert "LEGACY-SENTINEL" in out


def test_body_and_alert_body_both_render_when_both_are_filled() -> None:
    out = _extend("{% block body %}BODY-SENTINEL{% endblock %}{% block alert_body %}LEGACY-SENTINEL{% endblock %}")
    assert "BODY-SENTINEL" in out
    assert "LEGACY-SENTINEL" in out
    assert out.index("BODY-SENTINEL") < out.index("LEGACY-SENTINEL")


def test_neither_block_filled_emits_no_extra_markup() -> None:
    out = _extend("", variant="info", title="Heads up", message="Something happened.")
    assert "Heads up" in out
    assert "Something happened." in out


# --- icvoss/django-brickwork#476 / ADR-097: include-path variant allow= --------


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


def _include_alert(**ctx: object) -> str:
    from django.template.loader import render_to_string

    return render_to_string("brickwork/components/_alert.html", ctx)


def test_include_path_variant_mark_safed_payload_cannot_break_out() -> None:
    from django.utils.safestring import mark_safe

    attack = mark_safe('a" onclick="alert(1)')
    out = _include_alert(variant=attack, title="t", message="m")
    assert "alert(1)" not in out
    assert _on_star_attrs(out) == []
    # allow= omits the whole class attribute for an out-of-vocab value
    assert "bw-alert--" not in out


def test_include_path_unrecognised_variant_omits_class() -> None:
    out = _include_alert(variant="not-real", title="t", message="m")
    assert "bw-alert--not-real" not in out
    assert "not-real" not in out
    assert "bw-alert--" not in out


def test_include_path_success_variant_still_emits_its_literal() -> None:
    out = _include_alert(variant="success", title="t", message="m")
    assert "bw-alert--success" in out
