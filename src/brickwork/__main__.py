"""``python -m brickwork``: run brickwork's project-free commands.

The clean-directory entry point. ``manage.py startsite`` needs a Django project
to run in, which a new consumer with an empty directory does not have yet, and
building one only to have somewhere to run the command that builds one is the
step this module removes::

    pip install django-brickwork
    python -m brickwork startsite mysite
    cd mysite && python manage.py runserver

Only ``startsite`` is exposed. It writes files and reads no models, so it needs
nothing from Django except a configured app registry that can find the command;
this module supplies exactly that (``brickwork`` as the one installed app) and
no more. It never reads or writes the caller's own settings: if
``DJANGO_SETTINGS_MODULE`` is set in the environment it is ignored here.

The emitted project is a plain, owned copy (ADR-095): nothing it contains
imports this module or reaches back to it.
"""

from __future__ import annotations

import sys

USAGE = (
    "usage: python -m brickwork startsite [--starter {public-site,data-app}] DIRECTORY\n"
    "\n"
    "Emit a minimal, running Django project wired for brickwork into an empty directory.\n"
    "Run `python -m brickwork startsite --help` for the starters and options."
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "startsite":
        print(USAGE, file=sys.stderr)
        return 2

    from django.conf import settings
    from django.core.management import execute_from_command_line

    if not settings.configured:
        settings.configure(INSTALLED_APPS=["brickwork"], USE_TZ=True)
    execute_from_command_line(["python -m brickwork", *args])
    return 0


if __name__ == "__main__":
    sys.exit(main())
