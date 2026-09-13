"""Beat Phase D journey contracts (icvoss/django-brickwork#544)."""

from __future__ import annotations

import re
from pathlib import Path

from django.template import Context

from brickwork import examples
from tests.test_examples import _EXAMPLE_CONTEXTS, _SECTION_CONTEXTS, _example_engine

_ROOT = Path(__file__).resolve().parent.parent
_README = _ROOT / "src" / "brickwork" / "examples" / "README.md"
_INTEGRATION = _ROOT / "docs" / "INTEGRATION.md"

_JOURNEYS = {
    "Form validate": "app/form.html",
    "Modal": "app/confirm-modal.html",
    "Toast": "app/toast.html",
    "List + filter": "app/list.html",
    "Marketing CTA": "sections/cta/centred-band.html",
}


def test_examples_readme_links_all_five_journeys() -> None:
    text = _README.read_text(encoding="utf-8")
    assert "Journey contracts (Beat Phase D)" in text
    for label, path in _JOURNEYS.items():
        assert label in text, f"README missing journey label {label!r}"
        assert f"`{path}`" in text, f"README missing journey path {path!r}"


def test_integration_links_all_five_journeys() -> None:
    text = _INTEGRATION.read_text(encoding="utf-8")
    assert "Journey contracts (Beat Phase D" in text
    for path in _JOURNEYS.values():
        assert path in text, f"INTEGRATION.md missing journey path {path!r}"


def test_form_journey_ships_shared_partial_and_htmx_attrs() -> None:
    source = examples.read_example("app/form.html")
    assert "{% partialdef form_region inline %}" in source
    assert 'hx-target="this"' in source
    assert 'hx-swap="outerHTML"' in source
    assert "hx-post=" in source


def test_form_journey_renders_invalid_state() -> None:
    html = _example_engine().get_template("app/form.html").render(Context(_EXAMPLE_CONTEXTS["app/form.html"]))
    assert 'aria-invalid="true"' in html
    assert "invoice-form" in html


def test_modal_journey_is_consumer_partial_for_modal_root() -> None:
    source = examples.read_example("app/confirm-modal.html")
    assert '{% extends "brickwork/components/_modal.html" %}' in source
    assert "#bw-modal-root" in source
    assert "bw:modal:close" in source
    assert "hx-target=\"#bw-modal-root\"" in source
    html = _example_engine().get_template("app/confirm-modal.html").render(
        Context(_SECTION_CONTEXTS["app/confirm-modal.html"])
    )
    assert 'id="confirm-reset"' in html
    assert "bw-modal" in html
    assert "x-trap" in html


def test_toast_journey_ships_oob_partialdef() -> None:
    source = examples.read_example("app/toast.html")
    assert "{% partialdef toast_oob %}" in source
    assert 'hx-swap-oob="afterbegin:#bw-toast-region"' in source
    assert "hx-post=" in source
    html = _example_engine().get_template("app/toast.html").render(Context(_EXAMPLE_CONTEXTS["app/toast.html"]))
    assert "toast-demo-form" in html
    # Non-inline partialdef must not appear on the GET page.
    assert "hx-swap-oob" not in html


def test_toast_oob_partial_renders_into_toast_region_contract() -> None:
    oob = (
        _example_engine()
        .get_template("app/toast.html#toast_oob")
        .render(Context({"message": "Invoice saved.", "intent": "success", "duration": "normal"}))
    )
    assert 'hx-swap-oob="afterbegin:#bw-toast-region"' in oob
    assert "Invoice saved." in oob


def test_list_journey_ships_clear_path_and_phone_stack() -> None:
    source = examples.read_example("app/list.html")
    assert 'responsive="stack"' in source
    assert 'clear_href="/invoices/"' in source
    assert 'empty_action_href="/invoices/"' in source
    assert 'empty_action_label="Clear filters"' in source
    html = _example_engine().get_template("app/list.html").render(Context(_EXAMPLE_CONTEXTS["app/list.html"]))
    assert "bw-data-table--stack" in html


def test_marketing_cta_journey_ships_dual_cta_and_brand_note() -> None:
    source = examples.read_example("sections/cta/centred-band.html")
    assert "primary_cta_label=" in source
    assert "secondary_cta_label=" in source
    assert "brand-pack" in source or "brand tokens" in source
    html = _example_engine().get_template("sections/cta/centred-band.html").render(
        Context(_SECTION_CONTEXTS["sections/cta/centred-band.html"])
    )
    assert "Start free trial" in html
    assert "Talk to us" in html


def test_journeys_do_not_invent_alpine_start() -> None:
    """Journey examples must not call Alpine.start(); that stays host-owned."""
    for path in _JOURNEYS.values():
        source = examples.read_example(path)
        # Mentions in prose/comments are fine; an actual call is not.
        assert "Alpine.start()" not in source.replace("`Alpine.start()`", "")
        assert not re.search(r"\bx-data\s*=\s*[\"'](?!bw)", source), (
            f"{path} authors a non-bw Alpine component; journeys stay on shipped bw* data"
        )
