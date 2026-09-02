"""``manage.py startsite`` tests (ADR-095, icvoss/django-brickwork#470).

The command emits a SECOND, standalone Django project (its own settings
module, INSTALLED_APPS, urlconf), which cannot be exercised in-process
alongside the pytest-django settings this suite already configured: Django's
app registry is populated exactly once per process. The command's own file
emission is tested in-process (call_command against a tmp_path, no second
Django needed for that part); actually RUNNING the emitted project (`manage.py
check`, then rendering its three pages and asserting real content, not just a
200) runs in a subprocess with PYTHONPATH pointed at this repo's own src/, the
same way an installed django-brickwork wheel would be importable. This is also
the more honest test of what ADR-095 promises: a genuinely standalone,
runnable project, not a fixture rendered through this suite's own Engine.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import call_command

from brickwork.management.commands import _startsite_payload as payload
from brickwork.services.brand_css import render_brand_css

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"


def _emit(target: Path) -> None:
    call_command("startsite", str(target))


# --- File emission (in-process) ---------------------------------------------


def test_emits_every_documented_file(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    _emit(target)

    expected = [
        "manage.py",
        "mysite/__init__.py",
        "mysite/settings.py",
        "mysite/urls.py",
        "mysite/wsgi.py",
        "pages/__init__.py",
        "pages/nav.py",
        "pages/views.py",
        "pages/templates/pages/landing.html",
        "pages/templates/pages/dashboard.html",
        "pages/templates/pages/docs_home.html",
        "static/pages/brand.css",
        "README.md",
    ]
    for relative in expected:
        path = target / relative
        assert path.is_file(), f"startsite did not emit {relative}"


def test_refuses_a_non_empty_target(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    (target / "existing.txt").write_text("already here", encoding="utf-8")

    with pytest.raises(Exception, match="not empty"):
        _emit(target)


def test_emitted_pages_never_start_with_the_ownership_comment(tmp_path: Path) -> None:
    """{% extends %} must be the first tag in a Django template.

    The banner is real content this test proves is present (not merely that
    the command runs); this test guards the ordering constraint that makes
    inserting it safe at all.
    """
    target = tmp_path / "proj"
    _emit(target)
    for name in ("landing.html", "dashboard.html", "docs_home.html"):
        text = (target / "pages" / "templates" / "pages" / name).read_text(encoding="utf-8")
        first_line = text.splitlines()[0]
        assert first_line.startswith("{% extends "), f"{name} must open with extends, got {first_line!r}"
        assert "emitted by `manage.py startsite`" in text


def test_emitted_pages_link_the_brand_stylesheet_after_brickworks_own(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    _emit(target)
    for name in ("landing.html", "dashboard.html", "docs_home.html"):
        text = (target / "pages" / "templates" / "pages" / name).read_text(encoding="utf-8")
        assert "{% block head_extra %}" in text
        assert "{{ block.super }}" in text
        assert "pages/brand.css" in text


def test_nav_config_uses_only_registered_icon_names() -> None:
    """A regression pin: NAV_PY's icons must be real registry names.

    An unregistered icon name does not fail until the nav actually renders
    (bw_nav's IconNotFoundError), which the subprocess render test below
    also proves; this test pins the failure to the exact source so a future
    edit to NAV_PY that reintroduces a typo fails fast, without needing a
    full subprocess run.
    """
    from brickwork.icons import ICON_NAMES

    for line in payload.NAV_PY.splitlines():
        if 'icon="' not in line:
            continue
        icon_name = line.split('icon="', 1)[1].split('"', 1)[0]
        assert icon_name in ICON_NAMES, f"{icon_name!r} in the emitted nav.py is not a registered brickwork icon"


# --- Brand file contrast (in-process, real render_brand_css) ---------------


def test_brand_css_fg_on_accent_is_contrast_valid() -> None:
    """The literal placeholder tokens pass brickwork's own contrast check.

    render_brand_css(validate=True) raises BrandValidationError on a
    fg-on-accent pairing under 4.5:1 (docs/BRANDING.md, brickwork#35). This
    call is the same one the command itself makes when emitting brand.css;
    calling it directly here proves the LITERAL values in
    _startsite_payload.py stay valid as a standalone, fast assertion, not
    just as a side effect of the command succeeding.
    """
    css = render_brand_css(payload.LIGHT_TOKENS, payload.DARK_TOKENS, validate=True)
    assert "--bw-color-fg-on-accent: oklch(0.99 0 0);" in css  # light: white on the dark aubergine-ish accent
    assert '[data-theme="dark"]' in css


def test_brand_css_light_and_dark_fg_on_accent_differ() -> None:
    """The fg-on-accent flip (brickwork#35): copying the light value into dark
    is the documented trap this file exists to defuse for a new consumer."""
    assert payload.LIGHT_TOKENS["--bw-color-fg-on-accent"] != payload.DARK_TOKENS["--bw-color-fg-on-accent"]


def test_emitted_brand_css_file_matches_the_validated_render(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    _emit(target)
    written = (target / "static" / "pages" / "brand.css").read_text(encoding="utf-8")
    assert "--bw-color-fg-on-accent" in written
    assert ":root {" in written
    assert '[data-theme="dark"]' in written


# --- The emitted project actually runs (subprocess, real Django app registry) -


def _run_in_emitted_project(target: Path, code: str) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    full_env["PYTHONPATH"] = str(_SRC)
    full_env["DJANGO_SETTINGS_MODULE"] = "mysite.settings"
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        cwd=target,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def emitted_project(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    _emit(target)
    return target


def test_emitted_project_passes_manage_py_check(emitted_project: Path) -> None:
    full_env = dict(os.environ)
    full_env["PYTHONPATH"] = str(_SRC)
    # pytest-django sets DJANGO_SETTINGS_MODULE=tests.settings as a process
    # env var for the whole session, which would otherwise leak into this
    # subprocess and defeat manage.py's own setdefault("mysite.settings"):
    # os.environ.setdefault is a no-op when the key is already present.
    full_env["DJANGO_SETTINGS_MODULE"] = "mysite.settings"
    result = subprocess.run(  # noqa: S603
        [sys.executable, "manage.py", "check"],
        cwd=emitted_project,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # brickwork.W001 (the missing-theme-context-processor warning) must not
    # fire: that is the exact silent-empty-shell trap ADR-095 exists to close.
    assert "brickwork.W001" not in result.stdout
    assert "brickwork.W001" not in result.stderr


def test_emitted_project_renders_three_non_empty_pages(emitted_project: Path) -> None:
    code = """
import django, json
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ["testserver"]
from django.test import Client
c = Client()
results = {}
for path in ["/", "/app/", "/docs/"]:
    r = c.get(path)
    results[path] = {"status": r.status_code, "body": r.content.decode()}
print(json.dumps(results))
"""
    result = _run_in_emitted_project(emitted_project, code)
    assert result.returncode == 0, result.stdout + result.stderr
    results = json.loads(result.stdout.strip().splitlines()[-1])

    landing = results["/"]
    assert landing["status"] == 200
    assert "Northwind" in landing["body"]
    assert "Invoicing that chases itself" in landing["body"]
    assert "Acme" in landing["body"]  # a real logo, not an empty logo cloud

    dashboard = results["/app/"]
    assert dashboard["status"] == 200
    assert "Revenue" in dashboard["body"]
    assert "Quarterly report" in dashboard["body"]  # a real activity row, not an empty table
    assert 'aria-current="page"' in dashboard["body"]  # nav_active actually resolved

    docs = results["/docs/"]
    assert docs["status"] == 200
    assert "Getting started" in docs["body"]  # the has_published_docs=True branch, not the empty state
    assert "Nothing published yet" not in docs["body"]  # the empty-state branch must NOT have rendered


def test_emitted_project_pages_link_both_stylesheets_in_order(emitted_project: Path) -> None:
    code = """
import django, json
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ["testserver"]
from django.test import Client
c = Client()
r = c.get("/")
body = r.content.decode()
print(json.dumps({
    "brickwork_index": body.find("brickwork.css"),
    "brand_index": body.find("brand.css"),
}))
"""
    result = _run_in_emitted_project(emitted_project, code)
    assert result.returncode == 0, result.stdout + result.stderr
    payload_json = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload_json["brickwork_index"] != -1
    assert payload_json["brand_index"] != -1
    # Load order is load-bearing (docs/BRANDING.md): brand.css must load
    # AFTER brickwork.css, or its token overrides lose the cascade.
    assert payload_json["brickwork_index"] < payload_json["brand_index"]
