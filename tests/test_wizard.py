"""Render tests for patterns/wizard.html (04-interfaces section 4b, 0.14.0,
brickwork#59).

AC-BW-076-shaped: the pattern renders a complete page when a consumer
extends it with only the required context (title, steps), and renders every
documented region in order when every block is filled. The named blocks are
the semver-public contract (BR-BW-TPL-001), so these tests drive the pattern
the way a consumer does: {% extends %} plus block overrides. The pattern
itself extends shell/app.html, so every shell block/region stays available.
"""

from __future__ import annotations

from django.template import Context, Template
from django.template.loader import render_to_string

_STEPS = [
    {"label": "Account", "status": "complete"},
    {"label": "Business details", "status": "current"},
    {"label": "Review", "status": "upcoming"},
]


def _render(**ctx: object) -> str:
    ctx.setdefault("title", "Set up your store")
    ctx.setdefault("steps", _STEPS)
    return render_to_string("brickwork/patterns/wizard.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    ctx.setdefault("title", "Set up your store")
    ctx.setdefault("steps", _STEPS)
    source = "{% extends 'brickwork/patterns/wizard.html' %}" + blocks
    return Template(source).render(Context(ctx))


def _assert_complete_document(html: str) -> None:
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert 'id="bw-main"' in html


def test_wizard_with_only_title_and_steps_renders_a_complete_working_page() -> None:
    html = _render()
    _assert_complete_document(html)
    assert "Set up your store" in html  # page_header default wired from title
    assert "bw-stepper" in html  # stepper default wired from steps
    assert "bw-wizard__step" in html


def test_wizard_renders_through_the_app_shell() -> None:
    html = _render()
    assert "bw-app" in html and "bw-sidebar" in html and "bw-workspace" in html


def test_wizard_stepper_default_wires_the_steps_context() -> None:
    html = _render()
    for step in _STEPS:
        assert step["label"] in html
    assert 'aria-current="step"' in html


def test_wizard_stepper_orientation_flows_through() -> None:
    html = _render(stepper_orientation="vertical")
    assert "bw-stepper--vertical" in html


def test_wizard_nav_renders_nothing_when_back_url_absent() -> None:
    html = _render()
    assert "bw-wizard__nav" not in html


def test_wizard_nav_renders_back_link_when_back_url_present() -> None:
    html = _render(back_url="/signup/step-1/")
    assert 'href="/signup/step-1/"' in html
    assert "Back" in html
    assert "bw-wizard__nav" in html


def test_wizard_step_block_fills_the_step_content() -> None:
    html = _extend(
        "{% block wizard_step %}<form><label>Business name"
        '<input name="business_name"></label><button type="submit">Continue</button></form>{% endblock %}'
    )
    assert '<div class="bw-wizard__step">' in html
    assert "Business name" in html
    assert 'name="business_name"' in html


def test_wizard_stepper_block_can_be_overridden_to_hide_the_indicator() -> None:
    html = _extend("{% block wizard_stepper %}{% endblock %}")
    assert "bw-stepper" not in html


def test_wizard_description_flows_into_the_page_header() -> None:
    html = _render(description="A quick five-step setup.")
    assert "A quick five-step setup." in html


def test_wizard_every_region_filled_renders_in_documented_order() -> None:
    html = _extend(
        "{% block wizard_step %}<p>Step body.</p>{% endblock %}",
        back_url="/signup/step-1/",
    )
    assert html.index("bw-stepper") < html.index("bw-wizard__step") < html.index("bw-wizard__nav")
