"""Render tests for ``{% bw_token_specimen %}`` (THM-016, #268)."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

from brickwork.services.token_manifest import load_bearing


def _render(source: str, **ctx: object) -> str:
    return Template("{% load brickwork_theming %}" + source).render(Context(ctx))


def test_default_specimen_renders_load_bearing_rows_in_both_theme_panes() -> None:
    html = _render("{% bw_token_specimen %}")
    assert 'class="bw-token-specimen"' in html
    assert 'data-theme="light"' in html
    assert 'data-theme="dark"' in html
    assert "token-specimen.js" in html
    for entry in load_bearing():
        assert entry["name"] in html
        assert f"background: var({entry['name']})" in html
        if entry.get("contrastPair"):
            assert f'data-bw-token-pair="{entry["contrastPair"]}"' in html
            assert f"color: var({entry['name']})" in html
            assert f"background: var({entry['contrastPair']})" in html


def test_custom_tokens_list_is_validated_and_rendered() -> None:
    html = _render(
        "{% bw_token_specimen tokens=tokens heading=heading %}",
        tokens=["--bw-color-accent", "bw-color-surface"],
        heading="Accent delta",
    )
    assert "Accent delta" in html
    assert "--bw-color-accent" in html
    assert "--bw-color-surface" in html
    assert "--bw-color-danger" not in html.split("bw-token-specimen__list", 1)[1]


def test_unknown_or_empty_tokens_raise() -> None:
    with pytest.raises(TemplateSyntaxError, match="not in the overridable"):
        _render("{% bw_token_specimen tokens=tokens %}", tokens=["--bw-color-not-a-token"])
    with pytest.raises(TemplateSyntaxError, match="must not be empty"):
        _render("{% bw_token_specimen tokens=tokens %}", tokens=[])
    with pytest.raises(TemplateSyntaxError, match="sequence"):
        _render("{% bw_token_specimen tokens=tokens %}", tokens="--bw-color-accent")


def test_empty_graceful_is_not_applicable_because_load_bearing_always_ships() -> None:
    # The tag always has rows from the manifest; an all-empty include path does
    # not exist. Guard the assumption so a future empty loadBearing set fails
    # loudly here rather than shipping a blank section.
    assert len(load_bearing()) >= 1
    html = _render("{% bw_token_specimen %}")
    assert "bw-token-specimen__row" in html


def test_shipped_pe_script_exists_beside_marketing_overlay() -> None:
    root = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "js"
    assert (root / "token-specimen.js").is_file()
    text = (root / "token-specimen.js").read_text(encoding="utf-8")
    assert "data-bw-token-resolved" in text
    assert "getComputedStyle" in text


def test_level_l3_renders_radius_elevation_and_type_samples() -> None:
    html = _render('{% bw_token_specimen level="L3" %}')
    assert 'data-bw-token-kind="radius"' in html
    assert 'data-bw-token-kind="elevation"' in html
    assert 'data-bw-token-kind="type"' in html
    assert "bw-token-specimen__sample--radius" in html
    assert "border-radius: var(--bw-radius-md)" in html
    assert "box-shadow: var(--bw-elevation-2)" in html
    assert "font-family: var(--bw-font-family-sans)" in html
    assert "Theme tokens (L3)" in html


def test_level_and_tokens_are_mutually_exclusive() -> None:
    with pytest.raises(TemplateSyntaxError, match="tokens= or level="):
        _render(
            '{% bw_token_specimen level="L2" tokens=tokens %}',
            tokens=["--bw-color-accent"],
        )


def test_invalid_level_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="level="):
        _render('{% bw_token_specimen level="L9" %}')
