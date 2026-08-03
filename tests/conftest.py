"""Pytest collection guards for the brickwork suite.

test_integration.py exercises the brickwork_testapp (real views/URLs/forms) and
only runs under the settings_seams leg (which installs the testapp). Under the
default settings leg the testapp is absent, so its integration tests are skipped
at collection to avoid importing testapp models that are not installed (mirrors
the icv-media house pattern).

test_consumer_smoke.py exercises the SECOND, V3-shaped consumer harness
(tests/consumer/, brickwork#61) and only runs under the settings_consumer leg
(which installs the consumer app). Kept out of both the default leg and the
settings_seams leg the same way, so its models/routing never pollute either.

test_marketing.py exercises brickwork.marketing (1.2.0), installed in the
default leg and the settings_seams leg but NOT in settings_consumer.py (a
fixed, pre-existing V3-shaped harness orthogonal to the marketing kit):
skipped at collection under any leg where the sub-app is absent, the same
guard shape as the two legs above.
"""

from __future__ import annotations

from django.apps import apps


def pytest_ignore_collect(collection_path, config):
    path_str = str(collection_path)
    if "test_integration.py" in path_str:
        return not apps.is_installed("brickwork_testapp")
    if "test_consumer_smoke.py" in path_str:
        return not apps.is_installed("consumer")
    if "test_marketing.py" in path_str:
        # is_installed() checks the dotted app NAME ("brickwork.marketing"),
        # not its label ("brickwork_marketing", used everywhere else in this
        # file): the marketing sub-app is the one app here whose name and
        # label differ.
        return not apps.is_installed("brickwork.marketing")
    return False
