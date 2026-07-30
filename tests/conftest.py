"""Pytest collection guards for the brickwork suite.

test_integration.py exercises the brickwork_testapp (real views/URLs/forms) and
only runs under the settings_seams leg (which installs the testapp). Under the
default settings leg the testapp is absent, so its integration tests are skipped
at collection to avoid importing testapp models that are not installed (mirrors
the icv-media house pattern).
"""

from __future__ import annotations

from django.apps import apps


def pytest_ignore_collect(collection_path, config):
    if "test_integration.py" in str(collection_path):
        return not apps.is_installed("brickwork_testapp")
    return False
