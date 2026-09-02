"""Direct render tests for _empty_state.html (STA-001/002, CMP-032, SLOT wave,
ADR-077 SS4).

Covers the pre-existing context-variable path (byte-identical for an
include-only caller), the new concise blocks (icon/heading/body/action), and
the owner-mandated dual-shipping of each deprecated block
(title/description/empty_state_action) alongside its concise successor
(heading/body/action): both must render. "title"/"description" are corrected
here (ADR-077 SS4) because they named neither the context variable
(heading/body) nor the CSS class (bw-empty-state__heading/__body) they wrap.
"""

from __future__ import annotations

from django.template import Context, Template
from django.template.loader import render_to_string


def _render(**ctx: object) -> str:
    ctx.setdefault("heading", "No invoices yet")
    ctx.setdefault("body", "Create your first invoice to get started.")
    return render_to_string("brickwork/components/_empty_state.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    ctx.setdefault("heading", "No invoices yet")
    ctx.setdefault("body", "Create your first invoice to get started.")
    source = "{% extends 'brickwork/components/_empty_state.html' %}{% load brickwork_icons i18n %}" + blocks
    return Template(source).render(Context(ctx))


# --- backwards compatibility -------------------------------------------------


def test_include_only_heading_and_body_render_unchanged() -> None:
    out = _render()
    assert "No invoices yet" in out
    assert "Create your first invoice to get started." in out
    assert "bw-empty-state bw-empty-state--no_data" in out


def test_include_only_output_is_byte_identical_to_pre_slot_blocks() -> None:
    # Full-string equality: substring checks above would pass on a
    # whitespace-only regression from a stray {% if %} inside a new block.
    out = _render(heading="No invoices yet", body="Create your first invoice.")
    assert out == (
        '\n\n<div class="bw-empty-state bw-empty-state--no_data">\n  \n  \n    '
        '<svg class="bw-icon bw-empty-state__icon" style="--bw-icon-size: var(--bw-component-icon-size-xl)" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="var(--bw-component-icon-stroke-width, 2)" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 '
        '7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" /></svg>\n  \n  \n  <h2 class="bw-empty-state__heading">'
        'No invoices yet</h2>\n  <p class="bw-empty-state__body">Create your first invoice.</p>\n  \n  \n  \n  \n'
        "</div>\n"
    )


def test_include_only_action_href_and_label_still_render_the_anchor() -> None:
    out = _render(action_href="/invoices/new/", action_label="Create invoice")
    assert '<a class="bw-btn bw-btn--primary bw-btn--md" href="/invoices/new/">Create invoice</a>' in out


def test_no_results_variant_shows_the_search_icon_by_default() -> None:
    out = _render(variant="no_results")
    assert "bw-empty-state--no_results" in out
    assert "bw-empty-state__icon" in out


def test_default_variant_shows_the_folder_icon() -> None:
    out = _render()
    assert "bw-empty-state__icon" in out


# --- icon block ----------------------------------------------------------------


def test_icon_block_override_replaces_the_default_icon_markup() -> None:
    out = _extend("{% block icon %}<span>ICON-SENTINEL</span>{% endblock %}")
    assert "ICON-SENTINEL" in out
    assert "bw-empty-state__icon" not in out


# --- heading / body blocks, and deprecated title / description ---------------


def test_heading_block_override_wins_over_the_heading_context() -> None:
    out = _extend("{% block heading %}Custom heading{% endblock %}")
    assert "Custom heading" in out
    assert "No invoices yet" not in out


def test_body_block_override_wins_over_the_body_context() -> None:
    out = _extend("{% block body %}Custom body{% endblock %}")
    assert "Custom body" in out
    assert "Create your first invoice to get started." not in out


def test_the_deprecated_title_block_still_replaces_the_heading() -> None:
    # BR-BW-VER-001 parallel support means the OLD name keeps its OLD
    # behaviour. "title" wrapped the heading and replaced it, so a consumer
    # filling it must still get replacement, not their text appended to the
    # default. The deprecated block is nested INSIDE its successor for exactly
    # this reason: overriding either one replaces the same region.
    out = _extend("{% block title %}TITLE-SENTINEL{% endblock %}")
    assert "TITLE-SENTINEL" in out
    assert "No invoices yet" not in out


def test_the_deprecated_description_block_still_replaces_the_body() -> None:
    out = _extend("{% block description %}DESC-SENTINEL{% endblock %}")
    assert "DESC-SENTINEL" in out
    assert "Create your first invoice to get started." not in out


def test_heading_wins_when_both_heading_and_title_are_filled() -> None:
    # Filling the successor overrides the whole region, deprecated block
    # included: one region, one winner, never both concatenated into one h2.
    out = _extend("{% block heading %}HEADING-SENTINEL{% endblock %}{% block title %}TITLE-SENTINEL{% endblock %}")
    assert "HEADING-SENTINEL" in out
    assert "TITLE-SENTINEL" not in out


def test_body_wins_when_both_body_and_description_are_filled() -> None:
    out = _extend("{% block body %}BODY-SENTINEL{% endblock %}{% block description %}DESC-SENTINEL{% endblock %}")
    assert "BODY-SENTINEL" in out
    assert "DESC-SENTINEL" not in out


# --- action / empty_state_action dual-shipping --------------------------------


def test_action_block_default_content_is_the_existing_anchor() -> None:
    out = _render(action_href="/invoices/new/", action_label="Create invoice")
    assert '<a class="bw-btn bw-btn--primary bw-btn--md" href="/invoices/new/">Create invoice</a>' in out


def test_action_block_override_replaces_the_default_anchor() -> None:
    out = _extend(
        "{% block action %}<button>ACTION-SENTINEL</button>{% endblock %}",
        action_href="/invoices/new/",
        action_label="Create invoice",
    )
    assert "ACTION-SENTINEL" in out
    assert "Create invoice" not in out


def test_action_and_empty_state_action_both_render_when_both_are_filled() -> None:
    # Owner decision: ship both. The old prefixed name is deprecated (removed
    # at 4.0) but must not break; the new concise name is additive.
    out = _extend(
        "{% block action %}<div>ACTION-SENTINEL</div>{% endblock %}"
        "{% block empty_state_action %}<div>LEGACY-SENTINEL</div>{% endblock %}"
    )
    assert "ACTION-SENTINEL" in out
    assert "LEGACY-SENTINEL" in out
    assert out.index("ACTION-SENTINEL") < out.index("LEGACY-SENTINEL")


def test_empty_state_action_alone_still_renders_with_no_action_block_filled() -> None:
    out = _extend("{% block empty_state_action %}<div>LEGACY-SENTINEL</div>{% endblock %}")
    assert "LEGACY-SENTINEL" in out


def test_bare_empty_state_emits_no_action_markup() -> None:
    out = _render()
    assert "bw-btn" not in out


# --- size="sm" (ADR-060, STA-019, #218) ---------------------------------------


def test_default_size_carries_no_size_sm_class() -> None:
    out = _render()
    assert "bw-empty-state--size-sm" not in out


def test_size_sm_carries_the_size_sm_class() -> None:
    out = _render(size="sm")
    assert "bw-empty-state--size-sm" in out


def test_size_sm_with_heading_renders_a_paragraph_not_a_heading_element() -> None:
    out = _render(size="sm")
    assert '<p class="bw-empty-state__heading">No invoices yet</p>' in out
    assert "<h2" not in out


def test_size_sm_without_heading_renders_no_heading_markup_at_all() -> None:
    out = _render(size="sm", heading="")
    assert "bw-empty-state__heading" not in out


def test_size_md_without_heading_still_renders_the_empty_heading_element() -> None:
    # STA-003: heading stays required at "md"; an empty value still gets the
    # <h2> wrapper, unlike "sm" where an empty heading suppresses it entirely.
    out = _render(heading="")
    assert '<h2 class="bw-empty-state__heading"></h2>' in out


def test_size_sm_without_icon_renders_no_icon_markup() -> None:
    out = _render(size="sm")
    assert "bw-empty-state__icon" not in out


def test_size_sm_with_explicit_icon_still_renders_it() -> None:
    out = _render(size="sm", icon="trash")
    assert "bw-empty-state__icon" in out


def test_size_sm_action_renders_the_plain_link_not_the_primary_button() -> None:
    out = _render(size="sm", action_href="/invoices/new/", action_label="Create invoice")
    assert '<a class="bw-empty-state__action-link" href="/invoices/new/">Create invoice</a>' in out
    assert "bw-btn--primary" not in out


def test_size_md_action_still_renders_the_primary_button() -> None:
    out = _render(action_href="/invoices/new/", action_label="Create invoice")
    assert '<a class="bw-btn bw-btn--primary bw-btn--md" href="/invoices/new/">Create invoice</a>' in out
    assert "bw-empty-state__action-link" not in out


# --- icvoss/django-brickwork#391: variant must be constrained the same way
# --- size already is on the same line, not interpolated into attribute
# --- position -----------------------------------------------------------------


def _on_star_attrs(html: str) -> list[tuple[str, str]]:
    """Parse ``html`` and return every ``on*`` attribute actually present on
    any element, using ``html.parser`` rather than a regex/substring search
    (matching test_components.py's own ``_on_star_attrs`` for #349).

    A regex for ``onclick=`` also matches the correctly-escaped text INSIDE
    an attribute value, which is a false positive on clean output. Parsing
    and checking parsed attribute NAMES is the only technique that tells a
    live handler apart from its escaped, harmless text form.
    """
    from html.parser import HTMLParser

    class _Finder(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.found: list[tuple[str, str]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.found.extend((tag, name) for name, _value in attrs if name.startswith("on"))

    parser = _Finder()
    parser.feed(html)
    return parser.found


def test_variant_mark_safed_payload_cannot_break_out_of_the_class_attribute() -> None:
    # The exact repro from icvoss/django-brickwork#391: a mark_safe'd variant
    # closing the class attribute's quote and landing a live handler.
    from django.utils.safestring import mark_safe

    attack = mark_safe('a" onclick="alert(1)')
    out = _render(variant=attack)

    # Non-vacuity guard (ADR-084 section 7, #391's own recorded trap): a
    # probe that never reached the render passes "no handler found" for
    # free, proving nothing. The payload's marker text must actually be
    # checked for presence, and the control test below proves the same
    # payload DOES reach an unconstrained interpolation, so "not reached"
    # here is evidence the fix's match/literal branch is doing the work,
    # not evidence the probe itself is inert.
    reached = "alert(1)" in out
    assert not reached, (
        "the payload's own text landed in the rendered output, which means "
        "variant reached attribute position unconstrained; _empty_state.html "
        "must match variant against its closed vocabulary the same way it "
        "already matches size"
    )
    assert _on_star_attrs(out) == []


def test_variant_control_known_bad_inline_payload_is_detected_by_the_parser() -> None:
    # Teeth check: prove _on_star_attrs actually fires on a genuinely
    # unconstrained interpolation, using the same payload rendered directly
    # into attribute position via an ordinary include-only template, with no
    # constrain logic in the way. If this control did not detect a live
    # handler, the assertions above would be trivially true for the wrong
    # reason (a parser that never finds anything, not a template that is
    # actually safe).
    from django.template import Context, Template
    from django.utils.safestring import mark_safe

    attack = mark_safe('a" onclick="alert(1)')
    control_html = Template('<div class="bw-control bw-control--{{ v }}"></div>').render(Context({"v": attack}))
    assert "alert(1)" in control_html, "the control payload did not even reach the control template's output"
    assert _on_star_attrs(control_html) == [("div", "onclick")]


def test_variant_unrecognised_value_falls_back_to_the_no_data_literal() -> None:
    # The constrain pattern's other half: an unrecognised value is not just
    # blocked from attribute position, it resolves to the documented
    # default literal, matching size's existing fallback behaviour on the
    # same line.
    out = _render(variant="not-a-real-variant")
    assert "bw-empty-state--no_data" in out
    assert "bw-empty-state--not-a-real-variant" not in out


def test_variant_no_results_still_emits_its_own_literal_unchanged() -> None:
    # Regression guard alongside the fix: the documented second value must
    # keep resolving to its own literal, not collapse into the fallback.
    out = _render(variant="no_results")
    assert "bw-empty-state--no_results" in out
    assert "bw-empty-state--no_data" not in out
