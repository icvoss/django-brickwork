"""Shipped templates stay clean under string_if_invalid (brickwork#80).

Django's ``|default`` filter only substitutes for a defined-but-falsy value: a
genuinely undefined variable is replaced by the engine's ``string_if_invalid``
BEFORE the filter runs, so ``{{ layout|default:'sidebar' }}`` leaked
``INVALID_VARIABLE: layout`` into the shell of any consumer running the
recommended dev aid (observed adopting 1.1.0). Every optional-by-design
variable in the shipped templates now resolves via ``{% firstof %}`` (which
resolves with failures ignored and is immune), so these render each surface
with ONLY its required context, under a marker-bearing engine, and assert the
marker never appears while the documented defaults still do.

The consumer smoke leg (settings_consumer.py) additionally runs its whole
harness under ``string_if_invalid``, guarding the composed pages end to end.
"""

from __future__ import annotations

import pytest
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.test import override_settings

MARKER_PREFIX = "INVALID_VARIABLE"

_TEMPLATES_WITH_MARKER = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
            ],
            "string_if_invalid": f"{MARKER_PREFIX}: %s",
        },
    }
]

marker_engine = override_settings(TEMPLATES=_TEMPLATES_WITH_MARKER)


# --- the shells, empty context (the #80 repro) ------------------------------


@pytest.mark.parametrize(
    "template",
    ["brickwork/shell/app.html", "brickwork/shell/auth.html", "brickwork/shell/centred.html"],
)
@marker_engine
def test_shell_renders_no_invalid_marker_with_an_empty_context(template: str) -> None:
    html = render_to_string(template, {})
    assert MARKER_PREFIX not in html


@marker_engine
def test_app_shell_data_layout_still_defaults_to_sidebar() -> None:
    # The exact leak the issue names: data-layout="INVALID_VARIABLE: layout".
    html = render_to_string("brickwork/shell/app.html", {})
    assert 'data-layout="sidebar"' in html


@marker_engine
def test_app_shell_honours_an_explicit_layout_under_the_marker_engine() -> None:
    html = render_to_string("brickwork/shell/app.html", {"layout": "topbar"})
    assert 'data-layout="topbar"' in html


@marker_engine
def test_shell_html_axis_attributes_still_default() -> None:
    html = render_to_string("brickwork/shell/app.html", {})
    assert 'lang="en"' in html
    assert 'dir="ltr"' in html
    assert 'data-theme="light"' in html
    assert 'data-density="comfortable"' in html


@marker_engine
def test_shell_toast_region_still_defaults_to_top_end() -> None:
    # The include passes position through a {% firstof %} hoist; an undefined
    # bw_toast_position must yield the documented default, never the marker.
    html = render_to_string("brickwork/shell/app.html", {})
    assert "bw-toast-region--top-end" in html


# --- component includes, required context only ------------------------------

# (template, minimal required context, expected default fragment)
_COMPONENT_CASES = [
    ("brickwork/components/_toast_region.html", {}, "bw-toast-region--top-end"),
    (
        "brickwork/components/_empty_state.html",
        {"heading": "Nothing here", "body": "Add one."},
        "bw-empty-state--no_data",
    ),
    (
        "brickwork/components/_stepper.html",
        {"steps": [{"label": "One", "status": "current"}]},
        "bw-stepper--horizontal",
    ),
    (
        "brickwork/components/_disclosure.html",
        {"label": "More", "content": "Body"},
        "bw-disclosure--divided",
    ),
    ("brickwork/components/_modal.html", {"title": "Confirm"}, "bw-modal--md"),
    ("brickwork/components/_slide_over.html", {"title": "Details"}, "bw-slide-over--md"),
    ("brickwork/components/_account_menu.html", {"items": []}, "bw-account-menu--end"),
    ("brickwork/components/_filter_bar.html", {"fields": []}, 'action=""'),
    (
        "brickwork/components/_data_table.html",
        {"columns": [], "rows": []},
        'id="bw-data-table"',
    ),
    ("brickwork_marketing/components/_hero.html", {"heading": "Hello"}, "bw-hero--start"),
    (
        "brickwork_marketing/components/_feature_grid.html",
        {"items": [{"heading": "A", "body": "B"}]},
        "bw-feature-grid--3",
    ),
]


@pytest.mark.parametrize(("template", "context", "expected"), _COMPONENT_CASES)
@marker_engine
def test_component_renders_no_invalid_marker_with_required_context_only(
    template: str, context: dict, expected: str
) -> None:
    if template.startswith("brickwork_marketing/"):
        # The marketing sub-app is absent from the consumer leg
        # (settings_consumer.py), where its templates are not discoverable.
        from django.apps import apps

        if not apps.is_installed("brickwork.marketing"):
            pytest.skip("brickwork.marketing is not installed in this settings leg")
    html = render_to_string(template, context)
    assert MARKER_PREFIX not in html
    assert expected in html


# --- the field partial's readonly hoist -------------------------------------


@marker_engine
def test_field_partial_direct_include_does_not_go_readonly() -> None:
    # _field.html is documented for direct {% include ... with field=field %}
    # use; readonly is then genuinely undefined, and pre-#80 the marker string
    # (truthy) reached bw_field_widget and silently rendered the field readonly.
    from django import forms
    from django.template import Context, Template

    class _ProbeForm(forms.Form):
        name = forms.CharField()

    field = _ProbeForm()["name"]
    html = Template('{% include "brickwork/forms/_field.html" with field=field %}').render(Context({"field": field}))
    assert MARKER_PREFIX not in html
    assert "readonly" not in html


@marker_engine
def test_field_partial_still_honours_an_explicit_readonly() -> None:
    from django import forms
    from django.template import Context, Template

    class _ProbeForm(forms.Form):
        name = forms.CharField()

    field = _ProbeForm()["name"]
    html = Template('{% include "brickwork/forms/_field.html" with field=field readonly=True %}').render(
        Context({"field": field})
    )
    assert 'readonly="readonly"' in html


# --- source-level guard against the whole bug class -------------------------


def test_no_shipped_template_defaults_a_possibly_undefined_variable() -> None:
    # {{ var|default:... }} on a context-level variable is exactly the bypass
    # #80 fixed; {% firstof %} (or an always-defined attribute, e.g. a
    # dataclass field like RenderedNavItem.href in nav/_nav.html) is the house
    # pattern. Scan every shipped template so the bypass cannot quietly return.
    import pathlib
    import re

    package_dir = pathlib.Path(__file__).resolve().parent.parent / "src" / "brickwork"
    # {{ name|default:... }} where name is a BARE variable (no attribute dot):
    # an attribute lookup on an always-present object resolves (possibly to
    # None) and |default then works as intended, so dotted uses are allowed.
    bypass = re.compile(r"{{\s*[a-zA-Z_][a-zA-Z0-9_]*\|default:")
    offenders: list[str] = []
    for path in package_dir.rglob("templates/**/*.html"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if bypass.search(line):
                offenders.append(f"{path.relative_to(package_dir)}:{lineno}")
    assert not offenders, (
        f"|default on a bare context variable is bypassed by string_if_invalid "
        f"(brickwork#80); use {{% firstof %}} instead. Offenders: {offenders}"
    )


def test_bw_data_attrs_treats_the_invalid_marker_as_absent_not_as_an_error() -> None:
    """An optional data mapping must not raise under string_if_invalid.

    ``data`` is optional on both the data-table row and the stat, so a consumer
    whose rows simply have no ``data`` key must render normally. Under
    ``string_if_invalid`` a missing ``row.data`` resolves to the marker STRING,
    not to None, so a guard that only special-cased None and "" raised a hard
    TemplateSyntaxError and 500'd the whole page. A str can never be a valid
    mapping, so it means "not supplied", never "supplied and wrong".
    """
    from brickwork.templatetags.brickwork_components import bw_data_attrs

    assert bw_data_attrs(f"{MARKER_PREFIX}: row.data") == ""
    assert bw_data_attrs(None) == ""
    assert bw_data_attrs("") == ""
    # A genuinely wrong type is still an error: this guard must not become a
    # blanket "ignore anything unexpected", which would silently swallow a
    # consumer passing a list of pairs and wondering why nothing rendered.
    with pytest.raises(TemplateSyntaxError):
        bw_data_attrs([("data-id", "1")])


def test_bw_data_attrs_still_renders_a_real_mapping() -> None:
    from brickwork.templatetags.brickwork_components import bw_data_attrs

    out = bw_data_attrs({"data-id": "42", "data-state": "open"})
    assert 'data-id="42"' in out
    assert 'data-state="open"' in out
