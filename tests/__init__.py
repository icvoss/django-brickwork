"""Marks tests/ as a regular package, deliberately.

Without this file the ``tests`` package pytest resolves via
``pythonpath = ["src", "."]`` is an implicit namespace package, and a
third-party wheel that (accidentally) ships a top-level regular ``tests``
package wins import resolution regardless of sys.path order, hijacking
``DJANGO_SETTINGS_MODULE = "tests.settings"`` (icvoss/django-brickwork#97,
hit in a real consumer environment). A regular package always beats a
namespace package, so this file is load-bearing: do not delete it.
"""
