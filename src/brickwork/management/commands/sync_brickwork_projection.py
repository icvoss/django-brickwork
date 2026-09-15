"""``manage.py sync_brickwork_projection``: vendor ``tailwind-theme.css``.

Brickwork Theme Phase F (icvoss/django-brickwork#601). Replaces the AgentPM-
style hand copy of the Tailwind ``@theme`` projection from site-packages
into a consumer Vite tree. Not dual npm; not a full Tailwind redistribute.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from brickwork.services.css_delivery import sync_tailwind_theme


class Command(BaseCommand):
    help = (
        "Copy the installed brickwork Tailwind projection "
        "(static/brickwork/dist/tailwind-theme.css) into a consumer frontend "
        "path so Vite can @import it. Re-run after bumping django-brickwork."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "destination",
            help=(
                "File path to write, relative to the current working directory "
                "(for example frontend/src/brickwork-theme.css)."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite even when the destination already matches.",
        )

    def handle(self, *args, **options) -> None:
        dest = Path(options["destination"])
        try:
            result = sync_tailwind_theme(dest, force=options["force"])
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        except OSError as exc:
            raise CommandError(f"could not write {dest}: {exc}") from exc

        if result.wrote:
            self.stdout.write(
                self.style.SUCCESS(f"Wrote {result.bytes_written} bytes to {result.destination} (from {result.source})")
            )
        else:
            self.stdout.write(f"Already up to date: {result.destination} (matches installed projection)")
