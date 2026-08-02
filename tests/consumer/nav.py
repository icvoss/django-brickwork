"""The consumer harness's nav configuration (V3-shaped, brickwork#61 seam 3).

The "Reports" item declares required_features=(REPORTS_FLAG,), so
visible_items hides it unless the request's feature_checker reports that
flag enabled (features.make_feature_checker, wired in
context_processors.consumer_context).
"""

from __future__ import annotations

from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

from .features import REPORTS_FLAG

MAIN_NAV = (
    NavItem(key="tickets", label="Tickets", url_name="consumer:ticket-list", icon="folder"),
    NavItem(key="surface", label="Component surface", url_name="consumer:surface", icon="info"),
    NavItem(
        key="reports",
        label="Reports",
        url_name="consumer:reports",
        icon="file",
        required_features=(REPORTS_FLAG,),
    ),
)

validate_nav_config(MAIN_NAV)
