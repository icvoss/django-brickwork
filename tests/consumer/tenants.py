"""Multi-host tenant simulation (brickwork#61 seam 1 + 2).

A real V3-shaped brownfield app resolves its tenant via django-hosts (a
subdomain per tenant) and reads per-tenant branding from a Tenant model. This
fixture simulates both without either dependency: a plain dict keyed by
request host, so the middleware/theme-resolver seams are exercised without
pulling django-hosts into brickwork's own dev dependencies.

Two tenants, deliberately different on every axis the shell renders, so a
test comparing the two hosts is proving real branching, not incidental
sameness:

- acme.example.com: light theme, comfortable density, ltr, brand "acme".
- globex.example.com: dark theme, compact density, ltr, brand "globex".

A third, unknown host falls back to the harness default (no tenant match),
proving the resolver degrades gracefully rather than raising.
"""

from __future__ import annotations

from typing import TypedDict


class TenantConfig(TypedDict):
    slug: str
    brand_name: str
    nav_label: str
    theme: str
    density: str
    brand: str


TENANTS_BY_HOST: dict[str, TenantConfig] = {
    "acme.example.com": {
        "slug": "acme",
        "brand_name": "Acme Ltd",
        "nav_label": "Acme workspace",
        "theme": "light",
        "density": "comfortable",
        "brand": "acme",
    },
    "globex.example.com": {
        "slug": "globex",
        "brand_name": "Globex plc",
        "nav_label": "Globex workspace",
        "theme": "dark",
        "density": "compact",
        "brand": "globex",
    },
}

DEFAULT_TENANT: TenantConfig = {
    "slug": "default",
    "brand_name": "Consumer harness",
    "nav_label": "Workspace",
    "theme": "light",
    "density": "comfortable",
    "brand": "",
}


def tenant_for_host(host: str) -> TenantConfig:
    """Resolve a tenant config from a bare request host (no port).

    Never raises: an unrecognised host resolves to DEFAULT_TENANT, mirroring
    how a real multi-host app must not 500 on an unmapped host.
    """
    return TENANTS_BY_HOST.get(host, DEFAULT_TENANT)
