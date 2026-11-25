"""Tests for {% bw_notifications %} (brickwork#758)."""

from __future__ import annotations

from django.template import Context, Template


def test_bw_notifications_default_empty_shell() -> None:
    out = Template("{% load brickwork_components %}{% bw_notifications %}").render(Context())
    assert 'class="bw-notifications"' in out
    assert 'class="bw-notifications__trigger"' in out
    assert "bw-notifications__panel" in out
    assert "bw-notifications__empty" in out
    assert "No new notifications" in out
    assert "bw-notifications__count" not in out
    assert "<details" in out
    assert "<summary" in out


def test_bw_notifications_count_badge() -> None:
    out = Template("{% load brickwork_components %}{% bw_notifications count=4 %}").render(Context())
    assert 'class="bw-notifications__count"' in out
    assert ">4<" in out


def test_bw_notifications_zero_count_omits_badge() -> None:
    out = Template("{% load brickwork_components %}{% bw_notifications count=0 %}").render(Context())
    assert "bw-notifications__count" not in out


def test_bw_notifications_custom_label_and_empty() -> None:
    out = Template(
        '{% load brickwork_components %}{% bw_notifications label="Alerts" empty_message="Inbox clear" %}'
    ).render(Context())
    assert 'aria-label="Alerts"' in out
    assert "Inbox clear" in out


def test_bw_notifications_opened_stamps_open() -> None:
    out = Template("{% load brickwork_components %}{% bw_notifications opened=True %}").render(Context())
    assert '<details class="bw-notifications" open>' in out or "open>" in out
