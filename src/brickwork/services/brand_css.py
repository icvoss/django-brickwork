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
from brickwork.services.token_manifest import load_bearing, overridable_names

# A brand value must be an oklch literal (BR-BW-TOK-003: brickwork's colour
# contract is oklch) for the contrast check to run; the other accepted colour
# syntaxes below are emitted but skip the numeric check with a warning.
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


def _validate(values: dict[str, str], theme_label: str) -> None:
    """Reject unknown token names; hard-fail a contrast constraint that is
    definitively violated by two parseable oklch values. Warn (never raise) when
    a value is not a plain oklch literal (the check cannot run) or when a status
    hue is collapsed onto the accent."""
    vocabulary = overridable_names()
    for name in values:
        norm = _normalise_name(name)
        if norm not in vocabulary:
            raise BrandValidationError(
                f"unknown brickwork token {name!r} (normalised {norm!r}); "
                f"it is not in the overridable vocabulary (see the token manifest, brickwork#39)."
            )

    normed = {_normalise_name(k): v for k, v in values.items()}

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
    if validate:
        _validate(light, "light")
        if dark:
            _validate(dark, "dark")

    parts = [_block(":root", light)]
    if dark:
        parts.append(_block('[data-theme="dark"]', dark))
    return "\n\n".join(parts) + "\n"
