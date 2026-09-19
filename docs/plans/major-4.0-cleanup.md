# Plan: django-brickwork 4.0.0 clean-break major

**Status:** active (Phase 0 complete; implement next)
**Branch:** `release/4.0.0` in worktree `.claude/worktrees/major-4.0`
**Baseline tip:** `v3.38.0` / `39a3f9f` (Unreleased empty at start)
**Date:** 2026-09-19

## Intent

Ship **4.0.0** as one removal-only major: harvest every already-declared
"removed at 4.0" / next-major surface, end the temporary marketing dual-class
window, amend versioning honesty for an owner-only fleet, then release with
coordinated consumer pin bumps in the same wave.

Owner rulings already settled (do not re-litigate):

- Fleet is owner-only today → **no parallel-support window** for this major;
  clean break + migrate every owned consumer in the same pass (same ground as
  BR-BW-OPT-007).
- Whole declared cleanup lot in one pass, not drip minors.
- New features stay out.
- British English; no em or en dashes in prose.

## Non-goals

- brickworkui.com greenfield remaster / sell site beyond pin bump + forced renames
- Demand-gated #156 (`bw_command`), media picker, #570/#571, deferred debt
  (#290, #262, #385, …)
- Inventing renames not already marked for 4.0 / next major
- Reopening Beautiful by default vs G1
- Removing undeclared courtesy token aliases, `.bw-pricing-comparison*`,
  `bw-stat__trend*`, ranked-list kwargs aliases, or `_pricing_comparison.html`
  (flagged in discovery; **out of scope**)

## In-scope removals (verified still shipping)

### A. Deprecated template blocks (CHANGELOG 3.4.0 / `removedAt: "4.0.0"`)

| Old | Successor |
|---|---|
| `card_header` / `card_title` / `card_actions` / `card_body` / `card_footer` | `header` / `title` / `actions` / `body` / `footer` |
| `modal_title` / `modal_body` / `modal_footer` | `title` / `body` / `footer` |
| `slide_over_title` / `slide_over_body` / `slide_over_footer` | `title` / `body` / `footer` |
| `alert_body` | `body` |
| `tooltip_trigger` | `trigger` |
| `empty_state_action` | `action` |
| `_empty_state` blocks `title` / `description` | `heading` / `body` |

Touch: six templates under `src/brickwork/templates/brickwork/components/`,
`scripts/generate_template_manifest.py`, `template-manifest.json`,
`tests/template_contract_baseline.json`, consumer/test fixtures that still
fill old names. Tests that currently prove "deprecated still works" must
flip to prove old names are ignored / absent.

### B. Token `--bw-font-size-3xs` (TYP-022 / DESIGN.md / CHANGELOG)

Remove the rung from `component.tokens.json`, rebuild tokens/CSS/manifests,
update DESIGN.md, assert absence in gates. Floor remains `2xs` (chrome) /
`xs` (content). No package consumer. POSITIONING overridable token count
moves with the drop.

### C. Marketing dual-class window (ADR-113)

Declared in 3.37.0 as dual emit "for one minor"; tip is already 3.38.0, so
the calendar window is past while emit still ships both `.bw-site-*` and
`.bw-marketing-*` on shared chrome.

**4.0 close:** package emits `.bw-site-*` only on shared marketing/site
chrome; drop dual emit and dual CSS selectors that exist only to keep
`.bw-marketing-header*` / `.bw-marketing-footer*` alive as aliases.
Consumers must select `.bw-site-*` (or update hand-rolled markup). Marketing
composition classes that are not dual-class chrome (for example page/section
vocabulary already named `bw-marketing-*`) stay unless separately declared.

## Spec amendment (first-class)

Umbrella file: `docs/specs/django-brickwork/02-business-rules.md`

**BR-BW-VER-001** today requires N-1 parallel support + AST codemod before a
major removes a contract name.

**BR-BW-OPT-007** already carves clean-break option renames while no external
consumer exists, citing the same ground as ADR-056's 2.0.0 page-tier removal,
and says the ruling is re-examined if an external consumer appears.

**Amendment for this major (and standing while fleet stays owner-only):**

Amend BR-BW-VER-001 (or add an explicit owner-fleet carve-out immediately
under it) so that:

1. While brickwork has **no external consumer**, a major may remove already
   deprecated contract names as a **clean break**, migrating every owned
   consumer in the same release wave (OPT-007 precedent).
2. Parallel-support N-1 remains the default rule when an external consumer
   exists or appears; re-examine the carve-out then.
3. An AST / scripted codemod remains **useful and preferred** for owned
   fleets, but is **not** a mandatory delay gate that forces an extra N-1
   minor before the major.

Record the ruling date and cite this plan / release notes. Update the Rule
Index summary line if the wording changes.

Umbrella ROADMAP tip for django-brickwork must move to **4.0.0** in the same
honesty pass after ship (separate umbrella PR, same programme).

## Consumer blast list (same wave)

| Consumer | Current pin | Rename surface | Effort |
|---|---|---|---|
| `oss/sites/brickworkui.com` | `==3.37.0` (`<4`) | modal/tooltip blocks; hand-rolled `.bw-marketing-header*` + dual CSS | medium |
| `oss/sites/icvlocal.com` (vendablyconnect deploy) | `==3.18.0` (`<4`) | 17 demo block renames; no chrome dual | light |
| `oss/sites/icvoss.com` | `==3.33.0` (`<4`) | 8 gallery blocks; marketing-only header CSS | light to medium |
| `consentics/consentics_app` | `==3.32.0` | pin-only (no deprecated fills found) | none |
| `agentpm/agentpm-app` | `>=3.2,<3.3` | `card_body` + large pin leap | light + pin |
| `magmify` | `>=3.31.0` | many `modal_*`; review page CSS names | medium |

Private packages under `oss/private/`: no brickwork pins.

**Bar:** each consumer gets a worktree, pin `django-brickwork==4.0.0` (or
editable against the release commit until PyPI is live), apply renames, green
suite. File `owner/repo#N` only for hosts that cannot be edited in-session.

## Package implementation sequence

1. Spec amendment (umbrella VER-001 carve-out) in the umbrella PR track.
2. Remove deprecated blocks from templates; regenerate manifest + baseline.
3. Flip package tests: old names must not render; dual emit must stop; assert
   `3xs` absent.
4. Remove `3xs` from token source; rebuild frontend artefacts.
5. End dual-class emit in marketing/site chrome templates + CSS; update
   INTEGRATION / DESIGN / APPEARANCE notes.
6. Preferred: `scripts/codemod_4_0_blocks.py` (or similar) for block renames;
   help, not a substitute for the break.
7. Version bump to 4.0.0 in `pyproject.toml` + `__init__.py`; dated
   `## [4.0.0]` CHANGELOG with consumer-facing old → new upgrade list;
   Unreleased emptied of ship content.
8. Update POSITIONING Version gate and any token/a11y counts the drop moves.

## Release bar (six publish gates)

1. Version sync (`pyproject` / `__init__` / dated CHANGELOG; Unreleased empty).
2. Full CI green on the exact tag commit.
3. Simulate `publish.yml` install set in a clean venv; suite green there.
4. Build, `twine check`, inspect wheel contents, clean-venv import.
5. Confirm tagged commit's `publish.yml` is the workflow that should run.
6. Consumer-facing upgrade notes (old → new) in CHANGELOG / release notes.

Tag `v4.0.0` only after gates pass; watch publish; confirm PyPI; then umbrella
ROADMAP tip → 4.0.0.

## Verification protocol

- Implementer subagents write code; **tester** subagent runs the suite and
  merge-blocking gates (never the orchestrator skipping the tester).
- a11y fixtures / Playwright specs that select `.bw-marketing-header*` must
  move with chrome identity.
- Spot-check: deprecated block names absent from live `block_names()`;
  no dual landmark classes in marketing shell HTML; no `--bw-font-size-3xs`
  in shipped CSS/manifests.

## Owner confirm gate

Stop for a one-line owner confirm **only if** discovery finds a removal never
declared for 4.0 / next major, or a consumer that cannot be bumped.

**Discovery result:** no such stop. Dual-class close is in the mission brief
and the one-minor window has elapsed. Undeclared candidates stay out of scope.
All named and discovered owned consumers are editable in-session.

## Done when

- 4.0.0 on PyPI; Unreleased empty of ship content
- No deprecated 3.4.0 block names still render
- No `3xs` token; no marketing dual-class emit
- BR-BW-VER-001 (or carve-out) matches clean-break fleet policy
- Owned consumers pinned and green (or explicit blockers filed with `owner/repo#N`)
- This plan archived / status closed after ship
