"""{% bw_dropdown %} contract tests (04-interfaces section 4b, 0.8.0).

The tag renders the no-JS floor: a native <details>/<summary> disclosure of
plain links in a labelled <nav> landmark, with deliberately NO ARIA menu
semantics (role="menu" mandates arrow-key handling a no-JS page cannot
provide). bwDropdown upgrades the markup at init, so menu roles must be
absent from the server-rendered output (the _account_menu.html doctrine run
forwards, BR-BW-HTMX-006). Render-time enforcement (ICO-008 icon-only
aria_label, item variant validation, the attrs seam's name validation) raises
TemplateSyntaxError exactly as bw_button does.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_ITEMS = [
    {"label": "New widget", "url": "/widgets/new/", "icon": "plus"},
    {"label": "Draft widgets", "url": "/widgets/?status=draft"},
    {"divider": True},
    {"label": "Delete demo data", "url": "/reset/", "variant": "danger"},
]


def _render(src: str = "{% bw_dropdown items=items trigger_label='Actions' %}", **ctx: object) -> str:
    ctx.setdefault("items", _ITEMS)
    return engines["django"].from_string("{% load brickwork_interactions %}" + src).render(ctx)


# --- the no-JS floor (BR-BW-HTMX-001/006) -----------------------------------


def test_floor_is_a_details_disclosure_of_plain_links() -> None:
    html = _render()
    assert '<details class="bw-dropdown"' in html
    assert "<summary" in html
    assert 'href="/widgets/new/"' in html and 'href="/widgets/?status=draft"' in html
    # three actionable items render as ordinary anchors; the divider does not
    assert html.count("data-bw-dropdown-item") == 3


def test_no_aria_menu_semantics_in_server_markup() -> None:
    # Menu semantics are presented only when the behaviour they promise is
    # actually running: bwDropdown adds them at init, never the server.
    html = _render()
    assert 'role="menu"' not in html
    assert 'role="menuitem"' not in html
    assert "aria-haspopup" not in html
    assert "aria-expanded" not in html
    assert 'tabindex="-1"' not in html


def test_panel_is_a_nav_landmark_labelled_from_the_trigger() -> None:
    html = _render()
    assert '<nav class="bw-dropdown__panel"' in html
    assert 'aria-label="Actions"' in html


def test_trigger_reuses_the_button_chrome_with_the_variant() -> None:
    assert "bw-btn--secondary" in _render()  # the default trigger_variant
    assert "bw-btn--ghost" in _render("{% bw_dropdown items=items trigger_label='Actions' trigger_variant='ghost' %}")


def test_divider_renders_as_a_non_link_separator() -> None:
    html = _render()
    assert 'class="bw-dropdown__divider"' in html


def test_danger_variant_takes_the_danger_modifier() -> None:
    html = _render()
    assert html.count("bw-dropdown__item--danger") == 1


# --- placement (ADR-060 rule 1, closes #120) ---------------------------------


def test_placement_default_emits_no_end_modifier() -> None:
    html = _render()
    assert "bw-dropdown--end" not in html


def test_placement_end_emits_the_end_modifier() -> None:
    html = _render("{% bw_dropdown items=items trigger_label='Actions' placement='end' %}")
    assert "bw-dropdown--end" in html


def test_placement_invalid_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render("{% bw_dropdown items=items trigger_label='Actions' placement='middle' %}")


def test_item_icon_renders_decorative() -> None:
    html = _render()
    assert "bw-dropdown__item-icon" in html
    assert 'aria-hidden="true"' in html


# --- the attrs seam: consumer data-* metadata only, never a general
# --- attribute passthrough (ADR-083) -----------------------------------------


def test_attrs_seam_passes_through_a_plain_data_attribute_escaped() -> None:
    items = [{"label": "Export", "url": "/export/", "attrs": {"data-kind": 'a"b'}}]
    html = _render(items=items)
    assert 'data-kind="a&quot;b"' in html


def test_attrs_seam_rejects_the_reserved_data_bw_namespace() -> None:
    # Pinned to the attrs-seam rejection message specifically (not just
    # "attrs", which the "attrs must be a mapping" precondition message
    # also contains), so a precondition failure could not masquerade as
    # this class of rejection.
    items = [{"label": "Export", "url": "/export/", "attrs": {"data-bw-export": "1"}}]
    with pytest.raises(TemplateSyntaxError, match="item attrs contains an invalid attribute name"):
        _render(items=items)


@pytest.mark.parametrize("name", ["role", "onclick", "aria-label", "hx-post"])
def test_attrs_seam_rejects_non_data_attribute_names(name: str) -> None:
    # ADR-083: the seam protects what a component deliberately withholds
    # (an unstamped ARIA role, an unwired hx-* hook), not just what it
    # emits, so only data-* names are ever accepted here. A precondition
    # failure (a non-mapping attrs, tested separately below) raises a
    # different message, so this match is pinned to the attrs-seam
    # rejection specifically, not merely "some TemplateSyntaxError".
    items = [{"label": "Export", "url": "/export/", "attrs": {name: "1"}}]
    with pytest.raises(TemplateSyntaxError, match="item attrs contains an invalid attribute name"):
        _render(items=items)


def test_alpine_component_and_behaviour_args_are_wired() -> None:
    # BR-BW-JS-004: bwDropdown is the semver-public component name; the tag's
    # behaviour arguments flow through the x-data config (CBH-006/007).
    html = _render()
    assert 'x-data="bwDropdown(' in html
    assert "triggerMode: 'click'" in html
    assert "closeOnSelect: true" in html
    hover = _render("{% bw_dropdown items=items trigger_label='Actions' trigger_mode='hover' %}")
    assert "triggerMode: 'hover'" in hover
    sticky = _render("{% bw_dropdown items=items trigger_label='Actions' close_on_select=False %}")
    assert "closeOnSelect: false" in sticky


def test_icon_only_renders_the_aria_label_and_no_visible_label() -> None:
    html = _render(
        "{% bw_dropdown items=items icon_only=True aria_label='Widget actions' trigger_icon='more-horizontal' %}"
    )
    assert 'aria-label="Widget actions"' in html
    assert "bw-btn--icon-only" in html
    assert "bw-btn__label" not in html


def test_item_label_is_escaped() -> None:
    html = _render(items=[{"label": "<b>bold</b>", "url": "/x/"}])
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


# --- render-time enforcement raises ------------------------------------------


def test_missing_items_argument_is_a_parse_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        engines["django"].from_string("{% load brickwork_interactions %}{% bw_dropdown %}")


@pytest.mark.parametrize(
    "src, ctx",
    [
        # empty or non-list items
        ("{% bw_dropdown items=items trigger_label='A' %}", {"items": []}),
        ("{% bw_dropdown items=items trigger_label='A' %}", {"items": "not-a-list"}),
        # ICO-008: icon-only without an accessible name
        ("{% bw_dropdown items=items icon_only=True trigger_icon='more-horizontal' %}", {}),
        # a visible trigger requires a label
        ("{% bw_dropdown items=items %}", {}),
        # invalid enumerations
        ("{% bw_dropdown items=items trigger_label='A' trigger_variant='loud' %}", {}),
        ("{% bw_dropdown items=items trigger_label='A' trigger_mode='focus' %}", {}),
    ],
)
def test_invalid_arguments_raise(src: str, ctx: dict) -> None:
    with pytest.raises(TemplateSyntaxError):
        _render(src, **ctx)


@pytest.mark.parametrize(
    "items",
    [
        [{"label": "No url"}],
        [{"url": "/no-label/"}],
        [{"label": "Bad variant", "url": "/x/", "variant": "warning"}],
        [{"divider": True, "label": "dividers carry no other keys"}],
        [{"label": "Bad attrs", "url": "/x/", "attrs": "not-a-mapping"}],
        [{"label": "Bad attr name", "url": "/x/", "attrs": {'onclick="x" data-y': "v"}}],
    ],
)
def test_invalid_items_raise(items: list) -> None:
    with pytest.raises(TemplateSyntaxError):
        _render(items=items)


# --- the shipped JS bundle contract ------------------------------------------


def test_bundle_registers_bwdropdown_and_emits_bw_namespaced_events() -> None:
    # AC-BW-033/AC-BW-087 static leg: the compiled bundle carries the
    # semver-public component name and its documented bw: event names.
    bundle = _DIST_JS.read_text()
    assert "bwDropdown" in bundle
    assert "bw:dropdown:open" in bundle
    assert "bw:dropdown:close" in bundle


def test_bundle_never_starts_alpine_and_ships_no_sui_namespace() -> None:
    # BR-BW-JS-002 and the BR-BW-HTMX-004 namespace amendment.
    bundle = _DIST_JS.read_text()
    assert "Alpine.start(" not in bundle
    assert "sui:" not in bundle
