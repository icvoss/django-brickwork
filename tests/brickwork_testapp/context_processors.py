"""Wire the testapp's nav + theme into every template (consuming-project shape)."""

from __future__ import annotations

from brickwork.models import NavContext
from brickwork.services.navigation import resolve_active_item, visible_items
from brickwork.services.tokens import resolve_theme_attributes

from .nav import MAIN_NAV

# The topbar account menu (2 items, one danger) so every testapp page and the
# a11y fixtures exercise the disclosure.
_ACCOUNT_MENU_ITEMS = [
    {"label": "Settings", "url": "/settings/", "icon": "settings"},
    {"label": "Sign out", "url": "/widgets/", "icon": "log-out", "danger": True},
]


def _breadcrumb_trail(request):
    """A consuming-project-shaped trail: current page last, never linked."""
    view_name = getattr(request.resolver_match, "view_name", "")
    if view_name == "testapp:dashboard":
        return [{"label": "Home", "url": "/widgets/"}, {"label": "Dashboard"}]
    if view_name in {"testapp:interactions", "testapp:interaction-confirm"}:
        return [{"label": "Home", "url": "/widgets/"}, {"label": "Interactions"}]
    if view_name in {"testapp:widget-create", "testapp:widget-edit"}:
        return [
            {"label": "Home", "url": "/widgets/"},
            {"label": "Widgets", "url": "/widgets/"},
            {"label": "Widget"},
        ]
    return [{"label": "Home", "url": "/widgets/"}, {"label": "Widgets"}]


def _layout(request) -> str:
    """SHL-001 layout passthrough: ?layout=topbar flips the shell's layout ARG
    on every testapp page; anything else falls back to the sidebar default."""
    layout = request.GET.get("layout", "")
    return layout if layout in {"sidebar", "topbar"} else "sidebar"


def brickwork_context(request):
    perm = getattr(getattr(request, "user", None), "has_perm", lambda _p: True)
    context = NavContext(request=request, permission_checker=perm, feature_checker=lambda _f: True)
    items = visible_items(MAIN_NAV, context)
    active = resolve_active_item(items, request.resolver_match)
    theme = resolve_theme_attributes(request)
    return {
        "bw_nav_items": items,
        "bw_active_nav_item": active,
        "bw_theme": theme["theme"],
        "bw_density": theme["density"],
        "bw_dir": theme["dir"],
        "layout": _layout(request),
        "breadcrumb_trail": _breadcrumb_trail(request),
        "account_menu_items": _ACCOUNT_MENU_ITEMS,
    }
