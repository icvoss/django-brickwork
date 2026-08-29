"""The app/marketing family boundary is a check, not reviewer memory
(icvoss/django-brickwork#399, the check ruled on #371 gap 3).

`bw-feature-grid`, `bw-media-text`, `bw-listing-list__item` and friends ship in
the same compiled `brickwork.css` bundle an app-surface page loads, so nothing
at the CSS level stops a consumer using them there. They are marketing-family:
styled for marketing surfaces and restyled for marketing reasons, so
permitting them on app pages would make a marketing visual change silently an
app-surface regression, with nothing in the package connecting the two.

#371's own sentence is why this file exists rather than a paragraph in a doc:
"a habit enforced only by reviewer memory is not a boundary." A documented
prohibition with no check is reviewer memory with extra steps.

The marketing-family class list is DERIVED from frontend/src/marketing.css
(the classes it actually defines, not every class token it merely mentions in
a combinator, a :not(), or a comment), never hand-maintained beside it, so a
new marketing class is covered by construction the moment it ships.

App-surface templates are identified the same way tests/test_shell.py's own
SHELLS list already draws the family line: a shipped template whose own
{% extends %} targets brickwork/shell/app.html, brickwork/shell/auth.html or
brickwork/shell/centred.html.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests._class_contract import used_bw_classes

_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "brickwork"
_MARKETING_CSS = (Path(__file__).resolve().parent.parent / "frontend" / "src" / "marketing.css").read_text(
    encoding="utf-8"
)

# The same family line tests/test_shell.py's own SHELLS draws: these three
# shells, and only these three, are the app-surface family. The marketing
# shell (brickwork_marketing/shell/marketing.html) is deliberately excluded:
# a template extending it IS a marketing-family template, so it is exempt
# from this check by definition rather than by coincidence.
_APP_SHELLS = {
    "brickwork/shell/app.html",
    "brickwork/shell/auth.html",
    "brickwork/shell/centred.html",
}

_EXTENDS_RE = re.compile(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}')


def _defined_marketing_classes() -> set[str]:
    """Every ``bw-*`` class frontend/src/marketing.css itself DEFINES a rule
    for: a selector-list entry that is a bare class, optionally followed by a
    pseudo-class/pseudo-element chain, with nothing preceding it (no
    combinator, no descendant, no :not() argument). This excludes classes
    that merely appear inside marketing.css's own combinator selectors
    (``.bw-stat-band .bw-stat``), :not() exclusions (``:not(.bw-btn)``), or
    comments, none of which marketing.css defines a rule for."""
    without_comments = re.sub(r"/\*.*?\*/", "", _MARKETING_CSS, flags=re.S)
    defined: set[str] = set()
    for selector_list in re.findall(r"([^{}]+)\{", without_comments):
        for selector in selector_list.split(","):
            selector = selector.strip()
            match = re.match(r"^\.(bw-[\w-]+)(?::{1,2}[\w-]+(?:\([^)]*\))?)*$", selector)
            if match:
                defined.add(match.group(1))
    return defined


def _extends_target(html: str) -> str | None:
    match = _EXTENDS_RE.search(html)
    return match.group(1) if match else None


def _app_surface_templates() -> list[Path]:
    templates = []
    for path in _PACKAGE_DIR.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        if _extends_target(html) in _APP_SHELLS:
            templates.append(path)
    return templates


def test_marketing_class_derivation_finds_marketing_only_classes() -> None:
    # Teeth for the derivation itself: it must find a real marketing class
    # named in #371/#399 and must NOT pick up a shared component class that
    # merely appears inside marketing.css's own combinator/:not() selectors.
    classes = _defined_marketing_classes()
    assert "bw-feature-grid" in classes
    assert "bw-media-text" in classes
    assert "bw-listing-list__item" in classes
    assert "bw-card" not in classes  # only ever appears as a.bw-card / :not(.bw-btn) context, never defined here
    assert "bw-btn" not in classes  # only ever appears inside :not(.bw-btn)
    assert "bw-stat" not in classes  # only ever appears as a descendant, .bw-stat-band .bw-stat
    assert "bw-stat-grid" not in classes  # only ever mentioned in a comment


def test_app_surface_templates_are_found() -> None:
    # The denominator: a check that scans zero files passes vacuously. This
    # pins a floor so a future refactor that stops matching any template is
    # itself a failure, not a silent green.
    templates = _app_surface_templates()
    assert len(templates) >= 12, (
        f"expected at least 12 app-surface templates (app/, auth/, ops/, examples/app confirm.html); "
        f"found {len(templates)}: {sorted(str(t.relative_to(_PACKAGE_DIR)) for t in templates)}"
    )


def test_no_marketing_family_class_appears_in_an_app_surface_template() -> None:
    marketing_classes = _defined_marketing_classes()
    templates = _app_surface_templates()
    assert templates, "no app-surface templates found to scan; the check ran over zero files"

    offenders: dict[str, list[str]] = {}
    for path in templates:
        html = path.read_text(encoding="utf-8")
        used = used_bw_classes(html)
        hit = sorted(used & marketing_classes)
        if hit:
            offenders[str(path.relative_to(_PACKAGE_DIR))] = hit

    assert not offenders, (
        f"marketing-family classes appeared in {len(offenders)} of {len(templates)} scanned "
        f"app-surface templates (a habit enforced only by reviewer memory is not a boundary, "
        f"icvoss/django-brickwork#371): {offenders}"
    )
