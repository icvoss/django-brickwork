"""The archetype-test harness (W0.3 of the interface-system delivery plan).

Auto-discovers every full-page example (catalogue manifest ``kind ==
"archetype"``) and proves each one renders, at every theme, using exactly the
render-context source ``tests/test_examples.py`` already maintains
(``_EXAMPLE_CONTEXTS``), never a second, parallel context table. Reusing that
dict rather than re-deriving contexts is what keeps a new archetype's
enrolment honest: the same entry that makes ``test_examples.py`` render it
also makes this harness discover it, with no second place to remember to
update.

**Auto-discovery, not an explicit list.** The plan names the axe fixture
generator's own hand-maintained fixture list as this repo's precedent failure
mode for silent exclusion (``a11y/generate_fixtures.py``, extended by hand for
every new surface since 0.8.0). This harness never enumerates archetype names
itself: it reads ``items_by_kind("archetype")`` off the shipped catalogue
manifest (the sanctioned in-package reader,
``brickwork.services._catalogue_manifest``, W0.2) and walks whatever that
returns. Adding a 17th archetype under ``src/brickwork/examples/`` and
regenerating the manifest (``scripts/generate_catalogue_manifest.py``, already
drift-tested by ``tests/test_catalogue_manifest.py``) is the only step that
enrols it here; no edit to this file is needed.

**Missing context fails loudly, it does not skip.** If a new archetype ships
with no matching ``_EXAMPLE_CONTEXTS`` entry, ``test_every_archetype_has_a_
render_context_entry`` fails by name, immediately: the harness never lets an
uncontexted archetype fall through render-untested (which a ``pytest.skip``
or a ``try/except`` around the render call would do). The render tests below
also depend on that entry existing (a ``KeyError`` there is a second, blunter
failure signal for the same root cause), so the named assertion exists purely
to give CI an actionable, specific failure rather than a raw traceback.

**The reverse direction is checked too**: a ``_EXAMPLE_CONTEXTS`` entry with
no matching manifest archetype would mean the manifest itself has drifted
from the examples tree, already caught by
``tests/test_catalogue_manifest.py``'s byte-for-byte regeneration test; this
harness re-asserts the same invariant from the archetype-name-set angle,
which is the shape this file's own consumers care about.

Width source (ADR-079 section 6, ratified as the authoritative supported-width
matrix W0.3 consumes): the four ``--bw-breakpoint-*`` tokens are read directly
off the SHIPPED, built ``tokens.css``, never hardcoded here or duplicated from
the ADR's prose. ``a11y/generate_archetype_fixtures.py`` and
``a11y/archetypes.spec.mjs`` read the same file for the same reason: one
source, so a future token-value change (a rebuild) is picked up everywhere
without a second edit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.template import Context

from brickwork.services._catalogue_manifest import items_by_kind
from tests.test_examples import _EXAMPLE_CONTEXTS, _example_engine

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TOKENS_CSS = _REPO_ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "tokens.css"

# Both themes get the full render + width sweep, matching axe.spec.mjs's own
# THEMES list: a dark-only regression must fail this harness too.
THEMES = ("light", "dark")

# The four named breakpoint tokens ADR-079 emits; used only to assert their
# presence and shape here (never their literal values, which are read live in
# test_width_matrix_resolves_from_the_shipped_breakpoint_tokens below rather
# than copied into a second constant that could drift from tokens.css).
_BREAKPOINT_NAMES = ("sm", "md", "lg", "xl")


def _manifest_archetype_names() -> dict[str, str]:
    """Every manifest archetype, keyed by its ``_EXAMPLE_CONTEXTS`` name.

    The manifest names archetypes with an ``examples/`` prefix
    (``"examples/app/list.html"``); ``_EXAMPLE_CONTEXTS`` and
    ``brickwork.examples.list_examples()`` both use the bare, examples-root-
    relative form (``"app/list.html"``). Stripping the prefix here is the one
    translation step between the two sanctioned sources (the manifest for
    WHICH archetypes exist, ``_EXAMPLE_CONTEXTS`` for HOW to render one), so
    every other test in this module can key off a single dict without
    repeating the prefix strip.

    Returns a dict rather than a set/list so a failure can report both the
    example-relative name a test parametrizes on AND the manifest's own
    ``name`` field a maintainer would grep for.
    """
    return {entry["name"].removeprefix("examples/"): entry["name"] for entry in items_by_kind("archetype")}


def _read_breakpoint_tokens() -> dict[str, str]:
    """Parse ``--bw-breakpoint-<name>: <value>;`` straight out of the shipped
    ``tokens.css``. This is the single source every width-driven check in this
    harness (and the fixture generator, and the Playwright spec) resolves
    from: ADR-079 ships these as literal values on ``:root`` specifically
    because a viewport media query cannot resolve a ``var()``, so reading the
    literal here is not a workaround, it is the documented mechanism.
    """
    css = _TOKENS_CSS.read_text(encoding="utf-8")
    return dict(re.findall(r"--bw-breakpoint-(sm|md|lg|xl):\s*([0-9.]+rem);", css))


# ---------------------------------------------------------------------------
# 1. Auto-discovery: the manifest and _EXAMPLE_CONTEXTS agree on which
#    archetypes exist, in both directions.
# ---------------------------------------------------------------------------


def test_every_archetype_has_a_render_context_entry() -> None:
    """A new archetype with no _EXAMPLE_CONTEXTS entry fails here, by name,
    rather than being silently skipped by this harness or by test_examples.py.

    This is the harness's own enrolment gate: it is what makes "zero harness
    edits to add an archetype" honest rather than "zero edits, silently
    untested" (the exact trap the plan names the axe fixture generator's
    explicit list as precedent for).
    """
    manifest_names = _manifest_archetype_names()
    missing = sorted(name for name in manifest_names if name not in _EXAMPLE_CONTEXTS)
    assert not missing, (
        "the following catalogue-manifest archetypes have no tests.test_examples."
        f"_EXAMPLE_CONTEXTS entry, so the archetype harness cannot render them: {missing}. "
        "Add a context entry in tests/test_examples.py's _EXAMPLE_CONTEXTS (the same "
        "one the render tests use) alongside the new example."
    )


def test_every_render_context_entry_is_a_known_archetype_or_section() -> None:
    """The reverse direction: an _EXAMPLE_CONTEXTS entry with no matching
    manifest item would mean the manifest has drifted from the examples tree.
    tests/test_catalogue_manifest.py's byte-for-byte regeneration test already
    guards this from the manifest side; this re-asserts it from the name-set
    this harness itself depends on.
    """
    from tests.test_examples import _SECTION_CONTEXTS

    known_examples = {entry["name"].removeprefix("examples/") for entry in items_by_kind("archetype")}
    known_examples |= {entry["name"].removeprefix("examples/") for entry in items_by_kind("section")}
    stray = sorted(set(_EXAMPLE_CONTEXTS) | set(_SECTION_CONTEXTS))
    unknown = [name for name in stray if name not in known_examples]
    assert not unknown, (
        f"_EXAMPLE_CONTEXTS/_SECTION_CONTEXTS carries entries with no matching "
        f"catalogue-manifest item: {unknown}. Regenerate the manifest "
        "(scripts/generate_catalogue_manifest.py) or check for a stale entry."
    )


def test_the_manifest_reports_sixteen_archetypes() -> None:
    """Pins the Wave 0 baseline (docs/CATALOGUE.md section 5) so a silent drop
    in manifest coverage (a generator bug, a deleted example file) fails here
    too, not only in tests/test_catalogue_manifest.py."""
    assert len(items_by_kind("archetype")) == 16


# ---------------------------------------------------------------------------
# 2. Render gate: every archetype renders, in both themes, from the shared
#    context source.
# ---------------------------------------------------------------------------


def _archetype_ids() -> list[str]:
    return sorted(_manifest_archetype_names())


@pytest.mark.parametrize("name", _archetype_ids())
@pytest.mark.parametrize("theme", THEMES)
def test_every_archetype_renders_in_both_themes(theme: str, name: str) -> None:
    """The render-succeeds gate, per archetype per theme (plan W0.3's first
    named gate). Reuses the exact engine test_examples.py itself uses
    (_example_engine(): a standalone Engine pointed at the examples root,
    the only supported way to render one, ADR-056) so a rendering failure
    here is the same failure a consumer copying the file would hit.
    """
    context = dict(_EXAMPLE_CONTEXTS[name])
    context["bw_theme"] = theme
    template = _example_engine().get_template(name)
    html = template.render(Context(context))

    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert f'data-theme="{theme}"' in html, (
        f"{name} did not honour bw_theme={theme!r} on its root <html> element; "
        "the archetype-harness theme sweep depends on the two themes being "
        "genuinely distinguishable in the rendered markup."
    )


@pytest.mark.parametrize("name", _archetype_ids())
@pytest.mark.parametrize("theme", THEMES)
def test_every_archetype_leaves_no_unresolved_template_variable(theme: str, name: str) -> None:
    """Mirrors test_examples.py's own leak check, swept per theme: a context
    key that only test_examples.py's own (untimed) context happens to satisfy
    would otherwise pass there and still leak a stray {{ }} once bw_theme is
    injected on top, which is new input this harness adds that the sibling
    test never exercises."""
    context = dict(_EXAMPLE_CONTEXTS[name])
    context["bw_theme"] = theme
    template = _example_engine().get_template(name)
    html = template.render(Context(context))
    assert "{{" not in html
    assert "{%" not in html


@pytest.mark.parametrize("name", _archetype_ids())
def test_light_and_dark_renders_are_distinct(name: str) -> None:
    """The two themes must produce visibly distinct output (plan W0.3's
    'both themes produce distinct output' gate, the render-level half of it:
    a11y/archetypes.spec.mjs asserts the browser-computed-style half over the
    generated fixtures). A byte-identical light/dark render would mean
    data-theme was never actually wired through to anything, which the
    dedicated a11y fixture check cannot distinguish from "themed correctly but
    happens to look the same" without the source HTML differing first.
    """
    light_context = dict(_EXAMPLE_CONTEXTS[name])
    light_context["bw_theme"] = "light"
    dark_context = dict(_EXAMPLE_CONTEXTS[name])
    dark_context["bw_theme"] = "dark"
    template = _example_engine().get_template(name)
    light_html = template.render(Context(light_context))
    dark_html = template.render(Context(dark_context))
    assert light_html != dark_html


# ---------------------------------------------------------------------------
# 3. Width source: the W0.1 breakpoint tokens, read live, never hardcoded.
# ---------------------------------------------------------------------------


def test_width_matrix_resolves_from_the_shipped_breakpoint_tokens() -> None:
    """ADR-079 section 6 is the authoritative supported-width matrix; this
    proves the four tokens the matrix is built from actually exist, in rem,
    on the shipped stylesheet, so a rebuild that drops or renames one fails
    here rather than silently narrowing what a11y/archetypes.spec.mjs sweeps
    (that spec reads the identical regex against the identical file; this is
    the Python-side half of the same single-source contract).
    """
    tokens = _read_breakpoint_tokens()
    assert set(tokens) == set(_BREAKPOINT_NAMES), (
        f"expected --bw-breakpoint-{{sm,md,lg,xl}} on tokens.css, found {sorted(tokens)}. "
        "If W0.1's token names changed, both this harness and "
        "a11y/archetypes.spec.mjs must be updated to match (see ADR-079)."
    )
    for name, value in tokens.items():
        assert value.endswith("rem"), f"--bw-breakpoint-{name} is {value!r}, expected a rem value (ADR-079 section 4)"


def test_width_matrix_values_match_adr_079() -> None:
    """Pins the four literal values ADR-079 section 6 ratifies, so a value
    drift (not just a missing/renamed token) is caught here too. This is the
    one place in the harness a literal value is written down; every other
    consumer (the fixture generator, the Playwright spec) reads tokens.css
    directly rather than importing this constant, so there is still only one
    functional source, this is a pinning assertion against it, not a second
    source of truth other code depends on.
    """
    tokens = _read_breakpoint_tokens()
    assert tokens == {"sm": "40rem", "md": "48rem", "lg": "64rem", "xl": "80rem"}
