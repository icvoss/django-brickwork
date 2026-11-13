"""The registry of ``startsite`` starters (ADR-095, icvoss/django-brickwork#470).

A starter is a named, self-contained project payload: ``files()`` returns every
file it emits, and the remaining fields tell the command what to print once it
has written them. The command is the governed surface; a starter's name is part
of that surface (it is the value of ``--starter``), and what a starter emits is
not (ADR-095 section 3).

Adding a starter is one module plus one entry here. Resist adding a third
without an owner ruling: two starters, one per product shape a consumer starts
from, is the whole offer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from brickwork.management.commands import _startsite_data_app, _startsite_public_site


@dataclass(frozen=True)
class Starter:
    name: str
    summary: str
    files: Callable[[], dict[str, str]]
    #: Commands to run inside the emitted directory, in order, before it serves.
    setup_commands: tuple[str, ...]
    #: (path, what you see there) for each page the project serves.
    pages: tuple[tuple[str, str], ...]


STARTERS: dict[str, Starter] = {
    starter.name: starter
    for starter in (
        Starter(
            name="public-site",
            summary="a public site with no database: a marketing landing page and a docs home",
            files=_startsite_public_site.files,
            setup_commands=("python manage.py runserver",),
            pages=(("/", "the landing page"), ("/docs/", "the docs home")),
        ),
        Starter(
            name="data-app",
            summary="a database-backed app: an invoices dashboard and a filterable, sortable list",
            files=_startsite_data_app.files,
            setup_commands=(
                "python manage.py migrate",
                "python manage.py seed_demo",
                "python manage.py runserver",
            ),
            pages=(("/", "the dashboard"), ("/invoices/", "the invoice list")),
        ),
    )
}

DEFAULT_STARTER = "public-site"
