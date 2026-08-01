"""Brand-hook unit tests (0.10.0, 03-services amendment; AC-BW-096).

``ThemeAttributes`` gains ``brand`` (default ``""`` = nothing emitted). A
theme_resolver result that carries a brand wins (including an explicit ``""``
to suppress the default); otherwise ``BRICKWORK_DEFAULT_BRAND`` applies. A
non-empty brand must be an attribute-safe slug (``[A-Za-z][A-Za-z0-9_-]*``),
enforced at resolve time (the tabs id-safety precedent), and renders as
``data-bw-brand`` on the shell root <html>, NEVER on body or a link tag (the
derived color-mix tokens compute at :root). With brand unset the rendered
shell must be byte-identical to 0.9.0 output.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.test import override_settings

from brickwork.context_processors import theme
from brickwork.services.tokens import resolve_theme_attributes

SHELLS = ["brickwork/shell/app.html", "brickwork/shell/auth.html", "brickwork/shell/centred.html"]

# The exact <html> opening tag base.html emitted at 0.9.0 for a default render
# (no context). AC-BW-096: with brand unset the shell output is byte-identical
# to 0.9.0, so this literal must never change shape; the brand attribute may
# only ever ADD to it (asserted below), never alter it.
_UNBRANDED_HTML_TAG = '<html lang="en"\n      dir="ltr"\n      data-theme="light"\n      data-density="comfortable">'


class _Req:
    def __init__(self, headers=None):
        self.headers = headers or {}


def _html_tag(html: str) -> str:
    """The <html ...> opening tag of a rendered document."""
    start = html.index("<html")
    return html[start : html.index(">", start) + 1]


def _request():
    from django.test import RequestFactory

    return RequestFactory().get("/")


# --- service: default and setting fallback ---------------------------------


def test_brand_defaults_to_empty_string() -> None:
    attrs = resolve_theme_attributes(_Req())
    assert attrs["brand"] == ""


@override_settings(BRICKWORK_DEFAULT_BRAND="aubergine")
def test_setting_supplies_the_default_brand() -> None:
    attrs = resolve_theme_attributes(_Req())
    assert attrs["brand"] == "aubergine"


# --- service: resolver-vs-setting merge semantics ---------------------------


@override_settings(BRICKWORK_DEFAULT_BRAND="aubergine")
def test_resolver_brand_wins_over_the_setting() -> None:
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"brand": "plum"})
    assert attrs["brand"] == "plum"


@override_settings(BRICKWORK_DEFAULT_BRAND="aubergine")
def test_resolver_empty_brand_suppresses_the_setting_default() -> None:
    # an explicit "" from the resolver is a carried brand ("render nothing"),
    # not an omission, so it must win over the setting
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"brand": ""})
    assert attrs["brand"] == ""


@override_settings(BRICKWORK_DEFAULT_BRAND="aubergine")
def test_resolver_omitting_brand_falls_through_to_the_setting() -> None:
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"theme": "dark"})
    assert attrs["brand"] == "aubergine"


# --- service: slug validation (raises at resolve time) ----------------------


@pytest.mark.parametrize("slug", ["1bad", "a b", "-lead", "acme!", 'x"y'])
def test_invalid_setting_brand_raises_at_resolve_time(slug: str) -> None:
    with override_settings(BRICKWORK_DEFAULT_BRAND=slug), pytest.raises(ImproperlyConfigured, match="attribute-safe"):
        resolve_theme_attributes(_Req())


@pytest.mark.parametrize("slug", ["1bad", "a b"])
def test_invalid_resolver_brand_raises_at_resolve_time(slug: str) -> None:
    with pytest.raises(ImproperlyConfigured, match="attribute-safe"):
        resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"brand": slug})


@pytest.mark.parametrize("slug", ["A", "acme", "acme-2", "Acme_Corp", "a-b_c1"])
def test_valid_slugs_resolve_cleanly(slug: str) -> None:
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"brand": slug})
    assert attrs["brand"] == slug


# --- context processor: bw_brand surfacing ----------------------------------


def test_processor_omits_bw_brand_when_unbranded() -> None:
    # absent key, not an empty value: {% if bw_brand %} must see nothing, so
    # the unbranded shell stays byte-identical to 0.9.0
    assert "bw_brand" not in theme(_request())


@override_settings(BRICKWORK_DEFAULT_BRAND="aubergine")
def test_processor_surfaces_the_setting_brand() -> None:
    assert theme(_request())["bw_brand"] == "aubergine"


def _brand_resolver(request):
    return {"brand": "plum"}


@override_settings(
    BRICKWORK_DEFAULT_BRAND="aubergine",
    BRICKWORK_THEME_RESOLVER="tests.test_brand_hook._brand_resolver",
)
def test_processor_applies_the_resolver_brand_over_the_setting() -> None:
    assert theme(_request())["bw_brand"] == "plum"


@override_settings(BRICKWORK_DEFAULT_BRAND="1bad")
def test_processor_raises_on_an_invalid_setting_brand() -> None:
    with pytest.raises(ImproperlyConfigured, match="attribute-safe"):
        theme(_request())


# --- shell render: byte-identity without brand (AC-BW-096) -------------------


@pytest.mark.parametrize("template", SHELLS)
def test_unbranded_shell_contains_no_brand_attribute_anywhere(template: str) -> None:
    html = render_to_string(template, {})
    assert "data-bw-brand" not in html, f"{template} emitted data-bw-brand with no brand set"


@pytest.mark.parametrize("template", SHELLS)
def test_unbranded_html_tag_is_byte_identical_to_0_9_0(template: str) -> None:
    html = render_to_string(template, {})
    assert _html_tag(html) == _UNBRANDED_HTML_TAG


# --- shell render: the attribute lands on <html>, nowhere else ---------------


@pytest.mark.parametrize("template", SHELLS)
def test_branded_shell_carries_the_attribute_on_the_html_tag(template: str) -> None:
    html = render_to_string(template, {"bw_brand": "aubergine"})
    # exactly once, and inside the <html ...> opening tag (never body/link:
    # the derived color-mix tokens compute at :root)
    assert html.count("data-bw-brand") == 1
    assert 'data-bw-brand="aubergine"' in _html_tag(html)


@pytest.mark.parametrize("template", SHELLS)
def test_branded_attribute_precedes_head_and_body(template: str) -> None:
    # the site-precedent assertion: the attribute is on the root element,
    # before any <head>/<body> content it must recolour
    html = render_to_string(template, {"bw_brand": "aubergine"})
    assert html.index("data-bw-brand") < html.index("<head")
    assert html.index("data-bw-brand") < html.index("<body")


@pytest.mark.parametrize("template", SHELLS)
def test_brand_only_adds_the_attribute_to_the_0_9_0_tag(template: str) -> None:
    # the branded tag is the 0.9.0 tag plus ONLY the new attribute: nothing
    # else about the root element may change when a brand is set
    html = render_to_string(template, {"bw_brand": "aubergine"})
    expected = _UNBRANDED_HTML_TAG[:-1] + '\n      data-bw-brand="aubergine">'
    assert _html_tag(html) == expected
