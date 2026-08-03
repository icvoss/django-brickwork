"""Render tests for the page-templates kit (v1.1.0, spec 04 section 4a).

BR-BW-PAGE-002 / AC-BW-076: each page renders a complete valid document when a
consumer extends it with only the required context, and every documented
block fills in order when supplied. BR-BW-PAGE-003 is the load-bearing
backend-agnostic contract for the three auth pages: brickwork ships no view,
form, or field name, so the SAME auth_signin.html must render identically
whichever authentication backend's form is dropped into auth_body.
BR-BW-PAGE-004 records why form_page.html has no form_actions block: the
submit lives inside the consumer's own form_body <form>.

These tests drive the pages the way a consumer does: {% extends %} plus block
overrides, mirroring test_patterns.py's idiom exactly.
"""

from __future__ import annotations

import pytest
from django import forms
from django.template import Context, Template, TemplateSyntaxError
from django.template.loader import render_to_string

_SETTINGS_TABS = [
    {"key": "profile", "label": "Profile"},
    {"key": "billing", "label": "Billing"},
]


def _render(template: str, request=None, **ctx: object) -> str:
    return render_to_string(template, ctx, request=request)


def _extend(parent: str, blocks: str, **ctx: object) -> str:
    return Template("{% extends '" + parent + "' %}" + blocks).render(Context(ctx))


def _assert_complete_document(html: str) -> None:
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert 'id="bw-main"' in html


# --- pages/form_page.html ----------------------------------------------------


def test_form_page_with_only_title_renders_a_complete_working_page() -> None:
    html = _render("brickwork/pages/form_page.html", title="New widget")
    _assert_complete_document(html)
    assert "New widget" in html  # page_header default wired from title
    assert "<form" not in html  # form_body empty by default: no fabricated form


def test_form_page_emits_no_form_element_itself() -> None:
    # The pattern never wraps the consumer's own <form>: form_body is the
    # ONLY place a <form> may appear, and only the consumer supplies it.
    html = _render("brickwork/pages/form_page.html", title="New widget")
    assert "<form" not in html
    assert "</form>" not in html


def test_form_page_form_body_places_submit_inside_the_consumers_own_form() -> None:
    # BR-BW-PAGE-004: no form_actions block exists, so the submit lives
    # inside form_body, beside the fields, inside the consumer's own <form>.
    html = _extend(
        "brickwork/pages/form_page.html",
        "{% block form_body %}"
        '<form method="post" action="/widgets/new/">'
        "FIELDS-SENTINEL"
        '<button type="submit">SUBMIT-SENTINEL</button>'
        "</form>"
        "{% endblock %}",
        title="New widget",
    )
    assert html.count("<form") == 1
    form_start = html.index("<form")
    form_end = html.index("</form>") + len("</form>")
    form_span = html[form_start:form_end]
    assert "FIELDS-SENTINEL" in form_span
    assert "SUBMIT-SENTINEL" in form_span


def test_form_page_renders_through_the_app_shell() -> None:
    html = _render("brickwork/pages/form_page.html", title="New widget")
    assert "bw-app" in html and "bw-sidebar" in html and "bw-topbar" in html


# --- pages/settings.html -------------------------------------------------


def test_settings_with_tabs_and_active_tab_renders_a_complete_page() -> None:
    html = _render(
        "brickwork/pages/settings.html",
        title="Settings",
        settings_tabs=_SETTINGS_TABS,
        active_tab="profile",
    )
    _assert_complete_document(html)
    assert "Settings" in html
    assert "bw-tabs" in html


def test_settings_nav_default_produces_real_anchor_links() -> None:
    # The no-JS floor: {% bw_tabs %}'s own contract is a real anchor per tab,
    # switching sections via ordinary navigation with zero JS required.
    html = _render(
        "brickwork/pages/settings.html",
        title="Settings",
        settings_tabs=_SETTINGS_TABS,
        active_tab="profile",
    )
    assert '<a class="bw-tabs__tab' in html
    assert html.count("<a ") >= 2  # one anchor per tab


def test_settings_nav_raises_when_tabs_are_missing() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render("brickwork/pages/settings.html", title="Settings", active_tab="profile")


def test_settings_nav_raises_when_active_tab_is_missing() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render("brickwork/pages/settings.html", title="Settings", settings_tabs=_SETTINGS_TABS)


def test_settings_nav_raises_when_active_tab_does_not_match_any_key() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render(
            "brickwork/pages/settings.html",
            title="Settings",
            settings_tabs=_SETTINGS_TABS,
            active_tab="not-a-real-tab",
        )


def test_settings_body_fills_after_the_nav_in_document_order() -> None:
    html = _extend(
        "brickwork/pages/settings.html",
        "{% block settings_body %}BODY-SENTINEL{% endblock %}",
        title="Settings",
        settings_tabs=_SETTINGS_TABS,
        active_tab="profile",
    )
    assert html.index("bw-tabs") < html.index("BODY-SENTINEL")


def test_settings_nav_block_can_be_overridden() -> None:
    html = _extend(
        "brickwork/pages/settings.html",
        "{% block settings_nav %}NAV-SENTINEL{% endblock %}",
        title="Settings",
    )
    assert "NAV-SENTINEL" in html
    assert "bw-tabs" not in html


def test_settings_renders_through_the_app_shell() -> None:
    html = _render(
        "brickwork/pages/settings.html",
        title="Settings",
        settings_tabs=_SETTINGS_TABS,
        active_tab="profile",
    )
    assert "bw-app" in html and "bw-sidebar" in html and "bw-topbar" in html


# --- pages/console.html --------------------------------------------------


def test_console_with_title_heading_and_body_renders_a_complete_page() -> None:
    html = _render(
        "brickwork/pages/console.html",
        title="Reports",
        heading="No reports yet",
        body="Reports appear here once generated.",
    )
    _assert_complete_document(html)
    assert "Reports" in html
    assert "bw-empty-state" in html
    assert "No reports yet" in html
    assert "Reports appear here once generated." in html


def test_console_body_can_be_overridden_entirely() -> None:
    html = _extend(
        "brickwork/pages/console.html",
        "{% block console_body %}CONSOLE-SENTINEL{% endblock %}",
        title="Reports",
    )
    assert "CONSOLE-SENTINEL" in html
    assert "bw-empty-state" not in html


def test_console_renders_through_the_app_shell() -> None:
    html = _render(
        "brickwork/pages/console.html",
        title="Reports",
        heading="No reports yet",
        body="Reports appear here once generated.",
    )
    assert "bw-app" in html and "bw-sidebar" in html and "bw-topbar" in html


# --- pages/confirm.html ----------------------------------------------------


def test_confirm_renders_a_complete_page_with_no_context_at_all() -> None:
    html = _render("brickwork/pages/confirm.html")
    _assert_complete_document(html)


def test_confirm_body_and_actions_fill_in_document_order() -> None:
    html = _extend(
        "brickwork/pages/confirm.html",
        "{% block confirm_body %}BODY-SENTINEL{% endblock %}{% block confirm_actions %}ACTIONS-SENTINEL{% endblock %}",
    )
    positions = [html.index("BODY-SENTINEL"), html.index("ACTIONS-SENTINEL")]
    assert positions == sorted(positions), f"confirm regions out of documented order: {positions}"


def test_confirm_extends_the_centred_shell_with_no_sidebar_or_topbar_chrome() -> None:
    html = _render("brickwork/pages/confirm.html")
    assert "bw-centred" in html
    assert "bw-sidebar" not in html
    assert "bw-topbar" not in html
    assert 'id="bw-main"' in html


# --- pages/auth_signin.html, auth_signup.html, auth_reset.html -----------

_AUTH_PAGES = (
    "brickwork/pages/auth_signin.html",
    "brickwork/pages/auth_signup.html",
    "brickwork/pages/auth_reset.html",
)


def test_each_auth_page_renders_a_complete_page_with_no_context_at_all() -> None:
    for template in _AUTH_PAGES:
        html = _render(template)
        _assert_complete_document(html)


def test_each_auth_page_emits_no_form_element_by_default() -> None:
    for template in _AUTH_PAGES:
        html = _render(template)
        assert "<form" not in html, f"{template} must not emit a <form> of its own"


def test_each_auth_page_never_hard_codes_a_url_tag_target() -> None:
    # A hard-coded {% url %} name that does not exist in the consuming
    # project would 500 on render; none of these pages may reference one.
    for template in _AUTH_PAGES:
        html = _render(template)
        assert "{% url" not in html


def test_each_auth_page_never_hard_codes_a_backend_specific_field_name() -> None:
    # Neither allauth's "login" nor contrib.auth's "username" may appear as a
    # hard-coded field name/label anywhere in the bare render.
    for template in _AUTH_PAGES:
        html = _render(template)
        assert 'name="username"' not in html
        assert 'name="login"' not in html


def test_each_auth_page_extends_the_auth_shell_with_the_auth_panel() -> None:
    for template in _AUTH_PAGES:
        html = _render(template)
        assert "bw-auth" in html
        assert "bw-sidebar" not in html
        assert "bw-topbar" not in html


def test_auth_signin_heading_default_is_translated_sign_in_copy() -> None:
    html = _render("brickwork/pages/auth_signin.html")
    assert "Sign in" in html


def test_auth_signup_heading_default_is_translated_create_account_copy() -> None:
    html = _render("brickwork/pages/auth_signup.html")
    assert "Create your account" in html


def test_auth_reset_heading_default_is_translated_reset_password_copy() -> None:
    html = _render("brickwork/pages/auth_reset.html")
    assert "Reset your password" in html


def test_auth_heading_block_can_be_overridden() -> None:
    html = _extend(
        "brickwork/pages/auth_signin.html",
        "{% block auth_heading %}<h1>HEADING-SENTINEL</h1>{% endblock %}",
    )
    assert "HEADING-SENTINEL" in html
    assert "Sign in" not in html


def test_auth_heading_body_and_secondary_fill_in_document_order() -> None:
    html = _extend(
        "brickwork/pages/auth_signin.html",
        "{% block auth_heading %}HEADING-SENTINEL{% endblock %}"
        "{% block auth_body %}BODY-SENTINEL{% endblock %}"
        "{% block auth_secondary %}SECONDARY-SENTINEL{% endblock %}",
    )
    positions = [
        html.index("HEADING-SENTINEL"),
        html.index("BODY-SENTINEL"),
        html.index("SECONDARY-SENTINEL"),
    ]
    assert positions == sorted(positions), f"auth regions out of documented order: {positions}"


# --- BR-BW-PAGE-003: the backend-agnostic contract, the load-bearing test ---


class _AllauthShapedForm(forms.Form):
    """Field named exactly as allauth's own login form names it."""

    login = forms.CharField(label="Username or email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class _ContribAuthShapedForm(forms.Form):
    """Field named exactly as django.contrib.auth.forms.AuthenticationForm
    names it."""

    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


def _render_signin_with_form(form: forms.Form) -> str:
    return _extend(
        "brickwork/pages/auth_signin.html",
        "{% load brickwork_forms %}"
        "{% block auth_body %}"
        '<form method="post" action="/accounts/login/">'
        "{% bw_form form %}"
        "</form>"
        "{% endblock %}",
        form=form,
    )


def test_auth_signin_produces_identical_field_chrome_for_allauth_and_contrib_auth_forms() -> None:
    allauth_html = _render_signin_with_form(_AllauthShapedForm())
    contrib_html = _render_signin_with_form(_ContribAuthShapedForm())

    # Both go through the same _field.html chrome: same wrapper class, same
    # label pattern, same control wrapper, regardless of the field's name.
    for html in (allauth_html, contrib_html):
        assert 'class="bw-field"' in html
        assert 'class="bw-field__label"' in html
        assert 'class="bw-field__control"' in html

    # Each render shows its OWN field's label text (proving the fields
    # actually rendered, not a shared fixture ignoring the form entirely).
    assert "Username or email" in allauth_html
    assert "Username or email" not in contrib_html
    assert 'for="id_login"' in allauth_html

    assert "Username" in contrib_html
    assert 'for="id_username"' in contrib_html
    assert 'for="id_login"' not in contrib_html

    # Both share the password field name/label (present in both backends),
    # confirming the two renders are the SAME chrome mechanism at work, not
    # two different code paths that happen to look similar.
    assert 'for="id_password"' in allauth_html
    assert 'for="id_password"' in contrib_html


def test_bare_auth_signin_names_no_field_and_has_no_form() -> None:
    html = _render("brickwork/pages/auth_signin.html")
    assert "<form" not in html
    assert "{% url" not in html
    assert 'name="username"' not in html
    assert 'name="login"' not in html
