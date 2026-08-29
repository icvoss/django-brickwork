# brickwork positioning

**Status:** canonical positioning source. Updated by owner direction 2026-08-25.
**Scope:** every brickwork-facing copy surface (README.md, brickworkui.com,
PyPI description, any future landing page or pitch) derives its claims from
this document and must not diverge from it. Where a surface currently
contradicts it, that surface is wrong; see "Required downstream fixes" below.

**This is not itself marketing copy.** It is an internal reference: the
position, the evidence for each claim, and the boundaries. Anyone writing
brickwork-facing prose lifts claims from here, with the evidence attached.

---

## 1. Position statement

brickwork is being built as the complete interface foundation for
server-rendered Django. Its target coverage is the reusable design system
across public sites, product applications, data-heavy operations,
documentation, editorial publishing and transactional journeys: foundations,
components, layouts, interaction patterns and copyable page archetypes, on
Tailwind 4, Alpine 3 and HTMX 2. Django is its only hard runtime dependency.

The current shipped component inventory is not yet that complete system. Public
copy must distinguish the target from verified shipping coverage, while showing
the examples and released components that prove each available part.

It is brand-agnostic by construction: every visual value is a `--bw-*`
custom property, so a consumer rebrands it by overriding tokens, never by
touching component classes (`docs/BRANDING.md:3-4`).

## 2. Who it is for

A Django team that wants one branded, accessible design system across every
interface it ships, without rebuilding common design decisions for each new
site, app, content surface or workflow. It is not a Django-admin skin, a page
builder, a CMS, or a general Tailwind utility layer (see Boundaries, section
6).

## 3. The lead claim

**Beautiful defaults, proved by the examples.**

The founding statement (`docs/DESIGN.md:15-18`, owner-ratified): "brickwork
is the building blocks a user needs to build beautiful interfaces; our
defaults should be beautiful." Every component clears two hard gates: is it
accessible, and is it beautiful by default.

"Our defaults are beautiful" is an adjective, and a buyer discounts an
adjective. It becomes a claim a buyer can verify rather than take on trust
because the package ships 47 examples (21 pages, 26 sections) built from
nothing but the shipped substrate, with source readable in the repo. A buyer
checks the claim in one click instead of trusting the copy.

**The composition proof.** 46 of the 47 examples are pure composition: zero
bespoke CSS, built entirely from shipped tokens and components. One
exception, stated openly because it strengthens rather than weakens the
claim: `src/brickwork/examples/app/date-range-picker.html` adds a `<style>`
block. Every value in it is an existing `--bw-*` token (no new colour
invented), it is scoped under `.bw-drp` so it cannot leak into a host page,
it carries a comment stating this CSS must never be added to the shipped
stylesheet, and it exists specifically because brickwork ships no date picker
COMPONENT (BR-BW-INPUT-004 is a Fixed rule: no package-maintained
`bw_date_picker` tag, template or Alpine behaviour exists and none ever will;
`src/brickwork/examples/app/date-range-picker.html:5-11`). Three further
inline styles exist in that same file, all `display:none` /
`visibility:hidden`, structural rather than cosmetic
(`src/brickwork/examples/app/date-range-picker.html:632,697,817`).

**Say "no date picker component", never "no date picker".** A developer who
copies that example has a working date range picker: a calendar popover with
weekday and month grids, locale-aware via Django's own `django.utils.dates`,
single-date mode included, over a native `<input type="date">` no-JS floor
that stays the submitted control at all times. What brickwork declines to
ship is the maintained JS calendar component, not the capability. This is the
delivery model in miniature and the clearest illustration of the lead claim:
the substrate plus an example gets a consumer a real date picker they own
outright, with no component contract for brickwork to maintain or break.

**Why the examples are safe to give away.** ADR-056 (referenced at
`src/brickwork/examples/README.md:7`, `CHANGELOG.md:616-620`): examples are
the consumer's to own, never a contract they extend. Pages are copy-paste,
and `src/brickwork/examples/` sits off the Django template-loader path, so a
consumer cannot extend one by accident. The examples state this rule in their
own headers: "It is not on the template loader path, so you cannot extend it
(ADR-056)" (`src/brickwork/examples/app/date-range-picker.html:5-6`).

This resolves what otherwise reads as two competing definitions of
brickwork's value: ADR-054 says the defaults are beautiful; ADR-056 makes the
proof (the examples) safe to give away without turning it into a maintained
contract. One claim, two mechanisms.

**Never introduce a competitor's name as the shape of what brickwork is.**
The owner explicitly raised and rejected "Tailwind for Django" as a lead this
session. Position fresh, with the examples as evidence, not by analogy.

## 4. Supporting claims, in order

### 4.1 The upgrade boundary (the mechanism under the lead)

Substrate, components and shells upgrade under semver; a consumer's own
pages, copied from the examples, are theirs and never touched by an upgrade.
This is what makes "copy the example, then diverge freely" safe: the
copied page is not on the template-loader path, so there is no version of
brickwork that silently changes it (ADR-056, `src/brickwork/examples/README.md:7`).

### 4.2 Tested accessibility (the credibility floor)

State the mechanism, never the word "guarantee". A CI gate cannot guarantee
conformance; it can run consistently and be shown to catch real defects.

| What runs | Scope |
|---|---|
| axe-core WCAG 2.2 AA scan | 164 documents across two fixture sets: 122 hand-maintained pages (61 fixtures x light and dark) plus 42 archetype pages (21 catalogue archetypes x light and dark), blocking every push (`a11y-gate` CI job) |
| No-JS floor suite | blocking |
| Keyboard suites | blocking |
| Mobile-overflow checks | 4 widths: 320, 360, 375, 414px, blocking |
| Pixel-level composited contrast measurement | canvas `getImageData`, blocking |
| Tap-target size measurement | `getBoundingClientRect()`, every fixture at 375px, blocking (`a11y/axe.spec.mjs`, icvoss/django-brickwork#208) |
| Coarse-pointer touch-target measurement | `getBoundingClientRect()` under a `hasTouch: true` browser context, marketing header nav/actions, marketing footer links, breadcrumb links, blocking (icvoss/django-brickwork#242) |

**Two-tier target size.** The package's claimed conformance level is WCAG 2.2
AA, and 2.5.8 Target Size (Minimum) at AA requires 24x24 CSS px; every
interactive control and navigational link meets that floor unconditionally,
gated by the tap-target sweep above. A second tier goes further than the AA
claim: the marketing header nav, the marketing header actions slot, the
marketing footer links, and the breadcrumb trail take a `min-block-size` of
`--bw-size-touch-target-min` (2.75rem/44px, the WCAG 2.5.5 AAA and
platform-HIG bar) under `@media (pointer: coarse)`, so a touch-primary device
gets the larger target while a fine-pointer desktop render is unchanged.
**Gated** against the second row above: the coarse-pointer measurement
asserts >= 44px on those four surfaces and asserts the fine-pointer render
stays under 44px (a regression pin, not a new claim). State it as "44px on
coarse-pointer devices for these four nav surfaces", never a bare "44px
targets" or "AAA conformance": the package's claimed level stays AA.

**Automated testing has a ceiling.** Deque's published figure is that
automated tooling catches roughly 57% of accessibility issues. That figure is
Deque's, not brickwork's; it appears nowhere in this repo's own testing, and
must never be presented as something brickwork measured. State it as a
limitation of the axe-core claim, not a brickwork statistic.

**The strongest proof is the gate's own recorded miss.** The repository's own
test comments record a real 4.25:1 contrast defect that the axe gate ran
green over (`a11y/axe.spec.mjs:361-374`, tracked as issue #118). The reason
is structural, and worth stating: axe's contrast check does not rasterise the
page, so for text painted over a background image it reports "incomplete"
rather than a violation. The scrim was a gradient, so the composited ratio
depended on where a line of text fell: the heading passed while the lede sat
at 4.25:1 at the same time. That miss is why pixel-level contrast measurement
was added.
Admitting the gate missed something once, and naming what was added because
of it, is more persuasive than claiming the gate never misses. Use this in
copy rather than omit it.

**RTL has structural proof, not a tested fixture.** Logical-property counts
(4.3 below) are real structural evidence for RTL support, but there is no
`dir="rtl"` accessibility fixture in the 144-document gate. State this
distinction; do not imply RTL is axe-tested.

### 4.3 Token-first rebranding

`docs/BRANDING.md:3-4`: rebranding is done by overriding `--bw-*` tokens, not
by touching component classes. 358 unique `--bw-*` tokens exist (dated at
3.12.0), 286 overridable. 10 are load-bearing, of which 8 are unconditional:
a brand supplies roughly 16 lines of CSS (8 tokens x light and dark) to
rebrand the whole system, because base-theme derives its fine colour tokens
live from that small load-bearing set (`docs/BRANDING.md:6-8`).

Dark mode is an authored surface, not a computed inversion: `data-theme`
dark values are authored per token, not derived from light
(BR-BW-TOK-002, `docs/BRANDING.md:161-166`). Four theme axes are verified
working: brand (`data-bw-brand`), theme (`data-theme`), density (3 token
files), direction.

**RTL precision.** "Zero physical left/right properties" is true at the
property level: layout is built entirely on logical properties (273 in
source CSS, 500 in the compiled dist). It is not true at the value level:
one documented exception exists, `background-position: right` / `left` at
`frontend/src/components.css:384,391`, explicitly RTL-flipped at line 390
because `background-position` has no logical equivalent. State the exception
whenever the "zero" claim is made; a bare "zero" is disprovable in devtools.

## 5. The full verified numbers (source: code, drift-gated)

Rows marked **gated** are asserted by `tests/test_positioning.py` against the
shipped artefact or importable code at test time: a future edit to either the
code or this table that leaves them disagreeing fails CI. Rows marked
**dated** are mechanically derived as of the stated version but not cheaply
assertable in pytest without running Node or hand-listing every source file;
they carry the version at which they were counted so staleness is visible on
sight, and are refreshed by hand at the next audit.

| Fact | Value | Note |
|---|---|---|
| Components | 48 | 39 core, 9 marketing. **Gated** against `catalogue-manifest.json` |
| Shells | 5 | base, app, auth, centred, marketing. **Gated** against `catalogue-manifest.json` |
| Sections | 26 | **Gated** against `catalogue-manifest.json` |
| Archetypes | 21 | **Gated** against `catalogue-manifest.json` |
| Template tag registrations | 24 total | 17 `inclusion_tag`, 6 `simple_tag`, 1 `filter`. Write "17 component tags" or state the 24 total; never a bare "17 template tags". **Gated** by importing the templatetags libraries and counting `register.tags`/`register.filters` |
| Tokens | 358 unique `--bw-*` | 286 overridable; 10 load-bearing, 8 unconditional. **Overridable count gated** against `token-manifest.json`; the 358 total (all custom properties in compiled `tokens.css`) is **dated** at 3.12.0 |
| Alpine components | 15 | bwDropdown, bwTabs, bwModal, bwToastRegion, bwToast, bwCombobox, bwDismissible, bwTooltip, bwTagInput, bwDropzone, bwSidebarCollapse, bwSlideOver, bwTableSelection, bwSortable, bwThemeSwitch. **Gated** by parsing the `Alpine.data(...)` calls in `frontend/src/js/index.js`'s single registration point |
| Examples | 47 | 21 archetype pages, 26 sections. **Gated** against `catalogue-manifest.json` |
| Icons | 50 vendored Lucide SVG files | exposed as 53 callable names (3 aliases). State precisely; never a bare "50" or bare "53". **Dated** at 3.10.0 |
| Tests | 1023 test functions | across 58 files containing at least one `def test_` (90 Python files exist under `tests/` in total; most are fixtures, conftest or helpers with no test functions of their own). **Dated** at 3.10.0 (counted via `git grep -hE '^def test_' -- tests \| wc -l` for the function count, `git grep -lE '^def test_' -- tests \| wc -l` for the file count); not gated, this count moves with every PR |
| A11y gate | 164 axe-scanned documents | 122 hand-maintained (61 fixtures x light and dark) plus 42 archetype (21 catalogue archetypes x light and dark), blocking CI. Archetype fixture count **gated** against `catalogue-manifest.json`'s archetype count; the 122 hand-maintained fixtures are **gated** against the real `a11y/generate_fixtures.py` run's own written output by `tests/test_a11y_fixture_coverage.py` (icvoss/django-brickwork#226), so this figure can never drift from what the axe gate actually loads. Hand-maintained fixture COVERAGE (does every shell/component/section have at least one fixture) is separately **gated** by the same file against `catalogue-manifest.json`. The 53 to 55 fixture-file step (icvoss/django-brickwork#272, plus icvoss/django-brickwork#275's `bw_ranked_list` fixture landing independently on `main`) added `theme-switch-compact-<theme>.html`, the layout="compact" no-JS floor, and the ranked-list fixture: the pre-existing no-JS coverage only ever rendered layout="inline". The 55 to 56 step (icvoss/django-brickwork#185) added `data-table-empty-cta-<theme>.html`, the `_data_table.html` empty-state action CTA. The 56 to 57 step (the chart card work) added `chart-card-<theme>.html`, covering the real `{% bw_chart_mount %}` tag's accessible-name pairing plus the card's loading, error and empty states. The 57 to 58 step (the sparkline work) added `sparkline-<theme>.html`, covering both tones, the highlight marker and the no-JS floor. The 58 to 59 step (the trend indicator work, VIZ-017) added `trend-indicator-<theme>.html`, covering the up/down/flat states of the standalone `_trend_indicator.html` partial extracted from `_stat.html`'s own trend block. The 60 to 61 step (the scorecard/stat-comparison work, VIZ-011/012/019/020) added `scorecard-<theme>.html`, covering the shared dashboard grid's span= modifiers arranging real `_stat.html` cards, plus `_stat_comparison.html`'s sm/md/lg sizes each paired with a different trend direction. The archetype half then moved from 32 to 36 (16 to 18 catalogue archetypes) when the Data-heavy operations family shipped `queue.html` and `audit-trail.html`, then from 36 to 40 (18 to 20 catalogue archetypes) when the same family shipped `report.html` and `comparison.html`, then from 40 to 42 (20 to 21 catalogue archetypes) when it shipped `analysis-dashboard.html` |
| Logical properties | 273 in source CSS | 500 in compiled dist. **Dated** at 3.10.0. Reproducible: `grep -oE '\b[a-z-]*(inline\|block)[a-z-]*\s*:' frontend/src/components.css \| grep -v 'display\s*:\|inline-block' \| wc -l` gives 269 (declarations whose property name contains `inline` or `block`, excluding `display: inline-block`), plus `grep -oE '(^\|[^-a-z])inset\s*:' frontend/src/components.css \| wc -l` gives 4 (bare `inset:` shorthand declarations); 269 + 4 = 273. The prior 274 figure's methodology was never recorded (commit 8ee225d only logs the audit correction from 142 to 274, no rule); it is not reproducible from the recorded rule above, so the 1-count delta cannot be attributed honestly beyond "not the same method" |
| Version | 3.14.0 | consistent in `pyproject.toml` and `src/brickwork/__init__.py`. **Gated** |
| Hard runtime dependency | Django only | |
| Theme axes | 4 verified working | brand, theme, density, direction |
| Contract manifests | 2 | token, template; generated from source, CI drift-gated. Token manifest carries `minContrast: 4.5` on `fg-on-accent` |

## 6. Design boundaries

| Boundary | Statement |
|---|---|
| Django-admin | Not a Django-admin skin. It is for hand-built interfaces. |
| Design ownership | brickwork owns reusable interface design, including content, data and workflow patterns. Consumers own domain data, permissions, business rules and integrations. |
| Data visualisation | Brickwork owns the visual, layout, state and interaction contract. Consumers may supply a charting engine or specialist renderer that fits that contract. |
| Domain-specific rendering | A consumer owns product-unique semantics and business logic. Brickwork owns a reusable interface pattern whenever one exists. |
| Date entry | A package-maintained JavaScript calendar component is not currently shipped. A full date-range-picker example is available to copy and own. Brickwork owns the date-entry interface contract and may evolve its delivery model when a reusable component is warranted. |
| Utility layer | No general Tailwind utility layer; brickwork ships no `.grid`, `.gap-4`, `.px-3`. |
| Page builder / CMS | Not a page builder, not a CMS. No tenant-arbitrary content or CSS/JS. |
| Sanitisation | Styles markup; does not sanitise it. |
| Auth state | Never reads auth state; state is host-injected. |

## 7. The bounded competitive picture

Research found no package combining app shell, components, theming and a
marketing kit for server-rendered Django. This is **absence of evidence
within the searches run**, not a certified negative: never phrase it as "the
only" or "nothing else exists".

| Comparator | Why it is not the same category |
|---|---|
| django-unfold | Admin-only; not for hand-built application views |
| Flowbite, DaisyUI | Not Django-aware |
| django-crispy-forms | Forms only, no shell, no theming system |
| shadcn-django | Copy-paste, no shell, no upgrade path |

A Django core contributor states on the Django Forum (thread 40718) that
there is no agreed answer for Django UI component reuse. Cite this as
context for the gap, not as brickwork's own claim to uniqueness.

## 8. Market timing

JetBrains/DSF Django Developer Survey 2025 (approximately 4,600 respondents),
via the JetBrains blog summary: HTMX adoption among Django developers rose
from 5% (2021) to 24% (2025); Alpine from 3% to 14%; React fell from 37% to
32%. JetBrains' own framing: "the pendulum has shifted back towards
server-side templates." Attribute to the JetBrains blog summary; the figures
are as reported there, not from the raw dataset.

## 9. Claim-honesty rules for anyone writing brickwork copy

1. **Never write "guarantee" about accessibility.** State the mechanism (what
   runs, on how many documents, both themes, what else blocks) instead.
2. **Automated a11y testing has a ceiling.** Cite Deque's ~57% figure as
   Deque's, as a stated limitation, never as brickwork's own measurement.
3. **Use the gate's own recorded miss** (the 4.25:1 contrast defect that axe
   ran green over) as proof, not something to omit.
4. **Never claim a house aesthetic.** See section 10; brickwork's contract is
   tokens that enable different-looking products, not a look of its own.
5. **Never make an absolute claim a reader can disprove in devtools.** State
   the documented exception alongside any "zero" or "always" claim
   (background-position RTL exception, date-range-picker's scoped CSS).
6. **Bound every competitive claim.** "No package found combining X" plus the
   search-scope hedge, never "only" or "nothing else exists".
7. **Never invent a URL, a customer, a testimonial, a statistic, or a
   capability.** If a fact is missing, write `[FACT NEEDED: ...]` rather than
   filling it plausibly.
8. **State RTL precisely.** Structural proof (logical-property counts) exists;
   an axe-tested `dir="rtl"` fixture does not.
9. **Never state a delivery-model boundary as an absence of capability.**
   brickwork declines to ship certain things as maintained components; that is
   not the same as not providing them. "No date picker" is false and a
   developer disproves it by opening one example; "no date picker component"
   is true and explains the model. Check every "we do not ship X" claim for
   this confusion before publishing it.

## 10. Anti-pattern: no house aesthetic (what killed the previous copy)

The brickworkui.com hero claimed brickwork "produces warm, composed,
editorial-feeling products". Four independent review panels agreed this is a
category error: it attributes a site-level aesthetic to the package. The
warmth came from that site's own token override block, which any consumer
replaces. The words "warm", "editorial" and "composed" appear nowhere in
brickwork's positioning docs as brand voice.

**Rule: brickwork's positioning may never claim a house aesthetic.** The
ratified position is strong contracts and tokens that enable
different-looking products (ADR-054's three-layer model: substrate,
base-theme, brand-theme), where brand themes are the consumer's delta. A
claim that brickwork makes things look a particular way contradicts that
model.

The same copy also claimed "0 bespoke CSS frameworks" while the site shipped
661 lines of site-authored CSS, disprovable in devtools in under a minute.
**Rule: never make an absolute claim a reader can disprove with one tool.**

Note (not brand voice, do not "fix"): "editorial" appears once in the
codebase in a technical sense, distinguishing a callout component from an
application alert (`src/brickwork/examples/sections/content/callout.html:5`).
That is a UI-pattern term, unrelated to the rejected brand-voice claim above.

## 11. Required downstream fixes

These surfaces currently contradict this document and must be corrected to
match it:

| Surface | Contradiction | Fix |
|---|---|---|
| `README.md` | Was stale on package version and the a11y fixture/document count | RESOLVED 2026-08-26: version updated to 3.10.0 and the a11y line restated in the current two-gate, 138-document framing (106 hand-maintained plus 32 archetype), consistent with section 5's A11y gate row |
| `pyproject.toml:8` | Was "Accessible by construction" (a design claim), read against `README.md:11-12`'s "a *tested* guarantee... not a claim" (a verification claim positioned explicitly against design claims) | RESOLVED: `pyproject.toml:8` now reads "WCAG 2.2 AA tested in CI", which is a verification claim and aligns with README.md's framing; no reconciliation remains outstanding |
| `PILOT-ADOPTION-BRIEF.md` | Was pinned to 0.3.0 and the private index, and dropped "professional" from the definition | RESOLVED 2026-08-24: rewritten as a routing quickstart and renamed `docs/QUICKSTART.md` |
| Four documents each currently state brickwork's singular value differently: `README.md:10-13` ("its value is the professional baseline"), `docs/BRANDING.md:3-4` ("brickwork's whole point is that you rebrand it by overriding tokens"), `docs/DESIGN.md:15-18` (the beautiful-defaults founding statement), `pyproject.toml:8` (the category definition) | Four different leads for one product | This document settles it: beautiful defaults, proved by the examples (section 3), is the lead. Token-first rebranding (4.3) and the professional/tested-accessibility framing (4.2) become supporting claims, not competing leads |

---

*Every factual claim in this document carries its evidence inline. If a
future edit adds a claim without a file:line, ADR number, or named external
source next to it, that edit fails review.*
