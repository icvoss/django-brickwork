"""Shared machinery for "every emitted bw-* class has a real CSS rule".

Extracted from test_examples.py's `test_every_section_class_it_emits_is_actually_styled`
(icvoss/django-brickwork#120) so the same check can run over more than one
rendered surface without two copies of the same regex/allowlist logic
drifting apart. test_examples.py covers example sections; test_component_
class_contract.py (icvoss/django-brickwork#137) covers every shipped
component/form/nav/marketing template reachable only via {% include %} or a
component tag, which the section/example renders never exercise.

The COMPILED stylesheet is read here (not the frontend source): the source is
the build's input, and it is the built artefact that reaches a consumer's
page. A rule present in frontend/src but absent here (a build not re-run
before commit) is exactly the drift this machinery exists to catch.
"""

from __future__ import annotations

import re
from pathlib import Path

_COMPILED_CSS = (
    Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"
).read_text(encoding="utf-8")

_STYLED_CLASSES = set(re.findall(r"\.(bw-[a-zA-Z0-9_-]+)", _COMPILED_CSS))


def used_bw_classes(html: str) -> set[str]:
    """Every ``bw-*`` class token named in a rendered fragment's ``class="..."``
    attributes. A class used as a SELECTOR match, not merely mentioned in a
    comment (the same distinction `styled_bw_classes` draws on the CSS side)."""
    used: set[str] = set()
    for attr in re.findall(r'class="([^"]+)"', html):
        used.update(token for token in attr.split() if token.startswith("bw-"))
    return used


def styled_bw_classes() -> set[str]:
    """Every ``bw-*`` class the compiled stylesheet defines a rule for."""
    return _STYLED_CLASSES


def unstyled_classes(html: str, *, allowlist: set[str] = frozenset()) -> list[str]:
    """The classes ``html`` emits that carry no rule in the compiled CSS and are
    not in ``allowlist``. Sorted for stable, readable assertion failures."""
    return sorted(used_bw_classes(html) - _STYLED_CLASSES - allowlist)


# The single canonical "unstyled by design" allowlist (icvoss/django-brickwork#137):
# structural hooks that carry no visual rule of their own, verified individually,
# each with a comment stating WHAT actually styles the element. Both
# test_components.py and test_component_class_contract.py import this SAME set
# so there is exactly one place a justification can be added or go stale, not
# two lists that can silently drift apart (the failure mode this module was
# extracted to prevent in the first place). test_examples.py keeps its own
# separate allowlist: it covers example SECTION roots, a different rendering
# surface with its own doctrine of section-root exemptions, not the
# component/form/nav/marketing include surface this set covers.
UNSTYLED_BY_DESIGN: set[str] = {
    # --- pre-existing, carried across from test_components.py verbatim -------
    # _button.html's label span: the button's own background/padding/type
    # rules carry everything; the label is a plain inline text wrapper.
    "bw-btn__label",
    # _card.html's body region (icvoss/django-brickwork#130's own precedent,
    # documented in _card.html's docstring): the card's padding and the
    # header/footer margins already open every edge's gap.
    "bw-card__body",
    "bw-dropdown__item-label",  # text leaf inside a styled flex row.
    "bw-dropzone__label",  # text leaf inside the styled dropzone surface.
    "bw-empty-state--no_data",  # variant carries no visual distinction (STA-002).
    "bw-empty-state--no_results",  # ditto: the icon/copy alone differ, by design.
    "bw-tag-input",  # enhanced-state root; the .bw-input classes carry the look.
    "bw-tag-input__floor",  # ditto: the floor control borrows .bw-input's rules.
    # --- icvoss/django-brickwork#137 triage: 29 further structural hooks -----
    # (i) an icon whose bw-icon base class carries size/colour and whose
    # parent supplies the gap:
    "bw-btn__icon",  # {% bw_icon %} carries size/colour; .bw-btn's gap positions it.
    "bw-badge__icon",  # ditto; .bw-badge's gap positions it.
    "bw-stat__icon",  # ditto; .bw-stat's flex row positions it.
    "bw-nav__icon",  # ditto; .bw-nav__link's flex row positions it.
    "bw-nav-rail__icon",  # ditto; .bw-nav-rail__link's flex column positions it.
    "bw-nav-header__icon",  # ditto; .bw-nav-header__link's flex row positions it.
    # (ii) a bare text leaf inside a styled flex row:
    "bw-nav-header__label",  # text leaf beside bw-nav-header__icon in the link row.
    "bw-combobox__create-query",  # the typed-query echo inside the styled create option row.
    # Not in the original #137 triage list; surfaced by this file's own
    # per-vocabulary-value renders (bw_tabs, both variants): a bare text span
    # inside .bw-tabs__tab, which carries the type role, colour and the
    # active-state marker.
    "bw-tabs__label",
    # (iii) a bare root that never appears without a modifier which carries
    # everything, or a root whose children carry every rule:
    "bw-tabs",  # bare root; only .bw-tabs--underline/--pill carry any rule.
    "bw-form-fields",  # bare root; only .bw-form-fields--stacked/--grid carry any rule.
    "bw-nav__item",  # bare <li> wrapper; the child .bw-nav__link carries the whole row.
    "bw-nav-rail__item",  # ditto; the child .bw-nav-rail__link carries the whole row.
    "bw-page-header",  # bare grouping root; __title/__description carry all typography.
    "bw-page-header__titles",  # bare title+description wrapper; its children carry everything
    # (investigated for icvoss/django-brickwork#137: genuinely unstyled, and the
    # class-contract test DOES already catch it via _page_header (description),
    # bundled in the same failure as bw-page-header itself; there is no fixture
    # or context/coverage gap here, contrary to the triage's premise).
    "bw-stepper__marker-number",  # plain digit glyph; .bw-stepper__marker carries the circle.
    "bw-stepper__step--upcoming",  # variant carries no visual distinction, matching
    # bw-empty-state's --no_data/--no_results doctrine above: only --complete/
    # --current change the marker glyph.
    "bw-progress--indeterminate",  # state marker on the root; .bw-progress__fill--indeterminate
    # (a different, styled class) carries the actual animation.
    # (iv) a JS/consumer hook where a styled child carries the affordance
    # (bw-empty-state's --no_data/--no_results, bw-dropzone__label and
    # bw-tag-input/__floor above are also this category; not repeated here):
    "bw-data-table__row--linked",  # marker only; .bw-data-table__row-link inside carries the look.
    "bw-data-table__th--sortable",  # marker only; .bw-data-table__sort inside carries the look.
    "bw-combobox__floor",  # enhanced-state root; the .bw-input classes carry the look,
    # matching bw-tag-input__floor's own doctrine above.
    "bw-combobox__option--create",  # JS hook (data-bw-combobox-create); .bw-combobox__option
    # carries the row's look.
    # --- carried across from test_component_class_contract.py verbatim ------
    # marketing section roots whose children carry every rule (the
    # test_examples.py precedent for *-section wrappers, same reasoning
    # applied to the marketing sub-app's own section roots).
    "bw-feature-grid-section",
    "bw-pricing-table-section",
    "bw-stat-band-section",
    "bw-faq-section",
}
