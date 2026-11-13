"""``startsite`` tests (ADR-095, icvoss/django-brickwork#470).

The command emits a SECOND, standalone Django project (its own settings
module, INSTALLED_APPS, urlconf), which cannot be exercised in-process
alongside the pytest-django settings this suite already configured: Django's
app registry is populated exactly once per process. The command's own file
emission is tested in-process (call_command against a tmp_path, no second
Django needed for that part); actually RUNNING an emitted project (`manage.py
check`, then rendering its pages and asserting real content, not just a 200)
runs in a subprocess with PYTHONPATH pointed at this repo's own src/, the same
way an installed django-brickwork wheel would be importable. This is also the
more honest test of what ADR-095 promises: a genuinely standalone, runnable
project, not a fixture rendered through this suite's own Engine.

Two starters are covered (``public-site`` and ``data-app``), and so is the
clean-directory entry point, ``python -m brickwork startsite``, which has to
work with no Django project of any kind present.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from brickwork.management.commands import _startsite_data_app as data_app
from brickwork.management.commands import _startsite_payload as payload
from brickwork.management.commands import _startsite_public_site as public_site
from brickwork.management.commands._startsite_starters import DEFAULT_STARTER, STARTERS
from brickwork.services.brand_css import render_brand_css

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"

_COMMON_FILES = [
    "manage.py",
    ".gitignore",
    "requirements.txt",
    "README.md",
    "mysite/__init__.py",
    "mysite/settings.py",
    "mysite/urls.py",
    "mysite/wsgi.py",
    "static/brand.css",
]
_EXPECTED_FILES = {
    "public-site": [
        *_COMMON_FILES,
        "pages/__init__.py",
        "pages/nav.py",
        "pages/views.py",
        "pages/templates/pages/landing.html",
        "pages/templates/pages/docs_home.html",
    ],
    "data-app": [
        *_COMMON_FILES,
        "invoices/__init__.py",
        "invoices/models.py",
        "invoices/forms.py",
        "invoices/nav.py",
        "invoices/views.py",
        "invoices/migrations/__init__.py",
        "invoices/migrations/0001_initial.py",
        "invoices/management/__init__.py",
        "invoices/management/commands/__init__.py",
        "invoices/management/commands/seed_demo.py",
        "invoices/templates/invoices/dashboard.html",
        "invoices/templates/invoices/list.html",
    ],
}
_PAGE_TEMPLATES = {
    "public-site": ["pages/templates/pages/landing.html", "pages/templates/pages/docs_home.html"],
    "data-app": ["invoices/templates/invoices/dashboard.html", "invoices/templates/invoices/list.html"],
}
_starters = pytest.mark.parametrize("starter", sorted(STARTERS))


def _emit(target: Path, starter: str | None = None) -> None:
    if starter is None:
        call_command("startsite", str(target))
    else:
        call_command("startsite", str(target), starter=starter)


# --- File emission (in-process) ---------------------------------------------


def test_exactly_two_starters_are_offered() -> None:
    assert sorted(STARTERS) == ["data-app", "public-site"]
    assert DEFAULT_STARTER in STARTERS


@_starters
def test_emits_every_documented_file(tmp_path: Path, starter: str) -> None:
    target = tmp_path / "proj"
    _emit(target, starter)

    for relative in _EXPECTED_FILES[starter]:
        assert (target / relative).is_file(), f"startsite --starter {starter} did not emit {relative}"
    emitted = {str(p.relative_to(target)) for p in target.rglob("*") if p.is_file()}
    assert emitted == set(_EXPECTED_FILES[starter]), "startsite emitted files the test does not document"


@_starters
def test_emitted_requirements_pin_the_brickwork_that_wrote_them(tmp_path: Path, starter: str) -> None:
    """A clean-directory project must record its one dependency, or `pip install -r` has nothing to install."""
    import brickwork

    target = tmp_path / "proj"
    _emit(target, starter)
    lines = (target / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert f"django-brickwork=={brickwork.__version__}" in lines


def test_default_starter_is_the_public_site(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    _emit(target)
    assert (target / "pages" / "views.py").is_file()
    assert not (target / "invoices").exists()


def test_unknown_starter_is_rejected_before_any_write(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    with pytest.raises(CommandError, match="Unknown starter"):
        _emit(target, "blog")
    assert not target.exists()


def test_unknown_starter_on_the_command_line_exits_with_a_usage_error(tmp_path: Path) -> None:
    result = _run(["-m", "brickwork", "startsite", "--starter", "blog", "site"], tmp_path)
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert not (tmp_path / "site").exists()


@_starters
def test_refuses_a_non_empty_target(tmp_path: Path, starter: str) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    (target / "existing.txt").write_text("already here", encoding="utf-8")

    with pytest.raises(CommandError, match="not empty"):
        _emit(target, starter)
    assert [p.name for p in target.iterdir()] == ["existing.txt"], "a refused run must not write anything"


def test_accepts_an_existing_empty_directory(tmp_path: Path) -> None:
    """The clean-directory path: `mkdir mysite && cd mysite && ... startsite .` must work."""
    target = tmp_path / "proj"
    target.mkdir()
    _emit(target, "data-app")
    assert (target / "manage.py").is_file()


@pytest.mark.parametrize("entry", [".venv", "venv", ".git"])
def test_a_fresh_virtualenv_or_repository_does_not_make_the_directory_non_empty(tmp_path: Path, entry: str) -> None:
    """`mkdir mysite && cd mysite && python -m venv .venv && ... startsite .` is the documented path."""
    target = tmp_path / "proj"
    (target / entry).mkdir(parents=True)
    (target / entry / "marker").write_text("not ours", encoding="utf-8")
    _emit(target, "public-site")
    assert (target / "manage.py").is_file()
    assert (target / entry / "marker").read_text(encoding="utf-8") == "not ours"


@_starters
def test_emitted_pages_never_start_with_the_ownership_comment(tmp_path: Path, starter: str) -> None:
    """{% extends %} must be the first tag in a Django template.

    The banner is real content this test proves is present (not merely that
    the command runs); this test guards the ordering constraint that makes
    inserting it safe at all.
    """
    target = tmp_path / "proj"
    _emit(target, starter)
    for relative in _PAGE_TEMPLATES[starter]:
        text = (target / relative).read_text(encoding="utf-8")
        first_line = text.splitlines()[0]
        assert first_line.startswith("{% extends "), f"{relative} must open with extends, got {first_line!r}"
        assert "emitted by `manage.py startsite`" in text


@_starters
def test_emitted_pages_link_the_brand_stylesheet_after_brickworks_own(tmp_path: Path, starter: str) -> None:
    target = tmp_path / "proj"
    _emit(target, starter)
    for relative in _PAGE_TEMPLATES[starter]:
        text = (target / relative).read_text(encoding="utf-8")
        assert "{% block head_extra %}" in text
        assert "{{ block.super }}" in text
        assert "{% static 'brand.css' %}" in text


def test_data_app_drops_the_examples_buttons_that_point_nowhere(tmp_path: Path) -> None:
    """The examples hard-code a "New invoice" and an "Export" button to URLs the starter has no view for."""
    target = tmp_path / "proj"
    _emit(target, "data-app")
    for relative in _PAGE_TEMPLATES["data-app"]:
        text = (target / relative).read_text(encoding="utf-8")
        assert "{% block page_actions %}" not in text
        assert "/invoices/new/" not in text
        assert "/reports/export/" not in text
    # The list's filter bar is a plain GET form: this project loads no htmx.
    assert 'hx_get="' not in (target / "invoices/templates/invoices/list.html").read_text(encoding="utf-8")


def test_nav_configs_use_only_registered_icon_names() -> None:
    """A regression pin: every NAV_PY's icons must be real registry names.

    An unregistered icon name does not fail until the nav actually renders
    (bw_nav's IconNotFoundError), which the subprocess render tests below
    also prove; this test pins the failure to the exact source so a future
    edit to a NAV_PY that reintroduces a typo fails fast, without needing a
    full subprocess run.
    """
    from brickwork.icons import ICON_NAMES

    for nav_py in (public_site.NAV_PY, data_app.NAV_PY):
        icons = re.findall(r'icon="([^"]+)"', nav_py)
        assert icons, "a starter nav with no icons would make this test vacuous"
        for icon_name in icons:
            assert icon_name in ICON_NAMES, f"{icon_name!r} in an emitted nav.py is not a registered brickwork icon"


def test_only_the_public_site_installs_the_marketing_kit() -> None:
    """ADR-055: the marketing kit is opt-in, so a starter with no marketing page must not install it."""
    assert '"brickwork.marketing"' in payload.settings_py(app="pages", marketing=True)
    assert '"brickwork.marketing"' not in payload.settings_py(app="invoices", marketing=False)


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


@_starters
def test_emitted_brand_css_file_matches_the_validated_render(tmp_path: Path, starter: str) -> None:
    target = tmp_path / "proj"
    _emit(target, starter)
    written = (target / "static" / "brand.css").read_text(encoding="utf-8")
    assert "--bw-color-fg-on-accent" in written
    assert ":root {" in written
    assert '[data-theme="dark"]' in written


# --- Subprocess helpers (a real, separate Django process) ------------------


def _env(**extra: str) -> dict[str, str]:
    """A clean environment for a subprocess that must not inherit this suite's settings.

    pytest-django sets DJANGO_SETTINGS_MODULE=tests.settings as a process env
    var for the whole session, which would otherwise leak into a subprocess and
    defeat the emitted manage.py's own setdefault("mysite.settings"):
    os.environ.setdefault is a no-op when the key is already present.
    """
    env = dict(os.environ)
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env["PYTHONPATH"] = str(_SRC)
    env.update(extra)
    return env


def _run(args: list[str], cwd: Path, **extra_env: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, *args],
        cwd=cwd,
        env=_env(**extra_env),
        capture_output=True,
        text=True,
        timeout=120,
    )


_FETCH = """
import django, json, sys
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ["testserver"]
from django.test import Client
c = Client()
results = {}
for path in sys.argv[1:]:
    r = c.get(path)
    results[path] = {"status": r.status_code, "body": r.content.decode()}
print(json.dumps(results))
"""


def _fetch(target: Path, *paths: str) -> dict[str, dict]:
    result = _run(
        ["-c", _FETCH, *paths],
        target,
        DJANGO_SETTINGS_MODULE="mysite.settings",
        PYTHONPATH=f"{target}{os.pathsep}{_SRC}",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def _manage(target: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["manage.py", *args], target)


@pytest.fixture(params=sorted(STARTERS))
def any_emitted_project(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    _emit(target, request.param)
    if request.param == "data-app":
        migrate = _manage(target, "migrate", "--verbosity", "0")
        assert migrate.returncode == 0, migrate.stdout + migrate.stderr
    return target


@pytest.fixture
def public_site_project(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    _emit(target, "public-site")
    return target


@pytest.fixture
def data_app_project(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    _emit(target, "data-app")
    migrate = _manage(target, "migrate", "--verbosity", "0")
    assert migrate.returncode == 0, migrate.stdout + migrate.stderr
    return target


# --- The clean-directory path (python -m brickwork, no project present) ----


def test_clean_directory_path_needs_no_django_project(tmp_path: Path) -> None:
    """`pip install django-brickwork` then `python -m brickwork startsite`, in an empty directory.

    No settings module, no manage.py, no INSTALLED_APPS: this is the state a new
    consumer is in. A stray DJANGO_SETTINGS_MODULE pointing at nothing is set on
    purpose, to prove the entry point does not read the caller's settings.
    """
    workdir = tmp_path / "empty"
    workdir.mkdir()
    result = _run(
        ["-m", "brickwork", "startsite", "--starter", "data-app", "site"],
        workdir,
        DJANGO_SETTINGS_MODULE="does.not.exist",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (workdir / "site" / "manage.py").is_file()
    assert (workdir / "site" / "invoices" / "models.py").is_file()
    assert "python manage.py migrate" in result.stdout
    assert "python manage.py runserver" in result.stdout


def test_clean_directory_path_can_emit_into_the_current_directory(tmp_path: Path) -> None:
    workdir = tmp_path / "empty"
    workdir.mkdir()
    result = _run(["-m", "brickwork", "startsite", "."], workdir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (workdir / "manage.py").is_file()
    assert (workdir / "pages" / "views.py").is_file(), "the default starter is public-site"


def test_clean_directory_path_refuses_a_non_empty_directory(tmp_path: Path) -> None:
    workdir = tmp_path / "occupied"
    workdir.mkdir()
    (workdir / "notes.txt").write_text("mine", encoding="utf-8")
    result = _run(["-m", "brickwork", "startsite", "."], workdir)
    assert result.returncode != 0
    assert "not empty" in result.stderr
    assert [p.name for p in workdir.iterdir()] == ["notes.txt"]


@pytest.mark.parametrize("args", [[], ["migrate"], ["--help"]])
def test_module_entry_point_only_exposes_startsite(tmp_path: Path, args: list[str]) -> None:
    result = _run(["-m", "brickwork", *args], tmp_path)
    assert result.returncode == 2
    assert "startsite" in result.stderr


def test_module_entry_point_lists_both_starters_in_help(tmp_path: Path) -> None:
    result = _run(["-m", "brickwork", "startsite", "--help"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "public-site" in result.stdout
    assert "data-app" in result.stdout


# --- The emitted projects actually run (subprocess, real Django app registry) -


def test_emitted_project_passes_manage_py_check(any_emitted_project: Path) -> None:
    result = _manage(any_emitted_project, "check")
    assert result.returncode == 0, result.stdout + result.stderr
    # brickwork.W001 (the missing-theme-context-processor warning) must not
    # fire: that is the exact silent-empty-shell trap ADR-095 exists to close.
    assert "brickwork.W001" not in result.stdout
    assert "brickwork.W001" not in result.stderr


def test_public_site_renders_two_non_empty_pages(public_site_project: Path) -> None:
    results = _fetch(public_site_project, "/", "/docs/")

    landing = results["/"]
    assert landing["status"] == 200
    assert "Northwind" in landing["body"]
    assert "Invoicing that chases itself" in landing["body"]
    assert "Acme" in landing["body"]  # a real logo, not an empty logo cloud

    docs = results["/docs/"]
    assert docs["status"] == 200
    assert "Getting started" in docs["body"]  # the has_published_docs=True branch, not the empty state
    assert "Nothing published yet" not in docs["body"]  # the empty-state branch must NOT have rendered
    assert 'aria-current="page"' in docs["body"]  # nav_active actually resolved


def test_public_site_has_no_database_to_migrate(public_site_project: Path) -> None:
    settings_text = (public_site_project / "mysite" / "settings.py").read_text(encoding="utf-8")
    assert '"pages",' in settings_text
    assert "invoices" not in settings_text
    assert not list(public_site_project.rglob("models.py"))


def test_data_app_has_no_missing_migrations(data_app_project: Path) -> None:
    """The hand-written 0001 must match the model exactly, or the first `makemigrations` surprises the user."""
    result = _manage(data_app_project, "makemigrations", "--check", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr


def test_data_app_renders_honest_empty_states_before_seeding(data_app_project: Path) -> None:
    results = _fetch(data_app_project, "/", "/invoices/")

    dashboard = results["/"]
    assert dashboard["status"] == 200
    assert "Paid revenue" in dashboard["body"]
    assert "No accounts yet" in dashboard["body"]  # the ranked list's empty branch, from a real empty query
    assert "Nothing yet" in dashboard["body"]  # the activity table's empty branch

    invoices = results["/invoices/"]
    assert invoices["status"] == 200
    assert "No invoices match these filters" in invoices["body"]


def test_data_app_seed_demo_populates_and_is_idempotent(data_app_project: Path) -> None:
    first = _manage(data_app_project, "seed_demo")
    assert first.returncode == 0, first.stdout + first.stderr
    assert "Created 36 example invoices" in first.stdout
    second = _manage(data_app_project, "seed_demo")
    assert second.returncode == 0, second.stdout + second.stderr
    assert "nothing seeded" in second.stdout


def test_data_app_pages_show_database_rows(data_app_project: Path) -> None:
    assert _manage(data_app_project, "seed_demo").returncode == 0
    results = _fetch(data_app_project, "/", "/invoices/")

    dashboard = results["/"]
    assert dashboard["status"] == 200
    assert "Paid revenue" in dashboard["body"]
    assert "prior 30 days" in dashboard["body"]
    assert "INV-1036" in dashboard["body"]  # the newest seeded invoice, in the recent-activity table
    assert "Dunmore Retail" in dashboard["body"]  # a seeded client, in the top-accounts list
    assert "Show revenue by week" in dashboard["body"]  # the chart's accessible data-table sibling
    assert 'aria-current="page"' in dashboard["body"]  # nav_active actually resolved

    invoices = results["/invoices/"]
    assert invoices["status"] == 200
    assert "INV-1036" in invoices["body"]
    assert "Page 1 of 4" in invoices["body"]  # 36 rows at 10 a page: pagination is real


def test_data_app_list_filters_sorts_and_paginates(data_app_project: Path) -> None:
    assert _manage(data_app_project, "seed_demo").returncode == 0
    results = _fetch(
        data_app_project,
        "/invoices/?status=overdue",
        "/invoices/?q=acme&status=paid&sort=amount",
        "/invoices/?page=2",
        "/invoices/?sort=not-a-field",
        "/invoices/?status=bogus",
        "/invoices/?page=999",
    )
    for path, response in results.items():
        assert response["status"] == 200, f"{path} answered {response['status']}"

    overdue = results["/invoices/?status=overdue"]["body"]
    assert "Overdue" in overdue
    assert "INV-1030" in overdue  # seeded overdue
    assert "INV-1036" not in overdue  # seeded draft: the status filter really filtered

    acme = results["/invoices/?q=acme&status=paid&sort=amount"]["body"]
    assert "Acme Corp" in acme
    assert "Dunmore Retail" not in acme  # the search really filtered
    amounts = [int(v.replace(",", "")) for v in re.findall(r"\u00a3([\d,]+)</td>", acme)]
    assert amounts == sorted(amounts), "sort=amount must be ascending"

    page_two = results["/invoices/?page=2"]["body"]
    assert "Page 2 of 4" in page_two
    assert "INV-1036" not in page_two  # newest row lives on page one

    # A hand-edited sort cannot name an arbitrary field, and bad input never 500s.
    assert "INV-1036" in results["/invoices/?sort=not-a-field"]["body"]
    assert "not one of the available choices" in results["/invoices/?status=bogus"]["body"]
    assert "Page 4 of 4" in results["/invoices/?page=999"]["body"]  # Paginator.get_page clamps


def test_emitted_project_pages_link_both_stylesheets_in_order(any_emitted_project: Path) -> None:
    body = _fetch(any_emitted_project, "/")["/"]["body"]
    brickwork_index = body.find("brickwork.css")
    brand_index = body.find("brand.css")
    assert brickwork_index != -1
    assert brand_index != -1
    # Load order is load-bearing (docs/BRANDING.md): brand.css must load
    # AFTER brickwork.css, or its token overrides lose the cascade.
    assert brickwork_index < brand_index


def test_a11y_fixture_generator_renders_every_emitted_page_in_both_themes(tmp_path: Path) -> None:
    """ADR-095's gate renders the emitted projects, rather than an Engine copy.

    This is deliberately a generator-level assertion, separate from the
    Playwright scan that consumes these fixtures: it proves the generator
    reaches every emitted URL of both starters through their own settings,
    URLconfs and views, produces both themes, and inlines the two stylesheets
    that make a file:// accessibility scan representative. A generator that
    skips a page, loses dark mode, or omits the emitted brand stylesheet fails
    here before the browser suite could give an empty or visually incomplete
    scan a pass.
    """
    from a11y.generate_startsite_fixtures import generate_fixtures

    written = generate_fixtures(tmp_path)

    assert {path.name for path in written} == {
        "public-site-landing-light.html",
        "public-site-landing-dark.html",
        "public-site-docs-home-light.html",
        "public-site-docs-home-dark.html",
        "data-app-dashboard-light.html",
        "data-app-dashboard-dark.html",
        "data-app-invoices-light.html",
        "data-app-invoices-dark.html",
    }
    expected_content = {
        "public-site-landing": "Northwind",
        "public-site-docs-home": "Getting started",
        "data-app-dashboard": "Paid revenue",
        "data-app-invoices": "INV-1036",  # seeded rows, so the table is scanned populated, not empty
    }
    for path in written:
        page, theme = path.stem.rsplit("-", 1)
        html = path.read_text(encoding="utf-8")
        assert f'data-theme="{theme}"' in html
        assert expected_content[page] in html
        assert not re.search(r'<link rel="stylesheet" href="/?static/(?:brickwork/dist/brickwork|brand)\.css">', html)
