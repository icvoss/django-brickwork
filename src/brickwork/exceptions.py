"""brickwork exceptions (04-interfaces.md section 3)."""

from __future__ import annotations


class BrickworkError(Exception):
    """Base class for every brickwork-raised error."""


class NavConfigError(BrickworkError):
    """A navigation configuration is invalid (e.g. a duplicate key, BR-BW-NAV-002).

    Raised at configuration-build time (import time), never at request time, so a
    nav-collision bug surfaces on startup rather than as a runtime surprise.
    """
