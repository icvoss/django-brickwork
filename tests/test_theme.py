"""Theme-resolver + form-helper unit tests (four axes, 422 helper, BRD-009)."""

from __future__ import annotations

from brickwork.services.forms import is_htmx_validation_request
from brickwork.services.tokens import resolve_theme_attributes


class _Req:
    def __init__(self, headers=None, htmx=None):
        self.headers = headers or {}
        if htmx is not None:
            self.htmx = htmx


# --- theme resolution ------------------------------------------------------


def test_defaults_come_from_settings() -> None:
    attrs = resolve_theme_attributes(_Req())
    assert attrs["theme"] == "light"
    assert attrs["density"] == "comfortable"
    assert attrs["dir"] == "ltr"


def test_resolver_overrides_only_the_keys_it_sets() -> None:
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"theme": "dark"})
    assert attrs["theme"] == "dark"
    assert attrs["density"] == "comfortable"  # untouched
    assert attrs["dir"] == "ltr"


def test_resolver_can_return_rtl_and_dark_and_compact() -> None:
    attrs = resolve_theme_attributes(
        _Req(), theme_resolver=lambda _r: {"theme": "dark", "density": "compact", "dir": "rtl"}
    )
    assert (attrs["theme"], attrs["density"], attrs["dir"]) == ("dark", "compact", "rtl")


def test_resolver_may_carry_a_logo_url() -> None:  # BRD-009
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: {"logo": "/brand/acme.svg"})
    assert attrs["logo"] == "/brand/acme.svg"


def test_resolver_returning_none_is_safe() -> None:
    attrs = resolve_theme_attributes(_Req(), theme_resolver=lambda _r: None)
    assert attrs["theme"] == "light"


# --- 422 helper: header vs duck-typed request.htmx -------------------------


def test_htmx_detected_via_header() -> None:
    assert is_htmx_validation_request(_Req(headers={"HX-Request": "true"}))


def test_htmx_detected_via_duck_typed_attribute() -> None:
    assert is_htmx_validation_request(_Req(htmx=True))


def test_non_htmx_request_is_false() -> None:
    assert not is_htmx_validation_request(_Req())
    assert not is_htmx_validation_request(_Req(htmx=False))
