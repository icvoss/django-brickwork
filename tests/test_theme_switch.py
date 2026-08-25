"""{% bw_theme_switch %} contract tests (icvoss/django-brickwork#117).

The live root-level control over theme/density/dir/brand. ADR-060 governs
axes= (a closed, space-separated vocabulary); the no-JS floor is
deliberately "render nothing" (the ruling's one departure from the
package's usual doctrine); persistence follows SHL-003, generalised from
frontend/src/js/sidebar_collapse.js, with server-resolved axes rendering
locked (disabled, unchangeable) rather than free client toggles.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"


def _render(src: str = "{% bw_theme_switch %}", **ctx: object) -> str:
    return engines["django"].from_string("{% load brickwork_theming %}" + src).render(ctx)


# --- the no-JS floor (BR-BW-HTMX-001, the #117 ruling's departure) -----------


def test_control_root_ships_hidden() -> None:
    # The server-rendered page is already correctly themed, so a no-JS theme
    # switch would be a control that visibly does nothing. The floor is
    # "render nothing": the root ships hidden, and only bwThemeSwitch's init
    # removes it.
    html = _render()
    assert "data-bw-theme-switch" in html
    start = html.index("<div")
    root_tag = html[start : html.index(">", start)]
    assert "hidden" in root_tag


def test_alpine_component_is_wired() -> None:
    html = _render()
    assert 'x-data="bwThemeSwitch(' in html or 'x-data="bwThemeSwitch()"' in html


def test_every_focusable_control_is_inside_the_hidden_root() -> None:
    # The no-JS floor depends on `hidden` covering every radio the browser
    # accessibility tree and keyboard focus order could otherwise reach: a
    # single `hidden` attribute on the OUTERMOST element enclosing every
    # <input> is sufficient (the browser propagates hidden to all
    # descendants), but a `hidden` on some inner wrapper that leaves inputs
    # outside it is not. Parse the DOM structurally rather than checking the
    # root tag's own attribute string in isolation (that alone does not
    # prove containment), one call each for the default axes and the widest
    # (brand-inclusive) axis set, since a future template change could add a
    # control outside the root without breaking the substring-only check.
    from html.parser import HTMLParser

    class _ContainmentParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.depth = 0
            self.root_hidden_depth: int | None = None
            self.escaped_inputs: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            attr_names = {name for name, _ in attrs}
            if tag == "div" and self.root_hidden_depth is None:
                assert "hidden" in attr_names, "root <div> must carry the hidden attribute"
                self.root_hidden_depth = self.depth
            if tag in {"input", "fieldset"} and self.root_hidden_depth is None:
                self.escaped_inputs.append(tag)
            self.depth += 1

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.handle_starttag(tag, attrs)
            self.depth -= 1

        def handle_endtag(self, tag: str) -> None:
            self.depth -= 1

    for html in (
        _render(),
        _render('{% bw_theme_switch axes="theme density dir brand" brands=brands %}', brands={"acme": "Acme"}),
    ):
        parser = _ContainmentParser()
        parser.feed(html)
        assert parser.root_hidden_depth == 0, "the hidden div must be the outermost element"
        assert not parser.escaped_inputs, "every input/fieldset must be inside the hidden root"


# --- ADR-060 option grammar: axes= is a closed, space-separated vocabulary --


def test_default_axes_are_theme_density_dir() -> None:
    html = _render()
    assert 'data-bw-theme-switch-axis="theme"' in html
    assert 'data-bw-theme-switch-axis="density"' in html
    assert 'data-bw-theme-switch-axis="dir"' in html
    assert 'data-bw-theme-switch-axis="brand"' not in html


def test_axes_can_narrow_to_one() -> None:
    html = _render('{% bw_theme_switch axes="theme" %}')
    assert 'data-bw-theme-switch-axis="theme"' in html
    assert 'data-bw-theme-switch-axis="density"' not in html
    assert 'data-bw-theme-switch-axis="dir"' not in html


def test_axes_render_in_a_fixed_order_regardless_of_input_order() -> None:
    html = _render('{% bw_theme_switch axes="dir theme" %}')
    theme_pos = html.index('data-bw-theme-switch-axis="theme"')
    dir_pos = html.index('data-bw-theme-switch-axis="dir"')
    assert theme_pos < dir_pos


def test_unknown_axis_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="theme colour" %}')


def test_duplicate_axis_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="theme theme" %}')


def test_empty_axes_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="" %}')


# --- brand is opt-in, never a default axis (the ruling's constraint) --------


def test_brand_absent_by_default() -> None:
    html = _render()
    assert "bw-theme-switch__group" in html  # sanity: something rendered
    assert 'data-bw-theme-switch-axis="brand"' not in html


def test_brand_requested_without_brands_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="brand" %}')


def test_brand_requested_with_brands_renders_the_supplied_slugs() -> None:
    html = _render(
        '{% bw_theme_switch axes="brand" brands=brands %}',
        brands={"acme": "Acme", "globex": "Globex"},
    )
    assert 'data-bw-theme-switch-axis="brand"' in html
    assert 'value="acme"' in html
    assert "Acme" in html
    assert 'value="globex"' in html
    assert "Globex" in html


def test_brands_not_a_mapping_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="brand" brands="acme" %}')


def test_brands_key_with_an_unsafe_slug_raises() -> None:
    # review fix, #117: brands= keys become data-bw-brand attribute values
    # and [data-bw-brand="..."] selector values, so they must pass the same
    # attribute-safe slug rule resolve_theme_attributes applies to a
    # resolver's own brand key. Validated server-side at render time.
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="brand" brands=brands %}', brands={"bad slug!": "Bad"})


def test_brands_key_starting_with_a_digit_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch axes="brand" brands=brands %}', brands={"1acme": "Acme"})


def test_brands_valid_slugs_render() -> None:
    html = _render(
        '{% bw_theme_switch axes="brand" brands=brands %}',
        brands={"acme-1": "Acme", "globex_corp": "Globex"},
    )
    assert 'value="acme-1"' in html
    assert 'value="globex_corp"' in html


# --- the closed value vocabularies (ADR-060 rule 2: validated, not a suggestion)


def test_theme_values_are_light_and_dark() -> None:
    html = _render('{% bw_theme_switch axes="theme" %}')
    assert 'value="light"' in html
    assert 'value="dark"' in html


def test_density_values_are_the_three_documented_steps() -> None:
    html = _render('{% bw_theme_switch axes="density" %}')
    assert 'value="compact"' in html
    assert 'value="comfortable"' in html
    assert 'value="spacious"' in html


def test_dir_values_are_ltr_and_rtl() -> None:
    html = _render('{% bw_theme_switch axes="dir" %}')
    assert 'value="ltr"' in html
    assert 'value="rtl"' in html


# --- locked_axes: SHL-003 precedence, a server preference is never offered --
# as a client-overridable toggle (the #117 ruling) ---------------------------


def test_unlocked_axis_renders_enabled_radios() -> None:
    html = _render('{% bw_theme_switch axes="theme" %}')
    assert "data-bw-locked" not in html
    assert "disabled" not in html


def test_locked_axis_renders_disabled_radios_and_a_note() -> None:
    html = _render('{% bw_theme_switch axes="theme density dir" locked_axes="theme" %}')
    # the theme fieldset is locked; density/dir are not
    theme_block_start = html.index('data-bw-theme-switch-axis="theme"')
    theme_fieldset_start = html.rindex("<fieldset", 0, theme_block_start)
    theme_fieldset_end = html.index("</fieldset>", theme_fieldset_start)
    theme_fieldset = html[theme_fieldset_start:theme_fieldset_end]
    assert "data-bw-locked" in theme_fieldset
    assert "disabled" in theme_fieldset

    density_block_start = html.index('data-bw-theme-switch-axis="density"')
    density_fieldset_start = html.rindex("<fieldset", 0, density_block_start)
    density_fieldset_end = html.index("</fieldset>", density_fieldset_start)
    density_fieldset = html[density_fieldset_start:density_fieldset_end]
    assert "data-bw-locked" not in density_fieldset
    assert "disabled" not in density_fieldset


def test_locked_axes_can_lock_more_than_one() -> None:
    html = _render('{% bw_theme_switch axes="theme density" locked_axes="theme density" %}')
    assert html.count("data-bw-locked") == 2


def test_unknown_locked_axis_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_theme_switch locked_axes="colour" %}')


def test_bare_call_locks_from_bw_theme_locked_axes_context_variable() -> None:
    # review fix, #117 blocker 4: the documented bare {% bw_theme_switch %}
    # call (BRANDING.md) must be safe by default on a resolver-backed page,
    # so locked_axes= defaults from the ambient context variable
    # brickwork.context_processors.theme sets, rather than requiring the
    # caller to pass it explicitly.
    html = _render("{% bw_theme_switch %}", bw_theme_locked_axes="theme")
    theme_block_start = html.index('data-bw-theme-switch-axis="theme"')
    theme_fieldset_start = html.rindex("<fieldset", 0, theme_block_start)
    theme_fieldset_end = html.index("</fieldset>", theme_fieldset_start)
    assert "data-bw-locked" in html[theme_fieldset_start:theme_fieldset_end]


def test_bare_call_with_no_locked_axes_in_context_locks_nothing() -> None:
    html = _render("{% bw_theme_switch %}")
    assert "data-bw-locked" not in html


def test_explicit_locked_axes_overrides_the_context_default() -> None:
    # Passing locked_axes= (even "") is a deliberate override, not a merge:
    # the explicit empty string here forces every axis writable regardless
    # of what the context says.
    html = _render('{% bw_theme_switch locked_axes="" %}', bw_theme_locked_axes="theme")
    assert "data-bw-locked" not in html


# --- multiple instances on one page never collide (radio name/id uniqueness)


def test_two_instances_do_not_share_radio_group_names() -> None:
    html = _render("{% bw_theme_switch axes='theme' %}{% bw_theme_switch axes='theme' %}")
    import re

    # Each instance's "theme" axis renders two radios (light/dark) sharing
    # one name=, so dedupe to the per-instance group names before asserting
    # the two instances themselves do not collide.
    names = sorted(set(re.findall(r'name="([^"]+)"', html)))
    assert len(names) == 2
    assert names[0] != names[1]


def test_two_instances_do_not_share_root_ids() -> None:
    html = _render("{% bw_theme_switch axes='theme' %}{% bw_theme_switch axes='theme' %}")
    import re

    ids = re.findall(r'<div class="bw-theme-switch"\s+id="([^"]+)"', html)
    assert len(ids) == 2
    assert ids[0] != ids[1]


# --- accessible name (a fieldset of radios, per the issue's a11y guidance) --


def test_wrapper_has_a_semantic_target_for_aria_label() -> None:
    # review concern, #117: aria-label on a bare <div> with no ARIA role has
    # no semantic target and is ignored by assistive tech; role="group" is
    # the generic grouping role that DOES accept it.
    html = _render()
    start = html.index("<div")
    root_tag = html[start : html.index(">", start)]
    assert 'role="group"' in root_tag


def test_default_label_is_a_translated_string() -> None:
    html = _render()
    assert 'aria-label="Display settings"' in html


def test_label_override_is_used() -> None:
    html = _render('{% bw_theme_switch label="Try the theme" %}')
    assert 'aria-label="Try the theme"' in html


def test_each_axis_has_a_legend() -> None:
    html = _render('{% bw_theme_switch axes="theme density dir" %}')
    assert "<legend" in html
    assert html.count("<legend") == 3


# --- the shipped JS bundle contract ------------------------------------------


def test_bundle_registers_bwthemeswitch_and_emits_the_change_event() -> None:
    bundle = _DIST_JS.read_text()
    assert "bwThemeSwitch" in bundle
    assert "bw:theme-switch:change" in bundle


def test_bundle_never_starts_alpine_for_theme_switch() -> None:
    bundle = _DIST_JS.read_text()
    assert "Alpine.start(" not in bundle
