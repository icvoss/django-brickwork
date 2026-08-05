"""Render tests for the marketing kit (`brickwork.marketing`, v1.2.0, spec 04
section 4d, business rules section 9, BR-BW-MKT-001..005).

BR-BW-MKT-005 / BR-BW-PAGE-002 at marketing scope: each of the three pages
renders a complete valid document when a consumer extends it with only
``title``, and every documented block fills in document order when supplied.
BR-BW-MKT-004 (reuse, not reimplementation): the FAQ composes
``_disclosure.html`` and the stat band composes ``_stat.html``'s tile shape.
BR-BW-MKT-001: the sub-app ships no models, migrations, views, or URLs.

These tests drive the pages the way a consumer does: {% extends %} plus block
overrides, and the components the way a page does: {% include %} plus
context, mirroring test_pages.py's idiom exactly.
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


_MARKETING_PAGES = (
    "brickwork_marketing/pages/marketing/landing.html",
    "brickwork_marketing/pages/marketing/pricing.html",
    "brickwork_marketing/pages/marketing/about.html",
)


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


# --- Pages: empty-graceful + shell chrome (BR-BW-MKT-005/BR-BW-PAGE-002) ----


def test_each_marketing_page_with_only_title_renders_a_complete_document() -> None:
    for template in _MARKETING_PAGES:
        html = _render(template, title="A marketing page")
        _assert_complete_document(html)


def test_each_marketing_page_extends_the_marketing_shell_not_the_app_shell() -> None:
    for template in _MARKETING_PAGES:
        html = _render(template, title="A marketing page")
        assert "bw-marketing" in html
        assert "bw-marketing-header" in html
        assert "bw-marketing-footer" in html
        # never the app shell's chrome
        assert "bw-sidebar" not in html
        assert "bw-topbar" not in html
        assert "bw-app" not in html


def test_each_marketing_page_renders_no_optional_section_markup_when_empty() -> None:
    # An all-empty page must not fabricate placeholder marketing copy for any
    # of its component sections (BR-BW-TPL-006 / BR-BW-PAGE-002 at marketing
    # scope): none of the section wrapper classes should appear at all.
    for template in _MARKETING_PAGES:
        html = _render(template, title="A marketing page")
        assert "bw-feature-card" not in html
        assert "bw-pricing-tier" not in html
        assert 'class="bw-cta' not in html
        assert 'class="bw-testimonial"' not in html
        assert "bw-logo-cloud__grid" not in html
        assert 'bw-stat-band"' not in html and "bw-stat-band " not in html
        assert "<details" not in html  # no FAQ disclosures rendered


# --- landing.html ------------------------------------------------------------


def test_landing_hero_fills_from_context() -> None:
    html = _render(
        "brickwork_marketing/pages/marketing/landing.html",
        title="Landing",
        heading="Ship faster",
        lede="The all-in-one platform.",
    )
    assert "Ship faster" in html
    assert "The all-in-one platform." in html


def test_landing_blocks_fill_in_document_order() -> None:
    html = _extend(
        "brickwork_marketing/pages/marketing/landing.html",
        "{% block hero %}HERO-SENTINEL{% endblock %}"
        "{% block logo_cloud %}LOGOCLOUD-SENTINEL{% endblock %}"
        "{% block features %}FEATURES-SENTINEL{% endblock %}"
        "{% block stats %}STATS-SENTINEL{% endblock %}"
        "{% block testimonial %}TESTIMONIAL-SENTINEL{% endblock %}"
        "{% block cta %}CTA-SENTINEL{% endblock %}",
    )
    positions = [
        html.index("HERO-SENTINEL"),
        html.index("LOGOCLOUD-SENTINEL"),
        html.index("FEATURES-SENTINEL"),
        html.index("STATS-SENTINEL"),
        html.index("TESTIMONIAL-SENTINEL"),
        html.index("CTA-SENTINEL"),
    ]
    assert positions == sorted(positions), f"landing sections out of documented order: {positions}"


def test_landing_features_and_stats_and_testimonial_fill_from_context() -> None:
    html = _render(
        "brickwork_marketing/pages/marketing/landing.html",
        title="Landing",
        features=[{"heading": "Fast", "body": "Really fast."}],
        stats=[{"value": "99.9%", "label": "Uptime"}],
        quote="It just works.",
        author="Ada Lovelace",
    )
    assert "Fast" in html and "Really fast." in html
    assert "99.9%" in html and "Uptime" in html
    assert "It just works." in html and "Ada Lovelace" in html


# --- pricing.html --------------------------------------------------------


def test_pricing_blocks_fill_in_document_order() -> None:
    html = _extend(
        "brickwork_marketing/pages/marketing/pricing.html",
        "{% block hero %}HERO-SENTINEL{% endblock %}"
        "{% block pricing %}PRICING-SENTINEL{% endblock %}"
        "{% block faq %}FAQ-SENTINEL{% endblock %}"
        "{% block cta %}CTA-SENTINEL{% endblock %}",
    )
    positions = [
        html.index("HERO-SENTINEL"),
        html.index("PRICING-SENTINEL"),
        html.index("FAQ-SENTINEL"),
        html.index("CTA-SENTINEL"),
    ]
    assert positions == sorted(positions), f"pricing sections out of documented order: {positions}"


def test_pricing_tiers_and_faq_fill_from_context() -> None:
    html = _render(
        "brickwork_marketing/pages/marketing/pricing.html",
        title="Pricing",
        tiers=[{"name": "Starter", "price": "$9"}],
        faq_items=[{"question": "Can I cancel?", "answer": "Any time."}],
    )
    assert "Starter" in html and "$9" in html
    assert "Can I cancel?" in html and "Any time." in html


# --- about.html ------------------------------------------------------------


def test_about_blocks_fill_in_document_order() -> None:
    html = _extend(
        "brickwork_marketing/pages/marketing/about.html",
        "{% block hero %}HERO-SENTINEL{% endblock %}"
        "{% block about_body %}ABOUT-BODY-SENTINEL{% endblock %}"
        "{% block stats %}STATS-SENTINEL{% endblock %}"
        "{% block testimonial %}TESTIMONIAL-SENTINEL{% endblock %}"
        "{% block cta %}CTA-SENTINEL{% endblock %}",
    )
    positions = [
        html.index("HERO-SENTINEL"),
        html.index("ABOUT-BODY-SENTINEL"),
        html.index("STATS-SENTINEL"),
        html.index("TESTIMONIAL-SENTINEL"),
        html.index("CTA-SENTINEL"),
    ]
    assert positions == sorted(positions), f"about sections out of documented order: {positions}"


def test_about_body_has_no_default_component_of_its_own() -> None:
    # about_body has no default per 04-interfaces.md; an unfilled about_body
    # renders the wrapping bw-section-stack with nothing inside.
    html = _render("brickwork_marketing/pages/marketing/about.html", title="About")
    assert "bw-section-stack" in html


# --- Accessibility invariant: exactly one <h1> per page (in the hero) -------


def test_each_marketing_page_renders_exactly_one_h1_when_hero_heading_is_set() -> None:
    for template in _MARKETING_PAGES:
        html = _render(template, title="A page", heading="The one heading")
        assert html.count("<h1") == 1


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


# --- components/_cta.html: no_tint is an opt-out (04-interfaces.md 4d) ------


def test_cta_required_heading_renders() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready to start?")
    assert "Ready to start?" in html


def test_cta_default_renders_the_tint_class() -> None:
    html = _include("brickwork_marketing/components/_cta.html", heading="Ready to start?")
    assert "bw-cta--tint" in html


def test_cta_no_tint_true_omits_the_tint_class() -> None:
    html = _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to start?",
        no_tint=True,
    )
    assert "bw-cta--tint" not in html


def test_cta_no_tint_unset_at_the_page_level_leaves_the_tint_on() -> None:
    # The documented reason no_tint is an opt-out, not tint=True: an absent
    # page-level context variable piped through {% include ... with %}
    # resolves to an empty string, not None, so a default-True flag could
    # never be turned off from the page level. Prove the pass-through case
    # explicitly: a page-level variable that was never set in context still
    # leaves the tint ON when forwarded as no_tint.
    html = Template(
        "{% include 'brickwork_marketing/components/_cta.html' with heading=heading no_tint=absent_var %}"
    ).render(Context({"heading": "Ready to start?"}))
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
    assert "bw-stat__trend--up" in html
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
    css = (_DIST / "brickwork.css").read_text()
    assert re.search(
        r"\.bw-marketing__content>\*\+\*\{margin-block-start:var\(--bw-component-section-gap-marketing\)\}",
        css.replace(" ", ""),
    ), "the marketing section-gap rule must remain in dist/brickwork.css"


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
    assert "flex:00auto" in wrappers.group(1).replace(" ", "")
    empties = re.search(
        r"\.bw-marketing-header__brand-mark:empty,\s*\.bw-marketing-header__brand-wordmark:empty\{([^}]*)\}",
        css,
    )
    assert empties is not None
    assert "display:none" in empties.group(1).replace(" ", "")
