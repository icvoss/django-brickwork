"""DEBUG-only required-context checks for include-only templates (#482)."""

from __future__ import annotations

from django.template import Context, Template
from django.template.loader import render_to_string


def test_bw_require_emits_nothing_when_debug_is_off() -> None:
    html = Template("{% load brickwork_components %}{% bw_require title=title %}").render(
        Context({"bw_debug": False, "title": ""})
    )
    assert html == ""
    assert "data-bw-require-warn" not in html


def test_bw_require_emits_nothing_when_values_are_present() -> None:
    html = Template("{% load brickwork_components %}{% bw_require title=title %}").render(
        Context({"bw_debug": True, "title": "Invoices"})
    )
    assert html == ""


def test_bw_require_warns_when_a_required_string_is_empty() -> None:
    html = Template("{% load brickwork_components %}{% bw_require title=title %}").render(
        Context({"bw_debug": True, "title": "   "})
    )
    assert "data-bw-require-warn" in html
    assert "console.warn" in html
    assert "title" in html
    assert "DEBUG is on" in html


def test_bw_require_warns_when_a_required_mapping_is_empty() -> None:
    html = Template("{% load brickwork_components %}{% bw_require crumbs=crumbs %}").render(
        Context({"bw_debug": True, "crumbs": []})
    )
    assert "crumbs" in html
    assert "data-bw-require-warn" in html


def test_bw_require_treats_false_and_zero_as_present() -> None:
    html = Template("{% load brickwork_components %}{% bw_require flag=flag count=count %}").render(
        Context({"bw_debug": True, "flag": False, "count": 0})
    )
    assert html == ""


def test_page_header_warns_in_debug_when_title_is_missing() -> None:
    html = render_to_string("brickwork/components/_page_header.html", {"bw_debug": True})
    assert "data-bw-require-warn" in html
    assert "title" in html


def test_page_header_is_quiet_when_title_is_supplied() -> None:
    html = render_to_string(
        "brickwork/components/_page_header.html",
        {"bw_debug": True, "title": "Invoices"},
    )
    assert "data-bw-require-warn" not in html
    assert "Invoices" in html


def test_page_header_is_quiet_in_production_even_without_title() -> None:
    html = render_to_string("brickwork/components/_page_header.html", {"bw_debug": False})
    assert "data-bw-require-warn" not in html


def test_empty_state_requires_body_at_every_size() -> None:
    html = render_to_string(
        "brickwork/components/_empty_state.html",
        {"bw_debug": True, "heading": "Nothing yet", "size": "md"},
    )
    assert "data-bw-require-warn" in html
    assert "body" in html


def test_empty_state_skips_heading_require_at_size_sm() -> None:
    html = render_to_string(
        "brickwork/components/_empty_state.html",
        {"bw_debug": True, "body": "Try another filter.", "size": "sm"},
    )
    assert "data-bw-require-warn" not in html
