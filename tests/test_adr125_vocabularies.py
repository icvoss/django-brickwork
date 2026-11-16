"""ADR-125 vocabularies: one size grammar, one density axis, rail ``variant``.

django-brickwork#744. Every accepted size step must change the output
(ADR-060 rule 2: an accepted-but-unrendered step is a silent no-op), no
component inherits the full five-step set, and density is one three-value set
wherever it is a shared axis.
"""

from __future__ import annotations

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

from brickwork.appearance import (
    COMPONENT_OPTIONS,
    DENSITIES,
    DENSITIES_COMFORTABLE_COMPACT,
    OPTION_VOCABULARIES,
    SIZE_STEPS,
    size_subset,
    validate_options,
)
from brickwork.templatetags import brickwork_forms

_AVATAR = "brickwork/components/_avatar.html"
_CHIP = "brickwork/components/_chip.html"
_CARD = "brickwork/components/_card.html"
_BUTTON_GROUP = "brickwork/components/_button_group.html"
_MODAL = "brickwork/components/_modal.html"
_SLIDE_OVER = "brickwork/components/_slide_over.html"


def _render(path: str, **ctx: object) -> str:
    return render_to_string(path, ctx)


def _tag(src: str, **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + src).render(Context(ctx))


# --- the shared constants ----------------------------------------------------


def test_size_steps_are_the_five_step_grammar() -> None:
    assert SIZE_STEPS == ("xs", "sm", "md", "lg", "xl")


def test_densities_are_the_three_value_axis() -> None:
    assert frozenset({"comfortable", "compact", "spacious"}) == DENSITIES
    assert frozenset({"comfortable", "compact"}) == DENSITIES_COMFORTABLE_COMPACT


def test_bw_form_shares_the_one_density_constant() -> None:
    assert brickwork_forms._FORM_DENSITIES is DENSITIES


def test_size_subset_rejects_a_step_outside_the_grammar() -> None:
    with pytest.raises(ValueError, match="huge"):
        size_subset("sm", "huge")


def test_size_subset_allows_named_extra_values() -> None:
    assert size_subset("sm", extra=("full",)) == frozenset({"sm", "full"})


def test_no_shared_size_vocabulary_so_no_component_inherits_the_full_set() -> None:
    assert "size" not in OPTION_VOCABULARIES


def test_every_declared_size_is_a_subset_of_the_grammar_and_not_the_full_set() -> None:
    full = frozenset(SIZE_STEPS)
    for component, axes in COMPONENT_OPTIONS.items():
        if "size" not in axes:
            continue
        steps = axes["size"] - {"full"}
        assert steps <= full, component
        assert steps != full, f"{component} inherits the full set; declare what it renders"


def test_undeclared_component_rejects_size_by_name() -> None:
    with pytest.raises(TemplateSyntaxError, match="declares no size subset"):
        validate_options(component="brickwork/components/_divider.html", size="md")


def test_densities_axis_accepts_spacious_where_no_subset_is_declared() -> None:
    validate_options(component="brickwork/components/_unknown.html", density="spacious")


@pytest.mark.parametrize("component", ["brickwork/components/_data_table.html", "brickwork/components/_list_item.html"])
def test_density_subset_components_reject_spacious(component: str) -> None:
    # Their stylesheet renders comfortable and compact only; accepting spacious
    # would be a silent no-op.
    with pytest.raises(TemplateSyntaxError, match="density"):
        validate_options(component=component, density="spacious")


# --- each accepted step changes the output -----------------------------------


@pytest.mark.parametrize("size", ["xs", "sm", "md", "lg", "xl"])
def test_bw_button_each_step_emits_its_size_class(size: str) -> None:
    out = _tag('{% bw_button label="Go" size=size %}', size=size)
    assert f"bw-btn--size-{size}" in out


def test_bw_button_earns_the_whole_grammar_and_each_step_changes_the_output() -> None:
    # Button is the first component to earn all five steps (owner ruling
    # 2026-11-16). Each accepted step emits its own class, so none is a no-op.
    from brickwork.appearance import BUTTON_SIZES

    assert BUTTON_SIZES == frozenset(SIZE_STEPS)
    outputs = {size: _tag('{% bw_button label="Go" size=size %}', size=size) for size in SIZE_STEPS}
    assert len(set(outputs.values())) == len(SIZE_STEPS)


@pytest.mark.parametrize("size", ["xxs", "2xl", "huge", "full"])
def test_bw_button_rejects_a_step_outside_the_grammar(size: str) -> None:
    with pytest.raises(TemplateSyntaxError, match="bw_button size"):
        _tag('{% bw_button label="Go" size=size %}', size=size)


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_bw_gauge_each_step_emits_its_size_class(size: str) -> None:
    out = _tag("{% bw_gauge value=50 size=size %}", size=size)
    assert f"bw-gauge--size-{size}" in out


@pytest.mark.parametrize("size", ["xs", "xl"])
def test_bw_gauge_rejects_unearned_steps(size: str) -> None:
    with pytest.raises(TemplateSyntaxError, match="bw_gauge size"):
        _tag("{% bw_gauge value=50 size=size %}", size=size)


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_avatar_each_step_emits_its_size_class(size: str) -> None:
    assert f"bw-avatar--size-{size}" in _render(_AVATAR, initials="NC", size=size)


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_avatar_group_each_step_emits_its_size_class(size: str) -> None:
    out = _tag("{% bw_avatar_group avatars size=size %}", avatars=[{"initials": "NC"}], size=size)
    assert f"bw-avatar--size-{size}" in out


@pytest.mark.parametrize("size", ["sm", "md"])
def test_chip_each_step_emits_its_size_class(size: str) -> None:
    assert f"bw-chip--size-{size}" in _render(_CHIP, label="Open", size=size)


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_card_each_step_emits_its_size_class(size: str) -> None:
    assert f"bw-card--size-{size}" in _render(_CARD, title="T", size=size)


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_button_group_each_step_emits_its_size_class(size: str) -> None:
    out = _render(_BUTTON_GROUP, items=[{"label": "A", "href": "#"}], size=size)
    assert f"bw-button-group--size-{size}" in out
    assert f"bw-btn--size-{size}" in out


@pytest.mark.parametrize("size", ["sm", "md", "lg", "full"])
def test_modal_each_step_emits_its_size_class(size: str) -> None:
    assert f"bw-modal--size-{size}" in _render(_MODAL, title="T", size=size)


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_slide_over_each_step_emits_its_size_class(size: str) -> None:
    assert f"bw-slide-over--size-{size}" in _render(_SLIDE_OVER, title="T", size=size)


@pytest.mark.parametrize(
    "path,extra",
    [
        (_AVATAR, {"initials": "NC"}),
        (_CHIP, {"label": "Open"}),
        (_CARD, {"title": "T"}),
        (_BUTTON_GROUP, {"items": [{"label": "A", "href": "#"}]}),
        (_MODAL, {"title": "T"}),
        (_SLIDE_OVER, {"title": "T"}),
    ],
)
@pytest.mark.parametrize("size", ["xs", "xl"])
def test_components_reject_steps_they_have_not_earned(path: str, extra: dict, size: str) -> None:
    with pytest.raises(TemplateSyntaxError, match="size"):
        _render(path, size=size, **extra)


def test_no_template_emits_the_bare_size_spelling() -> None:
    # ADR-125 section 6: bw-<component>--size-<step> only. The bare spelling is
    # deprecated in the stylesheet and must not come out of the templates.
    out = _tag('{% bw_button label="Go" size="sm" %}')
    assert "bw-btn--sm" not in out.replace("bw-btn--size-sm", "")
