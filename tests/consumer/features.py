"""A waffle-style feature_checker (brickwork#61 seam 3).

Real waffle exposes ``waffle.flag_is_active(request, name)``. This fixture
simulates the same shape with no waffle dependency: a per-request set of
enabled flag names, read off the request by NavContext.feature_checker
(BR-BW-NAV-004: brickwork calls no flag API itself, only the host-injected
callable). ``?flags=`` on any request overrides the default set so a single
test client can prove both the hidden and the visible state without needing
two separate fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest

# The "reports" nav item is gated behind this flag; off by default, so the
# happy-path harness proves an item CAN be hidden, not just that it can be
# shown (a feature_checker that always returns True would pass silently).
REPORTS_FLAG = "reports_beta"

DEFAULT_ENABLED_FLAGS: frozenset[str] = frozenset()


def enabled_flags_for_request(request: HttpRequest) -> frozenset[str]:
    """Read the enabled-flags set for this request.

    ``?flags=reports_beta,other`` (comma-separated) overrides the default
    empty set; a plain request gets DEFAULT_ENABLED_FLAGS (nothing enabled).
    """
    raw = request.GET.get("flags")
    if raw is None:
        return DEFAULT_ENABLED_FLAGS
    return frozenset(name.strip() for name in raw.split(",") if name.strip())


def make_feature_checker(request: HttpRequest):
    """Return a NavContext-shaped feature_checker closed over this request."""
    enabled = enabled_flags_for_request(request)

    def feature_checker(flag_name: str) -> bool:
        return flag_name in enabled

    return feature_checker
