"""``manage.py startsite``: emit a minimal, running, designed brickwork project.

ADR-095 (icvoss/django-brickwork#470). A new consumer following
docs/QUICKSTART.md reaches a structurally correct, visually empty page: the
marketing/app/docs shells expose ``{% block %}``\\ s, not context variables, so
a bare ``{% extends %}`` that fills nothing correctly renders nothing, and the
shipped CSS hides every unfilled region on purpose (the ``:empty`` guards).
This command closes that gap by emitting a small, complete project rather than
routing the consumer through 2,714 lines of documentation.

What it emits (ADR-095 section 4): settings wired for ``brickwork`` and
``brickwork.marketing``, static files, and the theme context processor; a
brand token file carrying the seven load-bearing tokens plus a contrast-
verified ``--bw-color-fg-on-accent`` per theme; a nav config validated at
import; and three real pages, each with the view that feeds it, copied from
brickwork's own shipped examples across three families (Product applications,
Documentation, Marketing and public web).

**The emitted output is not supported surface (ADR-095 section 3).** It is a
plain, owned copy from the moment it is written: no update command, no
re-run-to-upgrade path, no semver guarantee on anything this command writes.
The command itself, its name, its flags and its exit behaviour, is the
governed surface; what it produces is a starting point.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from brickwork.management.commands import _startsite_payload as payload


class Command(BaseCommand):
    help = (
        "Emit a minimal, running Django project wired for brickwork: settings, "
        "a brand token file, a validated nav config, and three real pages with "
        "the views that feed them. The emitted project is yours outright from "
        "the moment it is written; this command does not upgrade or re-run "
        "against it later (ADR-095)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "directory",
            help="Directory to emit the project into. Created if it does not exist; refused if not empty.",
        )

    def handle(self, *args, **options) -> None:
        target = Path(options["directory"]).resolve()

        if target.exists() and any(target.iterdir()):
            raise CommandError(
                f"{target} already exists and is not empty. startsite emits into an empty "
                f"directory; point it at a fresh one, or clear this one first."
            )
        target.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []

        def write(relative: str, content: str) -> None:
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)

        write("manage.py", payload.MANAGE_PY)
        write("mysite/__init__.py", "")
        write("mysite/settings.py", payload.SETTINGS_PY)
        write("mysite/urls.py", payload.URLS_PY)
        write("mysite/wsgi.py", payload.WSGI_PY)
        write("pages/__init__.py", "")
        write("pages/nav.py", payload.NAV_PY)
        write("pages/views.py", payload.VIEWS_PY)
        write("pages/templates/pages/landing.html", payload.landing_html())
        write("pages/templates/pages/dashboard.html", payload.dashboard_html())
        write("pages/templates/pages/docs_home.html", payload.docs_home_html())
        write("static/pages/brand.css", payload.brand_css())
        write("README.md", payload.README_MD)

        (target / "manage.py").chmod(0o755)

        self.stdout.write(self.style.SUCCESS(f"Emitted a brickwork starter project into {target}"))
        for path in written:
            self.stdout.write(f"  {path.relative_to(target)}")
        self.stdout.write("")
        self.stdout.write("This project is yours outright: edit anything in it. Next steps:")
        self.stdout.write(f"  cd {target}")
        self.stdout.write("  python manage.py runserver")
        self.stdout.write("")
        self.stdout.write("Then open http://127.0.0.1:8000/ for the landing page, /app/ for the")
        self.stdout.write("dashboard, and /docs/ for the docs home. See the emitted README.md.")
