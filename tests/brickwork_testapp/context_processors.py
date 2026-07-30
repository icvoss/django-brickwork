"""Wire the testapp's nav + theme into every template (consuming-project shape)."""

from __future__ import annotations

from brickwork.models import NavContext
from brickwork.services.navigation import resolve_active_item, visible_items
from brickwork.services.tokens import resolve_theme_attributes

from .nav import MAIN_NAV


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
    }
