"""ADR-097 derived classifier gate (icvoss/django-brickwork#390).

Pins every attribute-position ``{{ }}`` under
``src/brickwork/templates/brickwork/`` to a checked-in inventory. The
classifier assigns each hit to ``composed``, ``extends_unreachable``, or
``known_exempt``. The gate fails when:

* a new unclassified site appears (inventory would have to grow), or
* an inventory entry no longer matches a live site (inventory would shrink
  without this PR updating it), or
* the classifier assigns a different category than the inventory records.

Seam-covered sites (``{% bw_attr %}`` / ``{% bw_data_attrs %}``) and
closed-vocabulary author-literal if/elif class modifiers are validated by
absence: they must not produce raw ``{{ }}`` hits for the values they own.

Teeth-checks cover both CONTRIBUTING.md directions (#286): matched-nothing
(scan floor; injected site must be seen) and matched-the-wrong-thing
(keep the locator matching while violating the classification / inventory
property).
"""

from __future__ import annotations

from collections import Counter

from tests._attr_position_classifier import (
    EXTENDS_GROUP,
    TEMPLATES_ROOT,
    classify_hit,
    classify_inventory,
    find_attr_interpolations,
    is_composed_attribute_value,
    strip_template_comments,
)

# ---------------------------------------------------------------------------
# Checked-in inventory (cannot grow or shrink silently)
#
# Keys are ``path|attr|expr[|expr...]`` from AttrInterpHit.key. Counts are
# multiplicities of identical keys. Citations live in the category doc
# strings below rather than per-key prose: migrating a site updates the
# matching Counter in the same change as the template.
# ---------------------------------------------------------------------------

# Partial-value / mixed-literal attributes (#390, #481 composed residue).
# Includes class modifier tokens, composed ids/selectors, x-data payloads,
# and CSS custom-property wrappers that still interpolate inside a larger
# attribute value.
_COMPOSED: dict[str, int] = {
    "components/_avatar.html|class|bw_size|bw_shape": 2,
    "components/_avatar_group.html|class|bw_size|bw_shape": 1,
    "components/_badge.html|class|variant": 1,
    "components/_button.html|class|variant|size": 3,
    "components/_button_group.html|class|bw_btn_variant|bw_size": 2,
    "components/_button_group.html|class|bw_variant|bw_size": 1,
    "components/_callout.html|class|bw_variant": 1,
    "components/_card.html|class|media_recipe": 1,
    "components/_chip.html|class|bw_variant|bw_size": 4,
    "components/_combobox.html|hx-indicator|listbox_id": 1,
    "components/_combobox.html|hx-target|listbox_id": 1,
    "components/_combobox.html|id|field_id": 1,
    "components/_combobox.html|id|listbox_id": 1,
    'components/_combobox.html|x-data|filter_mode|multiple|yesno:"true,false"|allow_create|yesno:"true,false"': 1,
    "components/_divider.html|class|bw_tone|bw_spacing": 2,
    "components/_dropdown.html|class|trigger_variant": 1,
    "components/_dropdown.html|x-data|trigger_mode|close_on_select|yesno:'true,false'": 1,
    "components/_gauge.html|class|size": 1,
    "components/_gauge.html|class|threshold_token": 1,
    "components/_gauge.html|style|circumference|dash_offset": 1,
    "components/_ranked_list.html|style|row.percent": 1,
    "components/_skeleton.html|class|variant": 1,
    "components/_site_header.html|class|site_header_modifiers": 1,
    "components/_sparkline.html|class|tone|direction": 1,
    "components/_sparkline.html|viewBox|width|height": 1,
    "components/_tabs.html|aria-labelledby|tabs_id|key": 1,
    "components/_tabs.html|class|variant": 1,
    "components/_tabs.html|id|tabs_id|key": 1,
    "components/_tabs.html|x-data|id|escapejs|active|escapejs|url_sync|yesno:'true,false'|lazy_load|yesno:'true,false'": 1,
    "components/_theme_switch.html|class|placement": 1,
    "components/_toast.html|class|variant": 1,
    "components/_toast.html|x-data|duration": 1,
    "components/_token_specimen.html|aria-label|fg|bg|floor": 1,
    "components/_token_specimen.html|class|row.kind": 1,
    "components/_token_specimen.html|style|row.contrast_pair|row.name": 1,
    "components/_token_specimen.html|style|row.name": 5,
    "forms/_form.html|class|layout": 1,
    "forms/_form.html|style|grid_columns": 1,
}

# ADR-097 section 6: extends-group residual attribute sites.
_EXTENDS_UNREACHABLE: dict[str, int] = {
    "components/_modal.html|aria-labelledby|bw_modal_instance_id": 1,
    "components/_modal.html|aria-label|bw_modal_close_label": 2,
    "components/_modal.html|id|bw_modal_instance_id": 2,
    "components/_slide_over.html|aria-labelledby|bw_slide_over_instance_id": 1,
    "components/_slide_over.html|aria-label|bw_slide_over_close_label": 2,
    "components/_slide_over.html|id|bw_slide_over_instance_id": 2,
    "components/_tooltip.html|aria-describedby|id": 1,
    "components/_tooltip.html|id|id": 2,
    "components/_tooltip.html|x-data|id|escapejs": 1,
}

# Whole-value ``attr="{{ var }}"`` residue still awaiting migration through
# ``{% bw_attr %}`` (or an explicit later decision). Citations: #390
# (umbrella), tag-path ``escape_attribute_value`` sites, style-context
# ``_skeleton.style_attr``, identifiers, and URL attributes (scheme
# validation remains out of scope per ADR-084). ``flatatt`` is Python-side
# and does not appear in this template inventory.
_KNOWN_EXEMPT: dict[str, int] = {
    "components/_button.html|href|href": 1,
    "components/_button.html|name|name": 1,
    "components/_button.html|type|type": 1,
    "components/_button.html|value|value": 1,
    "components/_button_group.html|type|item.type|default:'button'": 1,
    "components/_card.html|alt|media_alt": 1,
    "components/_card.html|src|media_src": 1,
    "components/_code.html|data-bw-code-copy-error-template|bw_code_copy_error": 1,
    "components/_code.html|data-bw-code-copy-success-template|bw_code_copy_success": 1,
    "components/_combobox.html|aria-controls|listbox_id": 1,
    "components/_combobox.html|aria-describedby|described_by": 2,
    "components/_combobox.html|aria-labelledby|label_id": 1,
    "components/_combobox.html|aria-label|bw_chip_remove_label|opt.label": 1,
    "components/_combobox.html|data-bw-chip-remove-label|bw_chip_remove_label": 1,
    "components/_combobox.html|data-bw-value|opt.value": 2,
    "components/_combobox.html|for|field_id": 1,
    "components/_combobox.html|hx-get|options_url": 1,
    "components/_combobox.html|id|error_id": 1,
    "components/_combobox.html|id|field_id": 1,
    "components/_combobox.html|id|help_id": 1,
    "components/_combobox.html|id|label_id": 1,
    "components/_combobox.html|id|listbox_id": 1,
    "components/_combobox.html|id|opt.option_id": 1,
    "components/_combobox.html|name|html_name": 1,
    "components/_combobox.html|placeholder|placeholder": 1,
    "components/_combobox.html|value|opt.value": 1,
    "components/_comparison_table.html|aria-labelledby|hid": 1,
    "components/_comparison_table.html|id|hid": 1,
    "components/_date_picker_chrome.html|id|bw_dpc_id": 1,
    "components/_date_picker_chrome.html|id|label_id": 1,
    "components/_dropdown.html|href|item.url": 1,
    "components/_dropzone.html|aria-describedby|error_id": 1,
    "components/_dropzone.html|aria-describedby|help_id|error_id": 1,
    "components/_dropzone.html|for|id": 1,
    "components/_dropzone.html|id|error_id": 1,
    "components/_dropzone.html|id|help_id": 1,
    "components/_dropzone.html|id|id": 1,
    "components/_filter_bar.html|id|filter_bar_id": 1,
    "components/_gauge.html|r|radius": 2,
    "components/_ranked_list.html|href|row.href": 1,
    "components/_skeleton.html|style|style_attr": 1,
    "components/_sparkline.html|cx|marker_cx": 1,
    "components/_sparkline.html|cy|marker_cy": 1,
    "components/_sparkline.html|d|path_d": 1,
    "components/_tabs.html|data-bw-tab-key|tab.key": 1,
    "components/_tabs.html|data-bw-tab-panel-id|tab.panel_id": 1,
    "components/_tabs.html|href|tab.url": 1,
    "components/_tabs.html|hx-get|lazy_url": 1,
    "components/_tabs.html|id|tab.tab_id": 1,
    "components/_tag_input.html|aria-describedby|help_id|error_id": 2,
    "components/_tag_input.html|data-bw-tag-remove-label|bw_tag_remove_label": 1,
    "components/_tag_input.html|for|id": 1,
    "components/_tag_input.html|id|error_id": 1,
    "components/_tag_input.html|id|help_id": 1,
    "components/_tag_input.html|id|id": 2,
    "components/_theme_switch.html|data-bw-theme-switch-axis|group.axis": 1,
    "components/_theme_switch.html|data-bw-theme-switch-values|values_element_id": 1,
    "components/_theme_switch.html|id|instance_id": 1,
    "components/_theme_switch.html|name|group.name": 1,
    "components/_theme_switch.html|value|option.value": 1,
    "components/_toast.html|href|action_href": 1,
    "components/_toast.html|id|id": 1,
    "components/_toc.html|aria-labelledby|toc_heading_id": 1,
    "components/_toc.html|id|toc_heading_id": 1,
    "components/_toggle.html|id|id": 1,
    "components/_toggle.html|name|name": 1,
    "components/_token_specimen.html|data-bw-min-contrast|row.min_contrast": 1,
    "components/_token_specimen.html|data-bw-token-kind|row.kind": 1,
    "components/_token_specimen.html|data-bw-token-pair|row.contrast_pair": 1,
    "components/_token_specimen.html|data-bw-token|row.name": 1,
    "components/_token_specimen.html|data-theme|theme": 1,
    "components/_version_switch.html|href|version.href": 1,
    "forms/_field.html|id|error_id": 1,
    "forms/_field.html|id|help_id": 1,
    "forms/_form.html|data-density|density": 1,
    "nav/_nav.html|href|item.href|default:'#'": 1,
    "nav/_nav_header.html|href|item.href|default:'#'": 1,
    "nav/_nav_rail.html|data-bw-nav-menu-trigger|item.key": 1,
    "nav/_nav_rail.html|href|item.href|default:'#'": 1,
    "shell/app.html|data-bw-sidebar-collapse-label|bw_sidebar_collapse_label": 1,
    "shell/app.html|data-bw-sidebar-expand-label|bw_sidebar_expand_label": 1,
    "shell/base.html|data-bw-brand|bw_brand": 1,
}

_EXPECTED: dict[str, Counter[str]] = {
    "composed": Counter(_COMPOSED),
    "extends_unreachable": Counter(_EXTENDS_UNREACHABLE),
    "known_exempt": Counter(_KNOWN_EXEMPT),
}


def _diff_counters(actual: Counter[str], expected: Counter[str]) -> str:
    extra = actual - expected
    missing = expected - actual
    parts: list[str] = []
    if extra:
        parts.append(
            "new/unclassified (would grow the inventory): " + ", ".join(f"{k}×{n}" for k, n in sorted(extra.items()))
        )
    if missing:
        parts.append(
            "stale inventory (would shrink without an update): "
            + ", ".join(f"{k}×{n}" for k, n in sorted(missing.items()))
        )
    return "; ".join(parts) or "(counters equal)"


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


def test_attr_position_inventory_matches_checked_in_allowlist() -> None:
    """Exact match: residual attribute-position sites cannot grow or shrink
    silently (ADR-097 Decision section 5)."""
    actual = classify_inventory()
    for category, expected in _EXPECTED.items():
        got = actual[category]
        assert got == expected, (
            f"category {category!r} drifted from the checked-in inventory "
            f"(icvoss/django-brickwork#390 / ADR-097): {_diff_counters(got, expected)}"
        )


def test_inventory_totals_are_non_vacuous() -> None:
    """Matched-nothing floor: a scan that found zero files or zero hits
    would pass an empty-allowlist gate vacuously."""
    templates = list(TEMPLATES_ROOT.rglob("*.html"))
    assert len(templates) >= 40, f"expected a real template tree; found {len(templates)}"
    hits = find_attr_interpolations()
    assert len(hits) >= 100, f"expected a non-empty residual set; found {len(hits)}"
    assert sum(_EXPECTED[c].total() for c in _EXPECTED) == len(hits)


# ---------------------------------------------------------------------------
# Classifier validated against the known set (before trusting categories)
# ---------------------------------------------------------------------------


def test_known_composed_class_sites_classify_as_composed() -> None:
    assert classify_hit("components/_badge.html", "class", "bw-badge bw-badge--{{ variant }}") == "composed"
    assert (
        classify_hit("components/_button.html", "class", "bw-btn bw-btn--{{ variant }} bw-btn--{{ size }}")
        == "composed"
    )
    assert is_composed_attribute_value("bw-badge bw-badge--{{ variant }}")


def test_known_extends_group_sites_classify_as_extends_unreachable() -> None:
    for path in EXTENDS_GROUP:
        assert classify_hit(path, "id", "{{ id }}") == "extends_unreachable"
        assert classify_hit(path, "aria-label", "{{ label }}") == "extends_unreachable"


def test_whole_value_consumer_interpolation_classifies_as_known_exempt() -> None:
    assert classify_hit("components/_search.html", "aria-label", "{{ search_label }}") == "known_exempt"
    assert not is_composed_attribute_value("{{ search_label }}")


def test_progress_seam_covered_sites_produce_no_raw_attr_interpolation() -> None:
    """Absence check for seam_covered: _progress routes label / valuenow /
    style through bw_attr, so those attributes must not appear as raw
    ``{{ }}`` hits."""
    progress = (TEMPLATES_ROOT / "components" / "_progress.html").read_text(encoding="utf-8")
    assert "{% bw_attr" in progress
    hits = [
        h
        for h in find_attr_interpolations(
            sources=[("components/_progress.html", progress)],
        )
        if h.attr in {"aria-label", "aria-valuenow", "style"}
    ]
    assert hits == [], f"progress still has raw attribute interpolations: {hits}"


def test_stat_size_uses_author_literal_if_elif_not_class_interpolation() -> None:
    """Absence check for closed_vocab_author_literal: _stat size is an
    if/elif author-literal ladder, not ``bw-stat--{{ size }}``."""
    stat = (TEMPLATES_ROOT / "components" / "_stat.html").read_text(encoding="utf-8")
    assert 'size == "sm"' in stat
    assert "bw-stat--{{" not in strip_template_comments(stat)
    hits = find_attr_interpolations(sources=[("components/_stat.html", stat)])
    assert hits == [], f"_stat should have no raw attribute {{ }} hits; got {hits}"


def test_docstring_examples_inside_comment_blocks_are_not_hits() -> None:
    """Account menu's docstring shows ``aria-label="{{ trigger_label }}"``
    inside ``{% comment %}``; that must not enter the inventory."""
    source = (TEMPLATES_ROOT / "components" / "_account_menu.html").read_text(encoding="utf-8")
    assert 'aria-label="{{ trigger_label }}"' in source  # present in the docstring
    hits = find_attr_interpolations(sources=[("components/_account_menu.html", source)])
    trigger_hits = [h for h in hits if "trigger_label" in h.key]
    assert trigger_hits == [], f"docstring example leaked into inventory: {trigger_hits}"


# ---------------------------------------------------------------------------
# Teeth-checks (#286): matched-nothing and matched-the-wrong-thing
# ---------------------------------------------------------------------------


def test_injected_unmigrated_site_fails_the_inventory_gate() -> None:
    """Matched-nothing direction for the gate property: a newly introduced
    ``aria-label="{{ evil }}"`` must be visible to the classifier and must
    not match the checked-in inventory."""
    fixture = '<div aria-label="{{ evil }}"></div>'
    hits = find_attr_interpolations(sources=[("components/_injected_gate_probe.html", fixture)])
    assert len(hits) == 1, "injector produced no hit; the scanner matched nothing"
    assert hits[0].attr == "aria-label"
    assert hits[0].key == "components/_injected_gate_probe.html|aria-label|evil"
    actual = classify_inventory(hits)
    # The probe is whole-value → known_exempt, and is absent from inventory.
    assert actual["known_exempt"] != _EXPECTED["known_exempt"]
    extra = actual["known_exempt"] - _EXPECTED["known_exempt"]
    assert hits[0].key in extra


def test_comment_only_interpolation_is_not_a_false_hit() -> None:
    """Keep the file looking like a template with ``{{ }}``, but only inside
    a comment: the scanner must not report a hit (matched-the-wrong-thing
    for 'any {{ }} counts as attribute position')."""
    fixture = '{% comment %}<div aria-label="{{ evil }}"></div>{% endcomment %}\n<div class="bw-x"></div>\n'
    hits = find_attr_interpolations(sources=[("components/_comment_probe.html", fixture)])
    assert hits == []


def test_composed_value_kept_matching_while_misclassified_as_exempt_is_detectable() -> None:
    """Matched-the-wrong-thing: the locator still finds the attribute, but
    classifying a composed class token as known_exempt must disagree with
    the inventory category for that key."""
    value = "bw-badge bw-badge--{{ variant }}"
    key = "components/_badge.html|class|variant"
    assert classify_hit("components/_badge.html", "class", value) == "composed"
    # A broken classifier that treated every hit as known_exempt would still
    # "match" the site while assigning the wrong category.
    wrong_category = "known_exempt"
    assert wrong_category != "composed"
    assert key in _COMPOSED
    assert key not in _KNOWN_EXEMPT


def test_inventory_shrink_without_template_change_is_detectable() -> None:
    """If an allowlist entry is deleted while the live site remains, the
    counters diverge (the shrink direction of the gate)."""
    shrunk = Counter(_KNOWN_EXEMPT)
    victim = "components/_skeleton.html|style|style_attr"
    assert shrunk[victim] == 1
    del shrunk[victim]
    live = classify_inventory()["known_exempt"]
    assert live != shrunk
    assert (live - shrunk)[victim] == 1


def test_is_composed_distinguishes_whole_value_from_partial() -> None:
    assert not is_composed_attribute_value("{{ label }}")
    assert not is_composed_attribute_value("  {{ label }}  ")
    assert is_composed_attribute_value("bw-x--{{ label }}")
    assert is_composed_attribute_value("{{ a }}-row-{{ b }}")
    assert is_composed_attribute_value("#{{ listbox_id }}")
