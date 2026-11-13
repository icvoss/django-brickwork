"""docs/QUICKSTART.md's documented paths work as written.

The quickstart makes two promises a reader acts on without reading any code:

* Path A: from an empty directory, ``python -m brickwork startsite`` emits a
  running project. That path is exercised end to end in ``test_startsite.py``;
  the test here pins the commands the document shows to the command that exists.
* Path B: on an existing project, the page's files, copied verbatim, give a
  working page with its context, nav and static brand stylesheet.

Path B is tested by extracting the fenced blocks from the document itself and
writing them into a project that Django's own ``startproject`` and ``startapp``
produced, so the document cannot drift from what runs: a renamed tag, kwarg or
template path that breaks the copy-paste path fails here, not for a reader.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from brickwork.management.commands._startsite_starters import STARTERS
from tests.test_startsite import _SRC, _run

_QUICKSTART = Path(__file__).resolve().parent.parent / "docs" / "QUICKSTART.md"

# **`path/to/file`** (optional note), a blank line, then a fenced block.
_FILE_BLOCK = re.compile(
    r"^\*\*`(?P<path>[^`]+)`\*\*[^\n]*\n\n```(?P<lang>\w+)\n(?P<code>.*?)\n```",
    re.DOTALL | re.MULTILINE,
)


def _section(heading: str) -> str:
    """The text of one ``## `` section of the quickstart, heading included."""
    text = _QUICKSTART.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(heading)}\n.*?(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert match, f"QUICKSTART.md has no '## {heading}' section"
    return match.group(0)


def test_path_a_documents_both_starters_and_the_clean_directory_command() -> None:
    section = _section("Path A: from an empty directory")
    assert "python -m brickwork startsite" in section
    for name in STARTERS:
        assert f"`{name}`" in section, f"Path A does not name the {name} starter"
    assert "--starter data-app" in section
    assert "python manage.py seed_demo" in section
    assert "django-admin startproject" in section, "Path A must say not to run startproject first"


def test_path_a_does_not_tell_the_reader_to_scaffold_before_startsite() -> None:
    """The old quickstart ran `django-admin startproject mysite .` then `startsite myproject`: two projects."""
    section = _section("Path A: from an empty directory")
    for line in section.splitlines():
        if line.startswith("django-admin startproject"):
            pytest.fail(f"Path A has a runnable startproject step: {line!r}")


def test_path_b_is_one_complete_integration_in_one_place() -> None:
    blocks = {m["path"]: m for m in _FILE_BLOCK.finditer(_section("Path B: an existing project, one complete page"))}
    assert set(blocks) == {
        "mysite/settings.py",  # settings: app, context processor, static dir
        "mysite/urls.py",  # URL
        "reports/views.py",  # view and context
        "reports/templates/reports/index.html",  # template
        "static/brand.css",  # static
    }


def test_path_b_files_as_written_produce_a_working_branded_page(tmp_path: Path) -> None:
    project = tmp_path / "site"
    project.mkdir()
    for command in (["startproject", "mysite", "."], ["startapp", "reports"]):
        made = _run(["-m", "django", *command], project)
        assert made.returncode == 0, made.stdout + made.stderr

    blocks = list(_FILE_BLOCK.finditer(_section("Path B: an existing project, one complete page")))
    assert len(blocks) == 5
    for block in blocks:
        path = project / block["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if block["path"] == "mysite/settings.py":
            # The document says "add to the bottom": append, never replace.
            with path.open("a", encoding="utf-8") as handle:
                handle.write("\n" + block["code"] + "\n")
        else:
            path.write_text(block["code"] + "\n", encoding="utf-8")

    env = {"DJANGO_SETTINGS_MODULE": "mysite.settings", "PYTHONPATH": f"{project}{os.pathsep}{_SRC}"}

    checked = _run(["manage.py", "check"], project)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "brickwork.W001" not in checked.stdout + checked.stderr

    fetch = """
import django, json
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ["testserver"]
from django.test import Client
response = Client().get("/reports/")
print(json.dumps({"status": response.status_code, "body": response.content.decode()}))
"""
    fetched = _run(["-c", fetch], project, **env)
    assert fetched.returncode == 0, fetched.stdout + fetched.stderr
    page = json.loads(fetched.stdout.strip().splitlines()[-1])
    body = page["body"]

    assert page["status"] == 200
    assert "Quarterly summary" in body  # the view's rows reached the table
    assert "Customer success" in body
    assert "Everything your team has published." in body  # the template's own header copy
    assert 'aria-current="page"' in body  # nav_active resolved against the request
    assert "Acme" in body  # the brand wordmark block

    # Static: both stylesheets linked, brand strictly after brickwork's own.
    assert -1 < body.find("brickwork.css") < body.find("brand.css")
    for static_name in ("brand.css", "brickwork/dist/brickwork.css"):
        found = _run(["manage.py", "findstatic", static_name], project)
        assert found.returncode == 0, found.stdout + found.stderr
        assert "No matching file found" not in found.stdout + found.stderr
