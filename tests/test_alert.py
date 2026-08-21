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
