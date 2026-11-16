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
# ADR-125 section 6: one closed five-step size grammar for the whole kit. It is
# the CEILING, never a default: a component earns steps and declares its own
# subset explicitly (``size_subset``). A step the stylesheet does not ship for a
# component is a silent no-op if accepted, so nothing inherits this full set.
SIZE_STEPS: Final[tuple[str, ...]] = ("xs", "sm", "md", "lg", "xl")
RADII: Final[frozenset[str]] = frozenset({"default", "sm", "lg", "xl", "none"})
HEADER_RECIPES: Final[frozenset[str]] = frozenset({"none", "plain", "bordered", "muted", "inverse", "accent"})
FOOTER_RECIPES: Final[frozenset[str]] = frozenset({"none", "plain", "muted", "actions"})
MEDIA_RECIPES: Final[frozenset[str]] = frozenset({"none", "bleed", "inset", "icon"})
BANDS: Final[frozenset[str]] = frozenset({"plain", "tint"})
WIDTHS: Final[frozenset[str]] = frozenset({"contained", "bleed"})
TONES: Final[frozenset[str]] = frozenset({"muted", "strong"})
SPACINGS: Final[frozenset[str]] = frozenset({"sm", "md", "lg"})
SHAPES: Final[frozenset[str]] = frozenset({"circle", "square"})
# The global density axis (ADR-125, ADR-060 rule 1): three values, one meaning.
# `{% bw_options density= %}` and `{% bw_form density= %}` share this set. A
# component that renders fewer densities declares its own subset.
DENSITIES: Final[frozenset[str]] = frozenset({"comfortable", "compact", "spacious"})


def size_subset(*steps: str, extra: tuple[str, ...] = ()) -> frozenset[str]:
    """A component's own closed size set: a subset of ``SIZE_STEPS``.

    ``extra`` names non-step values a component genuinely ships (modal ``full``).
    Raises ``ValueError`` at import time when a step is not one of the five, so
    a typo cannot ship as a silent vocabulary.
    """
    unknown = [step for step in steps if step not in SIZE_STEPS]
    if unknown:
        raise ValueError(f"size_subset: {unknown!r} are not in {SIZE_STEPS!r}")
    return frozenset((*steps, *extra))


# Explicit per-component size subsets. Each lists only the steps the shipped
# stylesheet renders for that component (ADR-125 section 6: xs and xl exist as
# tokens and appear on a component only when it earns them).
BUTTON_SIZES: Final[frozenset[str]] = size_subset("sm", "md", "lg")
GAUGE_SIZES: Final[frozenset[str]] = size_subset("sm", "md", "lg")
AVATAR_SIZES: Final[frozenset[str]] = size_subset("sm", "md", "lg")

# The two components whose stylesheet renders only comfortable and compact.
DENSITIES_COMFORTABLE_COMPACT: Final[frozenset[str]] = frozenset({"comfortable", "compact"})

# Axis name -> closed vocabulary. Used by {% bw_options %} keyword args.
OPTION_VOCABULARIES: Final[dict[str, frozenset[str]]] = {
    "surface": SURFACES,
    "elevation": ELEVATIONS,
    # No shared "size": every component declares its own subset in
    # COMPONENT_OPTIONS (ADR-125 section 6), so none inherits the full set.
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
        "size": size_subset("sm", "md"),
    },
    "brickwork/components/_card.html": {
        "size": size_subset("sm", "md", "lg"),
    },
    "brickwork/components/_callout.html": {
        "variant": frozenset({"note", "info", "success", "warning", "danger", "neutral"}),
    },
    "brickwork/components/_button_group.html": {
        "variant": frozenset({"segmented", "attached"}),
        "size": size_subset("sm", "md", "lg"),
    },
    "brickwork/components/_divider.html": {
        "tone": TONES,
        "spacing": SPACINGS,
    },
    "brickwork/components/_avatar.html": {
        "size": AVATAR_SIZES,
        "shape": SHAPES,
    },
    "brickwork/components/_empty_state.html": {
        "surface": frozenset({"framed", "plain"}),
    },
    "brickwork/components/_page_header.html": {
        "surface": frozenset({"default", "tint"}),
    },
    "brickwork/components/_data_table.html": {
        "density": DENSITIES_COMFORTABLE_COMPACT,
    },
    "brickwork/components/_list_item.html": {
        "density": DENSITIES_COMFORTABLE_COMPACT,
    },
    "brickwork/components/_modal.html": {
        "size": size_subset("sm", "md", "lg", extra=("full",)),
        "header_recipe": frozenset({"plain", "muted", "bordered"}),
        "footer_recipe": frozenset({"plain", "muted", "actions"}),
    },
    # Beat Phase E (icvoss/django-brickwork#540): same header/footer recipes
    # as modal. Size stays sm/md/lg (no full: a slide-over is edge-anchored).
    "brickwork/components/_slide_over.html": {
        "size": size_subset("sm", "md", "lg"),
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
        if vocabulary is None and name == "size":
            raise TemplateSyntaxError(
                f"bw_options on {component}: this component declares no size subset, so size= is unsupported. "
                f"Size steps are {list(SIZE_STEPS)} but each component declares the ones it renders "
                f"(COMPONENT_OPTIONS)."
            )
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
