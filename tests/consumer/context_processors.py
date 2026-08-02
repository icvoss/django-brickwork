"""Wire the consumer harness's nav + tenant branding into every template.

Mirrors brickwork_testapp's context_processors.py shape, but adds the two
extra seams #61 asks for: the feature_checker (from features.py, gating the
Reports nav item) and the resolved tenant's brand_name/nav_label (from
TenantHostMiddleware, for the sidebar header). The theme axes themselves
(bw_theme/bw_density/bw_dir/bw_brand) are NOT set here: they come from
brickwork.context_processors.theme via BRICKWORK_THEME_RESOLVER
(theme_resolver.resolve_tenant_theme), proving that seam independently of
this processor.
"""

from __future__ import annotations

from brickwork.models import NavContext
from brickwork.services.navigation import resolve_active_item, visible_items

from .features import make_feature_checker
from .nav import MAIN_NAV


def consumer_context(request):
    tenant = getattr(request, "consumer_tenant", None)
    perm = getattr(getattr(request, "user", None), "has_perm", lambda _p: True)
    context = NavContext(
        request=request,
        permission_checker=perm,
        feature_checker=make_feature_checker(request),
    )
    items = visible_items(MAIN_NAV, context)
    active = resolve_active_item(items, request.resolver_match)
    return {
        "bw_nav_items": items,
        "bw_active_nav_item": active,
        "tenant_brand_name": tenant["brand_name"] if tenant else "Consumer harness",
        "tenant_nav_label": tenant["nav_label"] if tenant else "Workspace",
    }
