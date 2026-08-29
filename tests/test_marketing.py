"""Render tests for the marketing kit (`brickwork.marketing`, 2.0.0, spec 04
section 4d, business rules section 9, BR-BW-MKT-001..005).

As of 2.0.0 (ADR-056) the kit ships COMPONENTS and a SHELL, and no pages: the
three marketing page templates a consumer used to {% extends %} and feed a
flat page-level context bag are retired, and the copy-paste examples that
replace them are package data covered by test_examples.py. So the contracts
under test here are the two surfaces that remain semver-public:

BR-BW-MKT-005 / BR-BW-PAGE-002 at marketing scope: the marketing shell renders
a complete valid document with nothing but its own blocks, carries the public
header/footer chrome and never the app shell's, and every block empties
gracefully.
BR-BW-MKT-004 (reuse, not reimplementation): the FAQ composes
``_disclosure.html`` and the stat band composes ``_stat.html``'s tile shape.
BR-BW-MKT-001: the sub-app ships no models, migrations, views, or URLs.

These tests drive the shell the way a consumer's own page does ({% extends %}
plus block overrides) and each component the way that page's body does
({% include %} plus context), mirroring the examples' composition exactly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

_DIST = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist"


def _render(template: str, request=None, **ctx: object) -> str:
    return render_to_string(template, ctx, request=request)


def _extend(parent: str, blocks: str, **ctx: object) -> str:
    return Template("{% extends '" + parent + "' %}" + blocks).render(Context(ctx))


def _include(template: str, **ctx: object) -> str:
    source = "{% include '" + template + "' with " + " ".join(f"{k}={k}" for k in ctx) + " %}"
    return Template(source).render(Context(ctx))


def _assert_complete_document(html: str) -> None:
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert 'id="bw-main"' in html


_MARKETING_SHELL = "brickwork_marketing/shell/marketing.html"


# --- BR-BW-MKT-001: sub-app ships no models/migrations/views/urls -----------


def test_marketing_sub_app_ships_no_models_or_urls() -> None:
    from django.apps import apps

    config = apps.get_app_config("brickwork_marketing")
    assert list(config.get_models()) == []
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("brickwork.marketing.urls")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("brickwork.marketing.models")


# --- shell/marketing.html: empty-graceful + chrome (BR-BW-MKT-005) ----------


def test_the_marketing_shell_with_no_blocks_filled_renders_a_complete_document() -> None:
    # BR-BW-PAGE-002 at marketing scope: the shell is what a consumer's own
    # page extends, so it must stand up as a valid document before that page
    # has filled a single block.
    html = _extend(_MARKETING_SHELL, "")
    _assert_complete_document(html)


def test_the_marketing_shell_carries_the_public_chrome_not_the_app_shell_s() -> None:
    html = _extend(_MARKETING_SHELL, "")
    assert "bw-marketing" in html
    assert "bw-marketing-header" in html
    assert "bw-marketing-footer" in html
    # never the app shell's chrome
    assert "bw-sidebar" not in html
    assert "bw-topbar" not in html
    assert "bw-app" not in html


def test_the_marketing_shell_fabricates_no_marketing_copy_of_its_own() -> None:
    # BR-BW-TPL-006: the shell owns chrome, never content. An unfilled shell
    # must not invent a hero, a pricing table, or any other section: the page
    # body is entirely the consumer's, so none of the component wrapper
    # classes may appear until that consumer composes one.
    html = _extend(_MARKETING_SHELL, "")
    assert "bw-hero" not in html
    assert "bw-feature-card" not in html
    assert "bw-pricing-tier" not in html
    assert 'class="bw-cta' not in html
    assert 'class="bw-testimonial"' not in html
    assert "bw-logo-cloud__grid" not in html
    assert 'bw-stat-band"' not in html and "bw-stat-band " not in html
    assert "<details" not in html  # no FAQ disclosures rendered


def test_the_marketing_shell_content_block_lands_inside_the_main_region() -> None:
    # The one region a page fills. It must land inside #bw-main (the skip
    # link's target), not in the header or footer chrome.
    html = _extend(_MARKETING_SHELL, "{% block content %}CONTENT-SENTINEL{% endblock %}")
    main_start = html.index('id="bw-main"')
    footer_start = html.index("bw-marketing-footer")
    assert main_start < html.index("CONTENT-SENTINEL") < footer_start


# --- shell/marketing.html: *_region wrapper blocks (icvoss/django-brickwork#263) --

# marketing_nav_region, marketing_actions_region and marketing_footer_region
# extend the app shell's subnav_region/breadcrumbs_region/page_header_region/
# footer_region idiom (BR-BW-TPL-001) to the marketing shell: a second, outer
# override seam around the wrapper ELEMENT, distinct from filling the inner
# content block. #263's consumer needed exactly this: a mobile-nav toggle as
# a sibling of the nav, without filling the outer marketing_header block and
# reproducing brand_logo/brand_wordmark/marketing_nav/marketing_actions.


def test_filling_only_the_inner_block_is_unaffected_by_the_new_region_wrappers() -> None:
    # Behaviour-preserving (the measured guarantee this change must not
    # break): a consumer who only ever filled the inner blocks (the pre-#263
    # seam) still gets the same wrapper markup, in the same position, that
    # existed before the _region blocks were added. The three wrapper
    # elements and their attributes survive untouched, and the filled
    # content still lands inside them, in header-then-footer document order.
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_nav %}<a href='/pricing/'>Pricing</a>{% endblock %}"
        "{% block marketing_actions %}<a href='/signup/'>Get started</a>{% endblock %}"
        "{% block marketing_footer %}<a href='/about/'>About</a>{% endblock %}",
    )
    assert '<nav class="bw-marketing-header__nav" aria-label="Primary">' in html
    assert '<div class="bw-marketing-header__actions">' in html
    assert '<footer class="bw-marketing-footer">' in html
    nav_start = html.index('class="bw-marketing-header__nav"')
    pricing_start = html.index("<a href='/pricing/'>Pricing</a>")
    actions_start = html.index('class="bw-marketing-header__actions"')
    get_started_start = html.index("<a href='/signup/'>Get started</a>")
    footer_start = html.index('class="bw-marketing-footer"')
    about_start = html.index("<a href='/about/'>About</a>")
    assert nav_start < pricing_start < actions_start < get_started_start < footer_start < about_start


def test_overriding_marketing_nav_region_replaces_the_nav_wrapper() -> None:
    # The new capability: a consumer overrides the _region block to replace
    # the <nav> element itself (here, to add a sibling mobile-nav toggle next
    # to it), rather than the app shell forcing a wholesale marketing_header
    # override to reach the same seam.
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_nav_region %}"
        '<div id="nav-region-replacement">'
        "<a href='/pricing/'>Pricing</a>"
        "</div>"
        "{% endblock %}",
    )
    assert '<div id="nav-region-replacement">' in html
    assert "bw-marketing-header__nav" not in html
    assert "<a href='/pricing/'>Pricing</a>" in html


def test_overriding_marketing_actions_region_replaces_the_actions_wrapper() -> None:
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_actions_region %}"
        '<div id="actions-region-replacement">'
        "<a href='/signup/'>Get started</a>"
        "</div>"
        "{% endblock %}",
    )
    assert '<div id="actions-region-replacement">' in html
    assert "bw-marketing-header__actions" not in html
    assert "<a href='/signup/'>Get started</a>" in html


def test_overriding_marketing_footer_region_replaces_the_footer_wrapper() -> None:
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_footer_region %}<div id='footer-region-replacement'>Replacement footer</div>{% endblock %}",
    )
    assert "<div id='footer-region-replacement'>Replacement footer</div>" in html
    assert "bw-marketing-footer" not in html


def test_overriding_marketing_nav_region_empty_removes_the_nav_and_its_chrome() -> None:
    # The capability filling the inner block alone can never offer: the
    # wrapper element itself is gone, not merely empty. marketing_actions
    # still renders, proving the removal is scoped to the nav region only.
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_nav_region %}{% endblock %}"
        "{% block marketing_actions %}<a href='/signup/'>Get started</a>{% endblock %}",
    )
    assert "bw-marketing-header__nav" not in html
    assert "<nav" not in html
    assert "bw-marketing-header__actions" in html
    assert "<a href='/signup/'>Get started</a>" in html


def test_overriding_marketing_actions_region_empty_removes_the_actions_and_its_chrome() -> None:
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_nav %}<a href='/pricing/'>Pricing</a>{% endblock %}"
        "{% block marketing_actions_region %}{% endblock %}",
    )
    assert "bw-marketing-header__actions" not in html
    assert "bw-marketing-header__nav" in html
    assert "<a href='/pricing/'>Pricing</a>" in html


def test_overriding_marketing_footer_region_empty_removes_the_footer_and_its_chrome() -> None:
    html = _extend(
        _MARKETING_SHELL,
        "{% block content %}CONTENT-SENTINEL{% endblock %}{% block marketing_footer_region %}{% endblock %}",
    )
    assert "bw-marketing-footer" not in html
    assert "<footer" not in html
    # the rest of the document is untouched
    assert "CONTENT-SENTINEL" in html
    _assert_complete_document(html)


def test_the_existing_block_names_all_still_render() -> None:
    # Constraint 1: every pre-#263 block name survives unchanged, in the same
    # position, once the region wrappers are added around some of them.
    #
    # The shell defines TEN unique block names on main (shell, shell_variant,
    # marketing_header, brand_logo, brand_wordmark, marketing_nav,
    # marketing_actions, content, marketing_footer, footer_legal). A bare
    # `grep -c "{% block"` reports eleven because marketing_actions appears a
    # second time inside the docstring's own auth-aware example, which is
    # prose rather than a block: count the names, not the tag occurrences.
    #
    # Nine of the ten are asserted below. `shell` is deliberately excluded:
    # overriding it replaces the entire shell body, so filling it would
    # remove the very regions the other assertions look for, and it is
    # covered by base.html's own tests rather than here.
    html = _extend(
        _MARKETING_SHELL,
        "{% block marketing_header %}HEADER-SENTINEL{% endblock %}"
        "{% block brand_logo %}LOGO-SENTINEL{% endblock %}"
        "{% block brand_wordmark %}WORDMARK-SENTINEL{% endblock %}"
        "{% block marketing_nav %}NAV-SENTINEL{% endblock %}"
        "{% block marketing_actions %}ACTIONS-SENTINEL{% endblock %}"
        "{% block content %}CONTENT-SENTINEL{% endblock %}"
        "{% block marketing_footer %}FOOTER-SENTINEL{% endblock %}"
        "{% block footer_legal %}LEGAL-SENTINEL{% endblock %}",
    )
    # marketing_header is overridden wholesale here, so it wins outright and
    # its own nested blocks (brand_logo etc.) are not independently rendered;
    # this proves the block still exists and is fillable, matching the
    # pre-existing single-block-override behaviour class.
    assert "HEADER-SENTINEL" in html
    assert "CONTENT-SENTINEL" in html
    assert "FOOTER-SENTINEL" in html
    assert "LEGAL-SENTINEL" in html

    # Filled independently (without overriding the parent marketing_header
    # block), each of the remaining names still renders in its own slot.
    independently_filled = _extend(
        _MARKETING_SHELL,
        "{% block brand_logo %}LOGO-SENTINEL{% endblock %}"
        "{% block brand_wordmark %}WORDMARK-SENTINEL{% endblock %}"
        "{% block marketing_nav %}NAV-SENTINEL{% endblock %}"
        "{% block marketing_actions %}ACTIONS-SENTINEL{% endblock %}",
    )
    assert "LOGO-SENTINEL" in independently_filled
    assert "WORDMARK-SENTINEL" in independently_filled
    assert "NAV-SENTINEL" in independently_filled
    assert "ACTIONS-SENTINEL" in independently_filled
    # shell_variant is also a pre-existing block name, asserted separately
    # since it renders into a class attribute rather than visible content.
    assert "bw-shell--marketing" in _extend(_MARKETING_SHELL, "")


# --- Accessibility invariant: the hero owns the single <h1> -----------------


def test_a_shell_composed_hero_heading_is_the_page_s_only_h1() -> None:
    # The hero renders its heading as h1 and the shell contributes none of its
    # own, so a page composing one hero has exactly one h1. This is the whole
    # of the "one h1 per page" invariant brickwork can hold: section count and
    # order are the consumer's own file now (ADR-056).
    html = _extend(
        _MARKETING_SHELL,
        "{% block content %}"
        "{% include 'brickwork_marketing/components/_hero.html' with heading=heading %}"
        "{% include 'brickwork_marketing/components/_feature_grid.html' with heading=features_heading %}"
        "{% endblock %}",
        heading="The one heading",
        features_heading="Why us",
    )
    assert html.count("<h1") == 1
    assert "The one heading" in html and "Why us" in html


def test_hero_with_no_heading_renders_no_h1() -> None:
    html = _render("brickwork_marketing/components/_hero.html")
    assert "<h1" not in html


# --- components/_hero.html --------------------------------------------------


def test_hero_all_empty_renders_a_bare_hero_band() -> None:
    html = _render("brickwork_marketing/components/_hero.html")
    assert "bw-hero" in html
    assert "bw-hero__eyebrow" not in html
    assert "bw-hero__lede" not in html
    assert "bw-hero__media" not in html
    assert "bw-hero__actions" not in html


def test_hero_heading_only_output_is_byte_identical_to_pre_slot_blocks() -> None:
    # Full-string equality: substring checks above would pass on a
    # whitespace-only regression from a stray {% if %} inside a new block.
    html = _render("brickwork_marketing/components/_hero.html", heading="Ship faster")
    assert html == (
        '\n\n<section class="bw-hero bw-hero--start">\n  <div class="bw-hero__copy">\n    \n    '
        '<h1 class="bw-hero__heading">Ship faster</h1>\n    \n    \n    \n    \n  </div>\n  \n</section>\n'
    )


def test_hero_with_full_context_renders_every_region() -> None:
    html = _include(
        "brickwork_marketing/components/_hero.html",
        eyebrow="New",
        heading="Ship faster",
        lede="The all-in-one platform.",
        primary_cta={"label": "Get started", "url": "/start/"},
        secondary_cta={"label": "Learn more", "url": "/learn/"},
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
        align="center",
    )
    assert "New" in html
    assert "Ship faster" in html
    assert "The all-in-one platform." in html
    assert "Get started" in html and 'href="/start/"' in html
    assert "Learn more" in html and 'href="/learn/"' in html
    assert "<img src='/hero.png'" in html
    assert "bw-hero--center" in html


def test_hero_media_omitted_renders_no_broken_image_box() -> None:
    html = _render("brickwork_marketing/components/_hero.html", heading="Text only")
    assert "bw-hero__media" not in html
    assert "<img" not in html


def test_hero_default_align_is_start() -> None:
    html = _render("brickwork_marketing/components/_hero.html", heading="Aligned")
    assert "bw-hero--start" in html


# --- components/_hero.html: media_placement (ADR-057 section 1a, #118) ------


def test_hero_media_placement_omitted_emits_no_modifier_class() -> None:
    # "below" (the shipped column-flex layout, media after the copy) is the
    # honestly-named default and is byte-identical to the pre-option output,
    # per test_hero_heading_only_output_is_byte_identical_to_pre_slot_blocks:
    # this test covers the same invariant when media is present too.
    html = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Ship faster",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert "bw-hero--media-behind" not in html
    assert "bw-hero--media-beside" not in html


def test_hero_media_placement_below_is_explicitly_the_same_as_omitted() -> None:
    omitted = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Ship faster",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
    )
    explicit = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Ship faster",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
        media_placement="below",
    )
    assert omitted == explicit


def test_hero_media_placement_behind_emits_its_modifier_class() -> None:
    html = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Framed",
        media=mark_safe("<svg viewBox='0 0 1 1'></svg>"),
        media_placement="behind",
    )
    assert "bw-hero--media-behind" in html
    assert "bw-hero--media-beside" not in html


def test_hero_media_placement_beside_emits_its_modifier_class() -> None:
    html = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Side by side",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
        media_placement="beside",
    )
    assert "bw-hero--media-beside" in html
    assert "bw-hero--media-behind" not in html


def test_hero_media_placement_is_css_only_and_adds_no_markup() -> None:
    # ADR-057 section 1a's binding rule on CSS-only axes: only the modifier
    # class changes, never the DOM shape. The scrim behind's contrast
    # contract needs is a CSS pseudo-element (::after), not a rendered node.
    below = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Same shape",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
    )
    behind = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Same shape",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
        media_placement="behind",
    )
    beside = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Same shape",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
        media_placement="beside",
    )
    strip_classes = lambda html: re.sub(r'\sclass="[^"]*"', "", html)  # noqa: E731
    assert strip_classes(below) == strip_classes(behind) == strip_classes(beside)


def test_hero_media_placement_unrecognised_value_falls_back_to_default() -> None:
    # _hero.html is include-consumed (no tag), so an unrecognised value
    # cannot raise (BR-BW-OPT-002); the CSS-contract test in
    # test_option_vocabularies.py is the enforcement for documented values,
    # and this pins the fallback behaviour for an undocumented one.
    html = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Ship faster",
        media_placement="sideways",
    )
    assert "bw-hero--media-behind" not in html
    assert "bw-hero--media-beside" not in html


# --- components/_hero.html: flat CTA kwargs (#98) ---------------------------


def test_hero_flat_cta_kwargs_render_identically_to_the_dict_shape() -> None:
    # #98: a template-authored caller cannot build a dict inline, so the CTAs
    # accept flat kwargs; both shapes must produce the same output.
    dict_html = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Ship faster",
        primary_cta={"label": "Get started", "url": "/start/"},
        secondary_cta={"label": "Learn more", "url": "/learn/"},
    )
    flat_html = _include(
        "brickwork_marketing/components/_hero.html",
        heading="Ship faster",
        primary_cta_label="Get started",
        primary_cta_href="/start/",
        secondary_cta_label="Learn more",
        secondary_cta_href="/learn/",
    )
    assert dict_html == flat_html


def test_hero_flat_primary_cta_alone_renders_the_actions_row() -> None:
    html = _include(
        "brickwork_marketing/components/_hero.html",
        primary_cta_label="Get started",
        primary_cta_href="/start/",
    )
    assert "bw-hero__actions" in html
    assert "Get started" in html and 'href="/start/"' in html


def test_hero_dict_wins_outright_when_both_shapes_are_supplied() -> None:
    html = _include(
        "brickwork_marketing/components/_hero.html",
        primary_cta={"label": "Dict label", "url": "/dict/"},
        primary_cta_label="Flat label",
        primary_cta_href="/flat/",
    )
    assert "Dict label" in html and 'href="/dict/"' in html
    assert "Flat label" not in html and "/flat/" not in html


def test_hero_flat_kwargs_forwarded_unset_render_no_actions() -> None:
    # The standing {% include ... with %} pass-through rule (the band
    # precedent): an absent page-level variable forwards as an empty string,
    # which must read as "no CTA", never as an empty button.
    html = Template(
        "{% include 'brickwork_marketing/components/_hero.html' with heading=heading"
        " primary_cta_label=absent_a primary_cta_href=absent_b %}"
    ).render(Context({"heading": "Ship faster"}))
    assert "bw-hero__actions" not in html


# --- components/_hero.html: named blocks (CMP wall, SLOT wave) --------------
#
# BR-BW-OPT-004: eyebrow/heading/lede are prose with no data object behind
# them, so a caller with structured copy (a translated mark, a rich lede with
# an inline link) needs a slot, not another flat-string kwarg. Each block
# wraps the existing conditional rendering, so a call site supplying only the
# flat context variables (tested above) renders unchanged.


def _extend_hero(blocks: str, **ctx: object) -> str:
    return _extend(
        "brickwork_marketing/components/_hero.html",
        "{% load brickwork_components %}" + blocks,
        **ctx,
    )


def test_hero_eyebrow_block_override_wins_over_the_eyebrow_context() -> None:
    html = _extend_hero(
        "{% block eyebrow %}<p>Custom eyebrow</p>{% endblock %}",
        heading="Ship faster",
        eyebrow="Ignored",
    )
    assert "Custom eyebrow" in html
    assert "Ignored" not in html


def test_hero_heading_block_override_wins_over_the_heading_context() -> None:
    html = _extend_hero(
        "{% block heading %}<h1>Custom heading</h1>{% endblock %}",
        heading="Ignored",
    )
    assert "Custom heading" in html
    assert "Ignored" not in html


def test_hero_lede_block_override_wins_over_the_lede_context() -> None:
    html = _extend_hero(
        "{% block lede %}<p>Custom lede</p>{% endblock %}",
        heading="Ship faster",
        lede="Ignored",
    )
    assert "Custom lede" in html
    assert "Ignored" not in html


def test_hero_actions_block_override_replaces_the_default_cta_row() -> None:
    html = _extend_hero(
        "{% block actions %}<div>ACTIONS-SENTINEL</div>{% endblock %}",
        heading="Ship faster",
        primary_cta_label="Get started",
        primary_cta_href="/start/",
    )
    assert "ACTIONS-SENTINEL" in html
    assert "Get started" not in html


def test_hero_media_block_override_replaces_the_default_media_region() -> None:
    html = _extend_hero(
        "{% block media %}<div>MEDIA-SENTINEL</div>{% endblock %}",
        heading="Ship faster",
    )
    assert "MEDIA-SENTINEL" in html


def test_hero_blocks_render_in_document_order() -> None:
    html = _extend_hero(
        "{% block eyebrow %}EYEBROW-SENTINEL{% endblock %}"
        "{% block heading %}HEADING-SENTINEL{% endblock %}"
        "{% block lede %}LEDE-SENTINEL{% endblock %}"
        "{% block actions %}ACTIONS-SENTINEL{% endblock %}"
        "{% block media %}MEDIA-SENTINEL{% endblock %}"
    )
    positions = [
        html.index("EYEBROW-SENTINEL"),
        html.index("HEADING-SENTINEL"),
        html.index("LEDE-SENTINEL"),
        html.index("ACTIONS-SENTINEL"),
        html.index("MEDIA-SENTINEL"),
    ]
    assert positions == sorted(positions), f"hero blocks out of document order: {positions}"


# --- components/_feature_grid.html -----------------------------------------


def test_feature_grid_with_items_renders_every_item() -> None:
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        heading="Why us",
        lede="A better way to build.",
        items=[
            {"icon": "check", "heading": "Fast", "body": "Really fast."},
            {"heading": "Simple", "body": "No fuss."},
        ],
        columns=2,
    )
    assert "Why us" in html
    assert "A better way to build." in html
    assert "Fast" in html and "Really fast." in html
    assert "Simple" in html and "No fuss." in html
    assert "bw-feature-grid--2" in html


def test_feature_grid_empty_items_renders_intro_alone() -> None:
    html = _include("brickwork_marketing/components/_feature_grid.html", heading="Why us")
    assert "Why us" in html
    assert "bw-feature-card" not in html


def test_feature_grid_fully_empty_renders_nothing() -> None:
    html = _render("brickwork_marketing/components/_feature_grid.html")
    assert html.strip() == ""


def test_feature_grid_item_without_icon_renders_no_icon() -> None:
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[{"heading": "Simple", "body": "No fuss."}],
    )
    assert "bw-feature-card__icon" not in html


# --- components/_feature_grid.html: linkable items (#99) --------------------


def test_feature_grid_item_with_url_renders_the_card_as_an_anchor() -> None:
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[{"heading": "Fast", "body": "Really fast.", "url": "/fast/"}],
    )
    assert '<a class="bw-feature-card bw-feature-card--link" href="/fast/">' in html
    assert "</a>" in html
    assert '<div class="bw-feature-card">' not in html


def test_feature_grid_item_without_url_renders_the_plain_div_unchanged() -> None:
    # The _stat.html href contract: no destination means no anchor, never a
    # clickable-looking card that goes nowhere.
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[{"heading": "Simple", "body": "No fuss."}],
    )
    assert '<div class="bw-feature-card">' in html
    assert "<a" not in html
    assert "bw-feature-card--link" not in html


def test_feature_grid_linked_item_aria_label_overrides_the_accessible_name() -> None:
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[
            {
                "heading": "Fast",
                "body": "Really fast.",
                "url": "/fast/",
                "aria_label": "Read about speed",
            }
        ],
    )
    assert 'aria-label="Read about speed"' in html


def test_feature_grid_aria_label_without_url_is_ignored() -> None:
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[{"heading": "Fast", "body": "Really fast.", "aria_label": "Ignored"}],
    )
    assert "aria-label" not in html


def test_feature_grid_mixes_linked_and_plain_items() -> None:
    html = _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[
            {"heading": "Fast", "body": "Really fast.", "url": "/fast/"},
            {"heading": "Simple", "body": "No fuss."},
        ],
    )
    assert '<a class="bw-feature-card bw-feature-card--link" href="/fast/">' in html
    assert '<div class="bw-feature-card">' in html


# --- components/_pricing_tier.html -----------------------------------------


def test_pricing_tier_required_context_renders() -> None:
    html = _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Starter",
        price="$9",
    )
    assert "Starter" in html
    assert "$9" in html
    assert "bw-pricing-tier--highlighted" not in html


def test_pricing_tier_optional_context_renders_every_region() -> None:
    html = _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Pro",
        price="$29",
        period="/month",
        description="For growing teams.",
        features=["Unlimited projects", "Priority support"],
        cta={"label": "Choose Pro", "url": "/pro/"},
        highlighted=True,
        badge="Most popular",
    )
    assert "/month" in html
    assert "For growing teams." in html
    assert "Unlimited projects" in html and "Priority support" in html
    assert "Choose Pro" in html and 'href="/pro/"' in html
    assert "bw-pricing-tier--highlighted" in html
    assert "Most popular" in html


def test_pricing_tier_badge_only_renders_when_highlighted() -> None:
    html = _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Starter",
        price="$9",
        badge="Most popular",
        highlighted=False,
    )
    assert "Most popular" not in html


def test_pricing_tier_flat_cta_kwargs_render_identically_to_the_dict_shape() -> None:
    # #98: cta accepts the flat cta_label/cta_href pair for template-authored
    # callers; both shapes must produce the same output.
    dict_html = _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Pro",
        price="$29",
        cta={"label": "Choose Pro", "url": "/pro/"},
    )
    flat_html = _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Pro",
        price="$29",
        cta_label="Choose Pro",
        cta_href="/pro/",
    )
    assert dict_html == flat_html
    assert "Choose Pro" in flat_html and 'href="/pro/"' in flat_html


def test_pricing_tier_dict_cta_wins_outright_when_both_shapes_are_supplied() -> None:
    html = _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Pro",
        price="$29",
        cta={"label": "Dict label", "url": "/dict/"},
        cta_label="Flat label",
        cta_href="/flat/",
    )
    assert "Dict label" in html and 'href="/dict/"' in html
    assert "Flat label" not in html and "/flat/" not in html


# --- components/_pricing_table.html ----------------------------------------


def test_pricing_table_with_tiers_renders_every_tier() -> None:
    html = _include(
        "brickwork_marketing/components/_pricing_table.html",
        heading="Plans",
        tiers=[{"name": "Starter", "price": "$9"}, {"name": "Pro", "price": "$29"}],
        note="Prices exclude tax.",
    )
    assert "Plans" in html
    assert "Starter" in html and "$9" in html
    assert "Pro" in html and "$29" in html
    assert "Prices exclude tax." in html
    assert "bw-pricing-table--single" not in html


def test_pricing_table_single_tier_renders_centred() -> None:
    html = _include(
        "brickwork_marketing/components/_pricing_table.html",
        tiers=[{"name": "Starter", "price": "$9"}],
    )
    assert "bw-pricing-table--single" in html


def test_pricing_table_empty_tiers_renders_intro_alone() -> None:
    html = _include("brickwork_marketing/components/_pricing_table.html", heading="Plans")
    assert "Plans" in html
    assert "bw-pricing-tier" not in html


def test_pricing_table_fully_empty_renders_nothing() -> None:
    html = _render("brickwork_marketing/components/_pricing_table.html")
    assert html.strip() == ""


def test_pricing_table_tier_dicts_accept_the_flat_cta_keys() -> None:
    # #98: the per-tier loop forwards cta_label/cta_url, so a view-built tier
    # dict may carry the flat pair instead of a nested cta dict.
    html = _include(
        "brickwork_marketing/components/_pricing_table.html",
        tiers=[{"name": "Pro", "price": "$29", "cta_label": "Choose Pro", "cta_url": "/pro/"}],
    )
    assert "Choose Pro" in html and 'href="/pro/"' in html


# --- components/_cta.html: band selects the tint treatment (04-interfaces.md 4d, ADR-057) ---


def test_cta_required_heading_renders() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready to start?")
    assert "Ready to start?" in html


def test_cta_default_renders_the_tint_class() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready to start?")
    assert "bw-cta--tint" in html


def test_cta_band_plain_omits_the_tint_class() -> None:
    html = _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to start?",
        band="plain",
    )
    assert "bw-cta--tint" not in html


def test_cta_band_unset_at_the_page_level_still_tints() -> None:
    # ADR-057 section 1a: band replaced the negated no_tint boolean precisely
    # because an absent page-level context variable piped through
    # {% include ... with %} resolves to an empty string, not None, so a
    # default-True flag could never be turned off from the page level. band's
    # three-valued string has no such ambiguity: {% firstof band 'tint' %}
    # treats the empty string as unset and falls back to "tint" correctly.
    # Prove the pass-through case explicitly: a page-level variable that was
    # never set in context still leaves the tint ON when forwarded as band.
    html = Template(
        "{% include 'brickwork_marketing/components/_cta.html' with heading=heading band=absent_var %}"
    ).render(Context({"heading": "Ready to start?"}))
    assert "bw-cta--tint" in html


def test_cta_band_omitted_entirely_still_tints() -> None:
    # The same guarantee holds when band is never mentioned in the include at
    # all, not merely forwarded from an absent variable: the omitted-flag
    # trap the old negated no_tint boolean was retired to fix.
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready to start?")
    assert "bw-cta--tint" in html


def test_cta_optional_context_renders_every_region() -> None:
    html = _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to start?",
        body="Join thousands of teams already using it.",
        primary_cta={"label": "Get started", "url": "/start/"},
        secondary_cta={"label": "Talk to sales", "url": "/sales/"},
    )
    assert "Join thousands of teams already using it." in html
    assert "Get started" in html and 'href="/start/"' in html
    assert "Talk to sales" in html and 'href="/sales/"' in html


def test_cta_flat_cta_kwargs_render_identically_to_the_dict_shape() -> None:
    # #98: the CTA band's buttons accept the same flat kwargs as the hero's.
    dict_html = _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to start?",
        primary_cta={"label": "Get started", "url": "/start/"},
        secondary_cta={"label": "Talk to sales", "url": "/sales/"},
    )
    flat_html = _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to start?",
        primary_cta_label="Get started",
        primary_cta_href="/start/",
        secondary_cta_label="Talk to sales",
        secondary_cta_href="/sales/",
    )
    assert dict_html == flat_html


def test_cta_flat_kwargs_forwarded_unset_render_no_actions() -> None:
    # Same pass-through rule as the hero: an absent page-level variable
    # forwarded by {% include ... with %} arrives as an empty string and must
    # not render an empty button.
    html = Template(
        "{% include 'brickwork_marketing/components/_cta.html' with heading=heading"
        " primary_cta_label=absent_a primary_cta_href=absent_b %}"
    ).render(Context({"heading": "Ready to start?"}))
    assert "bw-cta__actions" not in html


# --- components/_cta.html: width (ADR-057 section 1a, ADR-077 section 3a) ---


def test_cta_width_omitted_output_is_byte_identical_to_pre_width_axis() -> None:
    # Full-string equality, matching test_hero_heading_only_output_is_byte_
    # identical_to_pre_slot_blocks's precedent: proves width's addition is
    # additive for every existing caller, not merely "no bleed class seen".
    html = _render("brickwork_marketing/components/_cta.html", heading="Ready?")
    assert html == (
        '\n\n\n<section class="bw-cta bw-cta--tint">\n  <div class="bw-cta__inner">\n'
        '    <h2 class="bw-cta__heading">Ready?</h2>\n    \n    \n  </div>\n</section>\n\n'
    )


def test_cta_width_contained_is_explicitly_the_same_as_omitted() -> None:
    omitted = _render("brickwork_marketing/components/_cta.html", heading="Ready?")
    explicit = _include("brickwork_marketing/components/_cta.html", heading="Ready?", width="contained")
    assert omitted == explicit


def test_cta_width_bleed_emits_its_modifier_class() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready?", width="bleed")
    assert "bw-cta--bleed" in html


def test_cta_width_bleed_composes_with_a_tinted_band() -> None:
    # ADR-057 section 1a: width is orthogonal to band, so a tinted full-bleed
    # band is expressible with both classes present.
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready?", width="bleed", band="tint")
    assert "bw-cta--tint" in html
    assert "bw-cta--bleed" in html


def test_cta_width_bleed_composes_with_a_plain_band() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready?", width="bleed", band="plain")
    assert "bw-cta--tint" not in html
    assert "bw-cta--bleed" in html


def test_cta_width_is_css_only_and_adds_no_markup() -> None:
    # Matches test_hero_media_placement_is_css_only_and_adds_no_markup's
    # invariant: only the class list on the section root changes; the inner
    # markup is identical regardless of width.
    contained = _include("brickwork_marketing/components/_cta.html", heading="Ready?")
    bleed = _include("brickwork_marketing/components/_cta.html", heading="Ready?", width="bleed")
    assert bleed.replace(" bw-cta--bleed", "") == contained


def test_cta_width_unrecognised_value_falls_back_to_default() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready?", width="nonsense")
    assert "bw-cta--bleed" not in html


# --- components/_testimonial.html ------------------------------------------


def test_testimonial_required_quote_renders() -> None:
    html = _include("brickwork_marketing/components/_testimonial.html", quote="It just works.")
    assert "It just works." in html


def test_testimonial_fully_empty_renders_nothing() -> None:
    html = _render("brickwork_marketing/components/_testimonial.html")
    assert html.strip() == ""


def test_testimonial_avatar_alt_derives_from_author() -> None:
    html = _include(
        "brickwork_marketing/components/_testimonial.html",
        quote="It just works.",
        author="Ada Lovelace",
        avatar="/ada.png",
    )
    assert 'alt="Ada Lovelace"' in html


def test_testimonial_without_avatar_renders_no_broken_image() -> None:
    html = _include(
        "brickwork_marketing/components/_testimonial.html",
        quote="It just works.",
        author="Ada Lovelace",
    )
    assert "<img" not in html


def test_testimonial_optional_context_renders_every_region() -> None:
    html = _include(
        "brickwork_marketing/components/_testimonial.html",
        quote="It just works.",
        author="Ada Lovelace",
        role="CTO, Acme Ltd",
        avatar="/ada.png",
        logo=mark_safe("<img src='/acme-logo.svg' alt='Acme'>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert "Ada Lovelace" in html
    assert "CTO, Acme Ltd" in html
    assert "<img src='/acme-logo.svg'" in html


# --- components/_testimonial.html: the logo block (icvoss/django-brickwork#98/#118 pattern) ---


def test_testimonial_quote_only_output_is_byte_identical_to_pre_logo_block() -> None:
    # Full-string equality, matching test_hero_heading_only_output_is_byte_
    # identical_to_pre_slot_blocks's precedent: the logo block's default
    # content is the pre-existing {% if logo %} rendering, so a call site
    # supplying no attribution context at all renders byte-identically.
    html = _render("brickwork_marketing/components/_testimonial.html", quote="It just works.")
    assert html == (
        '\n\n<figure class="bw-testimonial">\n  <blockquote class="bw-testimonial__quote">\n'
        "    <p>It just works.</p>\n  </blockquote>\n  \n</figure>\n\n"
    )


def test_testimonial_logo_via_context_variable_is_byte_identical_to_pre_block() -> None:
    # The pre-existing path (logo passed as pre-rendered safe HTML context)
    # renders exactly as it always did once the block wraps it.
    html = _include(
        "brickwork_marketing/components/_testimonial.html",
        quote="It just works.",
        logo=mark_safe("<img src='/acme-logo.svg' alt='Acme'>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert html == (
        '\n\n<figure class="bw-testimonial">\n  <blockquote class="bw-testimonial__quote">\n'
        "    <p>It just works.</p>\n  </blockquote>\n  \n"
        '    <figcaption class="bw-testimonial__attribution">\n      \n'
        '      <div class="bw-testimonial__attribution-text">\n        \n        \n      </div>\n'
        "      <div class=\"bw-testimonial__logo\"><img src='/acme-logo.svg' alt='Acme'></div>\n"
        "    </figcaption>\n  \n</figure>\n\n"
    )


def _extend_testimonial(blocks: str, **ctx: object) -> str:
    return _extend("brickwork_marketing/components/_testimonial.html", blocks, **ctx)


def test_testimonial_logo_block_override_wins_over_the_logo_context() -> None:
    # examples/sections/testimonial/logo-and-quote.html's blocker: a Django
    # template cannot build a safe-HTML logo inline, so the block lets a
    # caller author the mark directly instead of a view supplying
    # mark_safe(...) markup.
    html = _extend_testimonial(
        "{% block logo %}<svg viewBox='0 0 160 40' aria-hidden='true'></svg>{% endblock %}",
        quote="It just works.",
        author="Priya Raman",
        logo=mark_safe("<img src='/ignored.svg'>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert "<svg viewBox='0 0 160 40'" in html
    assert "ignored.svg" not in html


def test_testimonial_logo_block_override_renders_when_the_figcaption_gate_is_open() -> None:
    # The figcaption only renders when author, role, avatar or logo is
    # truthy (unchanged gate, so a quote-only caller stays byte-identical).
    # A caller who wants to fill only the logo block still has to open that
    # gate the same way filling only avatar or only author always has: by
    # setting the corresponding context variable truthy.
    html = _extend_testimonial(
        "{% block logo %}<svg viewBox='0 0 160 40' aria-hidden='true'></svg>{% endblock %}",
        quote="It just works.",
        logo=" ",
    )
    assert "<figcaption" in html
    assert "<svg viewBox='0 0 160 40'" in html


def test_testimonial_logo_block_override_renders_nothing_when_the_gate_is_closed() -> None:
    # The documented limitation (template docstring, icvoss/django-brickwork#171):
    # filling the block alone does not open the figcaption gate, because Django
    # cannot detect that a block was overridden. A caller who sets none of the
    # four gate variables (author, role, avatar, logo) gets nothing at all, even
    # though the block itself was filled. This is the expected, bounded result,
    # not a bug: the block's markup is entirely absent, matching the pre-block
    # {% if logo %} gate's own behaviour for an unset logo.
    html = _extend_testimonial(
        "{% block logo %}<svg viewBox='0 0 160 40' aria-hidden='true'></svg>{% endblock %}",
        quote="It just works.",
    )
    assert "<figcaption" not in html
    assert "<svg" not in html


# --- components/_logo_cloud.html: alt is required, never invented ----------


def test_logo_cloud_requires_and_emits_alt() -> None:
    html = _include(
        "brickwork_marketing/components/_logo_cloud.html",
        logos=[{"src": "/acme.svg", "alt": "Acme"}],
    )
    assert 'alt="Acme"' in html
    assert 'src="/acme.svg"' in html


def test_logo_cloud_with_heading_only_renders_no_grid() -> None:
    html = _include("brickwork_marketing/components/_logo_cloud.html", heading="Trusted by teams at")
    assert "Trusted by teams at" in html
    assert "bw-logo-cloud__grid" not in html


def test_logo_cloud_fully_empty_renders_nothing() -> None:
    html = _render("brickwork_marketing/components/_logo_cloud.html")
    assert html.strip() == ""


def test_logo_cloud_greyscale_flag_adds_the_modifier_class() -> None:
    html = _include(
        "brickwork_marketing/components/_logo_cloud.html",
        logos=[{"src": "/acme.svg", "alt": "Acme"}],
        greyscale=True,
    )
    assert "bw-logo-cloud--greyscale" in html


# --- components/_stat_band.html: composes _stat.html (BR-BW-MKT-004) -------


def test_stat_band_composes_the_stat_tile_shape() -> None:
    html = _include(
        "brickwork_marketing/components/_stat_band.html",
        heading="By the numbers",
        stats=[{"value": "99.9%", "label": "Uptime"}],
    )
    assert "bw-stat-band" in html
    assert "bw-stat" in html  # the composed _stat.html tile class
    assert "99.9%" in html and "Uptime" in html


def test_stat_band_empty_stats_renders_heading_alone() -> None:
    html = _include("brickwork_marketing/components/_stat_band.html", heading="By the numbers")
    assert "By the numbers" in html
    # the stats grid wrapper (distinct from the always-present section class)
    assert '<div class="bw-stat-band">' not in html


def test_stat_band_fully_empty_renders_nothing() -> None:
    html = _render("brickwork_marketing/components/_stat_band.html")
    assert html.strip() == ""


def test_stat_band_trend_without_trend_label_still_pairs_glyph_with_hidden_text() -> None:
    # _stat.html itself enforces BR-BW-TPL-007 (a trend never rides on colour
    # alone): whenever trend is set it ALWAYS renders a directional glyph plus
    # a visually hidden text fallback, even with no trend_label supplied.
    # _stat_band.html passes trend/trend_label straight through unmodified
    # (04-interfaces.md 4d), so the same guarantee holds unchanged here.
    html = _include(
        "brickwork_marketing/components/_stat_band.html",
        stats=[{"value": "12%", "label": "Growth", "trend": "up"}],
    )
    assert "bw-trend--up" in html
    assert "bw-stat__trend" in html  # retained alongside bw-trend (icvoss/django-brickwork#334)
    assert "bw-visually-hidden" in html  # the accessible fallback text


def test_stat_band_trend_with_trend_label_renders_the_visible_text() -> None:
    html = _include(
        "brickwork_marketing/components/_stat_band.html",
        stats=[{"value": "12%", "label": "Growth", "trend": "up", "trend_label": "12% up on last month"}],
    )
    assert "12% up on last month" in html


# --- components/_faq.html: composes _disclosure.html (BR-BW-MKT-004) ------


def test_faq_composes_disclosure_details_and_summary() -> None:
    html = _include(
        "brickwork_marketing/components/_faq.html",
        heading="Frequently asked questions",
        items=[{"question": "Can I cancel?", "answer": "Any time."}],
    )
    assert "<details" in html
    assert "<summary" in html
    assert "Can I cancel?" in html
    assert "Any time." in html


def test_faq_empty_items_renders_heading_alone() -> None:
    html = _include("brickwork_marketing/components/_faq.html", heading="FAQ")
    assert "FAQ" in html
    assert "<details" not in html


def test_faq_fully_empty_renders_nothing() -> None:
    html = _render("brickwork_marketing/components/_faq.html")
    assert html.strip() == ""


def test_faq_single_open_shares_a_name_across_disclosures() -> None:
    html = _include(
        "brickwork_marketing/components/_faq.html",
        items=[
            {"question": "Can I cancel?", "answer": "Any time."},
            {"question": "Is there a free trial?", "answer": "Yes, 14 days."},
        ],
        single_open=True,
    )
    assert html.count('name="bw-faq"') == 2


def test_faq_without_single_open_shares_no_name() -> None:
    html = _include(
        "brickwork_marketing/components/_faq.html",
        items=[
            {"question": "Can I cancel?", "answer": "Any time."},
            {"question": "Is there a free trial?", "answer": "Yes, 14 days."},
        ],
    )
    assert "name=" not in html


# --- #86: the testimonial must not zero the composed section rhythm ---------
# These assert on the shipped dist CSS (the package product, the same idiom
# test_slide_over.py uses for the zero-footprint root): the defect was a
# cascade tie the render tests cannot see.


def test_testimonial_root_carries_no_blanket_margin_reset() -> None:
    # #86: `margin: 0` on .bw-testimonial tied on specificity with the shell's
    # `.bw-marketing__content > * + *` section-gap rule and, sitting later in
    # source order, won the tie, permanently zeroing the gap above any composed
    # testimonial. The class-specificity rule must not touch block margins.
    css = (_DIST / "brickwork.css").read_text()
    rule = re.search(r"\.bw-testimonial\{([^}]*)\}", css)
    assert rule is not None, "expected a .bw-testimonial rule in dist/brickwork.css"
    body = rule.group(1).replace(" ", "")
    assert "margin:0" not in body, "blanket margin reset regressed (#86)"
    assert "margin-block" not in body
    assert "margin-inline:auto" in body


def test_testimonial_ua_figure_margins_neutralised_at_zero_specificity() -> None:
    # The UA <figure> block margins are reset in a :where() rule (specificity
    # zero), so the shell's section-gap rule always wins when the testimonial
    # is composed as a marketing section.
    css = (_DIST / "brickwork.css").read_text()
    rule = re.search(r":where\(\.bw-testimonial\)\{([^}]*)\}", css)
    assert rule is not None, "expected a zero-specificity :where(.bw-testimonial) reset (#86)"
    assert "margin-block:0" in rule.group(1).replace(" ", "")


def test_marketing_section_gap_rule_composes_the_rhythm() -> None:
    # The full Tailwind compile pass (ADR-079 5a) groups the `* + *` selector
    # with the first-child selector below when they share a declaration
    # block, so the assertion matches the selector list rather than an exact
    # standalone rule.
    css = (_DIST / "brickwork.css").read_text().replace(" ", "")
    rule = re.search(
        r"([^{}]*\.bw-marketing__content>\*\+\*[^{}]*)\{([^}]*)\}",
        css,
    )
    assert rule is not None, "the marketing section-gap rule must remain in dist/brickwork.css"
    assert "margin-block-start:var(--bw-component-section-gap-marketing)" in rule.group(2)


# --- #111: the first content child needs its own block-start spacing --------


def test_the_first_marketing_section_gets_block_start_spacing() -> None:
    # #111: the section-gap rule above only spaces BETWEEN children, so a page
    # opening on a non-hero section (a page header, a feature grid) rendered
    # flush against the header's hairline and consumers were patching it with
    # their own padding wrapper.
    #
    # The full Tailwind compile pass (ADR-079 5a) drops the redundant `*`
    # before `:first-child` (`>:first-child` is equivalent to `>*:first-child`
    # for element matching) and may merge this selector with the `* + *` rule
    # above when they share a declaration block, so this matches the
    # selector/declaration pair rather than a single exact rule string.
    css = (_DIST / "brickwork.css").read_text().replace(" ", "")
    rule = re.search(
        r"([^{}]*\.bw-marketing__content>:first-child:not\(\.bw-hero\)[^{}]*)\{([^}]*)\}",
        css,
    )
    assert rule is not None, "the first-child marketing spacing rule must remain in dist/brickwork.css (#111)"
    assert "margin-block-start:var(--bw-component-section-gap-marketing)" in rule.group(2)


def test_the_hero_opts_out_of_the_first_child_spacing() -> None:
    # The hero owns its own vertical rhythm (padding-block), so applying the
    # first-child rule to it too would double the space on the canonical
    # landing page. The :not(.bw-hero) is load-bearing, not decoration.
    css = (_DIST / "brickwork.css").read_text().replace(" ", "")
    first_child_rules = re.findall(r"\.bw-marketing__content>:first-child([^{]*)\{", css)
    assert first_child_rules, "expected a first-child rule to exist at all"
    assert all(":not(.bw-hero)" in selector for selector in first_child_rules), (
        "every .bw-marketing__content first-child rule must exclude the hero (#111)"
    )


# --- #83: brand slot default sizing (--bw-component-logo-height) ------------


def test_marketing_shell_wraps_brand_blocks_in_brickwork_owned_elements() -> None:
    # #83 (the app shell's brickwork#93 wrapper precedent): brand_logo and
    # brand_wordmark are wrapped so the shell can constrain a dropped-in
    # mark/lockup without knowing the consumer's inner markup or classes.
    html = _extend(
        "brickwork_marketing/shell/marketing.html",
        "{% block brand_logo %}<svg viewBox='0 0 400 400'></svg>{% endblock %}"
        "{% block brand_wordmark %}Acme{% endblock %}",
    )
    assert '<span class="bw-marketing-header__brand-mark"><svg' in html
    assert '<span class="bw-marketing-header__brand-wordmark">Acme</span>' in html


def test_marketing_shell_unfilled_brand_blocks_leave_empty_wrappers() -> None:
    # An unfilled block leaves an :empty wrapper (collapsed by the CSS), so
    # the header's gap never renders a phantom slot.
    html = _extend("brickwork_marketing/shell/marketing.html", "")
    assert '<span class="bw-marketing-header__brand-mark"></span>' in html
    assert '<span class="bw-marketing-header__brand-wordmark"></span>' in html


def test_logo_height_token_is_emitted_with_its_default() -> None:
    tokens = (_DIST / "tokens.css").read_text()
    assert "--bw-component-logo-height: 2rem;" in tokens


def test_brand_slot_caps_a_dropped_in_logo_via_the_token_at_zero_specificity() -> None:
    # The img/svg leg is :where() (zero specificity), so a one-class consumer
    # rule overrides the default cap.
    css = (_DIST / "brickwork.css").read_text()
    rule = re.search(
        r"\.bw-marketing-header__brand-mark :where\(img,\s*svg\),\s*"
        r"\.bw-marketing-header__brand-wordmark :where\(img,\s*svg\)\{([^}]*)\}",
        css,
    )
    assert rule is not None, "expected the brand-slot logo cap rule in dist/brickwork.css (#83)"
    body = rule.group(1).replace(" ", "")
    assert "block-size:var(--bw-component-logo-height)" in body
    assert "inline-size:auto" in body


def test_brand_wrappers_do_not_grow_or_shrink_and_collapse_when_empty() -> None:
    css = (_DIST / "brickwork.css").read_text()
    wrappers = re.search(
        r"\.bw-marketing-header__brand-mark,\s*\.bw-marketing-header__brand-wordmark\{([^}]*)\}",
        css,
    )
    assert wrappers is not None
    assert "flex:none" in wrappers.group(1).replace(" ", "")
    empties = re.search(
        r"\.bw-marketing-header__brand-mark:empty,\s*\.bw-marketing-header__brand-wordmark:empty\{([^}]*)\}",
        css,
    )
    assert empties is not None
    assert "display:none" in empties.group(1).replace(" ", "")


# --- shell/marketing.html: auth-aware marketing_actions (#85) ---------------


def test_marketing_shell_actions_block_branches_on_auth_state() -> None:
    # The documented pattern (INTEGRATION.md section 8, the shell's own header
    # comment): brickwork never reads auth itself; the consumer branches its
    # marketing_actions block on request.user.is_authenticated. Prove the
    # branch renders both ways through the shell.
    from django.contrib.auth.models import AnonymousUser, User
    from django.test import RequestFactory

    source = (
        "{% extends 'brickwork_marketing/shell/marketing.html' %}"
        "{% block marketing_actions %}"
        "{% if request.user.is_authenticated %}"
        '<a href="/dashboard/">Dashboard</a>'
        "{% else %}"
        '<a href="/login/">Sign in</a>'
        "{% endif %}"
        "{% endblock %}"
    )
    request = RequestFactory().get("/")

    request.user = AnonymousUser()
    anon_html = Template(source).render(Context({"request": request}))
    assert "Sign in" in anon_html
    assert "Dashboard" not in anon_html

    request.user = User(username="ada")  # unsaved: is_authenticated is always True
    authed_html = Template(source).render(Context({"request": request}))
    assert "Dashboard" in authed_html
    assert "Sign in" not in authed_html


# --- #120: documented default values need a CSS rule, not just a class name -

# The option-grammar convergence (ADR-060) added rules for defaults that
# previously emitted a modifier class with no matching CSS: a component
# rendered its documented default fine because there was nothing to style
# beyond the base class, but the class itself was a broken promise (#120).


def test_slide_over_default_size_md_has_a_css_rule() -> None:
    css = (_DIST / "brickwork.css").read_text()
    assert ".bw-slide-over--md .bw-slide-over__panel{" in css


def test_tabs_default_variant_underline_has_a_css_rule() -> None:
    css = (_DIST / "brickwork.css").read_text()
    assert ".bw-tabs--underline .bw-tabs__list{" in css


def test_hero_default_align_start_has_a_css_rule() -> None:
    css = (_DIST / "brickwork.css").read_text()
    assert ".bw-hero--start{" in css.replace(" ", "")


def test_hero_align_end_has_a_css_rule() -> None:
    # New in this convergence: "end" was a documented align value with no
    # class before now (#120's mirror case for the hero).
    css = (_DIST / "brickwork.css").read_text()
    assert ".bw-hero--end{" in css.replace(" ", "")
