"""Tests for the icon registry and the {% bw_icon %} tag (ICO region of the-wall).

Covers the CORE bricks: ICO-001 (registry + seed), ICO-003 (name-not-raw-SVG,
injection-safe), ICO-004 (sizing), ICO-007 (decorative-vs-meaningful enforced),
ICO-013 (missing name fails loudly), plus ICO-014 (directional RTL flip) and
the #88 file-type seed set (video/audio/document/image/archive/spreadsheet).
"""

from __future__ import annotations

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

import brickwork.icons as icons  # for the live ICON_NAMES re-export (see below)
from brickwork.icons import (
    IconNotFoundError,
    get_icon,
    is_directional,
    register_icons,
)

# ICON_NAMES is a live, computed re-export (module __getattr__), so it must be
# read as an attribute (icons.ICON_NAMES) to reflect register_icons() calls;
# a `from brickwork.icons import ICON_NAMES` would freeze a snapshot at import
# time and miss later registrations.


def _render(snippet: str, **context: object) -> str:
    return Template("{% load brickwork_icons %}" + snippet).render(Context(context))


# --- registry (ICO-001) ---------------------------------------------------


def test_registry_resolves_a_seeded_name() -> None:
    inner = get_icon("trash")
    assert "<path" in inner  # inner paint markup, not a full <svg> wrapper
    assert "<svg" not in inner


def test_registry_strips_the_svg_wrapper_and_licence_comment() -> None:
    inner = get_icon("search")
    assert "width=" not in inner  # the fixed 24x24 wrapper is gone
    assert "@license" not in inner  # the vendored licence comment is stripped


def test_icon_names_is_the_sorted_contract_surface() -> None:
    names = icons.ICON_NAMES
    assert names == tuple(sorted(names))
    # a representative slice of the curated admin subset must be present
    for expected in ("trash", "chevron-down", "search", "menu", "alert-circle"):
        assert expected in names


def test_canonical_names_resolve_lucide_renames() -> None:
    # "trash" -> lucide trash-2, "edit" -> lucide square-pen: both must resolve
    # (the alias-table safety net; lucide-static ships no machine-readable map).
    assert get_icon("trash")
    assert get_icon("edit")


# --- missing name fails loudly (ICO-013) ----------------------------------


def test_unknown_name_raises_naming_the_icon() -> None:
    with pytest.raises(IconNotFoundError) as exc:
        get_icon("no-such-icon")
    assert "no-such-icon" in str(exc.value)


def test_tag_with_unknown_name_raises_not_blank() -> None:
    with pytest.raises(IconNotFoundError):
        _render('{% bw_icon "definitely-not-real" decorative=True %}')


# --- accessibility pairing enforced (ICO-007) -----------------------------


def test_decorative_icon_is_aria_hidden() -> None:
    out = _render('{% bw_icon "chevron-down" decorative=True %}')
    assert 'aria-hidden="true"' in out
    assert "role=" not in out


def test_meaningful_icon_gets_role_img_and_label() -> None:
    out = _render('{% bw_icon "trash" label="Delete item" %}')
    assert 'role="img"' in out
    assert 'aria-label="Delete item"' in out
    assert "aria-hidden" not in out


def test_icon_with_neither_label_nor_decorative_is_a_render_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_icon "trash" %}')


def test_icon_with_both_label_and_decorative_is_a_render_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_icon "trash" label="x" decorative=True %}')


# --- injection safety (ICO-003) -------------------------------------------


def test_label_is_html_escaped_never_raw() -> None:
    out = _render('{% bw_icon "trash" label=evil %}', evil='"><script>alert(1)</script>')
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_name_is_not_a_raw_svg_injection_vector() -> None:
    # A name is a registry key, never markup: an SVG-shaped "name" is simply an
    # unknown key and raises, it never reaches output as markup.
    with pytest.raises(IconNotFoundError):
        _render("{% bw_icon evil decorative=True %}", evil="<svg onload=alert(1)>")


# --- sizing (ICO-004) -----------------------------------------------------


def test_default_size_is_md_token() -> None:
    out = _render('{% bw_icon "trash" decorative=True %}')
    assert "--bw-icon-size: var(--bw-component-icon-size-md)" in out


@pytest.mark.parametrize("size", ["sm", "md", "lg", "xl"])
def test_each_valid_size_maps_to_its_token(size: str) -> None:
    out = _render(f'{{% bw_icon "trash" size="{size}" decorative=True %}}')
    # ICO-004: the token is applied via the --bw-icon-size CSS custom property
    # (which .bw-icon reads for width/height), NOT as an SVG width/height
    # attribute. SVG geometry attributes reject var(), so an attribute form
    # would silently render at the 300x150 default (issue #16). The size maps
    # to the canonical --bw-component-icon-size-* token (0.11.0 tier re-grammar:
    # --bw-icon-size-* and --bw-size-icon-* both collapsed into the component tier).
    assert f"--bw-icon-size: var(--bw-component-icon-size-{size})" in out
    # Match the SVG geometry attributes exactly (bounded by a space before
    # "width"), not as a bare substring: "stroke-width=" legitimately contains
    # "width=" and must not trip this assertion.
    assert ' width="var(' not in out
    assert ' height="var(' not in out


def test_invalid_size_is_a_render_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_icon "trash" size="huge" decorative=True %}')


# --- directional RTL flip (ICO-014) ---------------------------------------


def test_directional_icon_gets_the_flip_class() -> None:
    assert is_directional("chevron-forward")
    out = _render('{% bw_icon "chevron-forward" decorative=True %}')
    assert "bw-icon-directional" in out


def test_symmetric_icon_does_not_flip() -> None:
    assert not is_directional("search")
    out = _render('{% bw_icon "search" label="Search" %}')
    assert "bw-icon-directional" not in out


# --- file-type icons (#88, grown-on-demand seed per ICO-001) ---------------

_FILE_TYPE_NAMES = ("video", "audio", "document", "image", "archive", "spreadsheet")


@pytest.mark.parametrize("name", _FILE_TYPE_NAMES)
def test_file_type_icon_is_seeded(name: str) -> None:
    inner = get_icon(name)
    assert "<path" in inner  # inner paint markup, not a full <svg> wrapper
    assert "<svg" not in inner
    assert name in icons.ICON_NAMES


def test_file_type_icons_render_distinct_artwork() -> None:
    # The point of #88: a mixed media listing must be able to show a distinct
    # per-type badge, not one generic glyph for every non-image asset.
    glyphs = {get_icon(name) for name in ("video", "audio", "image", "archive", "spreadsheet")}
    assert len(glyphs) == 5


def test_document_shares_the_generic_file_artwork() -> None:
    # Deliberate alias: the text-lines glyph is the document icon, and the
    # generic "file" seeded that same artwork before the typed set existed.
    assert get_icon("document") == get_icon("file")


@pytest.mark.parametrize("name", _FILE_TYPE_NAMES)
def test_file_type_icons_are_not_directional(name: str) -> None:
    # File badges are symmetric glyphs; none flip under RTL (ICO-014).
    assert not is_directional(name)


def test_file_type_icon_renders_through_the_tag() -> None:
    out = _render('{% bw_icon "video" label="Video file" %}')
    assert 'role="img"' in out
    assert 'aria-label="Video file"' in out


# --- swap / project-merge (ICO-002 / ICO-012) -----------------------------


def test_register_icons_merges_and_can_flag_directional() -> None:
    register_icons(
        {"myapp-widget": '<path d="M1 1h10v10H1z" />'},
        directional=("myapp-widget",),
    )
    assert get_icon("myapp-widget")
    assert is_directional("myapp-widget")
    assert "myapp-widget" in icons.ICON_NAMES
