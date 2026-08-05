"""Tests for brickwork.context_processors.theme (#22).

The shell reads bw_theme / bw_density / bw_dir / bw_lang; the theme service
returns theme / density / dir with no language. This processor is the wiring that
maps one to the other, so a consumer that adds it gets a styled shell with no
hand mapping (the bug was a silent unstyled shell from the name mismatch).
"""

from __future__ import annotations

from django.test import RequestFactory, override_settings

from brickwork.context_processors import theme


def _request():
    return RequestFactory().get("/")


def test_maps_service_output_onto_bw_prefixed_names() -> None:
    ctx = theme(_request())
    # the exact names the shell's <html> tag reads
    assert ctx["bw_theme"] == "light"
    assert ctx["bw_density"] == "comfortable"
    assert ctx["bw_dir"] == "ltr"


def test_supplies_bw_lang_which_the_service_never_returns() -> None:
    ctx = theme(_request())
    assert "bw_lang" in ctx
    assert ctx["bw_lang"]  # non-empty (active language or "en")


@override_settings(
    BRICKWORK_DEFAULT_THEME="dark",
    BRICKWORK_DEFAULT_DENSITY="compact",
    BRICKWORK_DEFAULT_DIR="rtl",
)
def test_honours_the_brickwork_default_settings() -> None:
    ctx = theme(_request())
    assert ctx["bw_theme"] == "dark"
    assert ctx["bw_density"] == "compact"
    assert ctx["bw_dir"] == "rtl"


def _resolver(request):
    return {"theme": "dark", "logo": "/brand/logo.svg"}


@override_settings(BRICKWORK_THEME_RESOLVER="tests.test_context_processors._resolver")
def test_theme_resolver_setting_is_applied() -> None:
    ctx = theme(_request())
    assert ctx["bw_theme"] == "dark"  # overridden by the resolver
    assert ctx["bw_density"] == "comfortable"  # untouched, from defaults
    assert ctx["bw_logo"] == "/brand/logo.svg"  # a resolver logo is surfaced


def test_no_logo_key_when_resolver_supplies_none() -> None:
    # default (no resolver): no logo, and the key is absent (not a None value)
    ctx = theme(_request())
    assert "bw_logo" not in ctx


def test_bw_debug_follows_settings_debug() -> None:
    # brickwork#87: bw_debug gates the shell's dev-only registration detector;
    # it must track settings.DEBUG so production pages ship no detector script.
    assert theme(_request())["bw_debug"] is False  # test settings run DEBUG=False
    with override_settings(DEBUG=True):
        assert theme(_request())["bw_debug"] is True


# --- the resolver may key on ANY request state (#76) -----------------------
#
# BRANDING.md recipe 3: the resolver contract explicitly permits deriving the
# result from arbitrary per-request state (a session-derived active role being
# the named case), not only a tenant or host. These tests make that guarantee
# executable: a resolver reading request.active_role (the attribute an app's
# own middleware sets from a session key) drives the brand axis, and the value
# flips between requests within one "session" as the role switches.


def _role_resolver(request):
    role = getattr(request, "active_role", None)
    if role is None:
        return {}
    return {"brand": role}


@override_settings(BRICKWORK_THEME_RESOLVER="tests.test_context_processors._role_resolver")
def test_resolver_may_key_on_session_derived_request_state() -> None:
    request = _request()
    request.active_role = "coach"  # what an ActiveRoleMiddleware sets from the session
    ctx = theme(request)
    assert ctx["bw_brand"] == "coach"


@override_settings(BRICKWORK_THEME_RESOLVER="tests.test_context_processors._role_resolver")
def test_brand_follows_a_mid_session_role_switch_per_request() -> None:
    first = _request()
    first.active_role = "player"
    second = _request()
    second.active_role = "club"
    assert theme(first)["bw_brand"] == "player"
    assert theme(second)["bw_brand"] == "club"


@override_settings(BRICKWORK_THEME_RESOLVER="tests.test_context_processors._role_resolver")
def test_no_active_role_falls_back_to_defaults_with_no_brand_key() -> None:
    ctx = theme(_request())  # no active_role on the request
    assert "bw_brand" not in ctx
    assert ctx["bw_theme"] == "light"
