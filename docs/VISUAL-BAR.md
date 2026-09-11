# Visual bar: meet-or-beat Tailwind UI kits

**Status:** normative internal product bar. Adopted 2026-09-11.
**Audience:** package maintainers, design reviewers, showcase authors.
**Not for:** public marketing copy. Competitor names stay out of README,
PyPI, and brickworkui.com hero claims (`POSITIONING.md` claim-honesty rules).

This document stamps the visual quality bar brickwork must meet for the
workspace default: our Django projects use brickwork so substrate updates
propagate; brickwork must also look finished next to the leading Tailwind UI
kits. Composition tests, axe gates and catalogue counts are separate evidence.
They do not certify this bar.

**Companion docs:** [POSITIONING.md](POSITIONING.md) (lead claim and honesty),
[DESIGN.md](DESIGN.md) (token vocabulary), [BRANDING.md](BRANDING.md)
(override recipes), [INTERFACE-SYSTEM.md](INTERFACE-SYSTEM.md) (coverage
contract, not visual taste).

---

## 1. Licence and clean-room (non-negotiable)

Borrow **look and idea only**. Every shipped change is clean-room markup and
CSS on the `--bw-*` layer (reaffirming `BR-BW-MKT-003` and the standing
Tailwind Plus reference-only ruling).

| Allowed | Forbidden |
|---|---|
| Screenshots, notes, scorecards comparing rendered jobs | Pasting markup, class strings, or structure from a kit |
| "Kit X wins on spacing rhythm; fix brickwork tokens/CSS" | Redistributing kit assets, Figma files, or derivatives in the wheel |
| Local Tailwind Plus trees under the umbrella `docs/_examples/` as private Idea refs | Shipping Tailwind Plus code or anything competitive with Tailwind Labs under that licence |

MIT and similar kits (daisyUI, Flowbite free core, Preline free library,
Headless UI, and the others below) are Idea-reference only for the same
reason utility markup would bypass brickwork's token, brand and a11y
contract. Tailwind Plus remains reference-only even where we already own
copies; new purchases being closed does not relax the licence line.

---

## 2. Frozen kit panel (independent shortlist, 2026-09-11)

Do not expand this panel mid-cycle. Optional secondary Idea refs
(FlyonUI, HyperUI, Meraki UI, Mamba UI, Tailwind Starter Kit) stay off the
scorecard unless a miss has no panel analogue.

| Kit | Role as bar | What we borrow as ideas | What we do not take |
|---|---|---|---|
| **shadcn/ui** | Best for React/Next product UI taste: Tailwind-native, copy-paste ownership, strong a11y | Semantic token clarity, option grammar, compositional taste, a11y as default | React ownership model as our upgrade story (we pin and upgrade shells/components); their markup |
| **daisyUI** | Best free all-framework option: CSS plugin, themes, zero JS, strong for MVPs | Theme density, state coverage, "looks done" with little setup, no-JS expectation | Plugin/utility coupling that bypasses `--bw-*` |
| **Flowbite** | Best buyable full kit now: free core + Pro blocks/templates; multi-framework + Figma | Pattern inventory of a complete kit; block/template breadth as a coverage ambition | Markup, JS plugins, multi-framework bindings as brickwork's shape |
| **Preline UI** | HTML-first sites and dashboards; large free library + Pro blocks | Closest stack cousin: section and dashboard compositions, HTML-first interactions | Class names and script idioms as copy |
| **Tailgrids** | React blocks + Figma design system; solid Tailwind Plus alternative | Marketing and app block variety; how a design system is packaged for buyers | React/Figma artefacts into the package |
| **Tailkit** | Cheapest paid snippets (HTML/React/Vue); good for indies | Practical "indie completeness" checklist: what a paid snippet kit is expected to cover | Snippet-dump delivery; unpaid redistribution of their snippets |
| **Headless UI** | Accessible unstyled primitives (React/Vue) | Behaviour and a11y contracts for overlays, menus, disclosure, focus | Unstyled-only posture (brickwork owns chrome and tokens) |
| **Tailwind Plus** | Quality ceiling where we already own the set; new purchases closed | Hierarchy, section rhythm, header/footer/flyout craft under `docs/_examples/` | Any code or derivative in shipped templates or CSS |

### Review priority within a cycle

1. **Craft and HTML-first:** Tailwind Plus, Preline UI  
2. **Product UI and theme density:** shadcn/ui, daisyUI  
3. **Coverage gaps the first four expose:** Flowbite, Tailgrids, Tailkit  
4. **Behaviour / a11y only:** Headless UI, where the miss is interaction, not paint  

---

## 3. Surfaces under test

Fixed package-owned jobs. Prefer shipped examples under
`src/brickwork/examples/` rendered with **package-only CSS**, then the same
surfaces with **one intentional brand** override. Showcase brand CSS alone
does not prove package defaults.

| ID | Surface | Primary example / shell |
|---|---|---|
| S1 | App list | `examples/app/list.html` + app shell |
| S2 | App detail | `examples/app/detail.html` |
| S3 | App form | `examples/app/form.html` |
| S4 | App dashboard | `examples/app/dashboard.html` |
| S5 | Marketing landing | `examples/marketing/landing.html` + marketing shell |
| S6 | Marketing pricing | `examples/marketing/pricing.html` |
| S7 | Docs article | `examples/docs/article.html` + docs shell |
| S8 | Dense ops | `examples/ops/` report or dense list when shipped; else analysis-dashboard + data table |

Fixtures must be credible for the job (populated filters, realistic fields,
working assets). Thin or broken fixtures are site defects first; do not score
them as package visual wins or losses until corrected.

---

## 4. Scorecard axes

Each surface × theme (light, dark) × viewport (desktop ~1440px, phone ~375px).
Score **pass / fail / not applicable**. Failures cite the kit that sets the
bar and a one-line borrow idea.

| Axis | Pass means |
|---|---|
| Hierarchy | One clear focal point; heading scale is deliberate, not near-body |
| Typography | Type roles read as a system; measure and weight support the job |
| Spacing rhythm | Consistent vertical cadence; no large accidental voids or cramped bands |
| Surface differentiation | Content roles are distinguishable without relying on endless identical bordered boxes |
| Density | Appropriate for the family (marketing air vs ops density); not sparse by accident |
| States | Loading, empty and error are designed where the component promises them |
| Navigation / mobile chrome | Desktop nav and a usable mobile pattern; no verbatim consumer rebuild of shell internals |
| Forms | Labels, controls, help and errors align; primary actions are obvious |
| Section cadence (marketing) | Sections feel sequenced, not stacked templates |
| Brandability | The same composition still holds after a seven-token brand override |

**Out of scope for this scorecard:** axe CI green alone, inventory counts,
kiln or demo identity preference, whether every `INTERFACE-SYSTEM.md`
archetype exists.

---

## 5. Empty scorecard (fill on a rendered pass)

Record package version, date, reviewer, and whether the render used
package-default CSS only or also a named brand pack.

| Surface | Kit that led | Axes failed | Borrow idea (clean-room) | Package follow-up |
|---|---|---|---|---|
| S1 App list | | | | |
| S2 App detail | | | | |
| S3 App form | | | | |
| S4 App dashboard | | | | |
| S5 Marketing landing | | | | |
| S6 Marketing pricing | | | | |
| S7 Docs article | | | | |
| S8 Dense ops | | | | |

Store completed scorecards under `docs/audits/` with a dated filename, e.g.
`docs/audits/2026-09-11-visual-bar-scorecard.md`. Link the latest pass from
this section when one exists.

**Latest completed pass:** none yet.

---

## 6. Done criteria

This bar is met for a release train when:

1. An independent rendered review has filled the scorecard for S1 to S8 at
   both themes and both viewports against at least the priority-1 and
   priority-2 kits.  
2. Every fail has a package issue or an explicit "won't fix / consumer-owned"
   reason.  
3. Package-default CSS (no showcase brand) clears the axes that failed for
   substrate reasons.  
4. Public copy still does not claim a house aesthetic or name competitors as
   brickwork's identity (`POSITIONING.md` sections 3, 9, 10).

Workspace rule (separate from this file): our Django projects that ship
hand-built template UI standardise on brickwork so pins receive substrate
updates. This bar is what makes that standard visually defensible.

---

## 7. Revision

- **Panel freeze:** change the kit table only in a dated amendment with owner
  agreement.  
- **Surfaces:** add only when a new family becomes part of the workspace
  default proof set.  
- **Secondary kits:** may appear in a single scorecard row as Idea refs; they
  do not join the frozen panel without an amendment.
