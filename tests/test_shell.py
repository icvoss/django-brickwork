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
    html = _render(template)
    assert "<script" not in html.lower(), f"{template} emitted a <script> tag"


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


def test_layout_arg_selects_sidebar_vs_topbar(  # SHL-001
) -> None:
    sidebar = _render("brickwork/shell/app.html", layout="sidebar")
    topbar = _render("brickwork/shell/app.html", layout="topbar")
    assert 'data-layout="sidebar"' in sidebar
    assert 'data-layout="topbar"' in topbar
