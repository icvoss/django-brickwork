"""Regression tests for ``tests/_encoding_contract.py`` helper defects (#303)."""

from __future__ import annotations

import pytest

from tests._encoding_contract import (
    assert_no_progressbar_semantics,
    assert_ordered_list_element_survives_stripping,
)


def test_ordered_list_helper_finds_a_root_with_modifier_classes() -> None:
    html = '<ol class="bw-ranked-list bw-ranked-list--compact"><li>x</li></ol>'
    assert_ordered_list_element_survives_stripping(html, list_class="bw-ranked-list")


def test_ordered_list_helper_rejects_a_demoted_root_even_when_a_decoy_ol_exists() -> None:
    html = '<ol class="bw-ranked-list"><li>decoy</li></ol><div class="bw-ranked-list"><li>real rows</li></div>'
    with pytest.raises(AssertionError, match="not an <ol>"):
        assert_ordered_list_element_survives_stripping(html, list_class="bw-ranked-list")


def test_aria_value_substring_in_href_does_not_false_fail() -> None:
    html = (
        '<ol class="bw-ranked-list">'
        '<div class="bw-ranked-list__row"><a href="/dash/aria-valuetext-report/">x</a></div>'
        "</ol>"
    )
    assert_no_progressbar_semantics(html, component_tag="ol", component_class="bw-ranked-list")


def test_aria_value_substring_in_visible_label_text_does_not_false_fail() -> None:
    html = (
        '<ol class="bw-ranked-list">'
        '<div class="bw-ranked-list__row">'
        '<span class="bw-ranked-list__label">Migrating to aria-valuemax</span>'
        "</div></ol>"
    )
    assert_no_progressbar_semantics(html, component_tag="ol", component_class="bw-ranked-list")


def test_progress_chart_element_does_not_false_fail_progress_element_check() -> None:
    html = '<ol class="bw-ranked-list"><progress-chart class="bw-ranked-list__chart"></progress-chart></ol>'
    assert_no_progressbar_semantics(html, component_tag="ol", component_class="bw-ranked-list")
