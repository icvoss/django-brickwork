"""Render ``manage.py startsite`` output into a11y fixtures.

ADR-095 requires the project emitted by ``manage.py startsite`` to clear the
same WCAG 2.2 AA gate as the package itself. This generator deliberately does
not render the copied templates through this repository's configured Django
engine. It emits a temporary project, then starts that project's settings in
a subprocess and requests each of its real URLs. That is the boundary a new
consumer receives: its own settings, URLconf, app registry, views and copied
templates.

The resulting files are self-contained ``file://`` fixtures. Both the shipped
brickwork stylesheet and the emitted project's brand stylesheet are inlined,
so Playwright measures the actual cascade without needing a development
server. Six fixtures are written: the landing, dashboard and docs pages in
both light and dark themes.

Run:
DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:.:tests \
    python a11y/generate_startsite_fixtures.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import django

django.setup()

from django.core.management import call_command  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "a11y" / "fixtures" / "startsite"
THEMES = ("light", "dark")
PAGES = {
    "landing": "/",
    "dashboard": "/app/",
    "docs-home": "/docs/",
}
_RENDER = """
import json
import sys

import django

django.setup()

from django.conf import settings
from django.test import Client

settings.ALLOWED_HOSTS = ["testserver"]
settings.BRICKWORK_DEFAULT_THEME = sys.argv[1]
response = Client().get(sys.argv[2])
print(json.dumps({"status": response.status_code, "body": response.content.decode()}))
"""
_BRICKWORK_CSS_LINK = re.compile(r'<link rel="stylesheet" href="/static/brickwork/dist/brickwork\.css">')
_BRAND_CSS_LINK = re.compile(r'<link rel="stylesheet" href="/static/pages/brand\.css">')


def _render_page(target: Path, theme: str, path: str) -> str:
    """Request one emitted-project route under ``theme`` and return its HTML.

    A non-200 response or output that did not carry the requested theme is a
    generator failure, not an empty fixture for Playwright to accidentally
    accept. The latter guard proves the dark fixture was rendered by the
    emitted project's context processor rather than copied from light.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["DJANGO_SETTINGS_MODULE"] = "mysite.settings"
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _RENDER, theme, path],
        cwd=target,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError(f"startsite render failed for {path} ({theme}): {result.stdout}{result.stderr}")
    payload = json.loads(result.stdout)
    if payload["status"] != 200:
        raise RuntimeError(f"startsite rendered {path} ({theme}) with status {payload['status']}")
    html = payload["body"]
    if f'data-theme="{theme}"' not in html:
        raise RuntimeError(f"startsite rendered {path} without data-theme={theme!r}")
    return html


def _inline_stylesheets(html: str, target: Path) -> str:
    """Inline the two stylesheets the emitted document actually links.

    Each replacement is required exactly once. A changed shell or emitted
    payload that drops either stylesheet fails generation instead of producing
    a visually unstyled fixture whose axe result would be misleading.
    """
    brickwork_css = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text(encoding="utf-8")
    brand_css = (target / "static/pages/brand.css").read_text(encoding="utf-8")
    html, brickwork_replacements = _BRICKWORK_CSS_LINK.subn(f"<style>{brickwork_css}</style>", html)
    html, brand_replacements = _BRAND_CSS_LINK.subn(f"<style>{brand_css}</style>", html)
    if brickwork_replacements != 1 or brand_replacements != 1:
        raise RuntimeError(
            "startsite fixture expected one brickwork.css and one brand.css link, "
            f"got brickwork={brickwork_replacements}, brand={brand_replacements}"
        )
    return html


def generate_fixtures(out: Path = OUT) -> list[Path]:
    """Emit and render every required startsite page and theme fixture."""
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="brickwork-startsite-") as temporary_directory:
        target = Path(temporary_directory) / "project"
        call_command("startsite", str(target))
        written = []
        for name, path in PAGES.items():
            for theme in THEMES:
                html = _inline_stylesheets(_render_page(target, theme, path), target)
                fixture = out / f"{name}-{theme}.html"
                fixture.write_text(html, encoding="utf-8")
                written.append(fixture)
    return written


def main() -> None:
    written = generate_fixtures()
    print(f"startsite fixtures written ({len(written)}): {', '.join(path.name for path in written)}")


if __name__ == "__main__":
    main()
