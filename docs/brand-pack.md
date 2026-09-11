# Brand-pack contract for brickwork consumers

**Status:** normative consumer documentation contract.
**Companion:** [BRANDING.md](BRANDING.md) teaches the override mechanism and
axis recipes; [DESIGN.md](DESIGN.md) is the authoritative `--bw-*` vocabulary.
This file defines the portable per-brand documentation unit a consumer (or
agent) authors when a brand needs measured identity prose bound to an exact
override delta.

A brand pack is **consumer-owned**. The package owns this empty contract and
ships one fictional skeleton to copy. It does not ship kiln, demo-restaurant,
demo-saas, or any other product identity (OSS-APPS package-worthiness Q4;
ADR-054 brand themes as consumer deltas).

The directory *shape* (measured prose plus a token override sheet plus a
preview) is adapted from the open-design design-system package layout idea
([nexu-io/open-design](https://github.com/nexu-io/open-design), Apache-2.0).
Do not copy that project's brand-named package content (Stripe, Apple, and
similar) into a brickwork consumer or into this package. Bind everything to
`--bw-*` names from DESIGN.md; never to a parallel token schema.

---

## Required files

A consumer brand pack is a directory containing at least:

| File | Job |
|---|---|
| `DESIGN.md` | Measured identity prose. Required H2 jobs below. Every numeric claim cites a `--bw-*` override or is marked deferred to base-theme. |
| `tokens.css` (or a clearly named fragment such as `brand.css`) | Only the override delta: `--bw-*` custom properties the brand authors. Load this stylesheet **after** the package `tokens.css` / `brickwork.css` so the cascade wins ([BRANDING.md](BRANDING.md)). |
| Preview path | A documented route or file that proves the overrides on real surfaces. Prefer a Django-rendered live specimen once [icvoss/django-brickwork#268](https://github.com/icvoss/django-brickwork/issues/268) lands; until then a static HTML page or a named Django URL in the consuming project is an acceptable interim artefact. |

Optional and still consumer-owned: font files, logo assets, a short `USAGE.md`
for site-specific composition notes. None of those replace the three required
files.

Place the pack wherever the consuming project keeps brand artefacts (for
example `frontend/brands/<slug>/` or `docs/brands/<slug>/`). The package does
not prescribe a site path; it only requires the three artefacts and the rules
below.

---

## Required H2 jobs in `DESIGN.md`

Every pack `DESIGN.md` must include these headings (numbering is optional;
the job of each section is not). Write what the brand decides. Mark what it
does not decide.

1. **Visual theme and atmosphere**: one short paragraph of measured intent
   (surfaces, ink, accent role, restraint). No trademark-inspired catalogue
   prose.
2. **Colour roles**: each authored role names its working value and the
   exact `--bw-color-*` token it overrides. Cover at least the load-bearing
   seven from BRANDING.md, plus `--bw-color-fg-on-accent` per theme. Derived
   tiers the brand does not author stay unmarked or are listed as deferred.
3. **Typography**: family stacks bound to `--bw-font-family-sans`,
   `--bw-font-family-display`, and `--bw-font-family-mono`. Any size, weight,
   line-height, tracking, or role metric cites `--bw-font-*` / `--bw-text-*`
   or is marked deferred to base-theme.
4. **Component signal**: which substrate surfaces carry the brand accent
   (for example primary CTAs only). State explicitly that `.bw-*` classes are
   not restyled; chrome stays on package tokens.
5. **Layout intent**: spacing and radius intent bound to `--bw-space-*` and
   `--bw-radius-*`, or deferred. Do not invent a parallel spacing ladder.
6. **Depth and elevation**: any brand-tinted shadow cites
   `--bw-elevation-*`, or the section states that elevation is deferred to
   base-theme.
7. **Do and do not**: short checklist: fg-on-accent per theme, keep danger
   distinct from accent, respect `prefers-reduced-motion`, never invent token
   names.
8. **Responsive behaviour**: brand-specific collapse notes only where they
   differ from substrate shells; otherwise defer to `--bw-breakpoint-*` and
   package shells.
9. **Agent brief**: a pasteable paragraph: override only documented
   `--bw-*` names after package tokens; verify fg-on-accent at 4.5:1 in both
   themes; compose pages from brickwork sections; do not fork components.

Sections may be short. An honest "deferred to base-theme" is correct; an
invented parallel scale is not.

---

## The numeric-claim rule (reviewer acceptance gate)

**Every numeric claim in the pack cites a `--bw-*` override in `tokens.css`
(or the named fragment), or is marked deferred to base-theme.**

A reviewer **must reject** a proposed pack that invents:

- a parallel spacing scale instead of binding `--bw-space-*`
- parallel shadow or depth recipes instead of binding `--bw-elevation-*`
- a parallel type size, weight, tracking, or role scale instead of binding
  `--bw-font-*` and/or `--bw-text-*`

Also reject packs that:

- introduce a second token schema (for example open-design A1/A2 names such
  as `--accent` / `--bg` used as the brand contract alongside or instead of
  `--bw-*`)
- restyle `.bw-*` classes or ship a `components.html` kit as brand content
- place kiln, demo, or other product identity into django-brickwork itself

Colour hex or oklch values that appear in `DESIGN.md` tables must match the
override fragment for the same role, or be labelled non-authoritative working
references with the authoritative value in the fragment.

---

## Non-goals

This contract deliberately excludes:

| Non-goal | Why |
|---|---|
| A second token schema | brickwork already owns `--bw-*` names, derivation, and the load-bearing manifest (DESIGN.md, ADR-054). |
| A `components.html` / component-manifest kit in the pack | Component chrome is substrate-owned; brands override tokens, never fork templates. |
| Trademark-inspired catalogue content | Same reasoning as the Tailwind Plus reference-only ruling: look and idea only; clean-room on `--bw-*`. |
| Kiln, demo-restaurant, demo-saas, or other product identity in this package | OSS-APPS Q4; filled packs live on the consuming site (for example brickworkui.com) after this contract exists. |
| open-design daemon / craft / manifest runtime fields | Optional discovery tooling is a later consumer choice, not part of this contract. |
| Releasing brand content from this package | The package ships the contract and one fictional skeleton only. |

---

## Preview and the live specimen

The preferred proof surface is a Django-rendered token specimen that exercises
package shells and components under the brand overrides. That capability is
tracked as [icvoss/django-brickwork#268](https://github.com/icvoss/django-brickwork/issues/268).
Until it ships, document an interim preview path in the pack (static HTML or
a consumer URL) and state that it is interim.

Do not treat static open-design-style preview HTML as a second component kit.

---

## Worked skeleton

Copy [examples/brand-pack/northline/](examples/brand-pack/northline/) into the
consuming project and rename the slug. Northline is a **fictional** B2B
console brand written only to demonstrate the contract. It is not a product
identity and must not be treated as kiln or as a recommended look.

The skeleton includes:

- `DESIGN.md` with all nine H2 jobs, several sections deliberately deferred
- `tokens.css` with a small light and dark override delta
- `preview/README.md` pointing at the interim preview expectation and #268

---

## Relationship to the theming mechanism

| Need | Document |
|---|---|
| How to override tokens, axes, emitter, fg-on-accent | [BRANDING.md](BRANDING.md) |
| Every token name and derivation | [DESIGN.md](DESIGN.md) |
| Portable per-brand prose + delta + preview unit | This file |
| Ownership of foundations vs consumer identity | [INTERFACE-SYSTEM.md](INTERFACE-SYSTEM.md) |
