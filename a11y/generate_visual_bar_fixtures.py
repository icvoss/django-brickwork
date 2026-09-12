"""Render the VISUAL-BAR scorecard surfaces (S1 to S8) for private stills.

Package-only CSS (compiled brickwork.css inlined). No showcase brand pack.
Uses the same sanctioned examples Engine and ``_EXAMPLE_CONTEXTS`` as the
archetype fixture generator (ADR-056). Output is a fixed map of the eight
surfaces under ``a11y/fixtures/visual-bar/``, which stays gitignored with the
rest of ``a11y/fixtures/``.

This generator is deliberately separate from ``generate_archetype_fixtures.py``:
the scorecard freezes eight jobs named in ``docs/VISUAL-BAR.md``, including
S8 ops analysis even when the broader archetype sweep is stale or incomplete.
Adding a ninth scorecard surface requires a VISUAL-BAR amendment, not a silent
extra row here.

Run::

    DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:.:tests \\
      python a11y/generate_visual_bar_fixtures.py

Then capture stills with ``npm run visual-bar:capture``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import django

django.setup()

from django.template import Context  # noqa: E402
from tests.test_examples import _EXAMPLE_CONTEXTS, _example_engine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text(encoding="utf-8")
OUT = Path(__file__).resolve().parent / "fixtures" / "visual-bar"
OUT.mkdir(parents=True, exist_ok=True)

_STATIC_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*brickwork\.css">')

THEMES = ("light", "dark")

# Frozen map from docs/VISUAL-BAR.md section 3. Keys are scorecard surface IDs.
SURFACES: dict[str, dict[str, str]] = {
    "s1": {
        "label": "App list",
        "example": "app/list.html",
    },
    "s2": {
        "label": "App detail",
        "example": "app/detail.html",
    },
    "s3": {
        "label": "App form",
        "example": "app/form.html",
    },
    "s4": {
        "label": "App dashboard",
        "example": "app/dashboard.html",
    },
    "s5": {
        "label": "Marketing landing",
        "example": "marketing/landing.html",
    },
    "s6": {
        "label": "Marketing pricing",
        "example": "marketing/pricing.html",
    },
    "s7": {
        "label": "Docs article",
        "example": "docs/article.html",
    },
    "s8": {
        "label": "Dense ops",
        "example": "ops/analysis-dashboard.html",
    },
}


def _inline_css(html: str) -> str:
    """Replace the static stylesheet link with compiled CSS for file:// load."""
    return _STATIC_LINK.sub(f"<style>{CSS}</style>", html)


def render_surface(example_name: str, theme: str) -> str:
    """Render one scorecard surface through the examples Engine."""
    if example_name not in _EXAMPLE_CONTEXTS:
        raise KeyError(
            f"{example_name!r} has no tests.test_examples._EXAMPLE_CONTEXTS entry; the scorecard cannot render it."
        )
    context = dict(_EXAMPLE_CONTEXTS[example_name])
    context["bw_theme"] = theme
    template = _example_engine().get_template(example_name)
    return _inline_css(template.render(Context(context)))


def main() -> None:
    missing = sorted(entry["example"] for entry in SURFACES.values() if entry["example"] not in _EXAMPLE_CONTEXTS)
    if missing:
        raise SystemExit(
            "VISUAL-BAR surfaces lack _EXAMPLE_CONTEXTS entries: "
            f"{missing}. Add contexts before generating scorecard fixtures."
        )

    written: list[str] = []
    manifest_surfaces: list[dict[str, str]] = []
    for surface_id, entry in SURFACES.items():
        example = entry["example"]
        for theme in THEMES:
            html = render_surface(example, theme)
            filename = f"{surface_id}-{theme}.html"
            path = OUT / filename
            path.write_text(html, encoding="utf-8")
            written.append(filename)
        manifest_surfaces.append(
            {
                "id": surface_id,
                "label": entry["label"],
                "example": example,
                "light": f"{surface_id}-light.html",
                "dark": f"{surface_id}-dark.html",
            }
        )

    package_version = (ROOT / "src/brickwork/__init__.py").read_text(encoding="utf-8")
    version_match = re.search(r'__version__\s*=\s*"([^"]+)"', package_version)
    version = version_match.group(1) if version_match else "unknown"

    manifest = {
        "package": "django-brickwork",
        "version": version,
        "css": "package-only (brickwork.css inlined; no showcase brand)",
        "surfaces": manifest_surfaces,
        "themes": list(THEMES),
        "note": "Private audit fixtures for docs/VISUAL-BAR.md. Not a CI gate.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"visual-bar fixtures written ({len(written)}): {', '.join(written)}")
    print(f"manifest: {OUT / 'manifest.json'} (package {version})")


if __name__ == "__main__":
    main()
