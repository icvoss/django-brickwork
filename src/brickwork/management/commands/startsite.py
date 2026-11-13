"""``startsite``: emit a minimal, running brickwork project.

ADR-095 (icvoss/django-brickwork#470). A new consumer following
docs/QUICKSTART.md reaches a structurally correct, visually empty page: the
marketing/app/docs shells expose ``{% block %}``\\ s, not context variables, so
a bare ``{% extends %}`` that fills nothing correctly renders nothing, and the
shipped CSS hides every unfilled region on purpose (the ``:empty`` guards).
This command closes that gap by emitting a small, complete project rather than
routing the consumer through thousands of lines of documentation.

Two ways to run it, one command:

* ``python -m brickwork startsite DIRECTORY`` from an empty directory, with
  nothing but ``pip install django-brickwork`` done. This is the clean-directory
  path: ``brickwork.__main__`` configures just enough Django to run this command
  without a project of its own, so there is no chicken-and-egg step of building
  a project first only to have somewhere to run the command that builds one.
* ``python manage.py startsite DIRECTORY`` inside a project that already lists
  ``brickwork`` in ``INSTALLED_APPS``. The result is a separate, standalone
  project in ``DIRECTORY``; it does not touch the project you ran it from.

Two starters, selected with ``--starter`` (ADR-095 section 4; each is a payload
in ``_startsite_starters.py``):

* ``public-site``: a public site with no database. A marketing landing page and
  a docs home, each with the view that feeds it.
* ``data-app``: a database-backed application. An ``invoices`` app with a model,
  a migration and a seed command, a dashboard whose figures are aggregates over
  it, and a filterable, sortable, paginated list.

Both emit settings wired for ``brickwork`` (plus ``brickwork.marketing`` where a
page needs it), the theme context processor, a brand token file carrying the
seven load-bearing tokens plus a contrast-verified ``--bw-color-fg-on-accent``,
and a nav config validated at import. Pages are copied from brickwork's own
shipped examples.

**The emitted output is not supported surface (ADR-095 section 3).** It is a
plain, owned copy from the moment it is written: no update command, no
re-run-to-upgrade path, no semver guarantee on anything this command writes.
The command itself, its name, its flags, its starter names and its exit
behaviour, is the governed surface; what it produces is a starting point.

Failure modes (icvoss/django-brickwork#492): a non-empty target directory
(``.git``, ``.venv`` and ``venv`` entries do not count, so a directory that holds
only a fresh virtual environment or repository is still empty for this purpose)
raises ``CommandError`` before any write, as does an unknown ``--starter``
(on the command line argparse rejects it first, with exit status 2). Filesystem failures during
emission (permission denied, read-only volume, disk full) propagate as the
underlying ``OSError`` subclass from ``Path.mkdir`` or ``Path.write_text``;
they are not caught or translated.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from brickwork.management.commands._startsite_starters import DEFAULT_STARTER, STARTERS

#: Entries that do not make a directory "not empty". A virtual environment and
#: a git repository are what a developer creates in a fresh project directory
#: before running this command, and none of them collides with anything it
#: emits, so refusing on them would make the documented clean-directory path
#: (`mkdir mysite && cd mysite && python -m venv .venv && ...`) fail on its
#: own second step.
_IGNORED_ENTRIES = frozenset({".git", ".venv", "venv"})


class Command(BaseCommand):
    help = (
        "Emit a minimal, running Django project wired for brickwork, from one of two "
        "starters: public-site (landing page and docs home, no database) or data-app "
        "(an invoices dashboard and list backed by a database). Runs from an empty "
        "directory with `python -m brickwork startsite DIRECTORY`, or inside an "
        "existing project with `manage.py startsite DIRECTORY`. The emitted project "
        "is yours outright from the moment it is written; this command does not "
        "upgrade or re-run against it later (ADR-095)."
    )

    # The command only writes files; it reads no models and no urlconf. Running
    # the project checks would also fail the clean-directory path, where there
    # is deliberately no project settings module to check.
    requires_system_checks: list[str] = []

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "directory",
            help="Directory to emit the project into. Created if it does not exist; refused if not empty.",
        )
        parser.add_argument(
            "--starter",
            choices=sorted(STARTERS),
            default=DEFAULT_STARTER,
            help="Which starter to emit (default: %(default)s). "
            + "; ".join(f"{name}: {starter.summary}" for name, starter in sorted(STARTERS.items())),
        )

    def handle(self, *args, **options) -> None:
        # argparse already rejects an unknown --starter on the command line;
        # call_command(starter=...) bypasses that, so check here too.
        if options["starter"] not in STARTERS:
            raise CommandError(f"Unknown starter {options['starter']!r}. Choose one of: {', '.join(sorted(STARTERS))}.")
        starter = STARTERS[options["starter"]]
        target = Path(options["directory"]).resolve()

        if target.exists() and any(entry.name not in _IGNORED_ENTRIES for entry in target.iterdir()):
            raise CommandError(
                f"{target} already exists and is not empty. startsite emits into an empty "
                f"directory (a .git, .venv or venv entry does not count); point it at a "
                f"fresh one, or clear this one first."
            )
        target.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for relative, content in starter.files().items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)

        (target / "manage.py").chmod(0o755)

        self.stdout.write(self.style.SUCCESS(f"Emitted the {starter.name} starter ({starter.summary}) into {target}"))
        for path in written:
            self.stdout.write(f"  {path.relative_to(target)}")
        self.stdout.write("")
        self.stdout.write("This project is yours outright: edit anything in it. Next steps:")
        self.stdout.write(f"  cd {target}")
        for command in starter.setup_commands:
            self.stdout.write(f"  {command}")
        self.stdout.write("")
        pages = ", ".join(f"{path} for {what}" for path, what in starter.pages)
        self.stdout.write(f"Then open http://127.0.0.1:8000/ : {pages}. See the emitted README.md.")
