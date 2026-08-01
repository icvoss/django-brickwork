"""The testapp's nav configuration (a consuming-project-shaped example)."""

from __future__ import annotations

from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

MAIN_NAV = (
    NavItem(key="dashboard", label="Dashboard", url_name="testapp:dashboard", icon="home"),
    NavItem(key="widgets", label="Widgets", url_name="testapp:widget-list", icon="folder"),
    NavItem(key="interactions", label="Interactions", url_name="testapp:interactions", icon="info"),
    NavItem(
        key="admin-section",
        label="Admin",
        section_header=True,
        children=(
            NavItem(key="settings", label="Settings", url_name="testapp:settings-index", icon="settings"),
            NavItem(key="docs", label="Docs", external_url="https://example.com/docs", icon="file"),
            NavItem(key="inbox", label="Inbox", url_name="testapp:widget-list", badge=12, icon="bell"),
        ),
    ),
)

validate_nav_config(MAIN_NAV)
