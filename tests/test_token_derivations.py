"""Derivation-layer contract tests (DESIGN.md section 3).

Every derived token carries a live CSS expression in $extensions.bw.derived and
keeps its resolved default as $value. These tests recompute each expression by
linear interpolation in oklch (the model color-mix() uses) and assert the result
stays within a small tolerance of the $value baseline, guarding both the tuned
percentage constants and future default-value edits. Hue IS asserted whenever
the computed chroma is perceptible (>= 0.02): an achromatic mix partner (black,
white, transparent, or a chroma-0 token) is hue-powerless per CSS Color 4, so
the resolved hue equals the source token's hue, and a $value baseline carrying
a ramp-step hue instead of the true resolved hue is dishonest (DESIGN.md
section 3).

A second guard asserts the shipped component CSS only references token names the
build actually emits, so a rename or a missed source addition cannot ship a
dangling var().
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SOURCE = _ROOT / "src" / "brickwork" / "tokens" / "source"
_DIST = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"
_FRONTEND = _ROOT / "frontend" / "src"

# Tolerances for the linear-oklch recomputation against the $value baseline.
_TOL_L = 0.015
_TOL_C = 0.02
_TOL_ALPHA = 0.01
# Hue honesty: asserted only when the computed chroma is perceptible; below the
# floor the hue is visually powerless and ramp-step baselines are harmless.
_TOL_H = 4.0
_HUE_CHROMA_FLOOR = 0.02

_OKLCH = re.compile(r"^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:/\s*([\d.]+)\s*)?\)$")
_ALIAS = re.compile(r"^\{([a-z0-9.-]+)\}$")
# The full derivation grammar (DESIGN.md section 3): a single color-mix over a
# --bw-color-* reference with an achromatic or token partner, or a plain alias.
_MIX = re.compile(
    r"^color-mix\(in oklch, var\((--bw-color-[a-z0-9-]+)\) (\d+(?:\.\d+)?)%, "
    r"(black|white|transparent|var\(--bw-color-[a-z0-9-]+\))\)$"
)
_VAR = re.compile(r"^var\((--bw-color-[a-z0-9-]+)\)$")


def _load(name: str) -> dict:
    return json.loads((_SOURCE / f"{name}.tokens.json").read_text())


def _parse_oklch(value: str) -> tuple[float, float, float, float]:
    m = _OKLCH.match(value)
    assert m, f"not an oklch literal: {value!r}"
    lightness, chroma, hue, alpha = m.groups()
    return (float(lightness), float(chroma), float(hue), float(alpha) if alpha else 1.0)


def _resolve_alias(value: str, primitives: dict) -> str:
    """Resolve a {primitive.*} alias to its oklch literal (aliases never chain)."""
    m = _ALIAS.match(value)
    if not m:
        return value
    node = primitives
    for part in m.group(1).split("."):
        node = node[part]
    return node["$value"]


class _Theme:
    """One theme file's tokens: baselines (resolved $value) plus derivations."""

    def __init__(self, name: str) -> None:
        primitives = _load("primitive")
        data = _load(f"semantic.{name}")
        self.name = name
        self.baseline: dict[str, str] = {}
        self.derived: dict[str, str] = {}
        for group_key, group in data.items():
            for token_key, token in group.items():
                if token_key.startswith("$"):
                    continue
                css_name = f"--bw-{group_key}-{token_key}"
                self.baseline[css_name] = _resolve_alias(token["$value"], primitives)
                derived = token.get("$extensions", {}).get("bw", {}).get("derived")
                if derived is not None:
                    self.derived[css_name] = derived

    def components(self, css_name: str) -> tuple[float, float, float, float]:
        return _parse_oklch(self.baseline[css_name])


def _themes() -> list[_Theme]:
    return [_Theme("light"), _Theme("dark")]


def _hue_distance(h1: float, h2: float) -> float:
    """Circular distance between two hue angles in degrees."""
    d = abs(h1 - h2) % 360.0
    return min(d, 360.0 - d)


def _evaluate(theme: _Theme, expression: str) -> tuple[float, float, float, float]:
    """Linear oklch interpolation of a derived expression: (L, C, H, alpha).

    Baseline $values (never other derived expressions) resolve the var()
    references, so each token's tolerance is checked independently rather than
    compounding down a chain. Hue follows CSS Color 4 interpolation: a
    chroma-0 side is hue-powerless (treated as missing), so black, white,
    transparent, and achromatic token partners pass the source hue through;
    two chromatic sides interpolate along the shorter arc.
    """
    var_match = _VAR.match(expression)
    if var_match:
        lightness, chroma, hue, alpha = theme.components(var_match.group(1))
        return (lightness, chroma, hue, alpha)
    mix_match = _MIX.match(expression)
    assert mix_match, (
        f"[{theme.name}] derived expression does not match the DESIGN.md section 3 grammar: {expression!r}"
    )
    base_name, percent, partner = mix_match.groups()
    p = float(percent) / 100.0
    l1, c1, h1, a1 = theme.components(base_name)
    if partner == "transparent":
        # Premultiplied-alpha interpolation: the transparent side contributes no
        # colour, so the components pass through and only alpha scales.
        return (l1, c1, h1, p * a1)
    if partner == "black":
        l2, c2, h2, a2 = 0.0, 0.0, None, 1.0
    elif partner == "white":
        l2, c2, h2, a2 = 1.0, 0.0, None, 1.0
    else:
        l2, c2, h2, a2 = theme.components(partner[len("var(") : -1])
        if c2 == 0.0:
            h2 = None  # achromatic token partner: hue powerless
    if h2 is None:
        hue = h1
    elif c1 == 0.0:
        hue = h2
    else:
        delta = ((h2 - h1 + 180.0) % 360.0) - 180.0
        hue = (h1 + (1 - p) * delta) % 360.0
    return (p * l1 + (1 - p) * l2, p * c1 + (1 - p) * c2, hue, p * a1 + (1 - p) * a2)


@pytest.mark.parametrize("theme", _themes(), ids=lambda t: t.name)
def test_every_derived_expression_reproduces_its_baseline(theme: _Theme) -> None:
    assert theme.derived, f"expected derived tokens in semantic.{theme.name}"
    for css_name, expression in theme.derived.items():
        lightness, chroma, hue, alpha = _evaluate(theme, expression)
        base_l, base_c, base_h, base_a = theme.components(css_name)
        assert abs(lightness - base_l) <= _TOL_L, (
            f"[{theme.name}] {css_name}: derived L {lightness:.4f} vs baseline "
            f"{base_l:.4f} (tolerance {_TOL_L}); expression {expression!r}"
        )
        assert abs(chroma - base_c) <= _TOL_C, (
            f"[{theme.name}] {css_name}: derived C {chroma:.4f} vs baseline "
            f"{base_c:.4f} (tolerance {_TOL_C}); expression {expression!r}"
        )
        assert abs(alpha - base_a) <= _TOL_ALPHA, (
            f"[{theme.name}] {css_name}: derived alpha {alpha:.4f} vs baseline "
            f"{base_a:.4f} (tolerance {_TOL_ALPHA}); expression {expression!r}"
        )
        if chroma >= _HUE_CHROMA_FLOOR:
            assert _hue_distance(hue, base_h) <= _TOL_H, (
                f"[{theme.name}] {css_name}: derived hue {hue:.1f} vs baseline "
                f"{base_h:.1f} (tolerance {_TOL_H} degrees at chroma >= "
                f"{_HUE_CHROMA_FLOOR}); the $value baseline must carry the true "
                f"resolved hue; expression {expression!r}"
            )


def test_derived_expressions_contain_no_dtcg_braces() -> None:
    # Style Dictionary treats {a.b} inside a value as a reference; a brace in a
    # derived expression would be resolved (or crash) instead of passing through.
    for theme in _themes():
        for css_name, expression in theme.derived.items():
            assert "{" not in expression and "}" not in expression, (
                f"[{theme.name}] {css_name}: derived expression contains a brace "
                f"Style Dictionary would treat as a reference: {expression!r}"
            )


def test_frontend_css_only_references_emitted_token_names() -> None:
    """Every fallback-less var(--bw-*) in the component CSS must be emitted.

    References WITH a fallback, e.g. var(--bw-icon-size, var(--bw-icon-size-md)),
    are per-instance hooks set inline by templates and are exempt; their nested
    fallback references are still collected and checked.
    """
    emitted = set(re.findall(r"^\s*(--bw-[a-z0-9-]+):", (_DIST / "tokens.css").read_text(), re.M))
    assert emitted, "no custom properties found in dist/tokens.css"
    missing: dict[str, set[str]] = {}
    for css_path in sorted(_FRONTEND.glob("*.css")):
        for name, terminator in re.findall(r"var\((--bw-[a-z0-9-]+)\s*([,)])", css_path.read_text()):
            if terminator == ")" and name not in emitted:
                missing.setdefault(css_path.name, set()).add(name)
    assert not missing, f"frontend CSS references token names tokens.css does not emit: {missing}"
