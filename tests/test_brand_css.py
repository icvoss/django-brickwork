"""``render_brand_css`` emitter tests (brickwork#40).

Values in, valid ``:root`` / ``[data-theme="dark"]`` override CSS out, validated
against the shipped token manifest (brickwork#39) rather than a hand-kept second
list of names. The contrast maths (OKLab -> linear sRGB -> WCAG relative
luminance) is exercised directly in these cases; black/white round-trips to
21.0 (verified separately), so the pass/fail boundary here pins the fg-on-accent
constraint at 4.5:1 with real oklch literals rather than the trivial extremes.
"""

from __future__ import annotations

import warnings

import pytest

from brickwork.services.brand_css import BrandValidationError, render_brand_css

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
    # The recipe's derivation guarantee: the per-role override carries only the
    # authored load-bearing values, never flat copies of the derived family, so
    # -accent-hover / -accent-subtle / -focus-ring keep deriving live from the
    # per-request accent (see also the dist-side guard in
    # test_token_derivations.py).
    light, dark = _ROLE_BRANDS["club"]
    css = render_brand_css(light, dark)
    assert "--bw-color-accent-hover" not in css
    assert "--bw-color-accent-subtle" not in css
    assert "--bw-color-focus-ring" not in css


def test_non_oklch_value_warns_instead_of_raising() -> None:
    # a value that is not a plain oklch literal cannot be contrast-checked; this
    # must warn (the check cannot run), never raise (an unrelated CSS syntax
    # like a var() reference is legitimate brand input).
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        css = render_brand_css({"color-accent": "var(--some-other-token)", "color-fg-on-accent": _WHITE})
    assert any("cannot check" in str(w.message) for w in caught)
    assert "--bw-color-accent: var(--some-other-token);" in css
