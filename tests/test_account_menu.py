"""Account-menu component tests (#25, plus #73's POST sign-out item).

Renders the shipped _account_menu.html include directly (no testapp needed). The
component is a native <details>/<summary> disclosure of navigation links:
deliberately NO ARIA menu semantics (role="menu"/"menuitem" mandate arrow-key
handling a no-JS component cannot provide); the panel is a <nav> landmark
labelled from the trigger label, containing ordinary anchors.

#73: an item carrying method="post" renders a CSRF-safe POST <form>/<button>
instead of an <a>, since Django's LogoutView has been POST-only since 5.0 and a
GET <a href> against it 405s. This is additive: absent/"get" items are
byte-for-byte unchanged from before #73.
"""

from __future__ import annotations

from django.template.loader import render_to_string
from django.test import RequestFactory

_ITEMS = [
    {"label": "Settings", "url": "/settings/", "icon": "settings"},
    {"label": "Sign out", "url": "/logout/", "danger": True},
]


def _render(request=None, **ctx: object) -> str:
    ctx.setdefault("items", _ITEMS)
    return render_to_string("brickwork/components/_account_menu.html", ctx, request=request)


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


def test_placement_variant_class() -> None:
    assert "bw-account-menu--end" in _render()
    assert "bw-account-menu--start" in _render(placement="start")


def test_menu_open_flag_renders_the_open_attribute() -> None:
    assert " open" in _details_tag(_render(menu_open=True))
    assert " open" not in _details_tag(_render())


def test_inherited_open_variable_does_not_toggle_the_disclosure() -> None:
    # The flag is menu_open, NOT open: a page context that happens to carry a
    # truthy "open" (a common name) must never pop the account menu open.
    assert " open" not in _details_tag(_render(open=True))


def test_no_aria_menu_semantics_anywhere() -> None:
    # A details/summary disclosure of links must NOT claim menu semantics:
    # role="menu"/"menuitem" promise arrow-key handling no-JS markup cannot keep.
    html = _render(menu_open=True)
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


# --- #73: method="post" sign-out item -----------------------------------


def _post_item(**overrides: object) -> dict:
    item = {"label": "Sign out", "url": "/logout/", "method": "post", "danger": True}
    item.update(overrides)
    return item


def test_post_item_renders_a_csrf_form_with_a_submit_button() -> None:
    request = RequestFactory().get("/")
    html = _render(request=request, items=[_post_item()])
    assert '<form method="post" action="/logout/" class="bw-account-menu__item-form">' in html
    assert 'name="csrfmiddlewaretoken"' in html
    assert '<button type="submit" class="bw-account-menu__item bw-account-menu__item--danger">' in html
    assert "Sign out" in html
    # never an <a> for this item
    assert '<a class="bw-account-menu__item' not in html


def test_post_item_without_danger_omits_the_danger_class() -> None:
    request = RequestFactory().get("/")
    html = _render(request=request, items=[_post_item(danger=False, label="Switch account")])
    assert '<button type="submit" class="bw-account-menu__item">' in html
    assert "bw-account-menu__item--danger" not in html


def test_post_item_icon_renders_through_bw_icon_inside_the_button() -> None:
    request = RequestFactory().get("/")
    html = _render(request=request, items=[_post_item(icon="settings")])
    button_start = html.index("<button")
    button_end = html.index("</button>") + len("</button>")
    button_html = html[button_start:button_end]
    assert 'class="bw-icon bw-account-menu__item-icon"' in button_html
    assert 'aria-hidden="true"' in button_html


def test_get_or_absent_method_item_is_unchanged_from_before_73() -> None:
    # A plain link item (no method key, the pre-#73 shape) renders byte-for-
    # byte the same <a> markup: no <form>, no <button>.
    item = {"label": "Settings", "url": "/settings/", "icon": "settings"}
    html = _render(items=[item])
    assert "<form" not in html
    assert "<button" not in html
    assert '<a class="bw-account-menu__item"\n           href="/settings/">' in html


def test_explicit_get_method_item_renders_the_original_anchor() -> None:
    item = {"label": "Settings", "url": "/settings/", "method": "get"}
    html = _render(items=[item])
    assert "<form" not in html
    assert '<a class="bw-account-menu__item"' in html
    assert 'href="/settings/"' in html


def test_mixed_get_and_post_items_both_render_correctly() -> None:
    request = RequestFactory().get("/")
    items = [
        {"label": "Settings", "url": "/settings/", "icon": "settings"},
        _post_item(),
    ]
    html = _render(request=request, items=items)
    # one <a> for the get item, one <form>/<button> for the post item
    assert html.count('<a class="bw-account-menu__item"') == 1
    assert html.count('<form method="post"') == 1
    assert html.count('<button type="submit"') == 1
    assert html.index("Settings") < html.index("Sign out")
