"""Tests for _date_picker_chrome.html (icvoss/django-brickwork#628).

Chrome only: labelled field shell, optional range layout, trigger classes,
and a popover panel shell. No calendar engine and no bw_date_picker Alpine
behaviour (BR-BW-INPUT-004).
"""

from __future__ import annotations

import re

from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def _include(**ctx: object) -> str:
    return render_to_string("brickwork/components/_date_picker_chrome.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    source = "{% extends 'brickwork/components/_date_picker_chrome.html' %}{% load brickwork_components %}" + blocks
    return Template(source).render(Context(ctx))


def test_bw_require_warns_when_label_missing_in_debug() -> None:
    out = _include(bw_debug=True)
    assert "data-bw-require-warn" in out
    assert "label" in out


def test_renders_labelled_shell_and_closed_panel() -> None:
    fields = mark_safe(
        '<div class="bw-date-picker-chrome__field">'
        '<input type="date" class="bw-input" id="id_raised" name="raised" '
        'aria-labelledby="bw-dpc-demo-label">'
        '<button type="button" class="bw-date-picker-chrome__trigger" '
        'aria-label="Choose date">Open</button>'
        "</div>"
    )
    out = _include(label="Date raised", id="bw-dpc-demo", fields=fields)
    assert 'class="bw-date-picker-chrome"' in out
    assert 'id="bw-dpc-demo-label"' in out
    assert ">Date raised<" in out
    assert "bw-date-picker-chrome__fields" in out
    assert "bw-date-picker-chrome__field" in out
    assert "bw-date-picker-chrome__trigger" in out
    assert 'role="dialog"' in out
    assert 'aria-modal="true"' in out
    assert 'aria-label="Date raised"' in out
    assert re.search(r'class="bw-date-picker-chrome__panel"[^>]*\bhidden\b', out)


def test_range_layout_wraps_fields() -> None:
    out = _include(
        label="Date raised",
        range=True,
        fields=mark_safe(
            '<div class="bw-date-picker-chrome__field"><input type="date" class="bw-input" '
            'aria-label="Start"></div>'
            '<span class="bw-date-picker-chrome__separator" aria-hidden="true">-</span>'
            '<div class="bw-date-picker-chrome__field"><input type="date" class="bw-input" '
            'aria-label="End"></div>'
        ),
    )
    assert "bw-date-picker-chrome__range" in out
    assert "bw-date-picker-chrome__fields" not in out
    assert "bw-date-picker-chrome__separator" in out


def test_panel_open_and_custom_panel_label() -> None:
    out = _include(
        label="Date raised",
        panel_label="Choose dates",
        panel_open=True,
        panel=mark_safe('<p class="bw-date-picker-chrome__engine">Consumer calendar</p>'),
    )
    assert 'aria-label="Choose dates"' in out
    assert "Consumer calendar" in out
    panel_open_tag = re.search(r'class="bw-date-picker-chrome__panel"[^>]*>', out)
    assert panel_open_tag is not None
    assert "hidden" not in panel_open_tag.group(0)


def test_extends_fills_named_blocks() -> None:
    out = _extend(
        "{% block fields %}<input type='date' class='bw-input' aria-label='Day'>{% endblock %}"
        "{% block panel %}<p>Engine slot</p>{% endblock %}",
        label="Invoice date",
        panel_open=True,
    )
    assert "Invoice date" in out
    assert "Engine slot" in out
    assert "bw-input" in out


def test_help_text_renders_under_control() -> None:
    out = _include(label="Date raised", help_text="Inclusive of both ends.")
    assert "bw-field__help" in out
    assert "Inclusive of both ends." in out


def test_ships_no_date_engine_markers() -> None:
    """Regression: chrome must not grow a package calendar engine."""
    out = _include(label="Date raised", panel_open=True, panel=mark_safe("<p>slot</p>"))
    assert "bwDateRangePicker" not in out
    assert "bw_date_picker" not in out
    assert 'role="grid"' not in out
