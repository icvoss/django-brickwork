"""App-shell render tests (SHL region + the no-JS floor, BR-BW-HTMX-001).

The shell must render a complete, navigable document with NO JavaScript required:
no <script> tag is emitted by the shell itself, the sidebar toggle and mobile
drawer are native <details>, and a skip link is always present. These render the
shipped templates through Django's engine directly (no testapp needed for a pure
structural render).
"""

from __future__ import annotations

import re

import pytest
from django.template.loader import render_to_string

SHELLS = ["brickwork/shell/app.html", "brickwork/shell/auth.html", "brickwork/shell/centred.html"]


def _render(template: str, **context: object) -> str:
    return render_to_string(template, context)


# --- the no-JS floor (BR-BW-HTMX-001) -------------------------------------


@pytest.mark.parametrize("template", SHELLS)
def test_shell_emits_no_script_tag(template: str) -> None:
    # The shell itself loads no JS. A consumer adds Alpine/htmx via the head_js/
    # body_js blocks; the bare shell must be script-free so the no-JS floor holds.
    # (The one exception is the DEBUG-only registration detector, brickwork#87,
    # gated on bw_debug and absent here; see the detector tests below.)
    html = _render(template)
    assert "<script" not in html.lower(), f"{template} emitted a <script> tag"


# --- the DEBUG-only registration detector (brickwork#87) --------------------


def test_registration_detector_absent_without_bw_debug() -> None:
    # Production posture: bw_debug unset (or False) ships zero script bytes,
    # so the no-JS floor and CSP posture of a production page are untouched.
    assert "data-bw-registration-check" not in _render("brickwork/shell/app.html")
    assert "data-bw-registration-check" not in _render("brickwork/shell/app.html", bw_debug=False)


@pytest.mark.parametrize("template", SHELLS)
def test_registration_detector_renders_with_bw_debug(template: str) -> None:
    # With bw_debug on (the theme context processor maps settings.DEBUG onto
    # it), every shell carries the inline detector that turns the silent
    # dead-components trap into a console warning.
    html = _render(template, bw_debug=True)
    assert "data-bw-registration-check" in html
    assert "registerBrickworkComponents(Alpine)" in html
    assert "console.warn" in html
    # it keys on the marker registerBrickworkComponents stamps on <html>
    assert "data-bw-js-registered" in html


def test_registration_detector_block_can_be_overridden_away() -> None:
    # The documented CSP escape hatch: a consumer overrides the block (to add
    # a nonce or to empty it) without forking the shell.
    from django.template import Context, Template

    child = Template("{% extends 'brickwork/shell/app.html' %}{% block bw_js_registration_check %}{% endblock %}")
    html = child.render(Context({"bw_debug": True}))
    assert "data-bw-registration-check" not in html


@pytest.mark.parametrize("template", SHELLS)
def test_shell_leaks_no_template_comment_text(template: str) -> None:
    # A multi-line {# ... #} inline comment is NOT stripped by Django (inline
    # comments are single-line only), so it renders literally to the page. This
    # shipped as a visible-comment bug in 0.1.1 (seen on demo.vendablyconnect.com).
    # The rendered output must contain no comment markers and none of the known
    # comment prose.
    html = _render(template)
    assert "{#" not in html and "#}" not in html, f"{template} leaked a {{# #}} comment marker"
    for phrase in ("Skip link:", "first focusable element", "the audit found"):
        assert phrase not in html, f"{template} leaked comment text: {phrase!r}"


def test_no_shipped_template_uses_a_multiline_inline_comment() -> None:
    # Source-level guard against the whole bug class: Django's {# #} inline comment
    # is single-line only; a {# that spans to a later line is NOT stripped and
    # renders literally. Every multi-line comment must use {% comment %} instead.
    # This scans every shipped template so the bug cannot recur in one we do not
    # have an explicit render test for.
    import pathlib

    templates_dir = pathlib.Path(__file__).resolve().parent.parent / "src" / "brickwork" / "templates"
    offenders: list[str] = []
    for path in templates_dir.rglob("*.html"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # an opening {# with no closing #} on the same line = multi-line comment
            if "{#" in line and "#}" not in line.split("{#", 1)[1]:
                offenders.append(f"{path.relative_to(templates_dir)}:{lineno}")
    assert not offenders, (
        f"multi-line {{# #}} inline comments render literally; use {{% comment %}} instead. Offenders: {offenders}"
    )


@pytest.mark.parametrize("template", SHELLS)
def test_shell_has_a_skip_link_to_main(template: str) -> None:
    html = _render(template)
    assert 'class="bw-skip-link"' in html
    assert 'href="#bw-main"' in html
    assert 'id="bw-main"' in html


@pytest.mark.parametrize("template", SHELLS)
def test_shell_is_a_complete_document(template: str) -> None:
    html = _render(template)
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert "</body>" in html


# --- toast region wiring (BR-BW-HTMX-005) -----------------------------------


@pytest.mark.parametrize("template", SHELLS)
def test_shell_toast_region_defaults_to_top_end(template: str) -> None:
    # _toast_region.html renders its placement modifier off a `placement`
    # context variable (the ADR-060 rename). shell/base.html resolves
    # bw_toast_position and must include with placement=, not the old
    # `position=` key, or every shell page silently loses the ability to
    # move the toast region and always renders the top-end default.
    html = _render(template)
    assert "bw-toast-region--top-end" in html


@pytest.mark.parametrize("template", SHELLS)
def test_shell_bw_toast_position_context_var_moves_the_region(template: str) -> None:
    html = _render(template, bw_toast_position="bottom-start")
    assert "bw-toast-region--bottom-start" in html
    assert "bw-toast-region--top-end" not in html


# --- theme / density / direction attributes (four axes) --------------------


def test_shell_defaults_are_light_comfortable_ltr() -> None:
    html = _render("brickwork/shell/app.html")
    assert 'data-theme="light"' in html
    assert 'data-density="comfortable"' in html
    assert 'dir="ltr"' in html


def test_shell_honours_theme_density_dir_context() -> None:
    html = _render(
        "brickwork/shell/app.html",
        bw_theme="dark",
        bw_density="compact",
        bw_dir="rtl",
    )
    assert 'data-theme="dark"' in html
    assert 'data-density="compact"' in html
    assert 'dir="rtl"' in html


def test_shell_links_the_stable_css_artefact() -> None:
    html = _render("brickwork/shell/app.html")
    # referenced by plain {% static %}, stable filename (no hash)
    assert re.search(r'href="[^"]*brickwork/dist/brickwork\.css"', html)


# --- app shell structure (SHL region) --------------------------------------


def test_app_shell_has_sidebar_topbar_workspace() -> None:
    html = _render("brickwork/shell/app.html")
    assert 'class="bw-sidebar"' in html
    assert 'class="bw-topbar"' in html
    assert 'class="bw-workspace"' in html


def test_app_shell_mobile_drawer_is_native_details() -> None:
    # SHL-015/016: the mobile nav is a native <details>/<summary>, so it works
    # with zero JS. Assert the drawer is a real <details>, not a JS widget.
    html = _render("brickwork/shell/app.html")
    assert "<details" in html
    assert "<summary" in html
    assert 'class="bw-drawer"' in html


def test_app_shell_named_blocks_render_content() -> None:
    # A page filling a block gets its content in the right region. Use the
    # template engine with a child template extending the shell.
    from django.template import Context, Template

    child = Template(
        "{% extends 'brickwork/shell/app.html' %}"
        "{% block content %}<p id='probe'>hello workspace</p>{% endblock %}"
        "{% block topbar_search %}<input id='search'>{% endblock %}"
    )
    html = child.render(Context({}))
    assert "<p id='probe'>hello workspace</p>" in html
    assert "<input id='search'>" in html
    # the probe lands inside the workspace/content region
    assert html.index('id="bw-main"') < html.index("id='probe'")


def test_app_shell_wraps_brand_blocks_for_collapse(  # brickwork#93
) -> None:
    # brand_logo and brand_wordmark render inside brickwork-owned wrapper
    # elements (.bw-sidebar__brand-mark / __brand-wordmark) so the collapsed
    # rail can keep the mark and hide the wordmark without knowing the
    # consumer's own inner markup or classes. The wrappers must contain the
    # filled block content.
    from django.template import Context, Template

    child = Template(
        "{% extends 'brickwork/shell/app.html' %}"
        "{% block brand_logo %}<img id='mark' src='/m.svg'>{% endblock %}"
        "{% block brand_wordmark %}<span id='word'>Acme</span>{% endblock %}"
    )
    html = child.render(Context({}))
    assert "<span class=\"bw-sidebar__brand-mark\"><img id='mark' src='/m.svg'></span>" in html
    assert "<span class=\"bw-sidebar__brand-wordmark\"><span id='word'>Acme</span></span>" in html
    # both wrappers sit inside the sidebar header, before the toggle
    assert html.index("bw-sidebar__header") < html.index("bw-sidebar__brand-mark")
    assert html.index("bw-sidebar__brand-mark") < html.index("bw-sidebar__brand-wordmark")
    assert html.index("bw-sidebar__brand-wordmark") < html.index("bw-sidebar__toggle")


def test_app_shell_brand_wrappers_exist_even_when_blocks_unfilled(  # brickwork#93
) -> None:
    # The wrappers are always emitted (empty when a block is unfilled); the CSS
    # collapses an :empty wrapper to nothing, so a consumer filling neither
    # block still gets a clean header. Structural guarantee: both wrappers are
    # present in the default shell render.
    html = _render("brickwork/shell/app.html")
    assert 'class="bw-sidebar__brand-mark"' in html
    assert 'class="bw-sidebar__brand-wordmark"' in html


def test_layout_arg_selects_sidebar_vs_topbar(  # SHL-001
) -> None:
    sidebar = _render("brickwork/shell/app.html", layout="sidebar")
    topbar = _render("brickwork/shell/app.html", layout="topbar")
    assert 'data-layout="sidebar"' in sidebar
    assert 'data-layout="topbar"' in topbar


def test_layout_defaults_to_sidebar_when_unset() -> None:  # SHL-001
    html = _render("brickwork/shell/app.html")
    assert 'data-layout="sidebar"' in html


def test_layout_context_renders_through_an_extending_page() -> None:  # SHL-001
    # The layout ARG is a plain context var, so it must flow through a
    # consuming page's {% extends %} chain to the shell's data-layout hook
    # (the CSS-only topbar restyle keys off that attribute, 0.6.0).
    from django.template import Context, Template

    child = Template("{% extends 'brickwork/shell/app.html' %}{% block content %}<p id='probe'>x</p>{% endblock %}")
    html = child.render(Context({"layout": "topbar"}))
    assert 'data-layout="topbar"' in html
    assert "<p id='probe'>x</p>" in html
