"""Render every catalogue-manifest archetype to standalone HTML fixtures for
the W0.3 archetype-test harness (a11y/archetypes.spec.mjs).

This is a SEPARATE generator from a11y/generate_fixtures.py, deliberately: that
file is a hand-maintained enumeration of individual fixture calls, extended by
hand for every new surface since 0.8.0, which is exactly the "explicit list"
failure mode the interface-system delivery plan names as this repo's own
precedent for silent exclusion (a new page shipped, nobody added its fixture
call, the axe gate never saw it). Folding archetype coverage into that same
enumeration would inherit the same risk for archetypes specifically, the one
class of surface the plan is explicit must never regress that way again.

This script instead walks brickwork.services._catalogue_manifest.items_by_kind
("archetype") -- the SAME manifest the pytest harness
(tests/test_archetype_harness.py) discovers from -- and renders whatever that
returns, using the SAME render-context source both consumers share
(tests.test_examples._EXAMPLE_CONTEXTS). Adding a 17th archetype and
regenerating the manifest is the only step needed to enrol it in both the
pytest harness and this fixture set; nothing here is edited by hand per
archetype.

Fixtures land under a11y/fixtures/archetypes/, NOT directly in a11y/fixtures/:
a11y/axe.spec.mjs's own directory scan is non-recursive (readdirSync,
top-level .html only), so this subdirectory is invisible to that scan and
cannot collide with, double-count, or destabilise the hand-maintained fixture
set generate_fixtures.py already owns. a11y/archetypes.spec.mjs scans this
subdirectory on its own.

Run: DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:.:tests \
     python a11y/generate_archetype_fixtures.py
"""

from __future__ import annotations

import re
from pathlib import Path

import django

django.setup()

from django.template import Context  # noqa: E402
from tests.test_examples import _EXAMPLE_CONTEXTS, _example_engine  # noqa: E402

from brickwork.services._catalogue_manifest import items_by_kind  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text(encoding="utf-8")
OUT = Path(__file__).resolve().parent / "fixtures" / "archetypes"
OUT.mkdir(parents=True, exist_ok=True)

_STATIC_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*brickwork\.css">')

THEMES = ("light", "dark")


def _inline_css(html: str) -> str:
    """Replace the {% static %} stylesheet link with the compiled CSS inline,
    exactly as a11y/generate_fixtures.py's own _inline_css does, so this
    fixture is self-contained for a file:// load."""
    return _STATIC_LINK.sub(f"<style>{CSS}</style>", html)


def _slug(example_name: str) -> str:
    """ "app/list.html" -> "app-list"; the fixture filename stem, distinct from
    generate_fixtures.py's hand-chosen names by construction (this is derived,
    never hand-picked)."""
    return example_name.removesuffix(".html").replace("/", "-")


def discover_archetypes() -> dict[str, str]:
    """Every manifest archetype, keyed by its _EXAMPLE_CONTEXTS name.

    Mirrors tests/test_archetype_harness.py's own _manifest_archetype_names():
    the manifest names carry an "examples/" prefix, _EXAMPLE_CONTEXTS does
    not.
    """
    return {entry["name"].removeprefix("examples/"): entry["name"] for entry in items_by_kind("archetype")}


def render_archetype(example_name: str, theme: str) -> str:
    """Render one archetype through the real, sanctioned examples Engine
    (ADR-056: the only supported way to render an example), injecting bw_theme
    on top of its documented context. Raises KeyError, loudly, if
    example_name has no _EXAMPLE_CONTEXTS entry: this generator never skips an
    uncontexted archetype, matching the harness's own "fail loudly, not
    silently" contract.
    """
    context = dict(_EXAMPLE_CONTEXTS[example_name])
    context["bw_theme"] = theme
    template = _example_engine().get_template(example_name)
    html = template.render(Context(context))
    return _inline_css(html)


def main() -> None:
    archetypes = discover_archetypes()
    missing = sorted(name for name in archetypes if name not in _EXAMPLE_CONTEXTS)
    if missing:
        raise SystemExit(
            "the following catalogue-manifest archetypes have no "
            f"tests.test_examples._EXAMPLE_CONTEXTS entry: {missing}. "
            "Add a context entry (the render tests need it too) before fixtures "
            "can be generated for them."
        )

    written: list[str] = []
    for example_name in sorted(archetypes):
        slug = _slug(example_name)
        for theme in THEMES:
            html = render_archetype(example_name, theme)
            path = OUT / f"{slug}-{theme}.html"
            path.write_text(html, encoding="utf-8")
            written.append(path.name)

    print(f"archetype fixtures written ({len(written)}): {', '.join(written)}")


if __name__ == "__main__":
    main()
