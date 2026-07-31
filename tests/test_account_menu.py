"""Account-menu component tests (#25).

Renders the shipped _account_menu.html include directly (no testapp needed). The
component is a native <details>/<summary> disclosure of navigation links:
deliberately NO ARIA menu semantics (role="menu"/"menuitem" mandate arrow-key
handling a no-JS component cannot provide); the panel is a <nav> landmark
labelled from the trigger label, containing ordinary anchors.
"""

from __future__ import annotations

from django.template.loader import render_to_string

_ITEMS = [
    {"label": "Settings", "url": "/settings/", "icon": "settings"},
    {"label": "Sign out", "url": "/logout/", "danger": True},
]


def _render(**ctx: object) -> str:
    ctx.setdefault("items", _ITEMS)
    return render_to_string("brickwork/components/_account_menu.html", ctx)


def _details_tag(html: str) -> str:
    """The opening <details ...> tag only, for attribute assertions."""
    start = html.index("<details")
    return html[start : html.index(">", start)]


def test_renders_a_details_disclosure_with_the_default_trigger_label() -> None:
    html = _render()
    assert "<details" in html and "<summary" in html
    # the default label is the translated "Account" string
    assert '<span class="bw-account-menu__trigger-label">Account</span>' in html


def test_danger_item_carries_the_danger_class() -> None:
    html = _render()
    assert "bw-account-menu__item--danger" in html
    assert html.count("bw-account-menu__item--danger") == 1  # only the danger item


def test_align_variant_class() -> None:
    assert "bw-account-menu--end" in _render()
    assert "bw-account-menu--start" in _render(align="start")


def test_open_flag_renders_the_open_attribute() -> None:
    assert " open" in _details_tag(_render(open=True))
    assert " open" not in _details_tag(_render())


def test_no_aria_menu_semantics_anywhere() -> None:
    # A details/summary disclosure of links must NOT claim menu semantics:
    # role="menu"/"menuitem" promise arrow-key handling no-JS markup cannot keep.
    html = _render(open=True)
    assert 'role="menu"' not in html
    assert 'role="menuitem"' not in html


def test_panel_is_a_nav_landmark_labelled_from_the_trigger_label() -> None:
    html = _render(trigger_label="My account")
    assert '<nav class="bw-account-menu__panel" aria-label="My account">' in html
    assert '<span class="bw-account-menu__trigger-label">My account</span>' in html


def test_item_icons_render_through_bw_icon() -> None:
    html = _render()
    # the settings item's icon goes through {% bw_icon %}: base class + the
    # component's item-icon class, decorative (aria-hidden)
    assert 'class="bw-icon bw-account-menu__item-icon"' in html
    assert 'aria-hidden="true"' in html
