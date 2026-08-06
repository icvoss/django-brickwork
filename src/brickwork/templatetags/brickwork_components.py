"""Inclusion tags for the presentational components (button, badge, alert).

These carry a little logic (variant/size validation, the ICO-008 icon-only
accessible-name enforcement), so they are tags rather than bare {% include %}.
"""

from __future__ import annotations

from django import template
from django.template.exceptions import TemplateSyntaxError

register = template.Library()


@register.filter(name="list_item")
def list_item(sequence, index):
    """Return ``sequence[index]``, or ``""`` when the index is out of range.

    Django templates have no built-in "index a list by a loop counter"
    lookup (``|slice`` only takes a static ``start:stop`` literal), and
    ``_data_table.html``'s ``responsive="stack"`` mode needs exactly that: it
    walks ``columns`` to label each cell, in lockstep with ``row.cells``, by
    position (BR-BW-TPL-005, structure only, no data reshaping elsewhere).
    Silently returns "" on a bad index rather than raising, matching Django's
    own template philosophy of "fail quiet, not loud" for lookups (the same
    behaviour ``{{ dict.missing_key }}`` has).
    """
    try:
        return sequence[int(index)]
    except (IndexError, ValueError, TypeError):
        return ""


_BUTTON_VARIANTS = {"primary", "secondary", "ghost", "danger"}
_ALERT_VARIANTS = {"info", "success", "warning", "error"}
_SIZES = {"sm", "md", "lg"}
_SKELETON_VARIANTS = {"text", "title", "row", "block"}


@register.inclusion_tag("brickwork/components/_button.html")
def bw_button(
    label: str = "",
    *,
    variant: str = "primary",
    size: str = "md",
    type: str = "button",
    href: str = "",
    icon: str = "",
    icon_only: bool = False,
    loading: bool = False,
    disabled: bool = False,
    aria_label: str = "",
    name: str = "",
    value: str = "",
) -> dict:
    """A button or link-button. ICO-008: an icon-only button REQUIRES an
    accessible name (aria_label), else it is a render error (WCAG 4.1.2).

    ``name``/``value`` (icvoss/django-brickwork#119) carry WHICH submit was
    pressed back to the server, which is the whole mechanism a bulk-actions bar
    runs on (_bulk_actions_bar.html's own docstring documents exactly this
    call). They apply to the ``<button>`` branch only: ``name``/``value`` on an
    ``<a>`` are meaningless, so pairing them with ``href`` is a render error
    rather than a silent drop, which is the failure mode that let #119 sit
    undetected.
    """
    if variant not in _BUTTON_VARIANTS:
        raise TemplateSyntaxError(f"bw_button variant must be one of {sorted(_BUTTON_VARIANTS)}, got {variant!r}")
    if size not in _SIZES:
        raise TemplateSyntaxError(f"bw_button size must be one of {sorted(_SIZES)}, got {size!r}")
    if icon_only and not aria_label:
        raise TemplateSyntaxError(
            "bw_button icon_only=True requires aria_label= (an icon-only button "
            "with no accessible name is a WCAG 4.1.2 failure, ICO-008)."
        )
    if href and (name or value):
        raise TemplateSyntaxError(
            "bw_button name=/value= apply to the <button> branch only, but href= "
            "was given, which renders an <a>. A link carries its data in the URL, "
            "so drop name/value or drop href."
        )
    if value and not name:
        raise TemplateSyntaxError(
            "bw_button value= requires name= (a submit value with no name is "
            "never sent by the browser, so the server would see nothing)."
        )
    return {
        "label": label,
        "variant": variant,
        "size": size,
        "type": type,
        "href": href,
        "icon": icon,
        "icon_only": icon_only,
        "loading": loading,
        "disabled": disabled,
        "aria_label": aria_label,
        "name": name,
        "value": value,
    }


@register.inclusion_tag("brickwork/components/_badge.html")
def bw_badge(label: str, *, variant: str = "neutral", icon: str = "", dismissible: bool = False) -> dict:
    """A small status/label badge. Reserved for neutral information, never error
    communication (errors use bw_alert in banner form, STA-008). dismissible=True
    (04-interfaces 4b Dismissible section, CMP-012) adds the bwDismissible wiring
    and a hidden-until-init close control; False renders byte-identical to the
    pre-0.9.0 output."""
    return {"label": label, "variant": variant, "icon": icon, "dismissible": bool(dismissible)}


@register.inclusion_tag("brickwork/components/_alert.html")
def bw_alert(message: str = "", *, variant: str = "info", title: str = "", dismissible: bool = False) -> dict:
    """A full-width banner alert (role=alert), the loud-surface for errors and
    other page-level status (STA-008/009). dismissible=True (04-interfaces 4b
    Dismissible section, CMP-010) adds the bwDismissible wiring and a
    hidden-until-init close control; False renders byte-identical to the
    pre-0.9.0 output."""
    if variant not in _ALERT_VARIANTS:
        raise TemplateSyntaxError(f"bw_alert variant must be one of {sorted(_ALERT_VARIANTS)}, got {variant!r}")
    icon = {"info": "info", "success": "success", "warning": "alert-triangle", "error": "alert-circle"}[variant]
    return {"message": message, "variant": variant, "title": title, "icon": icon, "dismissible": bool(dismissible)}


@register.inclusion_tag("brickwork/components/_toggle.html")
def bw_toggle(
    label: str,
    *,
    id: str,
    name: str = "",
    value: str = "on",
    checked: bool = False,
    disabled: bool = False,
) -> dict:
    """A standalone labelled toggle switch, not bound to a Django form field
    (BR-BW-INPUT-001). ``label`` is required and non-empty (a switch with no
    accessible name is a WCAG 4.1.2 failure, the ICO-008 defect class); ``id``
    is required so the wrapping <label> pairs correctly. ``name`` defaults to
    ``id`` when omitted, matching how most single-control POST/hx-post payloads
    key their field. For a form-bound checkbox use bw_field_widget's own
    BR-BW-INPUT-001 opt-in (forms.CheckboxInput(attrs={"class": "bw-toggle"}))
    instead of this tag."""
    if not label:
        raise TemplateSyntaxError(
            "bw_toggle requires a non-empty label (a switch with no accessible name is a WCAG 4.1.2 failure)."
        )
    if not id:
        raise TemplateSyntaxError("bw_toggle requires id= (the wrapping label pairs with it).")
    return {
        "label": label,
        "id": id,
        "name": name or id,
        "value": value,
        "checked": bool(checked),
        "disabled": bool(disabled),
    }


@register.inclusion_tag("brickwork/components/_skeleton.html")
def bw_skeleton(
    *,
    variant: str = "text",
    count: int = 1,
    width: str = "",
    height: str = "",
) -> dict:
    """A loading placeholder (STA-004). Repeats ``count`` copies of the shape
    named by ``variant`` ("text" | "title" | "row" | "block"). A plain
    {% include %} cannot loop a variable count, so this is a tag: it
    validates ``variant`` and turns ``count`` into a range() the template
    iterates. ``width``/``height`` (CSS lengths, e.g. "12rem") override the
    variant's default box via the --bw-skeleton-w/-h custom properties;
    omitted keeps the variant's own default sizing."""
    if variant not in _SKELETON_VARIANTS:
        raise TemplateSyntaxError(f"bw_skeleton variant must be one of {sorted(_SKELETON_VARIANTS)}, got {variant!r}")
    if not isinstance(count, int) or count < 1:
        raise TemplateSyntaxError(f"bw_skeleton count must be a positive int, got {count!r}")
    style_parts = []
    if width:
        style_parts.append(f"--bw-skeleton-w: {width}")
    if height:
        style_parts.append(f"--bw-skeleton-h: {height}")
    return {
        "variant": variant,
        "count": range(count),
        # Plain (unescaped) string: the template renders it inside a
        # style="..." attribute, where Django's normal autoescaping of the
        # attribute value is exactly the protection needed (width/height are
        # caller-supplied CSS lengths, never markup).
        "style_attr": "; ".join(style_parts),
    }
