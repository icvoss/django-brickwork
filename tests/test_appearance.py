"""Appearance grammar: closed vocabularies and {% bw_options %} (#534)."""

from __future__ import annotations

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

from brickwork.appearance import (
    ELEVATIONS,
    FOOTER_RECIPES,
    HEADER_RECIPES,
    MEDIA_RECIPES,
    RADII,
    SIZES,
    SURFACES,
    validate_options,
)


def test_validate_options_accepts_every_closed_value() -> None:
    validate_options(
        component="test",
        surface="inverse",
        elevation="2",
        size="lg",
        radius="xl",
        header_recipe="accent",
        footer_recipe="actions",
        media_recipe="bleed",
        band="tint",
        width="bleed",
    )


def test_validate_options_skips_omitted_values() -> None:
    validate_options(component="test", surface="", elevation=None, header_recipe="  ")


@pytest.mark.parametrize(
    "axis,bad",
    [
        ("surface", "shiny"),
        ("elevation", "4"),
        ("size", "xl"),
        ("radius", "full"),
        ("header_recipe", "dark"),
        ("footer_recipe", "toolbar"),
        ("media_recipe", "cover"),
    ],
)
def test_validate_options_raises_on_unknown_value(axis: str, bad: str) -> None:
    with pytest.raises(TemplateSyntaxError, match=axis):
        validate_options(component="card", **{axis: bad})


def test_validate_options_rejects_unknown_axis() -> None:
    with pytest.raises(TemplateSyntaxError, match="unknown appearance axis"):
        validate_options(component="card", colour="red")


def test_bw_options_tag_raises_on_unknown_surface() -> None:
    with pytest.raises(TemplateSyntaxError, match="surface"):
        Template("{% load brickwork_components %}{% bw_options surface=surface %}").render(
            Context({"surface": "neon"})
        )


def test_bw_options_tag_is_quiet_when_valid() -> None:
    html = Template("{% load brickwork_components %}{% bw_options surface=surface elevation=elevation %}").render(
        Context({"surface": "raised", "elevation": "3"})
    )
    assert html == ""


def test_shared_vocabularies_match_appearance_doc_table() -> None:
    assert SURFACES == frozenset({"default", "raised", "tint", "inverse", "muted"})
    assert ELEVATIONS == frozenset({"0", "1", "2", "3"})
    assert SIZES == frozenset({"sm", "md", "lg"})
    assert RADII == frozenset({"default", "sm", "lg", "xl", "none"})
    assert HEADER_RECIPES == frozenset({"none", "plain", "bordered", "muted", "inverse", "accent"})
    assert FOOTER_RECIPES == frozenset({"none", "plain", "muted", "actions"})
    assert MEDIA_RECIPES == frozenset({"none", "bleed", "inset", "icon"})
