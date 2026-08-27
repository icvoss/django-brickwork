"""``render_brand_css``: brand override values in, valid :root/[data-theme] CSS out.

brickwork#40. A consuming platform (the motivating case is Magmify's per-tenant
theme builder, and vendably_v3's agency white-label, brickwork#49) stores brand
values as data and must render them as ``--bw-*`` token overrides at request time,
multi-tenant, with no per-tenant build. Every consumer doing this otherwise
hand-writes CSS generation against brickwork's token names and invents its own
validation, drifting against the semver-governed contract.

This service is that contract expressed as an API: values in, valid override CSS
out, validated against the shipped manifest (brickwork#39) rather than a
hand-kept second list. Pairs with ``docs/BRANDING.md``'s dynamic-theming recipe.

Public surface (semver-stable): ``render_brand_css``, ``BrandValidationError``.
"""

from __future__ import annotations

import math
import re
import warnings

from brickwork.exceptions import BrickworkError
from brickwork.services.token_manifest import contrast_pairs, load_bearing, overridable_names

# A brand value must be an oklch literal (BR-BW-TOK-003: brickwork's colour
# contract is oklch) for a numeric contrast check. Tenant accent overrides and
# their relevant surfaces therefore require it; other non-critical colour
# overrides can use the accepted syntaxes below.
_OKLCH = re.compile(
    r"^oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)\s*(?:/\s*([\d.]+%?)\s*)?\)$",
    re.IGNORECASE,
)

# Every value reaching the stylesheet must match one of these. CSS has no escaping
# mechanism for values: a `}` inside one IS a block terminator, so a value cannot be
# made safe on the way out and has to be rejected at the door. Same reasoning as the
# brand slug in services/tokens.py and the attribute names in
# templatetags/brickwork_interactions.py; this is the third place it applies.
_HEX = r"\#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})"
_NUM = r"[-+]?(?:\d*\.\d+|\d+)%?"
_ANGLE = r"[-+]?(?:\d*\.\d+|\d+)(?:deg|grad|rad|turn)?"
_FN_ARGS = rf"(?:\s*{_NUM}\s*[,/]?\s*){{2,4}}"
_VALUE_PATTERNS = (
    _OKLCH.pattern,
    rf"^{_HEX}$",
    rf"^rgba?\(\s*{_FN_ARGS}\)$",
    rf"^hsla?\(\s*{_ANGLE}\s*[,\s]\s*{_NUM}\s*[,\s]\s*{_NUM}\s*(?:[,/]\s*{_NUM}\s*)?\)$",
    rf"^(?:oklab|lab)\(\s*{_FN_ARGS}\)$",
    rf"^(?:lch)\(\s*{_NUM}\s+{_NUM}\s+{_ANGLE}\s*(?:/\s*{_NUM}\s*)?\)$",
    # A custom-property reference, optionally with a fallback. Documented brand input:
    # docs/BRANDING.md:50 collapses a status hue with `var(--bw-color-accent)`. The
    # referenced name is bounded to a custom-property identifier and the fallback to
    # one nested level, so this stays a colour reference and cannot carry a payload.
    r"^var\(\s*--[a-z0-9-]+\s*(?:,\s*[^(){};<>@\\]*(?:var\(\s*--[a-z0-9-]+\s*\))?[^(){};<>@\\]*)?\)$",
    # A bare CSS identifier: named colours (rebeccapurple), CSS-wide keywords
    # (inherit, currentColor, transparent). Deliberately not an enumerated list of
    # the 148 named colours; the shape is what matters for safety.
    r"^[a-z][a-z0-9-]*$",
)
_VALUE = re.compile("|".join(f"(?:{p})" for p in _VALUE_PATTERNS), re.IGNORECASE)

# Belt and braces alongside the allowlist above: these can never appear in a valid
# colour value, so if a future syntax addition widens _VALUE too far, the hole does
# not silently reopen. `url(` is listed because it exfiltrates on render.
_FORBIDDEN = ("{", "}", ";", "<", ">", "@", "/*", "*/", "\\", "url(")

_FOCUS_RING = "--bw-color-focus-ring"
_ACCENT = "--bw-color-accent"
_FOCUS_SURFACE_NAMES = ("--bw-color-surface", "--bw-color-surface-raised", "--bw-color-surface-inverse")
_DEFAULT_FOCUS_SURFACES = {
    "light": {
        "--bw-color-surface": "oklch(1 0 0)",
        "--bw-color-surface-raised": "oklch(1 0 0)",
        "--bw-color-surface-inverse": "oklch(0.205 0.005 265)",
    },
    "dark": {
        "--bw-color-surface": "oklch(0.18 0.005 265)",
        "--bw-color-surface-raised": "oklch(0.237 0.005 265)",
        "--bw-color-surface-inverse": "oklch(0.93 0.002 265)",
    },
}

# brickwork#289: package-default oklch literals for every token a contrastPairs
# derivation can reference, so _resolve_derived() below can evaluate a derived
# pair's effective colour even when the caller overrode only ONE of its inputs
# (the exact gap the contrastPairs manifest section exists to close: a brand
# overriding only --bw-color-surface, with no explicit --bw-color-X-fg or
# --bw-color-X-subtle in its override dict). Kept alongside
# _DEFAULT_FOCUS_SURFACES rather than merged with it: this table is consulted
# by expression resolution, not the focus-ring derivation.
_DEFAULT_DERIVATION_INPUTS = {
    "light": {
        "--bw-color-surface": "oklch(1 0 0)",
        "--bw-color-fg": "oklch(0.205 0.005 265)",
        "--bw-color-danger": "oklch(0.577 0.215 27)",
        "--bw-color-warning": "oklch(0.666 0.163 58)",
        "--bw-color-success": "oklch(0.627 0.155 149)",
        "--bw-color-info": "oklch(0.600 0.110 225)",
    },
    "dark": {
        "--bw-color-surface": "oklch(0.18 0.005 265)",
        "--bw-color-fg": "oklch(0.93 0.002 265)",
        "--bw-color-danger": "oklch(0.637 0.208 25)",
        "--bw-color-warning": "oklch(0.769 0.166 70)",
        "--bw-color-success": "oklch(0.723 0.169 152)",
        "--bw-color-info": "oklch(0.720 0.110 220)",
    },
}

# The single-level color-mix grammar DESIGN.md section 3 restricts derived
# expressions to (mirrors tests/test_token_derivations.py's _MIX so the two
# never drift): color-mix(in oklab, var(--bw-color-X) N%, PARTNER), PARTNER
# one of black, white, transparent, or var(--bw-color-*).
_DERIVED_MIX = re.compile(
    r"^color-mix\(in oklab, var\((--bw-color-[a-z0-9-]+)\) (\d+(?:\.\d+)?)%, "
    r"(black|white|transparent|var\(--bw-color-[a-z0-9-]+\))\)$"
)


class BrandValidationError(BrickworkError):
    """A brand override failed validation (unknown token name, a value that is not a
    recognised CSS colour, or a hard contrast failure on an authored-per-theme
    constraint).

    The value check is unconditional: unlike the name and contrast checks it is not
    governed by ``render_brand_css(..., validate=False)``, because emitting an
    unvalidated value is a CSS-injection sink regardless of how much the caller
    trusts its data (brickwork#133)."""


def _check_value(name: str, value: str) -> None:
    """Reject any value that is not a recognised CSS colour literal.

    Raises ``BrandValidationError`` rather than warning. A warning here would be
    worse than useless: the caller has already been handed the malicious stylesheet
    by the time it fires.
    """
    v = value.strip()
    if not v:
        raise BrandValidationError(
            f"brickwork: empty value for {name!r}. Supply a CSS colour literal "
            f"(oklch() preferred, see docs/BRANDING.md)."
        )
    lowered = v.lower()
    for bad in _FORBIDDEN:
        if bad in lowered:
            raise BrandValidationError(
                f"brickwork: value for {name!r} contains {bad!r}, which cannot appear in a "
                f"CSS colour value. Brand values are interpolated into a stylesheet and CSS "
                f"has no escaping mechanism, so this is rejected rather than sanitised "
                f"(brickwork#133)."
            )
    if not _VALUE.match(v):
        raise BrandValidationError(
            f"brickwork: value {value!r} for {name!r} is not a recognised CSS colour. "
            f"Accepted: oklch() (preferred, and the only form the contrast check can "
            f"verify), oklab(), lab(), lch(), hex, rgb()/rgba(), hsl()/hsla(), or a bare "
            f"keyword such as 'transparent' (docs/BRANDING.md)."
        )


def _normalise_name(name: str) -> str:
    """Accept both ``--bw-color-accent`` and the short ``color-accent`` form.

    The manifest and the emitted CSS use the full ``--bw-*`` custom-property name;
    a consumer keying its data by the short role name is common, so we accept
    either and always emit the full form.
    """
    n = name.strip()
    if n.startswith("--"):
        return n
    if n.startswith("bw-"):
        return f"--{n}"
    return f"--bw-{n}"


def _parse_oklch(value: str) -> tuple[float, float, float] | None:
    """(L, C, H) with L in 0..1, or None if not a plain oklch literal."""
    m = _OKLCH.match(value.strip())
    if not m:
        return None
    lightness_raw, chroma, hue, _alpha = m.groups()
    lightness = float(lightness_raw[:-1]) / 100 if lightness_raw.endswith("%") else float(lightness_raw)
    return (lightness, float(chroma), float(hue))


def _oklch_to_linear_srgb(lightness: float, chroma: float, hue_deg: float) -> tuple[float, float, float]:
    """OKLCH -> linear sRGB (per the OKLab spec, Ottosson 2020). Not clamped."""
    hue = math.radians(hue_deg)
    a = chroma * math.cos(hue)
    b = chroma * math.sin(hue)
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_**3, m_**3, s_**3
    r = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    bch = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3
    return (r, g, bch)


def _relative_luminance(value: str) -> float | None:
    """WCAG 2.x relative luminance of an oklch literal, or None if unparseable."""
    parsed = _parse_oklch(value)
    if parsed is None:
        return None
    r, g, b = _oklch_to_linear_srgb(*parsed)
    # WCAG relative luminance is defined on linear-light sRGB, which is exactly
    # what the OKLab->linear-sRGB step produces; clamp out-of-gamut to [0, 1].
    r, g, b = (min(max(c, 0.0), 1.0) for c in (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float | None:
    """WCAG contrast ratio between two oklch colours, or None if either is unparseable."""
    la, lb = _relative_luminance(a), _relative_luminance(b)
    if la is None or lb is None:
        return None
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _resolve_token(name: str, values: dict[str, str], theme_label: str) -> str | None:
    """The effective oklch literal for ``name``: the caller's override if given,
    else the package default for that theme. Returns None for a name this table
    does not know (the contrastPairs derivations only ever reference the status
    bases, --bw-color-surface, and --bw-color-fg, all covered)."""
    if name in values:
        return values[name]
    return _DEFAULT_DERIVATION_INPUTS.get(theme_label, {}).get(name)


def _resolve_derived(expression: str, values: dict[str, str], theme_label: str) -> str | None:
    """Evaluate a single-level ``color-mix(in oklab, var(--bw-color-X) N%, PARTNER)``
    derived expression (DESIGN.md section 3 grammar) to a concrete ``oklch()``
    literal, resolving each input against ``values`` (a brand's overrides) with a
    package-default fallback. Returns None if the expression is not a recognised
    var() or color-mix() reference, or if resolving an input fails (unparseable
    override, or a reference outside the known input table).

    This is what lets brickwork#289's contrastPairs check catch a brand that
    overrides only --bw-color-surface (or only a status base): neither
    --bw-color-X-fg nor --bw-color-X-subtle needs to be an explicit override for
    their EFFECTIVE colours, under that one override, to be computed and checked.
    Mirrors the Cartesian oklab mix in tests/test_token_derivations.py's
    _evaluate(): color-mix(in oklab, ...) interpolates the rectangular (L, a, b)
    triple, so an achromatic partner (black, white, transparent, or a token whose
    own chroma is 0) passes the source hue through with no special-casing.
    """
    var_match = re.match(r"^var\((--bw-color-[a-z0-9-]+)\)$", expression)
    if var_match:
        return _resolve_token(var_match.group(1), values, theme_label)
    mix_match = _DERIVED_MIX.match(expression)
    if not mix_match:
        return None
    base_name, percent, partner = mix_match.groups()
    base_value = _resolve_token(base_name, values, theme_label)
    if base_value is None:
        return None
    base = _parse_oklch(base_value)
    if base is None:
        return None
    p = float(percent) / 100.0
    l1, c1, h1 = base
    a1, b1 = c1 * math.cos(math.radians(h1)), c1 * math.sin(math.radians(h1))
    if partner == "transparent":
        # The status contrastPairs never mix toward transparent; guarded rather
        # than silently mis-evaluated if that ever changes.
        return None
    if partner == "black":
        l2, a2, b2 = 0.0, 0.0, 0.0
    elif partner == "white":
        l2, a2, b2 = 1.0, 0.0, 0.0
    else:
        partner_name = partner[len("var(") : -1]
        partner_value = _resolve_token(partner_name, values, theme_label)
        if partner_value is None:
            return None
        partner_parsed = _parse_oklch(partner_value)
        if partner_parsed is None:
            return None
        l2, c2, h2 = partner_parsed
        a2, b2 = c2 * math.cos(math.radians(h2)), c2 * math.sin(math.radians(h2))
    lightness = p * l1 + (1 - p) * l2
    a_mix = p * a1 + (1 - p) * a2
    b_mix = p * b1 + (1 - p) * b2
    chroma = math.hypot(a_mix, b_mix)
    hue = math.degrees(math.atan2(b_mix, a_mix)) % 360.0 if chroma > 0.0 else h1
    return f"oklch({lightness:.6f} {chroma:.6f} {hue:.4f})"


def _focus_surfaces(values: dict[str, str], theme_label: str) -> tuple[str, str, str]:
    """Resolve the three surfaces a focus outline can meet in one theme."""
    defaults = _DEFAULT_FOCUS_SURFACES[theme_label]
    surface = values.get("--bw-color-surface", defaults["--bw-color-surface"])
    raised = values.get(
        "--bw-color-surface-raised",
        surface if "--bw-color-surface" in values else defaults["--bw-color-surface-raised"],
    )
    inverse = values.get(
        "--bw-color-surface-inverse", values.get("--bw-color-fg", defaults["--bw-color-surface-inverse"])
    )
    return (surface, raised, inverse)


def _derive_focus_ring(accent: str, surfaces: tuple[str, str, str], theme_label: str) -> str:
    """Keep accent hue/chroma while selecting a ring lightness that clears 3:1."""
    parsed_accent = _parse_oklch(accent)
    if parsed_accent is None:
        # Unreachable through render_brand_css(): _validate() requires accent to be
        # concrete oklch before this function is ever called. Guarded rather than
        # asserted so a future internal caller that skips that check fails with the
        # same BrandValidationError a caller already expects, not a bare crash.
        raise BrandValidationError(
            f"brickwork: {accent!r} is not a concrete oklch() value, so no focus ring "
            f"can be derived from it (brickwork#145)."
        )
    _, chroma, hue = parsed_accent
    candidates: list[tuple[float, str]] = []
    for step in range(1, 1000):
        candidate = f"oklch({step / 1000:.3f} {chroma:g} {hue:g})"
        ratios = [_contrast_ratio(candidate, surface) for surface in surfaces]
        # Every surface reaching this function is either an authored oklch override
        # (validated as concrete oklch by _validate() before _derive_focus_ring is
        # called) or a hardcoded literal from _DEFAULT_FOCUS_SURFACES, and `candidate`
        # is always a well-formed oklch literal built two lines up, so a None ratio
        # cannot occur through the public render_brand_css() API today. It is checked
        # anyway, and raises the same BrandValidationError the ratio<3 branch below
        # raises, rather than assert (stripped under `python -O`, which would let a
        # None ratio reach `min()` as an unhandled TypeError instead of this guard,
        # brickwork#207) or a silent skip (which would understate the true minimum
        # ratio and could pass an accent that does not actually clear 3:1).
        known_ratios = [ratio for ratio in ratios if ratio is not None]
        if len(known_ratios) != len(ratios):
            raise BrandValidationError(
                f"brickwork: could not verify focus-ring contrast for {accent!r} against every "
                f"{theme_label} surface; a surface value was not a concrete oklch() literal "
                f"(brickwork#145)."
            )
        candidates.append((min(known_ratios), candidate))
    ratio, ring = max(candidates, key=lambda candidate: candidate[0])
    if ratio < 3:
        raise BrandValidationError(
            f"brickwork: {accent!r} cannot produce a focus ring with 3:1 contrast against every "
            f"{theme_label} surface. Choose a less extreme accent (brickwork#145)."
        )
    return ring


def _validate(values: dict[str, str], theme_label: str) -> None:
    """Reject unknown token names; hard-fail a contrast constraint that is
    definitively violated by two parseable oklch values. A tenant accent and
    every supplied focus-relevant surface must be concrete oklch so its focus
    ring can be verified; a collapsed status hue remains a warning."""
    vocabulary = overridable_names()
    for name in values:
        norm = _normalise_name(name)
        if norm not in vocabulary:
            raise BrandValidationError(
                f"unknown brickwork token {name!r} (normalised {norm!r}); "
                f"it is not in the overridable vocabulary (see the token manifest, brickwork#39)."
            )

    normed = {_normalise_name(k): v for k, v in values.items()}

    if _FOCUS_RING in normed:
        raise BrandValidationError(
            "brickwork: --bw-color-focus-ring is derived and validated from --bw-color-accent; "
            "do not override it directly (brickwork#145)."
        )
    if _ACCENT in normed:
        focus_inputs = (_ACCENT, *_FOCUS_SURFACE_NAMES, "--bw-color-fg")
        for name in focus_inputs:
            if name not in normed:
                continue
            if _parse_oklch(normed[name]) is None:
                raise BrandValidationError(
                    f"brickwork: {name} must be a concrete oklch() value when --bw-color-accent is "
                    f"overridden, so the {theme_label} focus ring can be verified (brickwork#145)."
                )

    # Contrast constraints declared in the manifest (fg-on-accent at 4.5:1).
    for entry in load_bearing():
        pair = entry.get("contrastPair")
        if not pair or entry["name"] not in normed or pair not in normed:
            continue
        ratio = _contrast_ratio(normed[entry["name"]], normed[pair])
        minimum = entry.get("minContrast", 4.5)
        if ratio is None:
            warnings.warn(
                f"brickwork: cannot check {entry['name']} contrast in the {theme_label} block "
                f"(values are not plain oklch literals); verify it meets {minimum}:1 yourself.",
                stacklevel=3,
            )
        elif ratio < minimum:
            raise BrandValidationError(
                f"brickwork: {entry['name']} fails contrast against {pair} in the {theme_label} block "
                f"({ratio:.2f}:1 < {minimum}:1). The safe text colour flips per theme; do not assume "
                f"white (docs/BRANDING.md, brickwork#35)."
            )

    # Derived-pair contrast constraints (brickwork#289): --bw-color-X-fg against
    # --bw-color-X-subtle. Unlike the loadBearing loop above, NEITHER side needs
    # to be an explicit override for this to fire: both are resolved through
    # _resolve_derived(), which falls back to the package default for any input
    # the caller did not override. This is what catches the reported defect
    # (overriding --bw-color-surface alone, with neither -fg nor -subtle named)
    # rather than only the case where a caller has typed a bad literal for both.
    for pair_entry in contrast_pairs():
        derived_expr = pair_entry.get("derived")
        pair_derived_expr = pair_entry.get("pairDerived")
        if not derived_expr or not pair_derived_expr:
            continue
        fg_value = _resolve_derived(derived_expr, normed, theme_label)
        pair_value = _resolve_derived(pair_derived_expr, normed, theme_label)
        if fg_value is None or pair_value is None:
            # An override supplied a non-oklch literal for one of the inputs
            # (hex, var(), a named colour): the pair genuinely cannot be
            # resolved from here, so warn rather than silently skip.
            warnings.warn(
                f"brickwork: cannot resolve {pair_entry['name']} contrast against "
                f"{pair_entry['contrastPair']} in the {theme_label} block (an input override is not "
                f"a plain oklch() literal); verify it meets {pair_entry.get('minContrast', 4.5)}:1 "
                f"yourself.",
                stacklevel=3,
            )
            continue
        ratio = _contrast_ratio(fg_value, pair_value)
        minimum = pair_entry.get("minContrast", 4.5)
        if ratio is not None and ratio < minimum:
            raise BrandValidationError(
                f"brickwork: {pair_entry['name']} would fail contrast against "
                f"{pair_entry['contrastPair']} in the {theme_label} block ({ratio:.2f}:1 < "
                f"{minimum}:1) under this override. Both are derived from --bw-color-surface (and "
                f"the status hue itself); overriding surface alone can still break this pairing "
                f"for an extreme enough value (brickwork#289)."
            )

    # Status hues collapsed onto accent: a warning, not an error (a brand may
    # legitimately have no distinct status hue, but destructive/positive actions
    # then read as the accent, which is usually a mistake, docs/BRANDING.md).
    accent = normed.get("--bw-color-accent")
    if accent is not None:
        for status in ("--bw-color-danger", "--bw-color-success", "--bw-color-warning"):
            if normed.get(status) == accent:
                warnings.warn(
                    f"brickwork: {status} is set to the same value as --bw-color-accent in the "
                    f"{theme_label} block; destructive/positive actions will not read distinctly "
                    f"(docs/BRANDING.md).",
                    stacklevel=3,
                )


def _block(selector: str, values: dict[str, str]) -> str:
    # The value check lives here, not in _validate(), because _block runs on every
    # emission path including validate=False. Checking in _validate alone would leave
    # the injection open on exactly the path a consumer picks when it believes its
    # data is trusted (brickwork#133).
    for k, v in values.items():
        _check_value(_normalise_name(k), v)
    lines = "\n".join(f"  {_normalise_name(k)}: {v.strip()};" for k, v in values.items())
    return f"{selector} {{\n{lines}\n}}"


def render_brand_css(
    light: dict[str, str],
    dark: dict[str, str] | None = None,
    *,
    validate: bool = True,
) -> str:
    """Render brand override values as a ``:root`` / ``[data-theme="dark"]`` block.

    ``light`` (and optional ``dark``) map token names to CSS values. Names may be
    given in the full ``--bw-color-accent`` form or the short ``color-accent``
    form; the output always uses the full custom-property name. The light block
    targets ``:root`` (the base theme); the dark block targets
    ``[data-theme="dark"]``, matching the documented override shape (docs/BRANDING.md).

    When ``validate`` is True (the default):

    - **unknown token names** raise ``BrandValidationError`` (checked against the
      shipped overridable vocabulary, brickwork#39, so a typo or a token semver
      moved is a loud failure, not a silent no-op);
    - a **contrast constraint** declared in the manifest (fg-on-accent at 4.5:1)
      is enforced when both its token and its pair are supplied as oklch literals,
      raising on a definitive failure (the fg-on-accent trap flips per theme,
      docs/BRANDING.md / brickwork#35);
    - an overridden **accent** must be concrete oklch, as must any supplied
      contrast-relevant surface. The service derives and emits an explicit
      focus-ring token with at least 3:1 contrast against surface, raised
      surface, and inverse surface. Direct focus-ring overrides are rejected;
    - a **status hue collapsed onto the accent** emits a warning (not an error).

    Independently of ``validate``, **every value is checked against the accepted CSS
    colour syntaxes** and a non-conforming one raises ``BrandValidationError``. This
    check cannot be switched off: values are interpolated into a stylesheet, CSS has
    no escaping mechanism for them, and a value containing ``}`` would otherwise close
    brickwork's block and take over the rest of the sheet (brickwork#133).

    Set ``validate=False`` to skip the name and contrast checks (e.g. when the values
    are known good and the call is hot); the value check still runs. Returns the CSS
    as a string; the caller decides where it lives (a per-request ``<style>`` in the
    shell head, a cached file, etc.).
    """
    light_values = dict(light)
    dark_values = dict(dark) if dark else None
    if validate:
        _validate(light_values, "light")
        if dark_values:
            _validate(dark_values, "dark")
        for values, theme_label in ((light_values, "light"), (dark_values, "dark")):
            if values and _ACCENT in {_normalise_name(name) for name in values}:
                normalised = {_normalise_name(name): value for name, value in values.items()}
                values[_FOCUS_RING] = _derive_focus_ring(
                    normalised[_ACCENT], _focus_surfaces(normalised, theme_label), theme_label
                )

    parts = [_block(":root", light_values)]
    if dark_values:
        parts.append(_block('[data-theme="dark"]', dark_values))
    return "\n\n".join(parts) + "\n"
