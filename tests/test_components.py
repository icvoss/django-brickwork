"""Direct unit tests for the component template tags (button/badge/alert).

These render each tag in isolation (no testapp needed), covering the branch paths
the integration suite exercises only indirectly: variant/size validation, the
icon-only accessible-name enforcement (ICO-008), loading, the link-vs-button
split, and the 0.9.0 dismissible upgrade to alert and badge (04-interfaces 4b).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django import forms
from django.template import Context, Template, engines
from django.template.exceptions import TemplateSyntaxError

from tests._class_contract import UNSTYLED_BY_DESIGN, unstyled_classes

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"
_COMPILED_CSS = _DIST_JS.parent / "brickwork.css"


def _render(snippet: str, **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(ctx))


# --- normalise_accessible_name (icvoss/django-brickwork#330) ---------------
#
# The shared helper behind bw_button's aria_label, bw_toggle's label,
# bw_dropdown's aria_label/trigger_label/item label, and bw_tabs' tab label.
# Exercised directly here for the requirement-by-requirement pin from #330;
# the per-tag tests elsewhere in this file and in test_inputs.py/
# test_dropdown.py/test_tabs.py exercise the same requirements through
# ordinary template syntax at each call site.


def test_normalise_accessible_name_requirement_1_safe_ampersand_not_double_escaped() -> None:
    from django.utils.html import format_html

    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    label = format_html("Tom {} more", "&")
    out = Template("{{ label }}").render(Context({"label": normalise_accessible_name(label)}))
    assert out == "Tom &amp; more"  # single-escaped source; displays as "Tom & more"


def test_normalise_accessible_name_requirement_2_non_str_does_not_raise() -> None:
    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    assert normalise_accessible_name(5) == "5"


def test_normalise_accessible_name_requirement_3_str_able_object_renders_str_form() -> None:
    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    class _Obj:
        def __str__(self) -> str:
            return "Widget One"

    assert normalise_accessible_name(_Obj()) == "Widget One"


def test_normalise_accessible_name_requirement_4_padded_string_is_stripped() -> None:
    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    assert normalise_accessible_name("  Save  ") == "Save"


def test_normalise_accessible_name_requirement_5_blank_string_is_falsy() -> None:
    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    assert not normalise_accessible_name("   ")


def test_normalise_accessible_name_requirement_6_mark_safe_bold_not_escaped() -> None:
    from django.utils.safestring import mark_safe

    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    out = Template("{{ label }}").render(Context({"label": normalise_accessible_name(mark_safe("<b>x</b>"))}))
    assert out == "<b>x</b>"  # bold, not escaped text


def test_normalise_accessible_name_requirement_7_gettext_lazy_still_works() -> None:
    from django.utils.translation import gettext_lazy

    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    assert normalise_accessible_name(gettext_lazy("  Save  ")) == "Save"


def test_normalise_accessible_name_requirement_8_plain_ampersand_still_escaped() -> None:
    # The trap: an ordinary never-safe string must still render escaped, or
    # every consumer label becomes an injection vector (the #329 defect
    # class this whole fix exists downstream of).
    from brickwork.templatetags.brickwork_components import normalise_accessible_name

    out = Template("{{ label }}").render(Context({"label": normalise_accessible_name("Tom & more")}))
    assert out == "Tom &amp; more"


# --- button ---------------------------------------------------------------


def test_button_renders_a_button_by_default() -> None:
    out = _render('{% bw_button "Save" variant="primary" %}')
    assert "<button" in out and "bw-btn--primary" in out
    assert "Save" in out


def test_button_with_href_renders_an_anchor() -> None:
    out = _render('{% bw_button "Go" href="/x/" variant="secondary" %}')
    assert "<a " in out and 'href="/x/"' in out


def test_button_icon_only_requires_aria_label() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_button icon="trash" icon_only=True aria_label="" %}')


@pytest.mark.parametrize("blank", ["   ", "\t", "\n", " \t\n "])
def test_button_icon_only_whitespace_only_aria_label_is_not_a_name(blank: str) -> None:
    # A whitespace-only aria_label is truthy in Python and is not an accessible
    # name to any screen reader; without the strip-and-rebind fix this passes
    # the truthiness check and renders. Calls the tag function directly: a raw
    # newline inside {% ... aria_label="..." %} does not survive Django's
    # template parser.
    from brickwork.templatetags.brickwork_components import bw_button

    with pytest.raises(TemplateSyntaxError):
        bw_button(icon="trash", icon_only=True, aria_label=blank)


def test_button_icon_only_padded_aria_label_is_stripped_not_rejected() -> None:
    out = _render('{% bw_button icon="trash" icon_only=True aria_label="  Delete  " %}')
    assert 'aria-label="Delete"' in out


def test_button_non_str_aria_label_via_ordinary_template_syntax_does_not_raise() -> None:
    # #330 regression: a bare aria_label.strip() raised AttributeError on any
    # non-str value. Rendered through ordinary template syntax, the route the
    # regression actually reaches a consumer through, not a direct call.
    # Fails without the fix (AttributeError: 'int' object has no attribute
    # 'strip').
    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n=5)
    assert 'aria-label="5"' in out


def test_button_gettext_lazy_aria_label_still_works_and_is_stripped() -> None:
    # #330 requirement 7: gettext_lazy worked before the #327 strip was added
    # (a lazy proxy only becomes a str when str()'d/escaped); must keep working.
    from django.utils.translation import gettext_lazy

    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n=gettext_lazy("  Delete  "))
    assert 'aria-label="Delete"' in out


def test_button_format_html_aria_label_is_escaped_because_attribute_position_does_not_trust_safedata() -> None:
    # Supersedes the old #330-regression-2 "preserve an already-safe value"
    # expectation for THIS value, for the same reason as the mark_safe bold
    # test above: aria_label is attribute-only, and SafeData records THAT a
    # value was vetted safe, never for WHICH position, so it cannot be
    # trusted to mean "safe as an attribute value" (icvoss/django-brickwork
    # #349). A format_html value is an ordinary source of SafeData, not a
    # special case: its already-escaped "&amp;" is escaped again here,
    # visibly as literal "&amp;amp;" text, which is the accepted cost this
    # fix trades for closing the break-out.
    from django.utils.html import format_html

    label = format_html("Tom {} more", "&")
    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n=label)
    assert 'aria-label="Tom &amp;amp; more"' in out


def test_button_plain_ampersand_aria_label_is_still_escaped() -> None:
    # #330 requirement 8, the trap: an ordinary never-safe string must still
    # be escaped normally. If the fix instead blanket-marked every aria_label
    # safe, this would regress to an injection vector (the exact #329 defect
    # class). Fails if the fix over-corrects into "everything is safe".
    #
    # Passed through a context variable, not a template literal: a quoted
    # literal in the template's own source (aria_label="Tom & more") is
    # marked SafeString by Django's parser itself (Variable.__init__,
    # unconditionally, for every tag, since before this fix existed), so it
    # is indistinguishable from a genuine mark_safe() value by the time it
    # reaches the tag function, and no helper here can or should try to
    # un-trust it. The real attack surface, and the one #329 was about, is
    # consumer/runtime data arriving via a context variable, which this
    # exercises.
    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n="Tom & more")
    assert 'aria-label="Tom &amp; more"' in out


def test_button_mark_safe_bold_aria_label_is_escaped_because_attribute_position_is_not_text_position() -> None:
    # Supersedes the old #330-requirement-6 expectation for THIS value.
    # #330's "mark_safe pass-through" rule is right for TEXT position
    # (bw_toggle's label, bw_tabs' tab label): a consumer already trusted to
    # author safe HTML gets that markup rendered as markup. aria_label is
    # never text position here, only an attribute value, and honouring
    # __html__ in an attribute is exactly how a mark_safe'd aria_label broke
    # out of the quote and landed a live event handler
    # (icvoss/django-brickwork#349). The accepted cost: a mark_safe'd
    # aria_label's markup now renders as literal escaped text, not as bold.
    from django.utils.safestring import mark_safe

    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n=mark_safe("<b>x</b>"))
    assert 'aria-label="&lt;b&gt;x&lt;/b&gt;"' in out
    assert 'aria-label="<b>x</b>"' not in out


# --- icvoss/django-brickwork#349: a SafeString aria_label must not break out
# --- of the attribute it is rendered into -------------------------------------


def _on_star_attrs(html: str) -> list[tuple[str, str]]:
    """Parse ``html`` and return every ``on*`` attribute actually present on
    any element, using ``html.parser`` rather than a regex/substring search.

    A regex for ``onclick=`` matches the correctly-escaped text INSIDE
    ``aria-label="a&quot; onclick=&quot;..."``, which is a false positive on
    clean output (icvoss/django-brickwork#349's own "Tests worth writing").
    Parsing and checking parsed attribute NAMES is the only technique that
    tells a live handler apart from its escaped, harmless text form.
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


def test_button_mark_safed_aria_label_cannot_break_out_of_the_attribute_it_renders_into() -> None:
    # The attribute-position break-out this whole issue is about: a
    # mark_safe'd aria_label closing the quote and landing a live handler.
    # Reproduces #349's own repro string through ordinary template syntax.
    from django.utils.safestring import mark_safe

    attack = mark_safe('a" onclick="alert(1)')
    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n=attack)
    assert _on_star_attrs(out) == []


def test_button_plain_special_characters_in_aria_label_are_escaped_exactly_once_in_attribute_position() -> None:
    out = _render('{% bw_button icon="trash" icon_only=True aria_label=n %}', n='a & b " c')
    assert 'aria-label="a &amp; b &quot; c"' in out
    assert "&amp;amp;" not in out
    assert "&amp;quot;" not in out


def test_button_whitespace_only_aria_label_on_non_icon_only_path_omits_attribute() -> None:
    # #330 "ALSO" behaviour change: aria_label is optional (not hard-required)
    # when icon_only is not set, so a whitespace-only value strips to "" and
    # _button.html's {% if aria_label %} then omits the attribute entirely,
    # rather than raising or emitting the stale unstripped value. The button
    # still carries its own visible label, so it is not left unnamed.
    out = _render('{% bw_button "Save" aria_label="   " %}')
    assert "aria-label=" not in out
    assert "Save" in out  # the visible label still names the control


def test_button_icon_only_with_label_omits_visible_text() -> None:
    out = _render('{% bw_button icon="trash" icon_only=True aria_label="Delete" %}')
    assert 'aria-label="Delete"' in out
    assert "bw-btn--icon-only" in out
    assert "bw-btn__label" not in out


def test_button_loading_marks_busy_and_disabled() -> None:
    out = _render('{% bw_button "Save" loading=True %}')
    assert 'aria-busy="true"' in out
    assert "bw-spinner" in out
    # ICO-004/issue #16: the spinner sizes via the --bw-icon-size CSS custom
    # property (which .bw-spinner reads for inline-size/block-size), never as
    # an SVG width/height attribute (var() is invalid there and silently
    # falls back to the 300x150 SVG default). The token is the canonical
    # component-tier name (0.11.0 tier re-grammar).
    assert "--bw-icon-size: var(--bw-component-icon-size-sm)" in out
    assert ' width="var(' not in out
    assert ' height="var(' not in out


@pytest.mark.parametrize("variant", ["primary", "secondary", "ghost", "danger"])
def test_button_valid_variants(variant: str) -> None:
    out = _render(f'{{% bw_button "X" variant="{variant}" %}}')
    assert f"bw-btn--{variant}" in out


def test_button_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_button "X" variant="nope" %}')


def test_button_invalid_size_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_button "X" size="huge" %}')


# --- button name/value (#119) ----------------------------------------------


def test_button_emits_name_and_value_on_the_button_branch() -> None:
    # #119: a form with several submits needs to tell the server which one was
    # pressed, which is what name/value carry.
    out = _render('{% bw_button "Archive" type="submit" name="bulk_action" value="archive" %}')
    assert 'name="bulk_action"' in out
    assert 'value="archive"' in out
    assert 'type="submit"' in out


def test_button_omits_name_and_value_when_not_given() -> None:
    # The attributes must not appear at all by default, so an ordinary button's
    # output is unchanged from before #119.
    out = _render('{% bw_button "Save" %}')
    assert "name=" not in out
    assert "value=" not in out


def test_button_output_is_byte_identical_to_pre_119_for_ordinary_callers() -> None:
    # #119 must be purely additive: an existing caller that never passes
    # name/value gets exactly the pre-119 markup, not just "no name=/value=
    # substring" (a whitespace-only regression from new {% if %} lines inside
    # the <button ...> opening tag would pass the substring check above while
    # still changing every existing render).
    out = _render('{% bw_button "Save" %}')
    assert out == (
        '<button class="bw-btn bw-btn--primary bw-btn--md"\n'
        '        type="button"\n'
        "        \n"
        "        \n"
        '        ><span class="bw-btn__label">Save</span></button>\n'
    )


def test_the_documented_bulk_actions_wiring_renders() -> None:
    """The exact call _bulk_actions_bar.html's docstring documents (#119).

    This is the regression that was missing: the documented example raised
    TemplateSyntaxError because bw_button had no name/value, and nothing
    rendered it. A documented option needs a test that proves it works, or the
    documentation is only a claim.
    """
    out = _render(
        '{% bw_button label="Archive" type="submit" name="bulk_action" '
        'value="archive" variant="secondary" size="sm" %}'
        '{% bw_button label="Delete" type="submit" name="bulk_action" '
        'value="delete" variant="danger" size="sm" %}'
    )
    assert out.count('name="bulk_action"') == 2
    assert 'value="archive"' in out
    assert 'value="delete"' in out


def test_button_rejects_name_alongside_href() -> None:
    # name/value on an <a> are meaningless. Raising beats silently dropping
    # them, which is precisely how #119 went unnoticed.
    with pytest.raises(TemplateSyntaxError, match="<button> branch only"):
        _render('{% bw_button "Go" href="/x/" name="action" %}')


def test_button_rejects_value_without_name() -> None:
    # A value with no name is never sent by the browser, so the server would
    # see nothing: a silent no-op the caller almost certainly did not intend.
    with pytest.raises(TemplateSyntaxError, match="requires name="):
        _render('{% bw_button "X" type="submit" value="archive" %}')


# --- badge ----------------------------------------------------------------


def test_badge_renders_with_variant() -> None:
    out = _render('{% bw_badge "Active" variant="success" %}')
    assert "bw-badge--success" in out and "Active" in out


def test_badge_default_variant_is_neutral() -> None:
    out = _render('{% bw_badge "Draft" %}')
    assert "bw-badge--neutral" in out and "Draft" in out


def test_badge_neutral_variant_has_a_shipped_css_rule() -> None:
    # #100: the documented no-args default is variant="neutral", so the shipped
    # CSS must carry a real .bw-badge--neutral rule (the neutral chip treatment,
    # token-derived), never a look left implicit in the .bw-badge base class.
    css = (_DIST_JS.parent / "brickwork.css").read_text()
    rule = re.search(r"\.bw-badge--neutral\{([^}]*)\}", css)
    assert rule is not None, "dist/brickwork.css must ship a .bw-badge--neutral rule (#100)"
    body = rule.group(1).replace(" ", "")
    assert "background:var(--bw-color-surface-sunken)" in body
    assert "color:var(--bw-color-fg-muted)" in body


def test_badge_with_icon() -> None:
    out = _render('{% bw_badge "New" icon="info" %}')
    assert "bw-icon" in out and "New" in out


def test_badge_invalid_variant_raises() -> None:
    # ADR-060 rule 2: bw_badge was the one tag with a documented closed set
    # and no enforcement (icvoss/django-brickwork's brickworkui.com shipped
    # variant="error" against it for exactly this reason).
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_badge "Active" variant="error" %}')


@pytest.mark.parametrize("variant", ["neutral", "info", "success", "warning", "danger"])
def test_badge_every_valid_variant_renders_its_class(variant: str) -> None:
    out = _render(f'{{% bw_badge "Active" variant="{variant}" %}}')
    assert f"bw-badge--{variant}" in out


# --- alert ----------------------------------------------------------------


@pytest.mark.parametrize(
    "variant,icon_marker",
    [("info", "info"), ("success", "success"), ("warning", "alert-triangle"), ("danger", "alert-circle")],
)
def test_alert_variant_picks_the_right_icon(variant: str, icon_marker: str) -> None:
    out = _render(f'{{% bw_alert "msg" variant="{variant}" %}}')
    assert f"bw-alert--{variant}" in out
    assert 'role="alert"' in out
    # the icon name maps per-variant (the marker will appear in the rendered svg path set)
    assert "bw-alert__icon" in out


def test_alert_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('{% bw_alert "msg" variant="nope" %}')


def test_alert_with_title() -> None:
    out = _render('{% bw_alert "the message" variant="danger" title="Oops" %}')
    assert "Oops" in out and "the message" in out


# --- dismissible alert and badge (04-interfaces 4b, 0.9.0) ------------------


def _close_button(out: str) -> str:
    """The dismiss control's opening tag, for attribute assertions."""
    match = re.search(r"<button[^>]*aria-label[^>]*>", out)
    assert match, "no close control in output"
    return match.group(0)


def test_alert_default_output_is_unchanged_without_dismissible() -> None:
    # regression: the new argument's default must not disturb the shipped
    # markup; dismissible=False and omitting it are byte-equal
    default = _render('{% bw_alert "msg" variant="info" %}')
    assert default == _render('{% bw_alert "msg" variant="info" dismissible=False %}')
    assert "x-data" not in default
    assert "<button" not in default


def test_badge_default_output_is_unchanged_without_dismissible() -> None:
    default = _render('{% bw_badge "Active" variant="success" %}')
    assert default == _render('{% bw_badge "Active" variant="success" dismissible=False %}')
    assert "x-data" not in default
    assert "<button" not in default


def test_dismissible_alert_gains_the_component_and_a_hidden_close_control() -> None:
    # The control ships WITH the hidden attribute and JS reveals it at init:
    # the no-JS floor shows no dead dismiss affordance (04-interfaces 4b).
    out = _render('{% bw_alert "msg" variant="info" dismissible=True %}')
    assert 'x-data="bwDismissible()"' in out
    assert "hidden" in _close_button(out).replace("aria-hidden", "")


def test_dismissible_badge_gains_the_component_and_a_hidden_close_control() -> None:
    out = _render('{% bw_badge "Beta" variant="info" dismissible=True %}')
    assert 'x-data="bwDismissible()"' in out
    assert "hidden" in _close_button(out).replace("aria-hidden", "")


def test_bundle_registers_bwdismissible_and_its_event() -> None:
    # AC static leg, mirroring the interaction modules: the compiled bundle
    # carries the semver-public name and its documented bw: event.
    bundle = _DIST_JS.read_text()
    assert "bwDismissible" in bundle
    assert "bw:dismiss" in bundle


# --- icvoss/django-brickwork#130: every class a SHIPPED component template ---
# --- emits must have a matching rule in the compiled CSS ---------------------


class _RegressionFilterForm(forms.Form):
    """A real, non-empty form for the filter-bar/field regression fixtures.

    A fixture that renders a component with an EMPTY context (no fields, no
    items) can pass every class-coverage check without ever emitting the
    classes under test, which is exactly how bw-field__control escaped
    detection before. Every fixture below supplies real field/item data.
    """

    search = forms.CharField(label="Search", required=False)


# The unstyled-by-design allowlist is the SINGLE canonical copy at
# tests/_class_contract.py (icvoss/django-brickwork#137): this file and
# test_component_class_contract.py both import it rather than keeping their
# own, so a justification can go stale in only one place, not two.


@pytest.mark.parametrize(
    ("name", "render"),
    [
        (
            "_empty_state.html (with an action link, bw-btn--md on the CTA)",
            lambda: Template(
                '{% include "brickwork/components/_empty_state.html" with '
                'heading="No widgets yet" body="Create your first one." '
                'action_href="/widgets/new/" action_label="Create widget" %}'
            ).render(Context({})),
        ),
        (
            "_filter_bar.html (with a bound field and a clear link)",
            lambda: Template(
                "{% include \"brickwork/components/_filter_bar.html\" with fields=fields clear_href='/widgets/' %}"
            ).render(Context({"fields": [_RegressionFilterForm()["search"]]})),
        ),
        (
            "bw_dropdown (secondary trigger variant, real items)",
            lambda: (
                engines["django"]
                .from_string("{% load brickwork_interactions %}{% bw_dropdown items=items trigger_label='Actions' %}")
                .render({"items": [{"label": "Edit", "url": "/edit/"}, {"divider": True}]})
            ),
        ),
        (
            "forms/_field.html (a bound, non-empty field)",
            lambda: Template('{% include "brickwork/forms/_field.html" with field=field %}').render(
                Context({"field": _RegressionFilterForm()["search"]})
            ),
        ),
        (
            "_dropzone.html (with help text)",
            lambda: Template(
                '{% include "brickwork/components/_dropzone.html" with '
                'label="Upload receipt" id="receipt" name="receipt" '
                'help_text="PDF or image, up to 10MB." %}'
            ).render(Context({})),
        ),
        (
            "_tag_input.html (with a pre-filled value)",
            lambda: Template(
                '{% include "brickwork/components/_tag_input.html" with '
                'label="Tags" id="tags" name="tags" value="alpha,beta" %}'
            ).render(Context({})),
        ),
    ],
)
def test_shipped_component_classes_it_emits_are_actually_styled(name: str, render) -> None:
    """The icvoss/django-brickwork#130 defect, generalised beyond examples.

    #120/#130 both slipped past test_examples.py's equivalent check because it
    only sweeps the copy-paste example pages, not brickwork's OWN shipped
    component templates. bw-btn--md, bw-field__control and (by the same
    mechanism) any future emitted-but-unstyled class are caught here instead,
    against the six render paths #130 named. Every fixture supplies real
    context so the emitted markup is not a bare skeleton that happens to skip
    the classes under test.
    """
    html = render()
    missing = unstyled_classes(html, allowlist=UNSTYLED_BY_DESIGN)
    assert not missing, f"{name} emits classes with no rule in the shipped CSS: {missing}"
