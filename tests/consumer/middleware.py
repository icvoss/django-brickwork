"""Multi-host shell branching (brickwork#61 seam 1).

Simulates the django-hosts pattern a real brownfield app uses: a middleware
that resolves the tenant from the request host and stashes it on the request
BEFORE the view runs, so both the view (which picks nav/branding) and the
theme resolver (which reads it in the context-processor pass) see the same
resolved tenant for one request. brickwork itself never reads this attribute:
it is entirely host-owned, consumed only by consumer.nav and
consumer.theme_resolver below (mirrors BR-BW-NAV-004's rule that brickwork
takes host-injected callables, never a named request attribute).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .tenants import tenant_for_host

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


class TenantHostMiddleware:
    """Resolve request.consumer_tenant from the bare host (no port)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        host = request.get_host().split(":")[0]
        request.consumer_tenant = tenant_for_host(host)
        return self.get_response(request)
