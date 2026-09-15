"""Brickwork Theme profile levels (ADR-110 / docs/THEME.md).

Pure helpers: given a set of authored ``--bw-*`` names (and optional density
default), infer the evidenced depth ladder (L0 to L4) and check a claimed
level. Does not emit CSS; pair with ``render_brand_css`` for validated
overrides. Kit-owned families remain overridable in the cascade but do **not**
count toward theme depth (THEME.md "Kit-owned").
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Literal

ThemeLevel = Literal["L0", "L1", "L2", "L3", "L4"]

_LEVEL_ORDER: Final[tuple[ThemeLevel, ...]] = ("L0", "L1", "L2", "L3", "L4")

# --- Required / evidence sets (THEME.md) ------------------------------------

L1_REQUIRED: Final[frozenset[str]] = frozenset(
    {
        "--bw-color-surface",
        "--bw-color-fg",
        "--bw-color-border",
        "--bw-color-accent",
        "--bw-color-danger",
        "--bw-color-success",
        "--bw-color-warning",
        "--bw-color-fg-on-accent",
    }
)

L2_FONTS: Final[frozenset[str]] = frozenset(
    {
        "--bw-font-family-sans",
        "--bw-font-family-display",
        "--bw-font-family-mono",
    }
)

L3_RADIUS: Final[frozenset[str]] = frozenset(
    {
        "--bw-radius-sm",
        "--bw-radius-md",
        "--bw-radius-lg",
    }
)

L3_ELEVATION: Final[frozenset[str]] = frozenset(
    {
        "--bw-elevation-1",
        "--bw-elevation-2",
        "--bw-elevation-3",
    }
)

# Surface / border ladder beyond the L1 load-bearing seven (+ fg-on-accent).
L3_SURFACES: Final[frozenset[str]] = frozenset(
    {
        "--bw-color-surface-raised",
        "--bw-color-surface-sunken",
        "--bw-color-surface-overlay",
        "--bw-color-surface-marketing-tint",
        "--bw-color-border-strong",
    }
)

L4_SPACE: Final[str] = "--bw-space-1"

# Prefixes that evidence density authorship (THEME.md L4).
_DENSITY_PREFIX: Final[str] = "--bw-density-"

# Kit-owned: may appear in override CSS, but never evidence a theme level.
# Prefix match; keep in sync with docs/THEME.md "Kit-owned".
KIT_OWNED_PREFIXES: Final[tuple[str, ...]] = (
    "--bw-focus-ring-width",
    "--bw-focus-ring-offset",
    "--bw-focus-ring-style",
    "--bw-z-",
    "--bw-duration-",
    "--bw-ease-",
    "--bw-transition-",
    "--bw-breakpoint-",
    "--bw-size-touch-target-min",
    "--bw-opacity-",
    "--bw-component-",
)

_LEVEL_RANK: Final[dict[ThemeLevel, int]] = {level: i for i, level in enumerate(_LEVEL_ORDER)}


def normalise_token_name(name: str) -> str:
    """Accept ``--bw-color-accent`` or ``color-accent``; always return full form."""
    stripped = name.strip()
    if stripped.startswith("--bw-"):
        return stripped
    if stripped.startswith("bw-"):
        return f"--{stripped}"
    return f"--bw-{stripped}"


def normalise_token_names(names: Iterable[str]) -> frozenset[str]:
    return frozenset(normalise_token_name(n) for n in names)


def is_kit_owned_token(name: str) -> bool:
    """True when the token is kit-owned and must not evidence theme depth."""
    norm = normalise_token_name(name)
    return any(norm == prefix or norm.startswith(prefix) for prefix in KIT_OWNED_PREFIXES)


def kit_owned_present(names: Iterable[str]) -> frozenset[str]:
    """Subset of *names* that are kit-owned (informational; not a hard refuse)."""
    return frozenset(n for n in normalise_token_names(names) if is_kit_owned_token(n))


def recommended_tokens_for_level(level: ThemeLevel) -> frozenset[str]:
    """Minimum recommended authored names for a claimed level (THEME.md).

    L3 returns the union of material axes (surfaces + radius + elevation); a
    pack needs only one coherent axis. L4 adds ``--bw-space-1``; density may
    instead be a ``data-density`` default (see ``has_density_default``).
    """
    if level == "L0":
        return frozenset()
    if level == "L1":
        return L1_REQUIRED
    if level == "L2":
        return L1_REQUIRED | L2_FONTS
    if level == "L3":
        return L1_REQUIRED | L2_FONTS | L3_RADIUS | L3_ELEVATION | L3_SURFACES
    # L4
    return L1_REQUIRED | L2_FONTS | L3_RADIUS | L3_ELEVATION | L3_SURFACES | {L4_SPACE}


def _has_l1(authored: frozenset[str]) -> bool:
    return authored >= L1_REQUIRED


def _has_l2(authored: frozenset[str]) -> bool:
    return _has_l1(authored) and authored >= L2_FONTS


def _has_l3_material(authored: frozenset[str]) -> bool:
    if authored >= L3_RADIUS:
        return True
    if authored >= L3_ELEVATION:
        return True
    return bool(authored & L3_SURFACES)


def _has_l3(authored: frozenset[str]) -> bool:
    return _has_l2(authored) and _has_l3_material(authored)


def _has_density_tokens(authored: frozenset[str]) -> bool:
    return any(n.startswith(_DENSITY_PREFIX) for n in authored)


def _has_l4(authored: frozenset[str], *, has_density_default: bool) -> bool:
    if not _has_l3(authored):
        return False
    return L4_SPACE in authored or has_density_default or _has_density_tokens(authored)


def infer_theme_level(
    names: Iterable[str],
    *,
    has_density_default: bool = False,
) -> ThemeLevel:
    """Highest level evidenced by authored token names (kit-owned ignored)."""
    authored = frozenset(n for n in normalise_token_names(names) if not is_kit_owned_token(n))
    if _has_l4(authored, has_density_default=has_density_default):
        return "L4"
    if _has_l3(authored):
        return "L3"
    if _has_l2(authored):
        return "L2"
    if _has_l1(authored):
        return "L1"
    return "L0"


@dataclass(frozen=True, slots=True)
class ThemeLevelReport:
    """Result of comparing a claimed level to evidenced authorship."""

    claimed: ThemeLevel
    evidenced: ThemeLevel
    ok: bool
    missing_for_claim: frozenset[str]
    kit_owned: frozenset[str]
    message: str


def _missing_for_claim(
    claimed: ThemeLevel,
    authored: frozenset[str],
    *,
    has_density_default: bool,
) -> frozenset[str]:
    """Tokens still needed to evidence *claimed* (best-effort for L3/L4 axes)."""
    if claimed == "L0":
        return frozenset()
    missing: set[str] = set()
    if claimed in {"L1", "L2", "L3", "L4"}:
        missing |= L1_REQUIRED - authored
    if claimed in {"L2", "L3", "L4"}:
        missing |= L2_FONTS - authored
    if claimed in {"L3", "L4"} and not _has_l3_material(authored):
        # Prefer showing the radius trio as the canonical gap when nothing
        # material is present (colours-only "L3" case).
        missing |= L3_RADIUS - authored
    if claimed == "L4" and L4_SPACE not in authored and not has_density_default and not _has_density_tokens(authored):
        missing.add(L4_SPACE)
    return frozenset(missing)


def check_theme_level(
    claimed: ThemeLevel,
    names: Iterable[str],
    *,
    has_density_default: bool = False,
) -> ThemeLevelReport:
    """Compare *claimed* to evidenced level.

    A colours-only map claiming L3 fails (``ok`` is False). Kit-owned tokens
    are reported but never raise by themselves; ``render_brand_css`` may still
    emit them if they are in the overridable vocabulary.
    """
    if claimed not in _LEVEL_RANK:
        raise ValueError(f"unknown theme level {claimed!r}; expected one of {_LEVEL_ORDER}")

    raw = normalise_token_names(names)
    kit = frozenset(n for n in raw if is_kit_owned_token(n))
    authored = frozenset(n for n in raw if n not in kit)
    evidenced = infer_theme_level(authored, has_density_default=has_density_default)
    ok = _LEVEL_RANK[evidenced] >= _LEVEL_RANK[claimed]
    missing = frozenset() if ok else _missing_for_claim(claimed, authored, has_density_default=has_density_default)

    if ok:
        message = f"claimed {claimed} evidenced as {evidenced}"
    else:
        missing_preview = ", ".join(sorted(missing)[:8])
        more = "" if len(missing) <= 8 else f" (+{len(missing) - 8} more)"
        message = f"claimed {claimed} but evidenced {evidenced}; missing for claim: {missing_preview}{more}"

    return ThemeLevelReport(
        claimed=claimed,
        evidenced=evidenced,
        ok=ok,
        missing_for_claim=missing,
        kit_owned=kit,
        message=message,
    )


def parse_level(value: str) -> ThemeLevel:
    """Parse ``L1`` / ``l2`` style strings; raise ``ValueError`` if invalid."""
    normalised = value.strip().upper()
    if normalised not in _LEVEL_RANK:
        raise ValueError(f"unknown theme level {value!r}; expected one of {_LEVEL_ORDER}")
    return normalised  # type: ignore[return-value]
