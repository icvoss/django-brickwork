# brickwork catalogue: information architecture

**Status:** Wave 0 (W0.2), package slice of the interface-system delivery
plan. Structure and mechanism, not a finished catalogue (plan decision D5):
this document and the manifest it describes cover what ships today; later
waves document their own additions as they ship, in their own PRs.

This is the IA for browsing and searching what brickwork ships: the
families and archetypes the catalogue organises around, the starting
journey a newcomer follows, the machine-readable manifest a site builds a
catalogue surface from, and the two open design questions this slice
resolved (render inputs, and family/wave status) with the reasoning
recorded.

## 1. The catalogue nouns

Four kinds, and they are the whole of D4's public grammar (Shells, Blocks,
Sections, Components) plus the one new catalogue-only noun D4 ratified
(Archetype). "Family" is a fifth concept, but never a fifth catalogue NOUN in
this sense: see section 3.

| Kind | What it is | Where it lives |
|---|---|---|
| Shell | The document skeleton and chrome a page extends | `templates/brickwork/shell/*.html`, `brickwork_marketing/shell/marketing.html` |
| Component | A reusable piece: button, card, table, hero, pricing table, ... | `templates/brickwork/components/_*.html`, `brickwork_marketing/components/_*.html` |
| Section | A copy-paste example of ONE band (a hero, a CTA, a pricing block) | `examples/sections/<type>/<variant>.html` |
| Archetype | A copy-paste example of a COMPLETE page | `examples/base.html`, `examples/app/*.html`, `examples/auth/*.html`, `examples/marketing/*.html`, `examples/ops/*.html` |

Forms (`forms/_*.html`) and nav (`nav/_*.html`) templates are their own
tag-consumed surface (`{% bw_form %}`, `{% bw_nav %}` and friends) rather
than catalogue components in this count, matching ROADMAP.md's baseline.

## 2. The family and archetype matrix

A family is a use-case cluster (INTERFACE-SYSTEM.md's term), spanning
shells, sections and archetypes, used for site IA, URLs and headings. It
groups catalogue items by the job a team is doing, not by what kind of
template they are.

**Shipped today** (has at least one archetype in the manifest):

| Family | Archetypes shipped |
|---|---|
| Product applications | list, detail, dashboard, create/edit (form), settings, confirm, wizard, date-range-picker, console |
| Transactional journeys | sign-in, sign-up, password reset |
| Marketing and public web | landing, pricing, about |
| Data-heavy operations | queue, audit trail, report, comparison |

**Planned, not yet shipped** (INTERFACE-SYSTEM.md names the required
archetype set; ROADMAP.md carries the wave each family expands in). This
document does not restate the wave numbers: see section 6 for why, and read
ROADMAP.md directly for current wave assignments, which move as waves land.

- Documentation
- Editorial and publishing

**Arranging bands within an app-surface archetype** (product applications and
data-heavy operations both extend an app-family shell) uses a closed,
two-class vocabulary: `.bw-band-grid` (with `--2`/`--3`/`--4`) for N-column
arrangement and `.bw-band-heading` for a band's own visible title. See
`docs/DESIGN.md` section 6.9 for the token-level detail (floors, the
type-role sizing, and the family-boundary test that keeps marketing-family
classes off these surfaces); `examples/ops/analysis-dashboard.html` is the
first shipped consumer of both.

Shells and components are cross-family building blocks, not scoped to one
family; the manifest's `usedByArchetypes` field on each names the shipped
archetypes drawing on it, from which the families in play can be read off
via each archetype's own `family` field (see section 5).

## 3. O1: family is a catalogue-only noun (verbatim)

Ratified as an owner ruling at adoption. Recorded here verbatim, and in the
delivery plan (`oss/docs/plans/brickwork-interface-system-delivery.md`):

> O1. Family vocabulary: catalogue-only noun. Family is a catalogue
> taxonomy noun, allowed in site IA, URLs and docs, never a package API
> identifier. Ratified as an owner ruling, recorded here and in the W0.2 IA
> document; no separate ADR needed.

In force: `family` is a JSON field and a documentation word only. No
template tag name or option, no CSS class or `--bw-*` token, and no public
Python name may carry "family" (or "primitive" or "pattern": the same
vocabulary gate, D4). A package PR adding a public identifier carrying any
of those three words is rejected in review regardless of intent.

**This is why the in-package catalogue-manifest reader is internal.** The
shipped JSON is the public contract (section 5): a consumer reads
`catalogue-manifest.json` directly, the same pattern brickworkui.com's own
gallery already uses for `template-manifest.json`. `brickwork.services.
_catalogue_manifest` (underscore-prefixed, this repo's existing convention
for a deliberately internal module) exists only to serve this repo's own
in-package consumers, its drift test today and the W0.3 harness next, so
its Python identifiers, including `FamilyEntry` and `families()`, carry
"family" without being public API and without touching O1: nothing there
is importable as part of `brickwork`'s documented public surface. A public
Python reader was considered and rejected for Wave 0 on exactly this
ground: no external consumer need for one has been shown, and inventing
public API ahead of a demonstrated need is the wrong side of YAGNI. If
that need appears later, it is a fresh O1 boundary question for the owner,
not a rename to make on a review pass.

## 4. The starting journey

The spine every piece of onboarding content, every gallery page, and this
document itself should walk a newcomer through, in this order:

1. **Choose a family.** What job is this interface for: a product console,
   a sign-in flow, a marketing page? Section 2's matrix is the index.
2. **Choose an archetype.** Within the family, which complete page is
   closest to what you are building? Not every family has full coverage yet
   (section 2); where it does not, start from the nearest shipped archetype
   or a section and compose.
3. **Apply your brand.** Seven load-bearing `--bw-*` tokens (see
   `docs/BRANDING.md`) turn the neutral default into your brand, before you
   touch a single template.
4. **Copy or extend.** An archetype or section is copied into your own
   `templates/` tree and edited (ADR-056: never extended from the
   installed package). A shell is extended and its blocks filled. A
   component is called by tag or include, in place, with your content.
5. **Connect your Django behaviour.** Wire the view: real querysets, real
   forms, the 422 HTMX loop for validation, real nav config. The archetype
   or section you copied already shows the shape of the context it expects
   (each file's own leading `{% comment %}` documents it).

## 5. The manifest: what it is, what it is not

`catalogue-manifest.json` (shipped at
`static/brickwork/dist/catalogue-manifest.json`, generated by
`scripts/generate_catalogue_manifest.py`) is the machine-readable record of
every shipped shell, component, section and archetype: 6 shells, 49
components, 27 sections, 21 archetypes (103 items; re-derived from a
regenerated manifest after the code-display work landed, icvoss/django-brickwork#259).
The 40th component was
`_theme_switch.html` (W0.4, icvoss/django-brickwork#228), the 41st was
`_ranked_list.html` (#183), and the 42nd was `_chart_card.html`, all shipped
after this document's original W0.2 baseline of 39 was written. Wave 1's viz
primitives then took it to 48, in landing order: `_sparkline.html` (43,
`cc4f793`), `_trend_indicator.html` (44, `65a4c78`), `_gauge.html` (45,
`915c707`), `_scorecard.html` and `_stat_comparison.html` (46 and 47,
`0c9104e`), and `_chart_data_table.html` (48, CHT-012). Wave 2's content
primitives then added `_code.html` (49, #259), a labelled, scrollable code
panel with a stated syntax-highlighting boundary (see its own header
comment): brickwork ships no tokenizer, a consumer highlights and passes
already-marked-safe markup in. The shell count separately moved to 6 when
the docs shell landed (ADR-091, #439), which this sentence had not
previously named. The ordinals are read
from each file's own adding commit, not from memory: an earlier version of
this sentence jumped from 42 to 46 and left three landings unnamed, including
the gauge, which appeared nowhere in this document at all.

**The original W0.2 baseline, as a fixed historical fact rather than a
moving check** (ROADMAP.md's "Current baseline" section states the same
figures in prose): 5 shells, 39 components, 42 examples split 16 archetypes
plus 26 sections. Archetypes moved from that baseline too, independently of
the component count above: the queue/audit-trail work opened the Data-heavy
operations family with two archetypes (18), and the report/comparison work
added two more to the same family (20); the analysis-dashboard work then
added a 21st. This paragraph, not a test assertion, is where that baseline
is recorded going forward (icvoss/django-brickwork#386): a frozen fact
belongs where it does not need editing every time the shipped tree grows
past it.

**It is a sibling of `template-manifest.json`, never merged into it**
(plan decision D8). `template-manifest.json` is the versioned
BR-BW-VER-001 contract for block/partial names: renaming or removing one
requires the parallel-support cycle and a major bump. Catalogue taxonomy
is a different consumer (a site building a catalogue browsing surface, not
a template author checking a block name is stable) and a different
stability promise: it is descriptive, generated from the shipped tree at
release time, and may evolve in minors as the catalogue itself grows
across waves.

**The JSON is the public contract, not a Python API.** A consumer reads
`catalogue-manifest.json` directly off the installed package, the same
pattern brickworkui.com's own `docs_app/gallery/manifest.py` already uses
for `template-manifest.json`. This repo ships an in-package reader
(`brickwork.services._catalogue_manifest`) for its own drift test and the
coming W0.3 harness, deliberately internal (underscore-prefixed) so no
Python identifier there is public API: see section 3 for why this is what
O1 requires, not an accident of naming.

Per item, the manifest carries:

- `name`, `kind` (`shell`/`component`/`section`/`archetype`), `family`
  (the archetype/section's family, `null` for a cross-family shell or
  component, or for `examples/base.html`, which is a raw document skeleton
  tied to no family);
- `templatePath` / `docSource`: the shipped path, and the pointer to where
  its full contract (states, accessibility notes, responsive behaviour) is
  documented today: **the template or example's own leading
  `{% comment %}`**, exactly the same header every shipped template already
  carries per the `brickwork` skill's documented convention ("Every shipped
  template documents its own contract... in a leading `{% comment %}`").
  Wave 0 ships this as a pointer, not a duplicate copy: see section 6 for
  why states/a11y/responsive facts are not restated as manifest fields yet;
- `usedByArchetypes` / `usedBySections` (on shells and components): which
  shipped examples actually compose this item, derived by walking the
  compiled template tree of every example (`{% include %}`/`{% extends %}`
  targets and `{% bw_* %}` tag calls), never hand-maintained;
- `composesItems` (on sections and archetypes): the inverse, which
  shells/components a given example pulls in;
- `requiresContext` (on sections and archetypes): whether the example needs
  render-context data to show its real content, rather than rendering from
  an empty context (see section 7).

The manifest also carries a top-level `families` list: package-truth
shipped-coverage counts only (`archetypeCount`, `sectionCount` per family),
no status or wave (section 8). `sectionCount` is `0` for every family
today because a section's own `family` field is `null`: a section lives
under its TYPE (`hero`, `cta`, `pricing`, ...), not one family, since the
same section is reusable across several families (a `cta/split` section
works equally in a marketing page or a product-application upsell). Only
archetypes are family-scoped today, because an archetype example lives
under one family's own example directory (`app/`, `auth/`, `marketing/`).

### 5a. The docSource label convention (icvoss/django-brickwork#234)

The pointer described above (`docSource`, "the template or example's own
leading `{% comment %}`") had no internal structure until #234: every
shipped item carried freeform prose plus the pre-existing Required/Optional
context markers, but nothing a consumer could parse for states,
accessibility notes or responsive behaviour specifically. A programmatic
scan of the 3.9.0 wheel found 46 of 87 items with no accessibility-flavoured
prose at all (including all 5 shells and every archetype), 58 with no
responsive-flavoured prose, and two examples
(`examples/sections/hero/media-behind.html`,
`examples/sections/hero/split-media.html`) with no leading comment
whatsoever.

**The format, settled with the consuming site to match its merged
`docs_app/gallery/docstrings.py` parser**: three line-leading labels inside
an item's existing leading `{% comment %}` block, exact spelling `States:`,
`Accessibility:`, `Responsive:` (capitalised, trailing colon, at line
start). Each label's prose runs until the next recognised label or the end
of the comment; a continuation line is indented so it reads as part of the
same entry rather than a new one. The three labels sit AFTER any existing
`Required context:`/`Optional:` sections, so the context-parsing convention
those sections already served is untouched; there is no ordering
requirement among the three labels themselves, and no markdown headings.

**The honesty rule governs content, not just presence.** Every sentence is
written FROM the template's own markup, its CSS, and the gate suites that
actually exercise it, never invented or padded to look complete:

- `States:` names the states the template genuinely implements (read off
  its classes, its JS, its conditional markup); an item with no states says
  so plainly rather than listing states it does not have.
- `Accessibility:` names what the blocking a11y suites actually verify for
  that item (axe WCAG 2.2 AA, keyboard operability, the no-JS floor,
  composited contrast where applicable) plus the item-specific semantics
  readable in its own markup (roles, aria attributes, focus behaviour). A
  claim that a gate covers an item is made only when a fixture or spec
  genuinely exercises that item; where coverage is thinner than a sibling
  component's (several enhanced-JS behaviours, for example, are asserted
  only at the Python/string level, with no browser-driven interaction
  test), the label says so rather than overstating it.
- `Responsive:` names the item's actual breakpoint behaviour in terms of
  the W0.1 tokens (`--bw-breakpoint-sm/md/lg/xl`), or states plainly that
  the item carries no width-dependent behaviour. A claim of "no breakpoint
  switch" is verified against the shipped CSS, not assumed from the
  item's shape.

**The gate**: `tests/test_catalogue_manifest.py` parametrizes one check per
manifest item (87 cases), asserting all three labels appear line-leading in
the FIRST `{% comment %}` block at that item's `docSource` path, resolved
through the same sanctioned mechanism its kind already uses elsewhere in
this repo (`django.template.loader.get_template(...).origin.name` for
shells/components; `brickwork.examples.read_example(...)` for
sections/archetypes). This is a presence gate, not a content gate: it
catches a missing label (or a missing comment block entirely, which is how
the two previously-commentless hero examples are caught) mechanically,
the same way every drift test in this file catches a missing fact; the
honesty rule above is a review-time discipline this gate cannot enforce by
itself, matching the "presence... never length or content" wording the
gate's own test docstring carries.

## 6. Wave 0 lookup path for returning practitioners, and what is deferred

**Served in Wave 0** (plan decision D5, scoped exactly to this): the
existing gallery index (browse by kind) plus search over the catalogue
manifest fields (`name`, `kind`, `family`). A practitioner who already
knows brickwork and wants to find "the pricing section" or "the settings
archetype" again is served by the manifest's flat, filterable item list.

**Deferred, deliberately, past Wave 0:**

- A per-item LIVE PREVIEW (a rendered page). #234 (still Wave 0 scope, a
  package slice) backfilled the states/accessibility/responsive DETAIL
  itself into every item's docSource header comment (section 5a), so that
  content now exists and is gated; what remains deferred is a site
  rendering it as a browsable per-item detail page. ROADMAP.md rule 5
  requires every wave to document its own additions as it ships; Wave 0's
  job is the manifest structure those additions land into, not a finished
  per-item detail page.
- A richer semantic/faceted search than flat field matching (filtering by
  "what states does this support", "is this keyboard-navigable" as
  structured, queryable facts rather than free-text pointers).
- Family/wave status surfaced in the manifest (section 8): the site's IA
  pages for a not-yet-shipped family are hand-authored against
  ROADMAP.md, not generated, by deliberate choice.

## 7. Render inputs: deferred by design

**Decision: the manifest does NOT carry render inputs (the context/data
needed to render an example's real content). This was weighed explicitly
and ruled out for Wave 0.**

The site's own render-fixture cost is real: `docs_app/gallery/fixtures.py`
is ~530 lines of hand-maintained `Fixture` context, one per item, and it is
the single biggest hand-maintenance surface in the site's gallery. If the
manifest's example entries carried the render inputs directly, the site
would not need to hand-write most of that file.

The reason it is ruled out anyway: **most of that context is not
JSON-representable without silently becoming a different, weaker contract**.
Reading the shipped tree confirms this directly, not by assumption:

- The majority of sections render from a genuinely empty context by design
  (typed copy inline, per ADR-056/the `brickwork` skill): these need no
  render-input field at all, `{}` already is the correct input, and the
  manifest's `requiresContext: false` already says so per item.
- A minority need list-of-dicts data a template cannot build inline
  (`features/icon-grid`, `pricing/three-tier`, `stats/inline-band`, all
  three `listing` variants: 6 sections, matching the manifest's
  `requiresContext: true` set). THIS part could be encoded as a JSON shape
  hint (`{"features": [{"icon": "str", "heading": "str", ...}]}`), and
  would be genuinely useful.
- But almost every ARCHETYPE (19 of 21; only `app/confirm.html` and
  `base.html` render empty) needs context that is not a JSON shape at all: a
  bound Django `Form` instance (`auth/signin.html`, `app/form.html`,
  `app/wizard.html`, `app/settings.html`), a resolved nav tree (every
  `app/*` archetype, via `{% bw_nav %}`), breadcrumb/table-row dicts that
  are genuinely data-shaped but sit alongside the Form/nav requirement in
  the same context. `tests/test_examples.py`'s own `_EXAMPLE_CONTEXTS` and
  the site's `fixtures.py` both confirm this independently: neither is a
  flat, JSON-safe dict for the archetype set.

Shipping ONLY the JSON-representable minority (the 6 sections) as render
data would produce a manifest that looks complete but is not: a consumer
calling `render(template, manifest_context)` gets a real render for those
6 items and a blank or broken render for essentially every archetype,
which is a worse failure mode than no render-input field at all, because
it invites exactly that call without a signal that most items are excluded.
That is the same class of empty-preview bug the site's own
`_leaf_markers`/marker-gate machinery in `fixtures.py` exists to catch, and
this manifest declining to ship a half-solution is what keeps that gate
meaningful rather than routinely half-bypassed.

**What the manifest ships instead**, so the site's fixture cost is at
least bounded rather than open-ended: `requiresContext` (so the site knows,
without opening 98 files, which items are the ones that need nothing, and
can retire any fixture entry for those to `{}`) and `docSource` (a pointer
to exactly where the required shape is documented in prose, so writing a
fixture is "read this one file's header comment" rather than "scrape the
whole tree"). This is a real, if partial, reduction in the fixture cost, not
a decision that the cost is untouched.

If a future wave wants to close this gap further, the honest next step is
a typed "fixture shape" concept scoped to the JSON-representable subset
only (the 6 sections above, plus any future ones with the same shape), with
its own explicit "form/nav-carrying items are out of scope" boundary,
rather than widening this field to a false promise of completeness.

## 8. Family status: package truth ships, roadmap truth does not

**Decision: the manifest carries shipped-family coverage (package truth).
It does NOT carry planned-family status or wave assignment (roadmap
truth). This was weighed explicitly, against a specific proposal from the
consuming site session (include both, with per-family status and wave),
and split rather than accepted or rejected whole.**

The discriminator is whose truth each half is, not whether a source
document exists for it:

- **The family taxonomy itself, and which shipped items belong to which
  family, is package truth.** It is derived the same way every other field
  in this manifest is: mechanically, from the shipped tree (an archetype's
  own directory), regenerated on every run, and caught by the drift test
  if it and the tree disagree. This ships: the manifest's top-level
  `families` list names every family with at least one shipped item, and
  each item's own `family` field (section 5) is populated from the same
  walk. Section 2's "Shipped today" table is this data, not a hand-typed
  copy of it.
- **Per-family status ("shipping" vs "planned") and wave assignment are
  roadmap truth.** There is no shipped-tree signal a generator can walk to
  produce "Wave 1" for Data-heavy operations: that fact lives only as
  prose in ROADMAP.md, a document the delivery plan itself declines to
  attach dates to ("ordered by dependency and user value, not by date").
  The only way the generator could produce it is by hand-transcribing
  ROADMAP.md's current wording into Python, which does not remove a
  source of truth, it adds a second one: the generator's transcription can
  now drift from ROADMAP.md with nothing to catch it, which is exactly the
  class of drift D8 created this sibling-manifest split to prevent in the
  first place, recreated one level down.
- **The staleness this produces is not bounded by the currency process.**
  A wheel built at 3.8.0 that asserts "Data-heavy operations: planned,
  Wave 1" keeps asserting exactly that in every install of 3.8.0, for as
  long as any consuming site stays pinned there, including well after
  Wave 1 actually ships in some later minor. W0.7's currency process
  bounds how long a stale claim can survive in this repo's own `main`; it
  has no mechanism that reaches into an already-published wheel sitting on
  a site's pin and updates what it asserts. A confidently wrong "planned"
  label on a family that has since shipped is a worse outcome for a
  catalogue consumer than no label at all.

**What ships instead**: `families` (package truth, mechanically generated,
drift-tested) plus the site building its own unshipped-family pages from
site-side content or a direct read of the umbrella plan, exactly as the
orchestrator's split proposes. If ROADMAP.md's wave assignments later
become something worth exposing as data rather than prose (for example, a
structured roadmap manifest living in `oss/docs/plans/` with its own
drift discipline against ROADMAP.md, read independently by a site), that
is a new artefact with its own review, not a field bolted onto this one.

## 9. Regenerating the manifest

```
DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:. \
    python scripts/generate_catalogue_manifest.py
```

Run after any change to a shipped shell, component, or example. CI's
`test` job re-runs this generator and fails the build on any diff
(`tests/test_catalogue_manifest.py`), the same drift discipline
`template-manifest.json` and `token-manifest.json` already carry. Do not
hand-edit the committed `catalogue-manifest.json`.
