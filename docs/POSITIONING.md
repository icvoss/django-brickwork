# brickwork positioning

**Status:** canonical positioning source. Approved by the owner 2026-08-24.
**Scope:** every brickwork-facing copy surface (README.md, brickworkui.com,
PyPI description, any future landing page or pitch) derives its claims from
this document and must not diverge from it. Where a surface currently
contradicts it, that surface is wrong; see "Required downstream fixes" below.

**This is not itself marketing copy.** It is an internal reference: the
position, the evidence for each claim, and the boundaries. Anyone writing
brickwork-facing prose lifts claims from here, with the evidence attached.

---

## 1. Position statement

brickwork is a professional UI substrate for server-rendered Django: an
application shell, navigation, an accessible form-field renderer, and
interaction primitives (modal, toast, dropdown, combobox, tabs, disclosure),
wrapped behind stable components, on Tailwind 4, Alpine 3 and HTMX 2. Django
is its only hard runtime dependency.

It is brand-agnostic by construction: every visual value is a `--bw-*`
custom property, so a consumer rebrands it by overriding tokens, never by
touching component classes (`docs/BRANDING.md:3-4`).

## 2. Who it is for

A Django team hand-building console, dashboard, or marketing-adjacent views
who wants a professional, accessible baseline without building a design
system first. Not a fit for a team that wants a Django-admin skin, a page
builder, or a general Tailwind utility layer (see Boundaries, section 6).

## 3. The lead claim

**Beautiful defaults, proved by the examples.**

The founding statement (`docs/DESIGN.md:15-18`, owner-ratified): "brickwork
is the building blocks a user needs to build beautiful interfaces; our
defaults should be beautiful." Every component clears two hard gates: is it
accessible, and is it beautiful by default.

"Our defaults are beautiful" is an adjective, and a buyer discounts an
adjective. It becomes a claim a buyer can verify rather than take on trust
because the package ships 42 examples (16 pages, 26 sections) built from
nothing but the shipped substrate, with source readable in the repo. A buyer
checks the claim in one click instead of trusting the copy.

**The composition proof.** 41 of the 42 examples are pure composition: zero
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
| axe-core WCAG 2.2 AA scan | 86 documents (43 fixtures x light and dark themes), blocking every push (`a11y-gate` CI job) |
| No-JS floor suite | blocking |
| Keyboard suites | blocking |
| Mobile-overflow checks | 4 widths: 320, 360, 375, 414px, blocking |
| Pixel-level composited contrast measurement | canvas `getImageData`, blocking |

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
`dir="rtl"` accessibility fixture in the 86-document gate. State this
distinction; do not imply RTL is axe-tested.

### 4.3 Token-first rebranding

`docs/BRANDING.md:3-4`: rebranding is done by overriding `--bw-*` tokens, not
by touching component classes. 332 unique `--bw-*` tokens exist, 265
overridable. 10 are load-bearing, of which 7 are unconditional (the "core
seven"): a brand supplies roughly 14 lines of CSS (7 tokens x light and
dark) to rebrand the whole system, because base-theme derives its fine
colour tokens live from that small load-bearing set (`docs/BRANDING.md:6-8`).

Dark mode is an authored surface, not a computed inversion: `data-theme`
dark values are authored per token, not derived from light
(BR-BW-TOK-002, `docs/BRANDING.md:161-166`). Four theme axes are verified
working: brand (`data-bw-brand`), theme (`data-theme`), density (3 token
files), direction.

**RTL precision.** "Zero physical left/right properties" is true at the
property level: layout is built entirely on logical properties (274 in
source CSS, 297 in the compiled dist). It is not true at the value level:
one documented exception exists, `background-position: right` / `left` at
`frontend/src/components.css:384,391`, explicitly RTL-flipped at line 390
because `background-position` has no logical equivalent. State the exception
whenever the "zero" claim is made; a bare "zero" is disprovable in devtools.

## 5. The full verified numbers (source: code at 3.5.1)

| Fact | Value | Note |
|---|---|---|
| Components | 39 | 30 core, 9 marketing |
| Shells | 5 | base, app, auth, centred, marketing |
| Template tag registrations | 18 total | 14 `inclusion_tag`, 3 `simple_tag`, 1 `filter`. Write "14 component tags" or state the 18 total; never a bare "14 template tags" |
| Tokens | 332 unique `--bw-*` | 265 overridable; 10 load-bearing (7 unconditional, the "core seven") |
| Alpine components | 13 | |
| Examples | 42 | 16 pages, 26 sections |
| Icons | 50 vendored Lucide SVG files | exposed as 53 callable names (3 aliases). State precisely; never a bare "50" or bare "53" |
| Tests | 899 test functions | across 52 files |
| A11y gate | 86 axe-scanned documents | 43 fixtures x light and dark, blocking CI |
| Logical properties | 274 in source CSS | 297 in compiled dist |
| Version | 3.5.1 | consistent in `pyproject.toml` and `src/brickwork/__init__.py` |
| Hard runtime dependency | Django only | |
| Theme axes | 4 verified working | brand, theme, density, direction |
| Contract manifests | 2 | token, template; generated from source, CI drift-gated. Token manifest carries `minContrast: 4.5` on `fg-on-accent` |

## 6. What brickwork is not (boundaries and non-goals)

| Boundary | Statement |
|---|---|
| Django-admin | Not a Django-admin skin. It is for hand-built views. |
| Chrome vs. content | brickwork owns the shell, nav, topbar, footer; the consumer owns everything inside `{% block content %}`. |
| Charts / data-viz | Declared non-goal. |
| Domain-specific rendering | Declared non-goal. Generic chrome migrates to brickwork; domain components with real Python logic stay on the consumer's own framework. That is a legitimate permanent end state, not a migration phase in progress. |
| Date picker component | No package-maintained date picker component, ever (BR-BW-INPUT-004, Fixed). Not the same as "no date picker": a full date range picker ships as a copyable example over a native `<input type="date">` floor (section 3). Never state this boundary without that distinction. |
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
| `README.md:17` | Says "stable, on public PyPI at 3.2.0", cites 78 fixtures | Update to 3.5.1 and 86 fixtures (tracked: issue #204) |
| `pyproject.toml:8` | "Accessible by construction" (a design claim) sits against `README.md:11-12`'s "a *tested* guarantee... not a claim" (a verification claim positioned explicitly against design claims) | Reconcile the two framings; do not ship a design claim and a verification claim that read as contradicting each other |
| `PILOT-ADOPTION-BRIEF.md` | Was pinned to 0.3.0 and the private index, and dropped "professional" from the definition | RESOLVED 2026-08-24: rewritten as a routing quickstart and renamed `docs/QUICKSTART.md` |
| Four documents each currently state brickwork's singular value differently: `README.md:10-13` ("its value is the professional baseline"), `docs/BRANDING.md:3-4` ("brickwork's whole point is that you rebrand it by overriding tokens"), `docs/DESIGN.md:15-18` (the beautiful-defaults founding statement), `pyproject.toml:8` (the category definition) | Four different leads for one product | This document settles it: beautiful defaults, proved by the examples (section 3), is the lead. Token-first rebranding (4.3) and the professional/tested-accessibility framing (4.2) become supporting claims, not competing leads |

---

*Every factual claim in this document carries its evidence inline. If a
future edit adds a claim without a file:line, ADR number, or named external
source next to it, that edit fails review.*
