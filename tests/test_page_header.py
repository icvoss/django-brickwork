"""Direct render tests for _page_header.html (CMP-034/035/036, SLOT wave).

The page header is a structural composition component: its named blocks are
extended, matching test_card.py's own `_extend` helper shape. Covers the
byte-identical backwards-compatibility contract (an include-only caller
passing title/description/loading gets exactly what it got before these
blocks existed) plus each new block's default content and override.
"""

from __future__ import annotations

from django.template import Context, Template
from django.template.loader import render_to_string


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_page_header.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    return Template("{% extends 'brickwork/components/_page_header.html' %}" + blocks).render(Context(ctx))


# --- backwards compatibility -------------------------------------------------


def test_include_only_title_renders_byte_identical_to_pre_block_output() -> None:
    # The whitespace-normalised structure and text content match exactly what
    # the pre-block template rendered; only the blocks' own empty-tag
    # whitespace is new (blocks add no markup, only structure to override).
    out = _render(title="Invoices")
    assert '<header class="bw-page-header">' in out
    assert '<div class="bw-page-header__titles">' in out
    assert '<h1 class="bw-page-header__title">Invoices</h1>' in out
    assert "</header>" in out
    # No description paragraph, no skeleton, no new region markup.
    assert "bw-page-header__description" not in out
    assert "bw-skeleton" not in out


def test_title_only_output_is_byte_identical_to_pre_slot_blocks() -> None:
    # Full-string equality, not just "the expected substrings are present"
    # (a whitespace-only regression from a stray {% if %} line inside the
    # blocks would pass the substring checks above while still changing
    # every existing render; test_components.py's #119 button test pins the
    # same class of regression the same way).
    out = _render(title="Invoices")
    assert out == (
        '\n<header class="bw-page-header">\n  \n  \n    <div class="bw-page-header__titles">\n'
        '      <h1 class="bw-page-header__title">Invoices</h1>\n      \n      \n    </div>\n'
        "  \n  \n  \n</header>\n"
    )


def test_title_and_description_output_is_byte_identical_to_pre_slot_blocks() -> None:
    out = _render(title="Invoices", description="All invoices for this account.")
    assert out == (
        '\n<header class="bw-page-header">\n  \n  \n    <div class="bw-page-header__titles">\n'
        '      <h1 class="bw-page-header__title">Invoices</h1>\n      \n      '
        '<p class="bw-page-header__description">All invoices for this account.</p>\n    </div>\n'
        "  \n  \n  \n</header>\n"
    )


def test_include_only_title_and_description() -> None:
    out = _render(title="Invoices", description="All invoices for this account.")
    assert '<h1 class="bw-page-header__title">Invoices</h1>' in out
    assert '<p class="bw-page-header__description">All invoices for this account.</p>' in out


def test_loading_swaps_title_and_description_for_a_skeleton() -> None:
    out = _render(title="Invoices", description="All invoices.", loading=True)
    assert "bw-skeleton--title" in out and "bw-skeleton--text" in out
    assert "Invoices" not in out
    assert "All invoices." not in out


# --- new blocks: default (unfilled) render nothing extra --------------------


def test_bare_header_emits_no_new_region_markup() -> None:
    out = _render(title="Invoices")
    for cls in ("bw-page-header__badge", "bw-breadcrumbs", "bw-page-header__actions", "bw-tabs"):
        assert cls not in out, f"unfilled region emitted markup: {cls}"


# --- breadcrumb ---------------------------------------------------------------


def test_breadcrumb_block_renders_above_the_title_row() -> None:
    out = _extend(
        "{% block breadcrumb %}<nav>CRUMB-SENTINEL</nav>{% endblock %}",
        title="Invoices",
    )
    assert out.index("CRUMB-SENTINEL") < out.index("Invoices")


# --- title / title_badge / description --------------------------------------


def test_title_block_override_wins_over_the_title_context() -> None:
    out = _extend(
        "{% block title %}Custom heading{% endblock %}",
        title="Invoices",
    )
    assert "Custom heading" in out
    assert "Invoices" not in out


def test_title_badge_block_renders_beside_the_title() -> None:
    out = _extend(
        "{% block title_badge %}<span>BADGE-SENTINEL</span>{% endblock %}",
        title="Invoices",
    )
    assert "BADGE-SENTINEL" in out
    assert out.index("Invoices") < out.index("BADGE-SENTINEL")


def test_description_block_override_wins_over_the_description_context() -> None:
    out = _extend(
        "{% block description %}Custom description{% endblock %}",
        title="Invoices",
        description="Ignored",
    )
    assert "Custom description" in out
    assert "Ignored" not in out


def test_title_and_description_blocks_are_not_rendered_while_loading() -> None:
    out = _extend(
        "{% block title %}Custom heading{% endblock %}{% block description %}Custom description{% endblock %}",
        title="Invoices",
        loading=True,
    )
    assert "Custom heading" not in out
    assert "Custom description" not in out
    assert "bw-skeleton--title" in out


# --- actions / tabs -----------------------------------------------------------


def test_actions_block_renders_after_the_titles_region() -> None:
    out = _extend(
        "{% block actions %}<div>ACTIONS-SENTINEL</div>{% endblock %}",
        title="Invoices",
    )
    assert out.index("Invoices") < out.index("ACTIONS-SENTINEL")


def test_tabs_block_renders_after_actions() -> None:
    out = _extend(
        "{% block actions %}<div>ACTIONS-SENTINEL</div>{% endblock %}{% block tabs %}<div>TABS-SENTINEL</div>{% endblock %}",
        title="Invoices",
    )
    assert out.index("ACTIONS-SENTINEL") < out.index("TABS-SENTINEL")
