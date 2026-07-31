"""The ``{% bw_icon %}`` template tag: name-referenced, injection-safe, a11y-enforced.

Usage::

    {% load brickwork_icons %}
    {% bw_icon "trash" label="Delete" %}          {# meaningful icon #}
    {% bw_icon "chevron-down" decorative=True %}   {# decorative icon #}
    {% bw_icon "search" size="lg" label="Search" %}

Auto-escaping / safety (ICO-003): the tag resolves ``name`` against the vetted
brickwork registry and emits the registry's pinned inner SVG markup. It NEVER
passes a request- or database-supplied string through ``|safe``; the only markup
marked safe is the registry's own vendored artwork plus attribute values that are
either from a fixed allow-list (``size``) or HTML-escaped (``label``). An unknown
name raises (ICO-013), so a template typo fails loudly, never as a blank icon.

Accessibility (ICO-007, enforced): every icon is EITHER decorative
(``decorative=True`` -> ``aria-hidden="true"``) OR meaningful (``label="..."`` ->
``role="img" aria-label="..."``). Supplying neither is a render-time error: an
icon with no accessible name and no ``aria-hidden`` is exactly the WCAG defect
class this tag exists to close. Supplying both is also an error (contradictory).
"""

from __future__ import annotations

from django import template
from django.template.exceptions import TemplateSyntaxError
from django.utils.html import conditional_escape
from django.utils.safestring import SafeString, mark_safe

from brickwork.icons import get_icon, is_directional

register = template.Library()

# size arg -> the --bw-icon-size-* token the icon sizes to (ICO-004: sm/md/lg/xl,
# aligned to context). Emitted as the --bw-icon-size CSS custom property (NOT an
# SVG width/height attribute: geometry attributes do not accept var(), so an
# attribute of var(--bw-icon-size-sm) is invalid and the icon renders at the
# 300x150 SVG default). .bw-icon reads --bw-icon-size for its width/height, so
# the actual size stays token-driven and density/brand aware.
_SIZE_TOKENS: dict[str, str] = {
    "sm": "var(--bw-icon-size-sm)",
    "md": "var(--bw-icon-size-md)",
    "lg": "var(--bw-icon-size-lg)",
    "xl": "var(--bw-icon-size-xl)",
}
_DEFAULT_SIZE = "md"


@register.simple_tag(name="bw_icon")
def bw_icon(
    name: str,
    *,
    size: str = _DEFAULT_SIZE,
    decorative: bool = False,
    label: str = "",
    css_class: str = "",
) -> SafeString:
    """Render a registered icon by name as an inline, accessible ``<svg>``.

    Args:
        name: a registered brickwork icon name (raises IconNotFoundError if not).
        size: one of ``sm|md|lg|xl`` (ICO-004); anything else is a render error.
        decorative: True marks the icon ``aria-hidden`` (no accessible name).
        label: an accessible name; sets ``role="img" aria-label`` (mutually
            exclusive with ``decorative``).
        css_class: extra CSS classes appended after the base ``bw-icon`` class.

    Returns a SafeString. The inner paint markup comes from the vetted registry,
    never from caller-supplied strings; ``label`` and ``css_class`` are escaped.
    """
    if size not in _SIZE_TOKENS:
        raise TemplateSyntaxError(f"{{% bw_icon %}}: size must be one of {sorted(_SIZE_TOKENS)}, got {size!r}.")

    # ICO-007: enforce the decorative-vs-meaningful pairing. Refuse to render an
    # icon that is neither (the "icon with no name and no aria-hidden" defect) or
    # both (contradictory intent).
    if decorative and label:
        raise TemplateSyntaxError(f'{{% bw_icon "{name}" %}}: pass either decorative=True OR a label, not both.')
    if not decorative and not label:
        raise TemplateSyntaxError(
            f'{{% bw_icon "{name}" %}}: an icon must be decorative=True (aria-hidden) '
            f"or carry a label= (accessible name). Refusing to render an "
            f"unlabelled, non-hidden icon (ICO-007, WCAG 4.1.2)."
        )

    inner = get_icon(name)  # raises IconNotFoundError on an unknown name (ICO-013)

    classes = "bw-icon"
    if is_directional(name):
        classes += " bw-icon-directional"  # flips under [dir="rtl"] (ICO-014)
    if css_class:
        classes += " " + conditional_escape(css_class)

    a11y = 'aria-hidden="true"' if decorative else f'role="img" aria-label="{conditional_escape(label)}"'

    svg = (
        f'<svg class="{classes}" '
        f'style="--bw-icon-size: {_SIZE_TOKENS[size]}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="var(--bw-icon-stroke-width, 2)" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f"{a11y}>{inner}</svg>"
    )
    # noqa justification (S308): `inner` is vetted registry artwork (never caller
    # input); `label`/`css_class` are conditional_escape'd above; `size` is from a
    # fixed allow-list. No untrusted string reaches this SafeString.
    return mark_safe(svg)  # noqa: S308
