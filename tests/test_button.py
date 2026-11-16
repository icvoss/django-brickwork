"""Button contract tests (docs/components/button.md in icvoss/brickwork,
AC-BTN-016): the Django delivery emits the same classes and state attributes
as the HTML and React deliveries (BTN-070), a loading or disabled link button
is the non-navigable span (BTN-001, BTN-031), an icon-only button without a
name is a render error (BTN-050), and the vendored CSS source is the monorepo's
raised Button (BTN-071).

The rendered-class assertions here duplicate nothing in ``test_components.py``:
that file covers variant and size validation, the accessible-name seam and
``name``/``value``; this one pins the state markup and the lockstep mirror.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

_ROOT = Path(__file__).resolve().parent.parent
_CSS_MIRROR = _ROOT / "frontend/src/components.css"


def _render(snippet: str, **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(ctx))


def _root_tag(html: str) -> str:
    return re.search(r"<(?:button|a|span)\b[^>]*>", html).group(0)  # type: ignore[union-attr]


def _classes(tag: str) -> list[str]:
    return re.search(r'class="([^"]*)"', tag).group(1).split()  # type: ignore[union-attr]


@pytest.mark.parametrize("variant", ["primary", "secondary", "ghost", "danger"])
@pytest.mark.parametrize("size", ["xs", "sm", "md", "lg", "xl"])
def test_button_emits_variant_and_explicit_size_class(variant: str, size: str) -> None:
    tag = _root_tag(_render(f'{{% bw_button "Go" variant="{variant}" size="{size}" %}}'))
    assert _classes(tag) == ["bw-btn", f"bw-btn--{variant}", f"bw-btn--size-{size}"]


def test_button_default_is_primary_md_and_type_button() -> None:
    tag = _root_tag(_render('{% bw_button "Go" %}'))
    assert _classes(tag) == ["bw-btn", "bw-btn--primary", "bw-btn--size-md"]
    assert 'type="button"' in tag


@pytest.mark.parametrize("size", ["xs", "sm", "md", "lg", "xl"])
@pytest.mark.parametrize("host", ["", 'href="/x/"', 'href="/x/" disabled=True', 'href="/x/" loading=True'])
def test_every_size_step_is_emitted_on_every_host_and_changes_the_output(size: str, host: str) -> None:
    # ADR-060 section 3: each accepted step must change the output. The class
    # list differs per step on the <button>, <a> and both non-navigable spans.
    tag = _root_tag(_render(f'{{% bw_button "Go" size="{size}" {host} %}}'))
    assert f"bw-btn--size-{size}" in _classes(tag)
    others = {
        _classes(_root_tag(_render(f'{{% bw_button "Go" size="{other}" {host} %}}')))[2]
        for other in ("xs", "sm", "md", "lg", "xl")
    }
    assert len(others) == 5


@pytest.mark.parametrize("size", ["xs", "sm", "md", "lg", "xl"])
def test_icon_only_button_carries_every_size_step(size: str) -> None:
    tag = _root_tag(_render(f'{{% bw_button icon="plus" icon_only=True aria_label="Add" size="{size}" %}}'))
    assert _classes(tag) == ["bw-btn", "bw-btn--primary", f"bw-btn--size-{size}", "bw-btn--icon-only"]


def test_button_never_emits_the_bare_size_spelling_or_solid() -> None:
    out = _render(
        '{% bw_button "A" size="xs" %}{% bw_button "B" size="sm" %}{% bw_button "C" size="lg" %}'
        '{% bw_button "D" size="xl" %}'
    )
    assert not re.search(r"bw-btn--(xs|sm|md|lg|xl)\b", out)
    assert "bw-btn--solid" not in out
    assert "bw-btn--outline" not in out


def test_loading_button_is_busy_and_disabled_with_a_decorative_spinner() -> None:
    out = _render('{% bw_button "Save" loading=True %}')
    tag = _root_tag(out)
    assert tag.startswith("<button")
    assert 'aria-busy="true"' in tag
    assert re.search(r"\sdisabled\b", tag)
    assert re.search(r'<svg class="bw-spinner"[^>]*aria-hidden="true"', out)
    # The spinner leads the label.
    assert out.index("bw-spinner") < out.index("bw-btn__label")


def test_loading_link_button_is_a_non_navigable_busy_span() -> None:
    # Before the Button raise a loading link button stayed a navigable <a>
    # with no aria-busy (GAP-BTN-5).
    out = _render('{% bw_button "Go" href="/x/" loading=True %}')
    tag = _root_tag(out)
    assert tag.startswith("<span")
    assert "href" not in out
    assert 'aria-disabled="true"' in tag
    assert 'aria-busy="true"' in tag
    # Busy keeps the variant colours, so it does not take the flat disabled class.
    assert "bw-btn--disabled" not in _classes(tag)
    assert "bw-spinner" in out


def test_disabled_link_button_is_a_flat_non_navigable_span() -> None:
    out = _render('{% bw_button "Go" href="/x/" disabled=True %}')
    tag = _root_tag(out)
    assert tag.startswith("<span")
    assert "href" not in out
    assert "bw-btn--disabled" in _classes(tag)
    assert 'aria-disabled="true"' in tag
    assert "aria-busy" not in tag


def test_disabled_and_loading_link_button_is_busy_not_flat() -> None:
    tag = _root_tag(_render('{% bw_button "Go" href="/x/" disabled=True loading=True %}'))
    assert tag.startswith("<span")
    assert 'aria-busy="true"' in tag
    assert "bw-btn--disabled" not in _classes(tag)


def test_enabled_link_button_is_a_navigable_anchor_with_the_same_classes() -> None:
    tag = _root_tag(_render('{% bw_button "Go" href="/x/" variant="ghost" %}'))
    assert tag.startswith("<a ")
    assert 'href="/x/"' in tag
    assert _classes(tag) == ["bw-btn", "bw-btn--ghost", "bw-btn--size-md"]
    assert "aria-disabled" not in tag


def test_disabled_button_uses_the_disabled_attribute_only() -> None:
    tag = _root_tag(_render('{% bw_button "Go" disabled=True %}'))
    assert re.search(r"\sdisabled\b", tag)
    assert "aria-busy" not in tag
    assert "bw-btn--disabled" not in _classes(tag)


def test_icon_leads_the_label_and_is_decorative() -> None:
    out = _render('{% bw_button "Add" icon="plus" %}')
    assert out.index("bw-btn__icon") < out.index("bw-btn__label")
    assert re.search(r'<svg[^>]*class="[^"]*bw-icon[^"]*bw-btn__icon[^"]*"', out)
    assert 'aria-hidden="true"' in out


def test_icon_only_is_square_modifier_without_a_label_and_needs_a_name() -> None:
    out = _render('{% bw_button icon="plus" icon_only=True aria_label="Add item" %}')
    assert "bw-btn--icon-only" in _classes(_root_tag(out))
    assert "bw-btn__label" not in out
    with pytest.raises(TemplateSyntaxError, match="aria_label"):
        _render('{% bw_button icon="plus" icon_only=True %}')


def test_icon_only_loading_shows_the_spinner_in_place_of_the_glyph() -> None:
    out = _render('{% bw_button icon="plus" icon_only=True aria_label="Saving" loading=True %}')
    assert "bw-spinner" in out
    assert "bw-btn__icon" not in out
    assert 'aria-busy="true"' in out


# --- the vendored CSS source is the monorepo's raised Button (BTN-071) ------


def _button_block() -> str:
    css = _CSS_MIRROR.read_text()
    start = css.index("/* --- Buttons (docs/components/button.md)")
    # The standalone rule, at a line start: ".bw-btn .bw-spinner {" (the icon and
    # spinner step rule inside the Button block) must not end the block early.
    end = css.index("\n.bw-spinner {")
    return css[start:end]


def test_css_mirror_guards_state_rules_against_disabled_and_busy_hosts() -> None:
    block = re.sub(r"/\*.*?\*/", "", _button_block(), flags=re.S)
    guard = ':not(.bw-btn--disabled, :disabled, [aria-disabled="true"], [aria-busy="true"])'
    # Every hover and press rule carries the guard; none uses the old single :not().
    assert ":not(.bw-btn--disabled):hover" not in block
    assert ":not(.bw-btn--disabled):active" not in block
    assert block.count(guard) >= 11
    assert '.bw-btn[aria-disabled="true"]:not([aria-busy="true"])' in block


def test_css_mirror_has_the_raised_button_fixes() -> None:
    block = re.sub(r"/\*.*?\*/", "", _button_block(), flags=re.S)
    assert "white-space: nowrap" in block
    assert re.search(r"\.bw-btn:hover\s*\{\s*text-decoration:\s*none", block)
    assert re.search(r"\.bw-btn \.bw-btn__icon\s*\{[^}]*background:\s*transparent", block)
    assert ":is(.bw-btn--primary, .bw-btn--solid)" in block
    # Geometry reads the size tokens, never the density base or a literal.
    assert "var(--bw-size-control-height-md)" in block
    assert "--bw-density-control-height" not in block


def test_css_mirror_has_no_accent_fg_token() -> None:
    # --bw-color-accent-fg is not a token; .bw-btn--solid read it (GAP-BTN-6).
    assert "--bw-color-accent-fg" not in re.sub(r"/\*.*?\*/", "", _button_block(), flags=re.S)


# --- ADR-126: the fit class on the template mirror and the tag ---------------
# The CSS rule for bw-btn--fit-fill ships in the vendored @bwui/css (0.1.5 on),
# so bw_button takes the fit option (django-brickwork#748): it is never a silent
# no-op (ADR-060 section 3).


def test_button_template_emits_fit_fill_on_every_host_after_icon_only() -> None:
    tpl = "{% include 'brickwork/components/_button.html' %}"
    base = {"label": "Go", "variant": "primary", "size": "md", "type": "button", "fit": "fill"}
    for extra, host in (
        ({}, "<button"),
        ({"href": "/x/"}, "<a "),
        ({"href": "/x/", "disabled": True}, "<span"),
    ):
        tag = _root_tag(Template(tpl).render(Context({**base, **extra})))
        assert tag.startswith(host)
        assert "bw-btn--fit-fill" in _classes(tag)
    icon_only = _classes(_root_tag(Template(tpl).render(Context({**base, "icon_only": True, "aria_label": "x"}))))
    assert icon_only.index("bw-btn--icon-only") < icon_only.index("bw-btn--fit-fill")


@pytest.mark.parametrize("fit", ["", "auto"])
def test_button_template_emits_no_fit_class_for_auto_or_absent(fit: str) -> None:
    tpl = "{% include 'brickwork/components/_button.html' %}"
    ctx = {"label": "Go", "variant": "primary", "size": "md", "type": "button", "fit": fit}
    assert "bw-btn--fit-fill" not in Template(tpl).render(Context(ctx))


@pytest.mark.parametrize("host", ["", 'href="/x/"', 'href="/x/" disabled=True', 'href="/x/" loading=True'])
def test_bw_button_fit_fill_adds_the_class_on_every_host(host: str) -> None:
    tag = _root_tag(_render(f'{{% bw_button "Go" fit="fill" {host} %}}'))
    assert "bw-btn--fit-fill" in _classes(tag)
    assert "bw-btn--fit-fill" not in _classes(_root_tag(_render(f'{{% bw_button "Go" {host} %}}')))


@pytest.mark.parametrize("size", ["xs", "sm", "md", "lg", "xl"])
def test_bw_button_fit_fill_keeps_the_size_class_and_orders_after_it(size: str) -> None:
    classes = _classes(_root_tag(_render(f'{{% bw_button "Go" size="{size}" fit="fill" %}}')))
    assert classes == ["bw-btn", "bw-btn--primary", f"bw-btn--size-{size}", "bw-btn--fit-fill"]


def test_bw_button_fit_auto_is_the_default_and_emits_no_class() -> None:
    assert _classes(_root_tag(_render('{% bw_button "Go" fit="auto" %}'))) == _classes(
        _root_tag(_render('{% bw_button "Go" %}'))
    )


def test_bw_button_rejects_an_unknown_fit_and_fill_with_icon_only() -> None:
    with pytest.raises(TemplateSyntaxError, match="fit must be one of"):
        _render('{% bw_button "Go" fit="block" %}')
    with pytest.raises(TemplateSyntaxError, match="icon_only"):
        _render('{% bw_button icon="plus" icon_only=True aria_label="Add" fit="fill" %}')


# --- five sizes and type that follows the step (owner ruling 2026-11-16) ------


def test_css_mirror_has_all_five_size_classes_each_repointing_the_five_role_variables() -> None:
    block = re.sub(r"/\*.*?\*/", "", _button_block(), flags=re.S)
    for step in ("xs", "sm", "md", "lg", "xl"):
        rule = re.search(rf"\.bw-btn--size-{step} \{{([^}}]*)\}}", block)
        assert rule, f".bw-btn--size-{step} has a rule"
        for role in ("height", "padding-inline", "icon", "gap"):
            target = "icon-size" if role == "icon" else role
            assert f"--bw-control-{target}: var(--bw-size-control-{role}-{step});" in rule.group(1), (step, role)
        # ADR-127 (@bwui 0.1.9): the label size reads the computed type ladder
        # for the step, not a per-control font-size token (those were removed).
        assert f"--bw-control-font-size: var(--bw-font-size-{step});" in rule.group(1), (step, "font-size")
    # xs and xl were never shipped bare, so they exist in the new grammar only.
    assert not re.search(r"\.bw-btn--(xs|xl)\b", block)


def test_css_mirror_label_reads_the_font_size_role_variable() -> None:
    block = re.sub(r"/\*.*?\*/", "", _button_block(), flags=re.S)
    base = re.search(r"\n\.bw-btn \{([^}]*)\}", block).group(1)
    assert "font-size: var(--bw-control-font-size);" in base
    assert "--bw-text-label-size" not in base
