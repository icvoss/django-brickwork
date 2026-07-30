"""Inclusion tags for the presentational components (button, badge, alert).

These carry a little logic (variant/size validation, the ICO-008 icon-only
accessible-name enforcement), so they are tags rather than bare {% include %}.
"""

from __future__ import annotations

from django import template
from django.template.exceptions import TemplateSyntaxError

register = template.Library()

_BUTTON_VARIANTS = {"primary", "secondary", "ghost", "danger"}
_ALERT_VARIANTS = {"info", "success", "warning", "error"}
_SIZES = {"sm", "md", "lg"}


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
) -> dict:
    """A button or link-button. ICO-008: an icon-only button REQUIRES an
    accessible name (aria_label), else it is a render error (WCAG 4.1.2)."""
    if variant not in _BUTTON_VARIANTS:
        raise TemplateSyntaxError(f"bw_button variant must be one of {sorted(_BUTTON_VARIANTS)}, got {variant!r}")
    if size not in _SIZES:
        raise TemplateSyntaxError(f"bw_button size must be one of {sorted(_SIZES)}, got {size!r}")
    if icon_only and not aria_label:
        raise TemplateSyntaxError(
            "bw_button icon_only=True requires aria_label= (an icon-only button "
            "with no accessible name is a WCAG 4.1.2 failure, ICO-008)."
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
    }


@register.inclusion_tag("brickwork/components/_badge.html")
def bw_badge(label: str, *, variant: str = "neutral", icon: str = "") -> dict:
    """A small status/label badge. Reserved for neutral information, never error
    communication (errors use bw_alert in banner form, STA-008)."""
    return {"label": label, "variant": variant, "icon": icon}


@register.inclusion_tag("brickwork/components/_alert.html")
def bw_alert(message: str = "", *, variant: str = "info", title: str = "") -> dict:
    """A full-width banner alert (role=alert), the loud-surface for errors and
    other page-level status (STA-008/009)."""
    if variant not in _ALERT_VARIANTS:
        raise TemplateSyntaxError(f"bw_alert variant must be one of {sorted(_ALERT_VARIANTS)}, got {variant!r}")
    icon = {"info": "info", "success": "success", "warning": "alert-triangle", "error": "alert-circle"}[variant]
    return {"message": message, "variant": variant, "title": title, "icon": icon}
