"""Disclosure component tests (04-interfaces section 4b, 0.8.0).

Renders the shipped _disclosure.html include directly (no testapp needed).
The component is a native <details>/<summary> element, so the no-JS floor
holds by construction (BR-BW-HTMX-001/006): it ships no JavaScript at all,
registers no Alpine.data component, and re-emits no bw: event. Single-open
accordion grouping rides the native <details name> attribute (CBH-016).
"""

from __future__ import annotations

from django.template import Context, Template, engines
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def _render(**ctx: object) -> str:
    ctx.setdefault("label", "What is brickwork?")
    ctx.setdefault("content", mark_safe("<p>Building blocks.</p>"))
    return render_to_string("brickwork/components/_disclosure.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    ctx.setdefault("label", "What is brickwork?")
    ctx.setdefault("content", mark_safe("<p>Building blocks.</p>"))
    source = "{% extends 'brickwork/components/_disclosure.html' %}" + blocks
    return Template(source).render(Context(ctx))


def _details_tag(html: str) -> str:
    """The opening <details ...> tag only, for attribute assertions."""
    start = html.index("<details")
    return html[start : html.index(">", start)]


def test_renders_a_native_details_summary_disclosure() -> None:
    html = _render()
    assert "<details" in html and "<summary" in html
    assert 'class="bw-disclosure bw-disclosure--divided"' in html
    assert '<span class="bw-disclosure__label">What is brickwork?</span>' in html
    assert '<div class="bw-disclosure__panel-inner"><p>Building blocks.</p></div>' in html


def test_default_output_is_byte_identical_to_pre_slot_blocks() -> None:
    # Full-string equality: substring checks above would pass on a
    # whitespace-only regression from a stray {% if %} inside trigger_meta's
    # new block.
    html = _render()
    assert html == (
        '\n\n<details class="bw-disclosure bw-disclosure--divided">\n  '
        '<summary class="bw-disclosure__trigger">\n    '
        '<span class="bw-disclosure__label">What is brickwork?</span>\n    \n    '
        '<svg class="bw-icon bw-disclosure__caret" style="--bw-icon-size: var(--bw-component-icon-size-sm)" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="var(--bw-component-icon-stroke-width, 2)" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>\n  </summary>\n  '
        '<div class="bw-disclosure__panel">\n    '
        '<div class="bw-disclosure__panel-inner"><p>Building blocks.</p></div>\n  </div>\n</details>\n'
    )


def test_ships_no_javascript_at_all() -> None:
    # JS-free by construction: no Alpine wiring, no htmx wiring, no script.
    html = _render()
    assert "x-data" not in html
    assert "hx-get" not in html and "hx-trigger" not in html
    assert "<script" not in html.lower()


def test_variant_variants() -> None:
    assert "bw-disclosure--divided" in _render()  # the default
    assert "bw-disclosure--bordered" in _render(variant="bordered")


def test_name_attribute_forms_a_native_accordion_group() -> None:
    # CBH-016: items sharing a name form a single-open accordion natively.
    assert ' name="faq"' in _details_tag(_render(name="faq"))
    assert " name=" not in _details_tag(_render())


def test_open_flag_renders_the_open_attribute() -> None:
    # CBH-017
    assert " open" in _details_tag(_render(open=True))
    assert " open" not in _details_tag(_render())


def test_trigger_meta_renders_at_the_trigger_inline_end() -> None:
    # CMP-027
    html = _render(trigger_meta=mark_safe('<span class="count">3</span>'))
    assert '<span class="bw-disclosure__meta"><span class="count">3</span></span>' in html
    assert "bw-disclosure__meta" not in _render()


def test_trigger_meta_block_override_wins_over_the_trigger_meta_context() -> None:
    # SLOT wave (CMP-027, the-wall): the block is safe to add here because
    # _disclosure.html is structural/include-consumed, not tag-consumed
    # (unlike _dropdown.html/_tabs.html/_toast.html/_combobox.html, whose
    # logic lives behind their {% bw_* %} tag).
    html = _extend(
        "{% block trigger_meta %}<span>META-SENTINEL</span>{% endblock %}",
        trigger_meta="Ignored",
    )
    assert "META-SENTINEL" in html
    assert "Ignored" not in html


def test_trigger_meta_block_override_works_with_no_context_variable_set() -> None:
    html = _extend("{% block trigger_meta %}<span>META-SENTINEL</span>{% endblock %}")
    assert "META-SENTINEL" in html


def test_caret_icon_is_decorative() -> None:
    html = _render()
    assert "bw-disclosure__caret" in html
    assert 'aria-hidden="true"' in html


def test_label_is_escaped() -> None:
    html = _render(label="<b>bold</b>")
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_unsafe_content_is_escaped() -> None:
    # content is documented as pre-rendered HTML marked safe at the call
    # site; a plain (unsafe) string must stay escaped.
    html = _render(content="<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_no_aria_menu_or_button_role_claims() -> None:
    # Native disclosure semantics only: the browser owns the behaviour.
    html = _render(open=True)
    assert 'role="' not in html


def test_a_group_of_three_shares_one_name() -> None:
    engine = engines["django"]
    template = engine.from_string(
        "{% for item in items %}"
        '{% include "brickwork/components/_disclosure.html" with label=item.label content=item.content name="faq" %}'
        "{% endfor %}"
    )
    html = template.render({"items": [{"label": f"Q{n}", "content": f"A{n}"} for n in range(3)]})
    assert html.count('name="faq"') == 3
    assert html.count("<details") == 3
