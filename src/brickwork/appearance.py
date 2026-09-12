"""Shared closed appearance vocabularies for include-consumed components.

Beautiful-defaults suite (icvoss/django-brickwork#533): one grammar for
surface / elevation / region recipes and the axes ADR-057 / ADR-060 already
named. Components adopt only the axes that apply. Unknown values raise
``TemplateSyntaxError`` via ``validate_options`` / ``{% bw_options %}``.

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
    """
    for name, value in options.items():
        if _is_omitted(value):
            continue
        vocabulary = OPTION_VOCABULARIES.get(name)
        if vocabulary is None:
            raise TemplateSyntaxError(
                f"bw_options on {component}: unknown appearance axis {name!r}. "
                f"Known axes: {sorted(OPTION_VOCABULARIES)}."
            )
        if not isinstance(value, str):
            raise TemplateSyntaxError(
                f"{component} {name}= must be a string drawn from {sorted(vocabulary)}, got {value!r}."
            )
        if value not in vocabulary:
            raise TemplateSyntaxError(f"{component} {name}= must be one of {sorted(vocabulary)}, got {value!r}.")
