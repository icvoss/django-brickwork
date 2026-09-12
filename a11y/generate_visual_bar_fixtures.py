"""Render the VISUAL-BAR scorecard surfaces (S1 to S8) for private stills.

Default: package-only CSS (compiled brickwork.css inlined). No showcase or
kiln brand. Optional brand pack via ``VISUAL_BAR_BRAND`` (currently
``northline`` only): after inlining brickwork.css, append that pack's
``tokens.css`` and set ``bw_brand`` so the shell emits ``data-bw-brand``.

Uses the same sanctioned examples Engine and ``_EXAMPLE_CONTEXTS`` as the
archetype fixture generator (ADR-056). Output is a fixed map of the eight
surfaces under ``a11y/fixtures/visual-bar/`` (package-only) or
``a11y/fixtures/visual-bar-<brand>/`` when a brand is set. Both stay
gitignored with the rest of ``a11y/fixtures/``.

This generator is deliberately separate from ``generate_archetype_fixtures.py``:
the scorecard freezes eight jobs named in ``docs/VISUAL-BAR.md``, including
S8 ops analysis even when the broader archetype sweep is stale or incomplete.
Adding a ninth scorecard surface requires a VISUAL-BAR amendment, not a silent
extra row here.

Run::

    DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:.:tests \\
      python a11y/generate_visual_bar_fixtures.py

Brand pack (northline skeleton)::

    VISUAL_BAR_BRAND=northline \\
      DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:.:tests \\
      python a11y/generate_visual_bar_fixtures.py

Then capture stills with ``npm run visual-bar:capture`` (or
``visual-bar:capture:northline``).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import django

django.setup()

from django.template import Context  # noqa: E402
from tests.test_examples import _EXAMPLE_CONTEXTS, _example_engine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text(encoding="utf-8")
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"

_STATIC_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*brickwork\.css">')
_STYLE_CLOSE = re.compile(r"</style>", re.IGNORECASE)

THEMES = ("light", "dark")

# Supported brand packs for the second scorecard leg. Empty env = package-only.
KNOWN_BRANDS: dict[str, Path] = {
    "northline": ROOT / "docs/examples/brand-pack/northline/tokens.css",
}

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


def _brand_from_env() -> str:
    """Return the brand slug from VISUAL_BAR_BRAND, or empty for package-only."""
    raw = (os.environ.get("VISUAL_BAR_BRAND") or "").strip()
    if not raw:
        return ""
    if raw not in KNOWN_BRANDS:
        known = ", ".join(sorted(KNOWN_BRANDS)) or "(none)"
        raise SystemExit(f"VISUAL_BAR_BRAND={raw!r} is not a known scorecard brand pack. Known: {known}.")
    path = KNOWN_BRANDS[raw]
    if not path.is_file():
        raise SystemExit(f"Brand pack tokens missing for {raw!r}: expected {path}")
    return raw


def _out_dir(brand: str) -> Path:
    if brand:
        return FIXTURES_ROOT / f"visual-bar-{brand}"
    return FIXTURES_ROOT / "visual-bar"


def _inline_css(html: str, brand: str) -> str:
    """Replace the static stylesheet link with compiled CSS for file:// load.

    When a brand is set, append that pack's tokens.css after brickwork.css so
    the cascade matches BRANDING.md (brand delta loads after package CSS).
    """
    html = _STATIC_LINK.sub(f"<style>{CSS}</style>", html)
    if not brand:
        return html
    brand_css = KNOWN_BRANDS[brand].read_text(encoding="utf-8")
    # Insert brand sheet immediately after the first inlined style block.
    match = _STYLE_CLOSE.search(html)
    if match is None:
        raise SystemExit("Could not find inlined <style> after brickwork.css substitution.")
    insert_at = match.end()
    return html[:insert_at] + f'\n<style data-bw-brand-pack="{brand}">{brand_css}</style>' + html[insert_at:]


def render_surface(example_name: str, theme: str, brand: str) -> str:
    """Render one scorecard surface through the examples Engine."""
    if example_name not in _EXAMPLE_CONTEXTS:
        raise KeyError(
            f"{example_name!r} has no tests.test_examples._EXAMPLE_CONTEXTS entry; the scorecard cannot render it."
        )
    context = dict(_EXAMPLE_CONTEXTS[example_name])
    context["bw_theme"] = theme
    if brand:
        context["bw_brand"] = brand
    template = _example_engine().get_template(example_name)
    return _inline_css(template.render(Context(context)), brand)


def main() -> None:
    brand = _brand_from_env()
    out = _out_dir(brand)
    out.mkdir(parents=True, exist_ok=True)

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
            html = render_surface(example, theme, brand)
            filename = f"{surface_id}-{theme}.html"
            path = out / filename
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

    if brand:
        css_note = (
            f"package brickwork.css inlined, then docs/examples/brand-pack/{brand}/tokens.css; "
            f'data-bw-brand="{brand}" on html root (no showcase/kiln)'
        )
    else:
        css_note = "package-only (brickwork.css inlined; no showcase brand)"

    manifest = {
        "package": "django-brickwork",
        "version": version,
        "brand": brand or None,
        "css": css_note,
        "surfaces": manifest_surfaces,
        "themes": list(THEMES),
        "note": "Private audit fixtures for docs/VISUAL-BAR.md. Not a CI gate.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    label = f"brand={brand}" if brand else "package-only"
    print(f"visual-bar fixtures written ({len(written)}, {label}): {', '.join(written)}")
    print(f"manifest: {out / 'manifest.json'} (package {version})")


if __name__ == "__main__":
    main()
