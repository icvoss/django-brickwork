"""The BRICKWORK_THEME_RESOLVER target (brickwork#61 seam 2).

Proves the context-processor mapping (brickwork.context_processors.theme)
wires a per-tenant resolver's output onto the shell's bw_* vars, which then
render as data-* attributes on <html> (brickwork.services.tokens's own
contract). Reads the tenant TenantHostMiddleware already resolved onto the
request; this is the only place consumer/ reads that attribute, keeping the
host-injected-callable boundary in one file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .tenants import tenant_for_host

if TYPE_CHECKING:
    from django.http import HttpRequest

    from brickwork.services.tokens import ThemeAttributes


def resolve_tenant_theme(request: HttpRequest) -> ThemeAttributes:
    """Per-tenant theme/density/dir/brand, resolved from the request host.

    Falls back to resolving the host directly (rather than trusting
    request.consumer_tenant to already be set) so this function is also
    independently correct if ever called outside the middleware's reach,
    matching resolve_theme_attributes' own "never assume a request
    attribute" discipline.
    """
    host = request.get_host().split(":")[0]
    tenant = tenant_for_host(host)
    return {
        "theme": tenant["theme"],
        "density": tenant["density"],
        "dir": "ltr",
        "brand": tenant["brand"],
    }
