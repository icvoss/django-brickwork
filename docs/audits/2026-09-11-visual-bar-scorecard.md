# Visual-bar scorecard: 2026-09-11 Phase 1 rendered

**Status:** Phase 1 rendered pass (package-only CSS). Not a beauty
certification. Not a completed programme pass under
[VISUAL-BAR.md](../VISUAL-BAR.md) section 6 (brand pack second leg deferred;
independent sign-off is Phase 5).
**Package under test:** django-brickwork `3.18.0`
(`src/brickwork/__init__.py` / `pyproject.toml` at tip `0afbc53`).
**Reviewer:** agent session (rendered stills + package tokens/templates).
**Render mode:** package-default CSS only (`npm run visual-bar:fixtures` then
`visual-bar:capture`). Brand pack second pass: deferred.
**Private stills:** `docs/audits/_stills/2026-09-11/` (gitignored; 32 PNGs,
light/dark × 1440/375 × S1 to S8). See [\_stills/README.md](_stills/README.md).

Bar: [VISUAL-BAR.md](../VISUAL-BAR.md). Clean-room only. Competitor names stay
out of public marketing copy. No kit markup pasted. No claim that brickwork
is beauty certified.

This file supersedes the same-day structure-only provisional (render-blocked)
judgement. Provisional hypotheses that stills overturned are noted below.

## Kit panel for this pass

Priority 1: Tailwind Plus, Preline UI.
Priority 2: shadcn/ui, daisyUI.
Priority 3 (coverage notes only): Flowbite, Tailgrids, Tailkit.
Behaviour only: Headless UI.
Secondary Idea-ref (clarify "finished" only): Forge stills under umbrella
`docs/_examples/forge-ui-kit-site/` (`07`, `08`, `09`, then `01`, `04`).

## Evidence

| Source | Present? | Use |
|---|---|---|
| Package stills S1 to S8, light/dark, 1440/375 | Yes | Primary scoring |
| Example templates + `tokens.css` | Yes | Confirm mechanism behind fails |
| Owned Tailwind Plus trees under umbrella `docs/_examples/tailwind-templates/` | Yes | Priority 1 Idea-ref (look only) |
| Forge stills `07`/`08`/`09`/`01`/`04` | Yes | Finished-ness clarification only |
| Intentional brand override render | No | Brandability: mechanism pass; visual hold deferred |

## Surfaces

| ID | Surface | Fixture used | Notes before scoring |
|---|---|---|---|
| S1 | App list | `examples/app/list.html` | Populated table; **empty filter fields**; **empty app nav** |
| S2 | App detail | `examples/app/detail.html` | Facts + related table; empty app nav |
| S3 | App form | `examples/app/form.html` | Structure OK; **Name/Email stand-in** for an invoice job |
| S4 | App dashboard | `examples/app/dashboard.html` | Four equal KPI tiles + table; empty app nav |
| S5 | Marketing landing | `examples/marketing/landing.html` | Text-only hero; **no mobile nav toggle**; thin logo cloud |
| S6 | Marketing pricing | `examples/marketing/pricing.html` | Highlighted tier works; **no mobile nav toggle**; thin FAQ |
| S7 | Docs article | `examples/docs/article.html` | Credible rail + prose + callout + code |
| S8 | Dense ops | `examples/ops/analysis-dashboard.html` | Weighted scorecard; **empty chart mount**; empty app nav |

## Scorecard (rendered, package-default)

Fill legend: **fail** = substrate loses the axis against the named kit bar.
**pass** = holds at both themes and both viewports inspected.
**n/a** unused.
Fixture defects are called out in Follow-up and are **not** scored as
substrate fails until corrected and re-rendered.

| Surface | Kit that led | Axes failed | Borrow idea (clean-room) | Follow-up |
|---|---|---|---|---|
| S1 App list | Preline (product density); shadcn (token clarity) | None firm on substrate. Density/hierarchy hold with two realistic rows. Dark table chrome acceptable. | Keep filter → table → empty → pagination as one job; tighten only if populated filters still show air | **Fixture first:** populate `filter_form` and scorecard `nav_items`. Then re-score nav chrome |
| S2 App detail | Preline | None firm. Definition + related + danger stack reads with clear job focus on desktop and phone | Prefer definition quieter than related table (already roughly true) | Fixture: populate nav. Re-check danger-zone weight after nav is real |
| S3 App form | shadcn / Preline; Forge `08` clarifies finished form grammar | None firm on chrome structure. Help/error craft not exercised by this fixture | Keep primary submit obvious; vertical field rhythm is fine | **Fixture first:** invoice-shaped fields (or labelled demo form). Do not judge form beauty on Name/Email alone. Forge `08` is Idea-ref only |
| S4 App dashboard | Preline / Tailwind Plus dashboards; Forge `07` clarifies finished | Hierarchy; density (argument flatness) | One headline metric + supporting cast; sparklines / activity+table split as token-level rhythm, not kit markup | Prefer analysis-dashboard argument shape for S4 example, or teach weighted spans in `app/dashboard.html`. Fixture: populate nav |
| S5 Marketing landing | Tailwind Plus; Preline; Forge `01` clarifies finished | Typography; spacing rhythm; surface differentiation; density (air); section cadence; navigation / mobile chrome | Distinct display pairing; larger and varied marketing cadence; alternating surface bands; feature surfaces with role; ship mobile disclosure in the scorecard example | **Fixture first:** include `_mobile_nav_toggle.html`; add hero media (also icvoss/django-brickwork#270). Then Phase 3 substrate craft |
| S6 Marketing pricing | Tailwind Plus; Preline; Forge `04` clarifies finished | Typography; section cadence; navigation / mobile chrome. Pricing tier chrome (border + elevation + highlight) **passes** | Pricing intro measure and section breathing room via tokens; keep highlighted tier | Same mobile toggle fixture as S5; enrich FAQ only if still thin after cadence tokens |
| S7 Docs article | Tailwind Plus docs / Preline content | None firm. Quiet prose is intentional and holds in stills | Keep content as the interface; measure and heading jump already read clearly | No substrate fail this pass |
| S8 Dense ops | Preline | None firm on argument order once chart emptiness is marked fixture. Density closer to pass than S4 | Keep headline → shape → breakdown; chart empty/loading must look designed | **Fixture first:** chart mount empty state or sample SVG. Populate nav. Re-score states craft |

### Axis matrix (package-default, both themes × both viewports)

| Axis | Rating | Evidence from stills |
|---|---|---|
| Hierarchy | Mixed | App list/detail/docs: pass. S4 equal tiles: fail. Marketing heroes: size works; display family equals sans so type alone under-delivers |
| Typography | Fail (defaults) | `--bw-font-family-display: var(--bw-font-family-sans)` with system UI stack (`tokens.css`). Marketing and app headings share one face |
| Spacing rhythm | Fail marketing; pass app | Marketing gap token 4rem; landing/pricing stills read as even stacks. App page header → body rhythm is fine |
| Surface differentiation | Fail marketing; pass app | Feature items are icon+text only; `--bw-color-surface-raised` aliases surface in light. Cards/tables/pricing tiers use hairline + elevation and pass |
| Density | Fail marketing air; pass app/ops mechanism | Marketing lacks section theatre. S8 denser than S4; S4 under-argues |
| States | Pass contract; craft blocked on thin fixtures | Table/filter/chart empty branches exist in components; S1 empty filters and S8 empty chart prevent craft scoring |
| Navigation / mobile chrome | Fail marketing examples; app nav unscored | S5/S6 at 375px wrap nav links and CTAs; no disclosure. Seam exists (`_mobile_nav_toggle.html`, #263 closed) but scorecard examples omit it. App sidebar empty by `_NAV_CONTEXT` |
| Forms | Pass structure | Labels, required marks, primary/ghost actions align. Pixel craft deferred until fixture fields match the job |
| Section cadence (marketing) | Fail | Hero → logos → features → stats → testimonial → CTA with uniform gap and no media; reads as stacked templates |
| Brandability | Pass mechanism; visual hold deferred | Seven-token override model unchanged; brand pack stills not run |

## Fixture hygiene (score before substrate)

Tracked as icvoss/django-brickwork#509. **Corrected 2026-09-12** in the
package examples and `_EXAMPLE_CONTEXTS`; private stills regenerated under
`docs/audits/_stills/2026-09-12/`.

| Gap | Status after #509 |
|---|---|
| S5/S6 omit `_mobile_nav_toggle.html` | Fixed in landing/pricing examples |
| App/ops empty `nav_items` | Fixed: shared `_APP_NAV_ITEMS` |
| S1 empty `filter_form` | Fixed: Search + Status |
| S5 hero has no `media` | Fixed: beside SVG via `hero_media` |
| S3 Name/Email stand-in | Fixed: account / amount / due date / memo |
| S8 blank chart mount | Fixed: chart card empty state |

Re-score after this land is optional for fixture axes; substrate craft
(#510 to #512) remains open.

## Kit comparison notes (clean-room)

| Kit | What led on this pass | Brickwork response |
|---|---|---|
| Tailwind Plus | Marketing hierarchy, section rhythm, header/flyout craft | Marketing cadence + mobile disclosure in examples; display pairing |
| Preline UI | HTML-first section and dashboard compositions | S4 weighted argument; marketing bands with surface roles |
| shadcn/ui | Semantic token clarity, form option grammar | Already strong on tokens/a11y; not a visual taste win alone |
| daisyUI | Theme density / "looks done" with little setup | Display/theme density gap on marketing defaults |
| Forge (Idea-ref) | Finished dashboard/form/settings stills | Clarifies sparklines, activity+table, richer forms; not a panel leader |

## Outcome

**Phase 1.1 to 1.3 complete for package-only CSS.** Every fail below has a
follow-up issue or an explicit fixture-first deferral. Brand pack leg and
independent sign-off remain open (Phases 4 to 5). Do **not** update
VISUAL-BAR "Latest completed pass" until section 6 done criteria are met.

### Ranked craft gaps for Phase 3 (substrate)

1. **Marketing section cadence and surface roles** (S5/S6): enlarge and vary
   marketing vertical rhythm; give feature/band surfaces distinct roles
   without card spam. Kit Idea refs: Tailwind Plus, Preline.
   Tracked: icvoss/django-brickwork#510.
2. **Default display typography**: stop relying on system sans for both body
   and display in package defaults, or document a deliberate base-theme
   display pairing brands can still override. Kit Idea refs: Tailwind Plus,
   daisyUI. Tracked: icvoss/django-brickwork#511.
3. **Marketing mobile chrome in scorecard fixtures, then craft**: put
   `_mobile_nav_toggle.html` into S5/S6 examples used for scoring (fixture
   #509), then raise disclosure craft toward Preline / Tailwind Plus
   HTML-first nav (clean-room CSS only).
4. **S4 dashboard argument**: equal KPI tiles flatten hierarchy. Tracked:
   icvoss/django-brickwork#512.

### Explicit non-claims

- This file does not certify beauty.
- Axe green, archetype harness green, and catalogue counts are out of scope
  for pass/fail here ([VISUAL-BAR.md](../VISUAL-BAR.md) section 4).
- Public copy must not name these kits as brickwork's identity
  ([POSITIONING.md](../POSITIONING.md)).
- Forge stills do not lead any scorecard row.
