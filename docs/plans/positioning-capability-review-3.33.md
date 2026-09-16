# Positioning capability review (django-brickwork 3.33.0)

**Status:** decision input. Not a rewrite of `docs/POSITIONING.md`.
**Superseded as decision frame by**
`docs/plans/positioning-greenfield-3.33.md` (greenfield buyer/capability pass;
prior A/B slogans are scored, not defaults). Keep this file as capability
inventory notes only.

**Tag reviewed:** `v3.33.0` (`8e6500d`).
**Tracker:** [icvoss/django-brickwork#614](https://github.com/icvoss/django-brickwork/issues/614).
**Companion:** site remaster `icvoss/brickworkui.com#233` (must not lock lead
copy until this ruling lands).

## Why reopen

Two problems are live at once:

1. **Lead claim split.** Package canon at 3.33.0 (POSITIONING section 3,
   README opening) is **Brickwork. Building blocks for beautiful apps and
   websites.** The flagship site homepage and site copy-platform still lead
   with **Beautiful interfaces for anything.** (umbrella plan
   `brickwork-interfaces-for-anything.md`, 2026-09-12). Downstream marketing
   cannot remaster honestly until one lead wins.
2. **Capability moved under the hedges.** POSITIONING section 1 still says
   the shipped inventory is "not yet that complete system" while Documentation
   and Editorial are **7/7**, Theme is a named product surface (THEME.md /
   ADR-110, L1 to L4), and section 5 gates **70** components / **6** shells /
   **236** axe documents. The hedge may still be true for some INTERFACE-SYSTEM
   archetype gaps (marketing/app/ops/transactional), but it is no longer an
   accurate one-line summary of what 3.33 is.

ADR-108 (package jobs vs showcase ownership) remains useful and should stay.
This review does not reopen that ownership line. It reopens **what we claim
the package is for**, grounded in what the wheel actually does.

## What the package consumes / does / produces (orientation)

### Consumes

- Django (hard runtime), consumer templates and views, consumer brand CSS
  (`--bw-*` overrides), optional Tailwind projection recipe, Alpine/HTMX on
  the documented stack.

### Does

- Ships a **substrate** (tokens, shells, primitives, interaction contracts,
  a11y gates).
- Ships a **reference catalogue** (archetypes and sections to copy and own,
  ADR-056).
- Ships an **installable starter** (`manage.py startsite`, ADR-095).
- Defines **Brickwork Theme** profiles (L0 to L4) as the consumer brand job
  on that substrate.

### Produces

- Installable wheel with gated catalogue counts, CSS/JS dist, examples off
  the template loader path, CI a11y evidence, Theme/brand-pack contracts.

## Capability facts at 3.33.0 (lift only what is gated or dated in POSITIONING)

| Fact | Value at 3.33.0 | Source |
|---|---|---|
| Lead in POSITIONING / README | Building blocks for beautiful apps and websites | POSITIONING §3; README |
| Components | 70 (51 core, 19 marketing) | POSITIONING §5 gated |
| Shells | 6 | POSITIONING §5 gated |
| Examples (README framing) | 61 examples + skeleton; site shows 73 copy-paste | README vs site copy: reconcile in ruling |
| Documentation family | 7/7 | POSITIONING §5 narrative; issue #428 |
| Editorial family | 7/7 | same |
| Theme product | L1 to L4 public claims after Phase G | THEME.md; POSITIONING §4.3 |
| Visual bar | Meet-bar PASS; beat 6/8 (S5 Lose, S3 N/S) | cited audits in POSITIONING §3 |
| A11y gate | 236 documents | POSITIONING §5 gated |
| Package / showcase split | ADR-108 | umbrella ADR |

## Honesty gaps (capability vs claim)

| Claim / surface | Problem |
|---|---|
| Site lead "Beautiful interfaces for anything." | Diverges from package POSITIONING at the pin the site installs |
| POSITIONING §1 "not yet that complete system" | Undersells Docs/Editorial complete + Theme product; needs a shipping-matrix sentence, not a blanket hedge |
| Umbrella interfaces-for-anything plan | Still names the 2026-09-12 lead as active; package canon moved 2026-09-15 |
| Site remaster brief v2 | Treated "Beautiful interfaces…" as hard product fact; must wait on this ruling |
| Example counts across README / site / POSITIONING composition prose | Risk of three numbers; gate or date one register |

## Options for the lead (decision)

| Option | Lead | Fits 3.33 capability when… | Risk |
|---|---|---|---|
| **A** | Keep **Building blocks for beautiful apps and websites.** | You want craft + composition + upgrade boundary as the promise; Theme and families are supporting proof | Site must drop "interfaces for anything" everywhere |
| **B** | Restore **Beautiful interfaces for anything.** | You want range/coverage as the promise now that Docs+Editorial ship and Theme levels exist | Must re-ground evidence (families + Theme), not revive editorial house feel; update README/POSITIONING |
| **C** | New lead, drafted only after owner names the job | Only if A and B both fail the prefer test against the real wheel | Do not invent in this review |

**Recommendation (for ruling, not self-executing):** run A and B against the
same buyer prefer test with 3.33 evidence cards (Theme L3 specimen, one Docs
archetype, one Editorial archetype, one app/ops surface, beat scorecard
honesty). Do not pick by nostalgia for either 2026-09-12 or 2026-09-15 copy.

## What must stay regardless of lead

- Claim honesty rules (POSITIONING §9).
- No house aesthetic (§10).
- ADR-108 package vs showcase ownership.
- Visual-bar and beat cites with soft-pass forbidden.
- Theme L1 to L4 claim bounds (do not say L1 recolours "the whole system").
- Distinguish target INTERFACE-SYSTEM coverage from verified shipping per family.

## Proposed next steps

1. Owner picks A, B, or commissions C.
2. Single PR on `django-brickwork`: POSITIONING §1 and §3, README opening,
   gated counts if needed, "complete system" hedge rewritten as a family
   shipping matrix.
3. Follow-on: brickworkui.com remaster (#233) and umbrella marketing banners
   align to the ruling in the same wave.
4. Close or retarget any site work that assumed the other lead.

## Non-goals

- Rewriting VISUAL-BAR panel membership.
- Moving showcase sell folds into the package (ADR-108 stands).
- Implementing site display before the lead is singular.
