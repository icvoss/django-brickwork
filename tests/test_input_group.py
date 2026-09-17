"""Direct render tests for _input_group.html (icvoss/django-brickwork#624)."""

from __future__ import annotations

from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def _control(**attrs: str) -> str:
    """A marked-safe bw-input stand-in (real call sites pass SafeString widgets)."""
    parts = " ".join(f'{key}="{value}"' for key, value in attrs.items())
    return mark_safe(f'<input class="bw-input" {parts}>')


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_input_group.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    source = "{% extends 'brickwork/components/_input_group.html' %}{% load brickwork_icons %}" + blocks
    return Template(source).render(Context(ctx))


def test_prefix_text_wraps_slotted_field() -> None:
    out = _render(prefix="£", field=_control(type="text", id="id_amount", name="amount"))
    assert 'class="bw-input-group"' in out
    assert 'role="group"' in out
    assert "bw-input-group__addon--prefix" in out
    assert "£" in out
    assert 'id="id_amount"' in out
    assert "bw-input-group__addon--suffix" not in out


def test_suffix_text_and_prefix_icon() -> None:
    out = _render(
        prefix_icon="search",
        suffix=".com",
        field=_control(type="text", name="domain"),
    )
    assert "bw-input-group__addon--prefix" in out
    assert "bw-input-group__addon--suffix" in out
    assert "bw-input-group__icon" in out
    assert ".com" in out
    assert 'aria-hidden="true"' in out


def test_field_block_override_replaces_context_field() -> None:
    out = _extend(
        '{% block field %}<input class="bw-input" id="block-field" type="text">{% endblock %}',
        prefix="https://",
        field=mark_safe('<input id="ctx-field">'),
    )
    assert 'id="block-field"' in out
    assert "ctx-field" not in out
    assert "https://" in out


def test_prefix_block_override_replaces_default_addon() -> None:
    out = _extend(
        '{% block prefix %}<span class="custom-prefix">CUSTOM</span>{% endblock %}'
        '{% block field %}<input class="bw-input" type="text">{% endblock %}',
        prefix="£",
    )
    assert "CUSTOM" in out
    assert "bw-input-group__addon--prefix" not in out


def test_aria_label_emitted_when_supplied() -> None:
    out = _render(
        prefix="£",
        aria_label="Amount in pounds",
        field=_control(type="text"),
    )
    assert 'aria-label="Amount in pounds"' in out


def test_addons_are_aria_hidden() -> None:
    out = _render(prefix="£", suffix="GBP", field=_control(type="text"))
    assert out.count('aria-hidden="true"') >= 2
