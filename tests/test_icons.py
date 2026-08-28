"""Tests for the icon registry and the {% bw_icon %} tag (ICO region of the-wall).

Covers the CORE bricks: ICO-001 (registry + seed), ICO-003 (name-not-raw-SVG,
injection-safe), ICO-004 (sizing), ICO-007 (decorative-vs-meaningful enforced),
ICO-013 (missing name fails loudly), plus ICO-014 (directional RTL flip) and
the #88 file-type seed set (video/audio/document/image/archive/spreadsheet).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import mark_safe

import brickwork.icons as icons  # for the live ICON_NAMES re-export (see below)
from brickwork.icons import (
    IconNotFoundError,
    get_icon,
    is_directional,
    register_icons,
)
from brickwork.templatetags.brickwork_icons import bw_icon

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


# --- the exception hierarchy is mask-proof (brickwork#74) ------------------


def test_icon_not_found_error_is_not_a_keyerror() -> None:
    # Django 6's {% partialdef %}/{% partial %} machinery catches a bare
    # KeyError and re-reports it as "Partial ... is not defined", so the
    # exception must never be a KeyError or a typoed icon name inside a partial
    # points the consumer at a phantom missing partial (#74).
    assert not issubclass(IconNotFoundError, KeyError)


def test_icon_not_found_error_is_a_lookuperror_and_a_brickworkerror() -> None:
    from brickwork.exceptions import BrickworkError

    assert issubclass(IconNotFoundError, LookupError)
    assert issubclass(IconNotFoundError, BrickworkError)


def test_unknown_name_close_to_a_registered_one_gets_a_suggestion() -> None:
    with pytest.raises(IconNotFoundError) as exc:
        get_icon("chevron-dwn")
    msg = str(exc.value)
    assert "chevron-dwn" in msg
    assert "Did you mean" in msg
    assert "chevron-down" in msg


def test_unknown_name_with_no_near_miss_gets_no_suggestion() -> None:
    with pytest.raises(IconNotFoundError) as exc:
        get_icon("zzz-completely-unrelated")
    assert "Did you mean" not in str(exc.value)


def test_icon_error_inside_a_template_partial_is_not_masked() -> None:
    # The #74 repro: an unknown icon raised INSIDE a {% partialdef %} body. With
    # a KeyError-based exception, Django's partial machinery swallowed it and
    # re-raised "Partial 'probe' is not defined in the current template"; the
    # real error must surface instead, naming the icon.
    template = Template(
        "{% load brickwork_icons %}"
        "{% partialdef probe %}{% bw_icon 'chevron-dwn' decorative=True %}{% endpartialdef %}"
        "{% partial probe %}"
    )
    with pytest.raises(IconNotFoundError) as exc:
        template.render(Context({}))
    msg = str(exc.value)
    assert "chevron-dwn" in msg
    assert "Partial" not in msg


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


@pytest.mark.parametrize("blank", ["   ", "\t", "\n", " \t\n "])
def test_whitespace_only_label_is_not_an_accessible_name(blank: str) -> None:
    """A hard-required check that " " satisfies is not a requirement.

    Calls the tag function directly rather than through a template literal:
    a raw newline inside {% bw_icon label="..." %} does not survive Django's
    template parser, so the template route would test the parser rather than
    this contract for two of the four parametrised cases.
    """
    with pytest.raises(TemplateSyntaxError):
        bw_icon("trash", label=blank)


@pytest.mark.parametrize("blank", ["   ", "\t", "\n", " \t\n "])
def test_whitespace_only_label_with_decorative_is_accepted_as_decorative(blank: str) -> None:
    # Before the fix, a whitespace-only label is truthy, so decorative=True
    # plus label="   " hit the "pass either...not both" branch and raised.
    # After stripping, label collapses to "" before either branch is tested,
    # so this renders decorative and never raises. Fails without the fix.
    out = bw_icon("trash", decorative=True, label=blank)
    assert 'aria-hidden="true"' in out
    assert "role=" not in out


def test_padded_label_is_stripped_not_rejected() -> None:
    # Stripping must not turn a real name with stray spaces into an error.
    out = bw_icon("trash", label="  Delete item  ")
    assert 'aria-label="Delete item"' in out


def test_non_str_label_via_ordinary_template_syntax_does_not_raise() -> None:
    # #330 regression: bw_icon's label = label.strip() raised AttributeError
    # on any non-str value. Rendered through ordinary template syntax (not a
    # direct call), since that is how the regression actually reaches a
    # consumer: {% bw_icon n label=n %} with an int context variable is
    # entirely ordinary Django, not a contrived call. Fails without the fix
    # (AttributeError: 'int' object has no attribute 'strip').
    out = _render('{% bw_icon "trash" label=n %}', n=5)
    assert 'aria-label="5"' in out


def test_str_able_object_label_renders_its_str_form() -> None:
    # A model instance or any other __str__-able object as a label is
    # ordinary Django usage. Fails without the fix for the same reason as
    # the int case above.
    class _Labelled:
        def __str__(self) -> str:
            return "Widget One"

    out = _render('{% bw_icon "trash" label=obj %}', obj=_Labelled())
    assert 'aria-label="Widget One"' in out


# --- injection safety (ICO-003) -------------------------------------------


def test_label_is_html_escaped_never_raw() -> None:
    out = _render('{% bw_icon "trash" label=evil %}', evil='"><script>alert(1)</script>')
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_css_class_is_html_escaped_never_raw() -> None:
    out = _render('{% bw_icon "trash" decorative=True css_class=evil %}', evil='"><script>alert(1)</script>')
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_mark_safed_css_class_is_still_escaped_not_a_breakout() -> None:
    # The #329 repro: conditional_escape honours __html__, so a SafeString
    # passed through it renders VERBATIM in the class attribute, closing the
    # quote and landing a live attribute on the element. A plain string was
    # always escaped correctly (the test above already covers that); this is
    # the case that only fails without the fix, because only a SafeString
    # exercises conditional_escape's __html__ passthrough at all.
    out = _render(
        '{% bw_icon "trash" decorative=True css_class=evil %}',
        evil=mark_safe('a" onmouseover="alert(1)'),
    )
    assert 'onmouseover="alert(1)"' not in out
    assert "&quot;" in out


def test_mark_safed_label_is_still_escaped_not_a_breakout() -> None:
    # Same repro as the css_class case above, on the other attribute-value
    # call site (brickwork_icons.py:96's aria-label). Fails without the fix
    # for the same reason: a plain string was already safe, only a
    # SafeString exercises conditional_escape's __html__ passthrough.
    out = _render(
        '{% bw_icon "trash" label=evil %}',
        evil=mark_safe('a" onmouseover="alert(1)'),
    )
    assert 'onmouseover="alert(1)"' not in out
    assert "&quot;" in out


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


def test_reregistering_a_seed_name_overrides_and_keeps_the_directional_flag() -> None:
    # Override semantics (#77): re-registering an existing name is the supported
    # whole-glyph swap, and a seed-directional name stays directional when its
    # glyph is swapped (the flag set only accumulates), so a family swap keeps
    # the RTL mirror working with no extra wiring.
    original = get_icon("chevron-forward")
    assert is_directional("chevron-forward")
    try:
        register_icons({"chevron-forward": '<path d="M2 2l10 10" />'})
        assert get_icon("chevron-forward") == '<path d="M2 2l10 10" />'
        assert is_directional("chevron-forward")
    finally:
        register_icons({"chevron-forward": original})  # revert = register back


def test_registered_icon_markup_is_trusted_by_contract_not_vetted() -> None:
    # Documents the corrected bw_icon noqa justification (icvoss/django-brickwork
    # #330): register_icons() is a public, documented API (ICO-002/ICO-012) that
    # merges its mapping into the registry with no validation. This is NOT a bug
    # to fix here (that is a separate, deliberately out-of-scope design
    # decision): it is the same trust boundary as any other mark_safe call, and
    # this test exists so the "inner is vetted" claim never silently regresses
    # back into the noqa comment without a test noticing the registry has no
    # gate. A consumer registering unsanitised markup gets it rendered raw.
    try:
        register_icons({"pwn-330": '"><script>alert(1)</script>'})
        out = bw_icon("pwn-330", decorative=True)
        assert "<script>alert(1)</script>" in out
    finally:
        icons._registry._ICONS.pop("pwn-330", None)


# --- the chrome-internal name list is documented and cannot rot (#77) ------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SHIPPED_TEMPLATES = _REPO_ROOT / "src" / "brickwork" / "templates"
_INTEGRATION_DOC = _REPO_ROOT / "docs" / "INTEGRATION.md"

# The literal-name grammar the shipped templates use; a variable-valued
# {% bw_icon item.icon %} is consumer data, not a chrome dependency, and is
# deliberately not matched.
# Two shapes count as a hard reference. The first is the direct
# {% bw_icon "name" %} call. The second is an icon_name="name" binding on a
# {% with %} that feeds a partial calling {% bw_icon icon_name %}: introduced by
# the sort_link partial (#137), where the name is still a literal in the
# template text, just bound one step earlier. Scanning only the direct form
# would let the guard lose sight of an icon the template genuinely ships, which
# is the exact rot #77 exists to prevent.
_TEMPLATE_ICON_LITERAL = re.compile(r'bw_icon\s+"([a-z0-9-]+)"|icon_name="([a-z0-9-]+)"')
_DOC_MARKED_REGION = re.compile(
    r"<!-- chrome-icon-names:start -->(.*?)<!-- chrome-icon-names:end -->",
    re.DOTALL,
)


def _chrome_names_from_templates() -> set[str]:
    names: set[str] = set()
    for path in sorted(_SHIPPED_TEMPLATES.rglob("*.html")):
        for direct, bound in _TEMPLATE_ICON_LITERAL.findall(path.read_text(encoding="utf-8")):
            names.add(direct or bound)
    return names


def _chrome_names_from_doc() -> set[str]:
    match = _DOC_MARKED_REGION.search(_INTEGRATION_DOC.read_text(encoding="utf-8"))
    assert match is not None, "INTEGRATION.md must keep the chrome-icon-names markers (#77)"
    return set(re.findall(r"`([a-z0-9-]+)`", match.group(1)))


def test_documented_chrome_icon_list_matches_the_shipped_templates() -> None:
    # The drift guard (#77): the minimum-set list INTEGRATION.md publishes for
    # alternate-family consumers must equal the names the shipped templates
    # actually hard-reference. A template gaining or losing a chrome icon
    # without the doc moving fails here, so the published contract cannot rot.
    assert _chrome_names_from_doc() == _chrome_names_from_templates()


def test_every_chrome_referenced_name_is_registered_in_the_seed() -> None:
    # The chrome must render out of the box: every name a shipped template
    # hard-references resolves against the seed with no consumer registration.
    for name in sorted(_chrome_names_from_templates()):
        assert get_icon(name)
