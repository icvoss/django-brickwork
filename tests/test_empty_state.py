"""Direct render tests for _empty_state.html (STA-001/002, CMP-032, SLOT wave).

Covers the pre-existing context-variable path (byte-identical for an
include-only caller), the new concise blocks (icon/title/description/action),
and the owner-mandated dual-shipping of the deprecated `empty_state_action`
block alongside the new `action` block: both must render.
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


# --- title / description blocks -----------------------------------------------


def test_title_block_override_wins_over_the_heading_context() -> None:
    out = _extend("{% block title %}Custom title{% endblock %}")
    assert "Custom title" in out
    assert "No invoices yet" not in out


def test_description_block_override_wins_over_the_body_context() -> None:
    out = _extend("{% block description %}Custom description{% endblock %}")
    assert "Custom description" in out
    assert "Create your first invoice to get started." not in out


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
