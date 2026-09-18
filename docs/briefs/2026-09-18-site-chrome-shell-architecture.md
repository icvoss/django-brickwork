# Brief: site chrome across shells

**Status:** decision-ready for package owners (analysis only; no ADR filed, no implementation).  
**Date:** 2026-09-18  
**Package tip examined:** `origin/main` @ `605ed9d` (django-brickwork 3.36.0).  
**Consumer proof:** brickworkui.com at `/Users/nigelcopley/Projects/oss/sites/brickworkui.com` (pin `django-brickwork==3.33.0` at time of reading; chrome gap still present at package tip).

---

## 1. Problem statement

Two different problems are being conflated.

**Layout divergence is intentional.** Marketing, docs, app, auth, and centred shells are different layout contracts: landmarks, source order, and region sets differ on purpose. ADR-091 decided docs is its own shell because docs must emit article-then-rail while marketing emits a single `content` block inside `<main>`. That divergence should stay.

**Site chrome drift is not intentional.** Repeating chrome (brand, primary nav, header actions, site footer) is the same product surface whether the page is Home or Docs. On brickworkui.com, Home extends the marketing shell and Docs extends the docs shell, yet both reuse the same marketing header/footer includes. Band, measure, sticky behaviour, and landmark classes still diverge, so the site invents `bwui-docs-site-header__inner`, sticky rules on `.bw-docs-site-header`, and a `.bw-marketing-header__nav .bw-nav__list` row bridge. That is evidence of a **package gap** (no shared site-chrome composition that both outer seams can consume), with **secondary consumer debt** (outdated mobile-header fork; `{% bw_nav %}` in the marketing header slot instead of the documented `{% bw_nav_header %}`).

Prefer≥4 marketing sites that ship both a public marketing surface and a docs surface need one chrome contract. Layout shells must not force them to re-solve measure and band twice.

---

## 2. Current contract map

### 2.1 Base to shells

`brickwork/shell/base.html` owns the document skeleton (`{% static %}` CSS, theme attributes on `<html>`, skip link to `#bw-main`, toast/modal/slide-over roots). Concrete shells fill `{% block shell %}` and must emit exactly one `<main id="bw-main">`.

| Shell | Path | Layout contract | Outer site-chrome seams |
|---|---|---|---|
| app | `brickwork/shell/app.html` | sidebar + topbar + workspace | app brand / topbar / footer (product chrome, not public site chrome) |
| auth | `brickwork/shell/auth.html` | centred auth panel | brand slots only |
| centred | `brickwork/shell/centred.html` | single main | none |
| docs | `brickwork/shell/docs.html` | article-then-rail inside main (ADR-091) | `docs_site_header` / `docs_site_footer` (+ `_region` wrappers), **outside** main |
| marketing | `brickwork_marketing/shell/marketing.html` | single `content` stream | structured `marketing_header` (brand / nav / actions) and `marketing_footer` / `footer_legal`, with package `__inner` measure |

Docs page-local `docs_header` / `docs_footer` / `docs_nav` sit **inside** main and must not be used for repeating site chrome (docs shell header comment; INTEGRATION site-chrome recipe).

### 2.2 Marketing vs docs chrome ownership today

| Concern | Marketing shell | Docs shell |
|---|---|---|
| Landmark | `<header class="bw-marketing-header">` | `<header class="bw-docs-site-header">` when filled |
| Measure / band | Package `.bw-marketing-header__inner` + sticky/band in `marketing.css` | Seam only; contents unopinionated. `shell.css` may paint the landmark lightly; **no** shared `__inner` measure contract |
| Slots | `brand_*`, `marketing_nav`, `marketing_actions` (+ `_region`) | Single fill block; consumer supplies all composition |
| Package include for shared chrome | None shared with docs | INTEGRATION teaches consumer `_site_header.html` / `_site_footer.html` |

There is **no** package-owned site-chrome include that both shells compose. #448 / ADR-091 amendment added docs outer seams precisely so consumers would stop re-wrapping docs in `.bw-marketing*` by overriding `{% block shell %}`. That fixed landmark honesty. It did not give docs marketing-grade band/measure/slots.

### 2.3 Nav styling ownership

| Layer | File | Owns |
|---|---|---|
| Tree / sidebar / app-topbar `bw_nav` | `frontend/src/nav.css` | `.bw-nav__*` including vertical list defaults |
| Marketing-header horizontal renderer | `nav.css` | `.bw-nav-header__*` (documented as matching marketing header plain-anchor weight) |
| Marketing header chrome | `frontend/src/marketing.css` | `.bw-marketing-header*`, overlay, mobile toggle sibling rules |
| Docs layout + thin site chrome | `frontend/src/shell.css` | `.bw-docs-*`, `.bw-docs-site-header` / `footer` |

Family boundary: marketing chrome classes are not a supported skin for the docs shell. Consumers cannot simply reuse marketing header CSS on docs landmarks without fighting that boundary.

### 2.4 Documented nav-in-header pattern

INTEGRATION "Three renderers": `{% bw_nav_header %}` is the supported menu-driven **horizontal marketing-header** row. The marketing shell comment still describes `marketing_nav` as a plain list of links, "unlike the app shell's `{% bw_nav %}`". Marketing examples use bare anchors. Putting recursive `{% bw_nav %}` (sidebar list skin) inside `.bw-marketing-header__nav` is therefore **consumer composition**, not the package default path. brickworkui.com does exactly that and bridges row layout in site CSS.

### 2.5 Related package precedent: #667

Issue #667 / PR #679 shipped `.bw-section` / `.bw-section__inner` so marketing bands stop inventing site `*-inner` rails for section measure. Same defect class as site chrome: package owned a coarse parent, consumers invented prefixed inners. #667 fixed **section** atmosphere. It did not unify **site header/footer** across shells.

### 2.6 Consumer proof (brickworkui.com)

- Home: extends `brickwork_marketing/shell/marketing.html`; fills `marketing_header` with `_marketing_header.html`.
- Docs: extends `brickwork/shell/docs.html` via `templates/docs_app/_docs_base.html`; fills `docs_site_header` with `bwui-docs-site-header__inner` wrapping the **same** `_marketing_header.html`.
- Shared nav items via `_marketing_nav.html` then `{% bw_nav items=header_nav_items %}`.
- Site CSS (`frontend/css/main.css`): sticky/band on `.bw-docs-site-header`; measure on `.bwui-docs-site-header__inner`; row bridge for `.bw-marketing-header__nav .bw-nav__list`.

**Verdict:** primary defect is the missing package shared-chrome contract. Secondary debt is consumer composition (wholesale header override, site-owned mobile toggle, `bw_nav` instead of `bw_nav_header`).

---

## 3. Options table

Scores: **Y** = meets, **P** = partial, **N** = fails. "Drift" = stops Home/Docs chrome drift for a Prefer≥4 marketing site. "Landmarks" = preserves docs article-then-rail and app sidebar honesty. "Teach" = new consumer can extend/fill once and override by block. "Reversal" = cost for existing shell consumers (lower is better). "False same" = risk of empty rails / wrong source order / forced sameness.

| Option | Drift | Landmarks | ADR-056/091 | Teach | Reversal | False same | Notes |
|---|---|---|---|---|---|---|---|
| **A** Status quo | N | Y | Y | N | low | low | Seams exist; Prefer≥4 sites keep inventing `bwui-*` |
| **B** Shared site-chrome contract | Y | Y | Y | Y | medium | low | Layouts stay separate; chrome composition is package-owned and family-neutral |
| **C** Primary chrome shell | Y | P | P | Y | high | medium | New extendable parent; easy to smuggle optional rails and blur ADR-091 |
| **D** Mega-shell | Y* | N | N | N | very high | high | *Same template does not equal honest landmarks; rejects ADR-091 |
| **E** Examples-only full chrome | P | Y | Y | P | low | low | Teaches copy-paste; does not stop drift without a package seam |
| **F** Consumer-owned base only | N | Y | Y | P | low | low | Leaves Prefer≥4 sites alone with the gap |

\*D can look unified in CSS while emitting the wrong source order or collapsing docs into a flag on marketing.

---

## 4. Recommendation and non-goals

### Recommendation: **B**, with teaching from **E**, and **C deferred**

**Primary path: B (shared site-chrome contract).**

Ship a package-owned, **family-neutral** site header and footer composition (templates + CSS classes + documented slots) that:

1. The marketing shell's default header/footer **use** (include or identical markup), so Home stays byte-stable or near-stable for existing marketing consumers.
2. The docs shell's `docs_site_header` / `docs_site_footer` **consume the same include**, so Docs gets the same band, measure, brand, nav, and actions without `bwui-*-inner` stopgaps.
3. App / auth / centred **do not** gain marketing site chrome by accident; they keep their own contracts. A Prefer≥4 site that wants the public chrome on a rare centred page fills an explicit include, not an inherited mega-layout.

**Teaching model (E as pedagogy, not the contract):** copy-paste examples under `examples/` show (a) marketing page using the shell defaults, (b) docs page filling `docs_site_*` with the shared includes, (c) override recipes (swap actions, drop footer groups, overlay modifier on marketing only). Whole pages stay copy-paste (ADR-056). Shells stay extendable. Examples are never importable bases.

**Reject D.** ADR-091 already rejected bolting docs onto marketing via a flag because source order differs. A mega-shell with every region optional recreates that fork, invites empty sidebars on marketing, and trains consumers to toggle landmarks instead of choosing a layout contract. Landmark and source-order honesty beat one template.

**Defer C** until B is proven insufficient. A "primary chrome shell" that surface shells extend adds inheritance and migration cost; optional rails on that parent recreate D's failure mode. If, after B, Prefer≥4 sites still cannot teach "extend once" without copying large chrome trees, revisit a **chrome-only** parent with **no layout rails** (C narrowed). Do not start there.

**Reject A and F as the long-term answer.** Acceptable only as interim while B ships.

**Reject E alone.** Examples without a package chrome seam leave the next Prefer≥4 site inventing `bwui-*` again.

### Non-goals

- Merging docs layout into the marketing shell (ADR-091).
- Making whole pages extendable (ADR-056).
- Replacing app sidebar / topbar with public site chrome.
- Treating brickworkui.com's `{% bw_nav %}`-in-header bridge as the package pattern (correct toward `{% bw_nav_header %}` or an equivalent horizontal site-nav renderer).
- Expanding #667 section shell into site chrome (related class of gap; separate artefact).

### Proposed site-chrome API (for B)

**Templates (names indicative; exact names for the ADR):**

- `brickwork/components/_site_header.html` (or marketing-kit path promoted to shared / family-neutral): slots or blocks for brand mark, brand wordmark, nav, actions; optional modifiers (sticky default on; overlay stays marketing-shell-only via shell class or explicit modifier).
- `brickwork/components/_site_footer.html`: content + legal slots; optional footer link-group composition (may reuse or generalise `_marketing_footer_groups.html`).

**CSS (family-neutral):**

- `.bw-site-header`, `.bw-site-header__inner`, `__brand`, `__brand-mark`, `__brand-wordmark`, `__nav`, `__actions`
- `.bw-site-footer`, `.bw-site-footer__inner`, content/legal analogues
- Live in `shell.css` (or a dedicated site-chrome partial in the build), **not** under `.bw-marketing` only
- Marketing shell may keep `.bw-marketing-header` as an alias or thin wrapper for compatibility, or migrate class names in a breaking minor with a clear CHANGELOG (owner call; see open questions)

**Consumption:**

- Marketing shell default `marketing_header` / `marketing_footer` compose the shared includes (preserve region/`_region` override seams).
- Docs: `{% block docs_site_header %}{% include "…/_site_header.html" %}{% endblock %}` (and footer), as in INTEGRATION, but the include is **package** and already carries measure/band.
- Nav inside site header: document `{% bw_nav_header %}` (or rename to site-nav if clearer) as the menu-driven path; keep bare-anchor examples for static marketing sites.

**What surface shells still own exclusively:**

- Docs: article-then-rail, `docs_nav`, page-local `docs_header` / `docs_footer`, disclosure rail behaviour.
- Marketing: overlay header mode (ADR-105), marketing content measure / `.bw-section` stream, marketing-only modifiers.
- App: sidebar, topbar, workspace, mobile drawer.
- Auth / centred: their panel layouts.

---

## 5. Proposed ADR outline

**Title:** Site chrome is a shared package composition; layout shells stay separate.

**Context:** Prefer≥4 sites ship marketing + docs. Docs outer seams (#448) fixed landmark placement but left chrome composition consumer-owned. brickworkui.com proves drift (band/measure/`bwui-*-inner`). #667 fixed the same pattern for sections, not site chrome.

**Decision:**

1. Introduce a family-neutral site header/footer composition (templates + CSS) as the package contract for repeating public chrome.
2. Marketing and docs outer seams both consume it; layout shells remain distinct (ADR-091 stands).
3. Whole-page examples teach overrides by copy-paste (ADR-056 stands).
4. Explicitly reject a mega-shell and reject bolting docs layout onto marketing.

**Consequences:**

- Positive: Home/Docs chrome can match without site-prefixed inners; teaching path is "include once, override slots."
- Negative: class rename or dual-class period for marketing header; family-boundary / CSS layering work; consumer migration on Prefer≥4 sites.
- Neutral: app chrome unchanged; section shell (#667) unchanged.

**Affects (merge-time checklist):**

- New or promoted templates for site header/footer
- `frontend/src/shell.css` (or new partial) + marketing.css compatibility
- `shell/marketing.html` and `shell/docs.html` headers/comments
- `docs/INTEGRATION.md` site-chrome recipe
- Examples: at least one docs archetype/page and one marketing page using the shared includes
- Tests: docs site chrome fixture, class-contract / family-boundary updates, a11y fixtures
- CHANGELOG consumer notes (breaking if marketing class names move)
- Follow-up issue for brickworkui.com pin + delete `bwui-docs-site-*` bridges

**Does not affect:** ADR-056 page doctrine; ADR-091 docs layout; app shell region set; chart/tooltip work.

---

## 6. Migration notes for brickworkui.com (first proving consumer)

After the package ships B (illustrative sequence; not work authorised by this brief):

1. Bump `django-brickwork` pin to the release that contains site chrome.
2. Replace `bwui-docs-site-header__inner` / footer inners with the package include (or fill docs seams with the same include Home effectively uses).
3. Delete sticky/band/measure rules in `frontend/css/main.css` that only existed to mirror marketing on docs landmarks.
4. Move header nav from `{% bw_nav %}` + row bridge to `{% bw_nav_header %}` (or the shipped site-nav renderer); delete `.bw-marketing-header__nav .bw-nav__list` bridges.
5. Prefer package marketing header slots / `_region` + shipped mobile toggle over wholesale `marketing_header` override, unless overlay or a documented exception still requires it.
6. Keep Home overlay modifiers as marketing-shell-only behaviour.
7. Re-run a11y / device-matrix assumptions that still mention wrapping Docs in `bw-marketing-header`.

Success criterion: Docs and Home share band, measure, brand, nav, and actions from package classes; site CSS no longer defines `bwui-*-inner` for that chrome.

---

## 7. Open questions for owners (max five)

1. **Class identity:** Keep `.bw-marketing-header` as the public name (docs landmarks also use those classes), or introduce `.bw-site-header` and treat marketing names as compatibility aliases for one minor? Compatibility cost vs honest naming.
2. **Breaking vs alias:** Is a dual-class period required for Prefer≥4 sites still on older pins, or is a single breaking minor acceptable given brickwork's no-deprecation-window norm?
3. **Overlay:** Does overlay mode (ADR-105) stay marketing-shell-only forever, or must site chrome expose an overlay modifier for docs (usually no)?
4. **Footer link groups:** Promote `_marketing_footer_groups.html` into the shared footer composition now, or leave footer body consumer-owned until a second Prefer≥4 site needs it?
5. **Scope of B vs deferred C:** Confirm that "extend once" means "extend the surface shell; include shared chrome," not "extend a new chrome parent shell," unless B fails teaching in a named Prefer≥4 pilot.

Everything else in this brief is decided from package contracts, ADR-056/091, #667 precedent, and brickworkui.com evidence.

---

## Appendix: evidence index

| Claim | Source |
|---|---|
| Docs is its own shell; article-then-rail | ADR-091 decision 1; `shell/docs.html` header |
| Pages copy-paste; shells extendable | ADR-056 decisions 1 and 2 |
| Docs site chrome seams outside main | ADR-091 amendment; `shell/docs.html` "Site chrome vs page-local" |
| Marketing structured header + `__inner` | `brickwork_marketing/shell/marketing.html`; `marketing.css` |
| `bw_nav_header` for marketing header menus | `docs/INTEGRATION.md` "Three renderers" |
| Section shell/inner precedent | icvoss/django-brickwork#667 / PR #679 |
| Consumer `bwui-docs-site-*` + shared includes | `sites/brickworkui.com/templates/docs_app/_docs_base.html`; `frontend/css/main.css` |
