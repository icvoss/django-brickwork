"""Shared closed appearance vocabularies for include-consumed components.

Beautiful-defaults suite (icvoss/django-brickwork#533): one grammar for
surface / elevation / region recipes and the axes ADR-057 / ADR-060 already
named. Beat Phase B (icvoss/django-brickwork#542) adds tone / spacing /
shape, plus per-component ``variant`` sets. Components adopt only the axes
that apply. Unknown values raise ``TemplateSyntaxError`` via
``validate_options`` / ``{% bw_options %}``.

Docs: ``docs/APPEARANCE.md``.
"""

from __future__ import annotations

from typing import Final

from django.template.exceptions import TemplateSyntaxError

# Shared closed sets. A component may expose a subset; silence in a template
# header means unsupported, never "supported and ignored".
SURFACES: Final[frozenset[str]] = frozenset({"default", "raised", "tint", "inverse", "muted"})
ELEVATIONS: Final[frozenset[str]] = frozenset({"0", "1", "2", "3"})
SIZES: Final[frozenset[str]] = frozenset({"sm", "md", "lg"})
RADII: Final[frozenset[str]] = frozenset({"default", "sm", "lg", "xl", "none"})
HEADER_RECIPES: Final[frozenset[str]] = frozenset({"none", "plain", "bordered", "muted", "inverse", "accent"})
FOOTER_RECIPES: Final[frozenset[str]] = frozenset({"none", "plain", "muted", "actions"})
MEDIA_RECIPES: Final[frozenset[str]] = frozenset({"none", "bleed", "inset", "icon"})
BANDS: Final[frozenset[str]] = frozenset({"plain", "tint"})
WIDTHS: Final[frozenset[str]] = frozenset({"contained", "bleed"})
TONES: Final[frozenset[str]] = frozenset({"muted", "strong"})
SPACINGS: Final[frozenset[str]] = frozenset({"sm", "md", "lg"})
SHAPES: Final[frozenset[str]] = frozenset({"circle", "square"})
DENSITIES: Final[frozenset[str]] = frozenset({"comfortable", "compact"})

# Axis name -> closed vocabulary. Used by {% bw_options %} keyword args.
OPTION_VOCABULARIES: Final[dict[str, frozenset[str]]] = {
    "surface": SURFACES,
    "elevation": ELEVATIONS,
    "size": SIZES,
    "radius": RADII,
    "header_recipe": HEADER_RECIPES,
    "footer_recipe": FOOTER_RECIPES,
    "media_recipe": MEDIA_RECIPES,
    "band": BANDS,
    "width": WIDTHS,
    "tone": TONES,
    "spacing": SPACINGS,
    "shape": SHAPES,
    "density": DENSITIES,
}

# Per-component closed sets for axes whose values are not shared (variant,
# and size subsets). Keyed by the template path passed as ``component=`` to
# ``{% bw_options %}``. An axis listed here overrides the shared vocabulary
# for that component only; ``variant`` has no shared set.
COMPONENT_OPTIONS: Final[dict[str, dict[str, frozenset[str]]]] = {
    "brickwork/components/_chip.html": {
        "variant": frozenset({"neutral", "info", "success", "warning", "danger"}),
        "size": frozenset({"sm", "md"}),
    },
    "brickwork/components/_callout.html": {
        "variant": frozenset({"note", "info", "success", "warning", "danger", "neutral"}),
    },
    "brickwork/components/_button_group.html": {
        "variant": frozenset({"segmented", "attached"}),
    },
    "brickwork/components/_divider.html": {
        "tone": TONES,
        "spacing": SPACINGS,
    },
    "brickwork/components/_avatar.html": {
        "size": SIZES,
        "shape": SHAPES,
    },
    "brickwork/components/_empty_state.html": {
        "surface": frozenset({"framed", "plain"}),
    },
    "brickwork/components/_page_header.html": {
        "surface": frozenset({"default", "tint"}),
    },
    "brickwork/components/_data_table.html": {
        "density": DENSITIES,
    },
    "brickwork/components/_list_item.html": {
        "density": DENSITIES,
    },
    "brickwork/components/_modal.html": {
        "size": frozenset({"sm", "md", "lg", "full"}),
        "header_recipe": frozenset({"plain", "muted", "bordered"}),
        "footer_recipe": frozenset({"plain", "muted", "actions"}),
    },
    # Beat Phase E (icvoss/django-brickwork#540): same header/footer recipes
    # as modal. Size stays sm/md/lg (no full: a slide-over is edge-anchored).
    "brickwork/components/_slide_over.html": {
        "size": frozenset({"sm", "md", "lg"}),
        "header_recipe": frozenset({"plain", "muted", "bordered"}),
        "footer_recipe": frozenset({"plain", "muted", "actions"}),
    },
}


def _is_omitted(value: object) -> bool:
    """True when the caller did not supply an option (use the authored default).

    Django resolves missing template variables to ``""``. Whitespace-only is
    omitted. ``False`` / ``0`` are not appearance options here.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def validate_options(*, component: str = "component", **options: object) -> None:
    """Raise ``TemplateSyntaxError`` when a supplied option is outside its set.

    Omitted values (missing / empty string) are skipped so existing call sites
    stay byte-identical. An explicit value must be a string in the closed set.
    Per-component vocabularies in ``COMPONENT_OPTIONS`` win over the shared
    ``OPTION_VOCABULARIES`` for the same axis name.
    """
    component_sets = COMPONENT_OPTIONS.get(component, {})
    for name, value in options.items():
        if _is_omitted(value):
            continue
        vocabulary = component_sets.get(name) or OPTION_VOCABULARIES.get(name)
        if vocabulary is None:
            known = sorted({*OPTION_VOCABULARIES, *component_sets})
            raise TemplateSyntaxError(
                f"bw_options on {component}: unknown appearance axis {name!r}. Known axes: {known}."
            )
        if not isinstance(value, str):
            raise TemplateSyntaxError(
                f"{component} {name}= must be a string drawn from {sorted(vocabulary)}, got {value!r}."
            )
        if value not in vocabulary:
            raise TemplateSyntaxError(f"{component} {name}= must be one of {sorted(vocabulary)}, got {value!r}.")
