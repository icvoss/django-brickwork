"""``render_brand_css`` emitter tests (brickwork#40).

Values in, valid ``:root`` / ``[data-theme="dark"]`` override CSS out, validated
against the shipped token manifest (brickwork#39) rather than a hand-kept second
list of names. The contrast maths (OKLab -> linear sRGB -> WCAG relative
luminance) is exercised directly in these cases; black/white round-trips to
21.0 (verified separately), so the pass/fail boundary here pins the fg-on-accent
constraint at 4.5:1 with real oklch literals rather than the trivial extremes.
"""

from __future__ import annotations

import re
import warnings

import pytest

from brickwork.services.brand_css import BrandValidationError, _contrast_ratio, _derive_focus_ring, render_brand_css

# A light, low-contrast accent: fails fg-on-accent against white (~1.57:1, well
# under the 4.5:1 minimum). This is the "assumed white always works" trap
# docs/BRANDING.md warns about (brickwork#35).
_LOW_CONTRAST_ACCENT = "oklch(0.86 0.06 350)"
_WHITE = "oklch(1 0 0)"
_DARK_INK = "oklch(0.145 0.004 265)"
# A dark, saturated accent: passes fg-on-accent against white (~8.98:1).
_AUBERGINE_ACCENT = "oklch(0.42 0.11 330)"


def test_renders_a_root_block_and_a_dark_theme_block() -> None:
    css = render_brand_css(
        {"color-accent": _AUBERGINE_ACCENT, "color-fg-on-accent": _WHITE},
        {"color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _DARK_INK},
    )
    assert ":root {" in css
    assert '[data-theme="dark"] {' in css
    assert "--bw-color-accent: oklch(0.42 0.11 330);" in css
    assert '[data-theme="dark"]' in css.split(":root {")[1]


def test_light_only_call_emits_no_dark_block() -> None:
    css = render_brand_css({"color-accent": _AUBERGINE_ACCENT, "color-fg-on-accent": _WHITE})
    assert ":root {" in css
    assert '[data-theme="dark"]' not in css


def test_accepts_both_short_and_full_bw_key_forms() -> None:
    css = render_brand_css(
        {"color-accent": _AUBERGINE_ACCENT, "--bw-color-fg-on-accent": _WHITE},
        validate=False,
    )
    assert "--bw-color-accent: oklch(0.42 0.11 330);" in css
    assert "--bw-color-fg-on-accent: oklch(1 0 0);" in css


def test_unknown_token_name_raises_brand_validation_error() -> None:
    with pytest.raises(BrandValidationError, match="unknown brickwork token"):
        render_brand_css({"color-not-a-real-token": _AUBERGINE_ACCENT})


def test_unknown_token_name_in_dark_block_raises() -> None:
    with pytest.raises(BrandValidationError, match="unknown brickwork token"):
        render_brand_css(
            {"color-accent": _AUBERGINE_ACCENT},
            {"color-not-a-real-token": _AUBERGINE_ACCENT},
        )


def test_definitive_fg_on_accent_contrast_failure_raises() -> None:
    # ~1.57:1, well under the 4.5:1 minimum: a definitive, loud failure.
    with pytest.raises(BrandValidationError, match="fails contrast"):
        render_brand_css({"color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _WHITE})


def test_correct_light_pairing_passes() -> None:
    # aubergine accent + white fg: ~8.98:1, comfortably above 4.5:1.
    css = render_brand_css({"color-accent": _AUBERGINE_ACCENT, "color-fg-on-accent": _WHITE})
    assert "--bw-color-accent:" in css


def test_accent_override_emits_a_verified_focus_ring() -> None:
    css = render_brand_css({"color-accent": _AUBERGINE_ACCENT, "color-fg-on-accent": _WHITE})
    match = re.search(r"--bw-color-focus-ring: (oklch\([^;]+\));", css)
    assert match is not None
    for surface in ("oklch(1 0 0)", "oklch(0.205 0.005 265)"):
        assert _contrast_ratio(match.group(1), surface) >= 3


def test_focus_ring_is_verified_against_each_supplied_surface() -> None:
    surfaces = {
        "color-surface": "oklch(0.98 0.003 265)",
        "color-surface-raised": "oklch(0.84 0.01 265)",
        "color-surface-inverse": "oklch(0.21 0.01 265)",
    }
    css = render_brand_css({"color-accent": _AUBERGINE_ACCENT, **surfaces})
    match = re.search(r"--bw-color-focus-ring: (oklch\([^;]+\));", css)
    assert match is not None
    for surface in surfaces.values():
        assert _contrast_ratio(match.group(1), surface) >= 3


def test_dark_focus_ring_is_verified_against_dark_theme_surfaces() -> None:
    css = render_brand_css(
        {"color-accent": _AUBERGINE_ACCENT, "color-fg-on-accent": _WHITE},
        {"color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _DARK_INK},
    )
    dark_css = css.split('[data-theme="dark"]', maxsplit=1)[1]
    match = re.search(r"--bw-color-focus-ring: (oklch\([^;]+\));", dark_css)
    assert match is not None
    for surface in ("oklch(0.18 0.005 265)", "oklch(0.237 0.005 265)", "oklch(0.93 0.002 265)"):
        assert _contrast_ratio(match.group(1), surface) >= 3


@pytest.mark.parametrize(
    "name,value",
    [
        ("color-accent", "#5c2a63"),
        ("color-surface", "#ffffff"),
        ("color-surface-raised", "var(--brand-surface)"),
        ("color-surface-inverse", "rgb(20, 20, 20)"),
        ("color-fg", "rebeccapurple"),
    ],
)
def test_focus_relevant_override_requires_oklch_when_accent_is_set(name: str, value: str) -> None:
    values = {"color-accent": _AUBERGINE_ACCENT, name: value}
    with pytest.raises(BrandValidationError, match="focus ring can be verified"):
        render_brand_css(values)


def test_direct_focus_ring_override_is_rejected() -> None:
    with pytest.raises(BrandValidationError, match="do not override it directly"):
        render_brand_css({"color-focus-ring": _AUBERGINE_ACCENT})


def test_correct_dark_pairing_passes() -> None:
    # the same low-contrast-against-white accent paired with dark ink instead:
    # ~12.6:1. This is the "the safe text colour flips per theme" case
    # docs/BRANDING.md documents: the SAME accent value that fails against
    # white passes against a dark fg-on-accent.
    css = render_brand_css({"color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _DARK_INK})
    assert "--bw-color-accent:" in css


def test_status_hue_equal_to_accent_warns_not_raises() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        css = render_brand_css({"color-accent": _AUBERGINE_ACCENT, "color-danger": _AUBERGINE_ACCENT})
    assert any("same value as --bw-color-accent" in str(w.message) for w in caught)
    assert "--bw-color-danger:" in css


def test_validate_false_skips_all_checks() -> None:
    # an unknown name and a failing contrast pair would both raise under
    # validate=True; validate=False must emit them unchecked.
    css = render_brand_css(
        {"color-not-a-real-token": "anything", "color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _WHITE},
        validate=False,
    )
    assert "--bw-color-not-a-real-token: anything;" in css
    assert "--bw-color-accent: oklch(0.86 0.06 350);" in css


# --- the per-role accent shape (#76, BRANDING.md recipe 3) -----------------
#
# N accents selected by a request attribute, one emitter call per role: each
# role carries its own light and dark accent with its own verified
# fg-on-accent (the #35 trap applied per accent). Two roles are enough to pin
# the shape: per-role blocks emit independently, validation runs per role, and
# the emitted overrides touch only load-bearing names so the shipped
# color-mix() derivations keep recolouring the accent family downstream.

_ROLE_BRANDS: dict[str, tuple[dict[str, str], dict[str, str]]] = {
    "club": (
        {"color-accent": _AUBERGINE_ACCENT, "color-fg-on-accent": _WHITE},
        {"color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _DARK_INK},
    ),
    "coach": (
        {"color-accent": "oklch(0.45 0.15 150)", "color-fg-on-accent": _WHITE},
        {"color-accent": "oklch(0.8 0.1 150)", "color-fg-on-accent": _DARK_INK},
    ),
}


@pytest.mark.parametrize("role", sorted(_ROLE_BRANDS))
def test_each_role_accent_emits_its_own_light_and_dark_blocks(role: str) -> None:
    light, dark = _ROLE_BRANDS[role]
    css = render_brand_css(light, dark)
    assert ":root {" in css
    assert '[data-theme="dark"] {' in css
    assert f"--bw-color-accent: {light['color-accent']};" in css
    assert f"--bw-color-accent: {dark['color-accent']};" in css.split('[data-theme="dark"]')[1]


def test_a_role_with_a_bad_fg_on_accent_pairing_fails_independently() -> None:
    # Per-accent validation: one role's wrong pairing (white on a light accent)
    # raises for THAT role's emitter call; the other roles are unaffected.
    with pytest.raises(BrandValidationError, match="fails contrast"):
        render_brand_css({"color-accent": _LOW_CONTRAST_ACCENT, "color-fg-on-accent": _WHITE})
    for role in _ROLE_BRANDS:
        light, dark = _ROLE_BRANDS[role]
        assert render_brand_css(light, dark)


def test_role_overrides_set_only_load_bearing_names_so_the_family_derives() -> None:
    # The recipe's derivation guarantee: per-role overrides carry only authored
    # load-bearing values, so the accent-hover and accent-subtle families keep
    # deriving live. Focus-ring is the deliberate exception: #145 emits an
    # explicit verified value after calculating its contrast.
    light, dark = _ROLE_BRANDS["club"]
    css = render_brand_css(light, dark)
    assert "--bw-color-accent-hover" not in css
    assert "--bw-color-accent-subtle" not in css
    assert "--bw-color-focus-ring: oklch(" in css


def test_non_oklch_accent_is_rejected_when_focus_contrast_cannot_be_verified() -> None:
    with pytest.raises(BrandValidationError, match="focus ring can be verified"):
        render_brand_css({"color-accent": "var(--some-other-token)", "color-fg-on-accent": _WHITE})


def test_unparseable_focus_surface_raises_brand_validation_error_not_type_error() -> None:
    # brickwork#207: _derive_focus_ring used to narrow a None contrast ratio with a
    # bare `assert`, which `python -O` strips, so a None ratio would reach `min()`
    # and raise an unhandled TypeError instead of the intended BrandValidationError.
    # render_brand_css() cannot reach this branch itself: _validate() already
    # requires every focus-relevant surface to be concrete oklch before
    # _derive_focus_ring is called (test_focus_relevant_override_requires_oklch_when_accent_is_set
    # above pins that at the public-API level). This calls the private helper
    # directly to exercise the narrowing itself, and pins the EXCEPTION TYPE, which
    # is exactly what silently changed under -O.
    with pytest.raises(BrandValidationError, match="could not verify focus-ring contrast"):
        _derive_focus_ring(
            _AUBERGINE_ACCENT,
            ("not-a-parseable-colour", _WHITE, _DARK_INK),
            "light",
        )


# --- value validation (brickwork#133) -------------------------------------
# CSS has no escaping mechanism for values: a `}` inside one IS a block
# terminator, so a hostile value cannot be made safe on the way out and must be
# rejected at the door. These assert the door is shut.


@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("brace breakout", "red } :root{--bw-color-accent:blue} body{background:red} .x{"),
        ("url exfiltration", "url(https://evil.example/x)"),
        ("comment injection", "red /* } */"),
        ("declaration chaining", "red; background: blue"),
        ("style-element breakout", "red</style><script>alert(1)</script>"),
        ("backslash escape", "red\\7d "),
        ("at-rule injection", "red } @import url(https://evil.example/x); .x{"),
        ("empty value", ""),
        ("whitespace-only value", "   "),
    ],
)
def test_hostile_value_is_rejected(label: str, value: str) -> None:
    with pytest.raises(BrandValidationError):
        render_brand_css(light={"color-accent": value})


def test_hostile_value_is_rejected_even_when_validate_is_false() -> None:
    # The value check lives in _block(), not _validate(), precisely so that the
    # path a consumer picks when it believes its data is trusted is not the one
    # path that emits an injection.
    with pytest.raises(BrandValidationError):
        render_brand_css(light={"color-accent": "red } body{background:red} .x{"}, validate=False)


@pytest.mark.parametrize(
    "value",
    [
        "oklch(0.65 0.2 250)",
        "oklch(0.65 0.2 250 / 0.5)",
        "#fff",
        "#ffffff",
        "#ffffffcc",
        "rgb(255, 0, 0)",
        "rgba(255, 0, 0, 0.5)",
        "hsl(210, 50%, 40%)",
        "hsl(210 50% 40% / 0.8)",
        "oklab(0.5 0.1 -0.1)",
        "lch(50% 40 220)",
        "transparent",
        "currentColor",
        "rebeccapurple",
        "inherit",
        "var(--bw-color-accent)",
        "var(--brand-accent, #ffffff)",
    ],
)
def test_legitimate_colour_value_is_accepted(value: str) -> None:
    css = render_brand_css(light={"color-accent": value}, validate=False)
    assert f"--bw-color-accent: {value};" in css
