# Greenfield positioning review: django-brickwork at 3.33.0

**Status:** RATIFIED as working canon 2026-09-16 (implementation of lead G1 on
`docs/positioning-g1-lead`; tracker #614). Prior leads retired in POSITIONING.
**Tag reviewed:** `v3.33.0`.
**Tracker:** [icvoss/django-brickwork#614](https://github.com/icvoss/django-brickwork/issues/614).
**Method:** buyer job and package capability first; slogan last. Existing
POSITIONING / site copy were cited only as drift evidence.

This document deliberately ignores "Beautiful interfaces for anything" and
"Building blocks for beautiful apps and websites" as candidates until the
end, where they are scored against the greenfield frame (not the other way
round).

---

## 1. Buyer and job (ordinary workflow)

**Actor:** a Django team shipping real product surfaces on server-rendered
templates (often HTMX + Alpine), not a React SPA team and not an admin-only
team.

**Trigger:** they need a public site, an app shell, an ops queue, docs, auth,
or content surfaces to look finished and share one brand, without rebuilding
design decisions per project.

**Job:** install one interface foundation, brand it, compose or copy pages,
wire Django behaviour, ship. Later: upgrade the foundation without rewriting
owned pages.

**Failure modes they already know:**

| Escape | Why it fails the job |
|---|---|
| Hand-roll Tailwind forever | No shared contract; every page reinvented |
| Admin skin (e.g. Unfold-class) | Wrong surface class for hand-built product UI |
| HTML/React Tailwind kit | Not Django-aware; no pin/upgrade story for shells |
| Copy-paste component dump | Looks like progress; breaks on redesign and a11y |

**Success:** one branded system across the surfaces they ship this year; pages
they own; foundation they can pin.

---

## 2. What the package actually is (capability, not aspiration)

### Consumes

Django project, consumer routes/views/data, consumer brand CSS on `--bw-*`,
documented Alpine/HTMX/Tailwind stack.

### Does (three jobs in one wheel; ADR-108)

| Job | Meaning at 3.33 |
|---|---|
| Substrate | Tokens, 6 shells, 70 components, interaction contracts, a11y CI, Theme axes |
| Reference catalogue | 40 archetypes + 32 sections + skeleton; copy and own (ADR-056) |
| Starter | `manage.py startsite` emits an owned project (ADR-095) |

Plus a named **Theme product** (THEME.md): L1 Recolour through L4 Rhythm on
the same tokens.

### Produces

An installable, semver-governed UI foundation. Success is not "the consumer
page is beautiful forever"; success is "the reusable interface decisions are
owned here, brandable, tested, and upgradable."

### Shipping coverage (catalogue-manifest at 3.33)

| Interface family | Archetypes shipped | Notes |
|---|---|---|
| Product applications | 13 | Strongest app coverage |
| Documentation | 7 | Complete vs INTERFACE-SYSTEM required set |
| Editorial and publishing | 7 | Complete vs required set |
| Data-heavy operations | 6 | Material ops set; viz still contract-bound |
| Marketing and public web | 4 | Partial vs required marketing list |
| Transactional journeys | 3 | Partial (auth-heavy; checkout-class gaps remain) |

**Honest completion line:** brickwork is a **shipping interface foundation
with deep app/docs/editorial coverage and partial marketing/transactional
coverage**, plus a Theme profile ladder. It is **not** "every interface
archetype in INTERFACE-SYSTEM is done."

Stale: INTERFACE-SYSTEM "Current state" still says documentation/editorial
are the highest-priority missing families. That paragraph is false at 3.33
and must be rewritten in the same wave as POSITIONING.

### Craft evidence (not lead substitutes)

- Meet-bar PASS (cited audit).
- Beat scorecard: lead or tie on 6 of 8 surfaces; S5 Lose; S3 N/S. Soft-pass
  forbidden.
- A11y: mechanism at 236 documents, not a guarantee.
- No house aesthetic: brand packs are consumer-owned.

---

## 3. Category (greenfield)

**Category name to own:**

> Server-rendered Django interface foundation (design system + shells +
> copyable pages + Theme profiles).

**Not the category:**

- Django-admin theme
- CMS / page builder
- General Tailwind utility kit
- "Tailwind for Django" (rejected as analogy-led identity)

**Competitive frame (bounded):** no package found combining app shell,
components, theming and marketing kit for server-rendered Django (search-scope
hedge required). Visual bar remains Tailwind UI kits for craft only.

---

## 4. Point of difference (what only this offer stacks)

Stack these; do not lead with inventory counts alone:

1. **Django-native substrate** that pins and upgrades under semver.
2. **Pages you own** (copy-paste examples off the loader path).
3. **One brand across families** via `--bw-*` and Theme L1 to L4.
4. **Accessibility as CI mechanism** at catalogue scale.
5. **Craft aimed at kit bar** with published miss honesty (S5).

The upgrade boundary (1+2) is the mechanism that makes giving the catalogue
away rational. Theme (3) is the 3.33 product surface most undersold publicly.
Coverage (families table) is proof of range, not a promise of "anything."

---

## 5. Positioning statement (classic form)

For **Django teams building hand-built product and public interfaces**
who **need one branded, accessible design system they can pin and upgrade**,
**brickwork** is the **server-rendered Django interface foundation**
that **ships shells, components, Theme profiles and copyable pages they own**,
unlike **admin skins, HTML-only Tailwind kits, or endless hand-rolled UI**,
**brickwork** keeps **the reusable interface contract in one upgradable
package while consumer pages stay theirs**.

---

## 6. Lead candidates (derived now; prior slogans scored later)

| ID | Lead | Why it fits capability | Risk |
|---|---|---|---|
| **G1** | **One interface system for the Django surfaces you ship.** | Matches six-family coverage + Django-native category; "surfaces you ship" hedges "anything" | Needs family honesty nearby |
| **G2** | **Pin the foundation. Own the pages.** | Names the ADR-056/095 mechanism buyers actually buy | Underplays craft and Theme unless support lines carry them |
| **G3** | **Theme your Django UI without forking the kit.** | Centres 3.33 Theme product | Narrow if Theme is support, not lead |

**Recommended lead: G1.**

**Recommended support line (subordinate, not competing):** G2's mechanism
("Pin the foundation. Own the pages.") plus a Theme proof line ("L1 recolour
to L4 rhythm on `--bw-*`").

**Recommended anti-leads:** beauty as the organising noun; "anything" without
a shipping matrix; inventory counts as the hero; competitor names as identity.

---

## 7. Score prior slogans against this frame (not as options to keep by default)

| Prior line | Score vs greenfield | Verdict |
|---|---|---|
| Beautiful interfaces for anything. | "Beautiful" is aim+audit, not a certified consumer outcome; "anything" overclaims vs partial marketing/transactional | **Retire as lead.** May survive only as aspirational north-star prose inside INTERFACE-SYSTEM, never as public H1 |
| Building blocks for beautiful apps and websites. | "Building blocks" undersells system/Theme/shells; sounds like a dump; "beautiful" still soft | **Retire as lead.** "Building blocks" may appear in subordinate mechanism copy if useful |

Neither prior line is the greenfield recommendation. Choosing A vs B from
#614's first draft is the wrong framing; choose **G1** (or G2/G3 with
recorded reason) and rewrite POSITIONING from that.

---

## 8. Message hierarchy (what every surface must carry)

1. **Lead (G1):** one interface system for the Django surfaces you ship.
2. **Category:** server-rendered Django interface foundation (not admin, not CMS).
3. **Mechanism:** pin/upgrade substrate; own copied pages; Theme L1 to L4.
4. **Proof:** family shipping matrix; meet/beat cites with misses; a11y mechanism.
5. **Boundary:** consumers own data, permissions, domain; no house aesthetic.

---

## 9. What to rewrite when the ruling lands

| Artefact | Change |
|---|---|
| `docs/POSITIONING.md` §1 to §3 | Greenfield statement, G1 lead, shipping matrix instead of blanket "not yet complete" |
| `README.md` opening | Same lead; Theme named; family honesty |
| `docs/INTERFACE-SYSTEM.md` Current state | Docs/Editorial complete; remaining gaps named |
| brickworkui.com | Align H1/meta to ruling; remaster #233 proceeds on display |
| Umbrella marketing plans | Banner prior leads; point here |

Claim-honesty rules (§9 style) and no-house-aesthetic (§10 style) **carry
forward** as process rules even when slogans die.

---

## 10. Decision asked of the owner

1. Accept **G1** as the public lead, or name G2/G3 / a rewritten G-line with
   equal capability grounding.
2. Explicitly **retire** both prior public leads (do not leave dual canon).
3. Authorise a POSITIONING + README + INTERFACE-SYSTEM current-state PR on
   that ruling before large site remaster copy locks.

Site display remaster may continue on wireframes that are lead-agnostic
(show Theme, families, craft), but **no H1/meta lock** until this decision
is written into POSITIONING.
