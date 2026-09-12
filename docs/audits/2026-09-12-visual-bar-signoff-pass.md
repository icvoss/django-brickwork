# Visual-bar Phase 5 re-sign-off: PASS

**Verdict:** **PASS** against [VISUAL-BAR.md](../VISUAL-BAR.md) section 6.
All four done criteria are met. Beauty claim language may be restored only
as an evidenced aim that cites this audit; house aesthetic and competitor
names remain forbidden.

**Reviewer:** independent agent re-review after remediation; not the
remediation author; not Phase 3 craft author. Did not write #510, #511,
#512, #515, #518, #528, or the FAIL notice in
[2026-09-12-visual-bar-signoff.md](2026-09-12-visual-bar-signoff.md).

**Package under test:** django-brickwork `3.18.0`.

| Item | Value |
|---|---|
| `main` tip at sign-off | `e79f828` (`fix: Phase 5 visual-bar substrate remediation (#519-#526) (#528)`) |
| Stills tip | same SHA; regenerated in this review, not taken from remediation stills |
| Package-only stills | `docs/audits/_stills/2026-09-12-resign/` (32 PNGs, gitignored) |
| Northline brand stills | `docs/audits/_stills/2026-09-12-resign-northline/` (32 PNGs, gitignored) |

**Render mode:** package-default CSS only for the scorecard; northline
seven-token override for Brandability only. No showcase or kiln CSS.

Bar: [VISUAL-BAR.md](../VISUAL-BAR.md). Clean-room throughout: no kit markup,
class strings or structure was read into the package.

---

## 1. Section 6 done criteria

| # | Criterion | Verdict |
|---|---|---|
| 1 | Independent rendered review has filled the scorecard for S1 to S8 at both themes and both viewports against at least the priority-1 and priority-2 kits | **PASS** |
| 2 | Every fail has a package issue or an explicit won't-fix / consumer-owned reason | **PASS** |
| 3 | Package-default CSS clears the axes that failed for substrate reasons | **PASS** |
| 4 | Public copy still does not claim a house aesthetic or name competitors as brickwork's identity | **PASS** (claim restore in the same PR cites this audit and keeps honesty rules) |

Criterion 1 holds because S8 now renders the designated dense-list example
(`examples/ops/dense-list.html`), fixtures on S1, S5 and S6 are deep enough
to score Density and Section cadence, and every surface was re-captured at
light/dark × 1440/375 from tip `e79f828`.

Criterion 3 holds because the five substrate blockers that failed the first
sign-off (#519 to #523), plus the S8 designation / phone tile stack (#525),
table alignment (#522), fixture credibility (#524) and detail danger-zone
composition (#526), are closed on this tip and cleared in the stills below.
Residual #500 (footer grouping vocabulary) remains a tracked low-severity
fail; it does not restore the Navigation, Forms or Typography substrate
fails that previously blocked the bar.

---

## 2. Adversarial remediation checks (this review)

Read with the Read tool against freshly captured PNGs under
`_stills/2026-09-12-resign/`. Soft-pass forbidden.

| Check | Stills | Result |
|---|---|---|
| S1 to S4, S8 at 375: visible mobile menu icon in topbar | `s1-light-375`, `s1-dark-375`, `s2-light-375`, `s3-light-375`, `s4-light-375`, `s4-dark-375`, `s8-light-375` | **Pass.** Hamburger is painted and readable on light and dark. |
| S5 / S6 at 375: only one of hamburger / cross when closed | `s5-light-375`, `s5-dark-375`, `s6-light-375`, `s6-dark-375` | **Pass.** Closed state shows hamburger alone. |
| S3: textarea taller than text inputs | `s3-light-375`, `s3-light-1440` | **Pass.** Memo textarea is several control-heights tall; Account / Amount / Due date stay single-line. |
| Amount columns end-aligned where applicable | `s1-*`, `s2-*`, `s4-*`, `s8-light-1440`, `s7-*-375` recovery table | **Pass.** Currency AMOUNT / VALUE columns and docs percentage columns read end-aligned. |
| S7 phone: docs nav jump link or discoverable nav | `s7-light-375`, `s7-dark-375` | **Pass.** "Documentation menu" sits above the article; bottom "Documentation" control remains discoverable. |
| S8 is dense-list per VISUAL-BAR | `s8-light-375`, `s8-light-1440` | **Pass.** Purchase-orders dense list with filters, metrics and table; not the undesignated analysis dashboard. |

---

## 3. Per-surface scorecard (package-default, light and dark, 1440 and 375)

| Surface | Kit that led | Axes failed | Borrow idea (clean-room) | Package follow-up |
|---|---|---|---|---|
| S1 App list | Preline, shadcn/ui | None blocking | Keep phone topbar affordance and end-aligned money columns | Residual polish only |
| S2 App detail | Preline | None blocking | Danger zone stays its own surface with a compact destructive control | #526 cleared in stills |
| S3 App form | shadcn/ui, Preline | None blocking | Keep textarea multi-line height; help and error grammar are now visible | Forms axis evidenced |
| S4 App dashboard | Preline, Tailwind Plus | None blocking | Phone stacks headline tiles; desktop weighted row still reads as the argument | #525 phone stack cleared |
| S5 Marketing landing | Tailwind Plus, Preline | Surface differentiation (footer groups) | Footer link map without elevated boxed cards | [#500](https://github.com/icvoss/django-brickwork/issues/500) |
| S6 Marketing pricing | Tailwind Plus, Preline | Surface differentiation (footer vocabulary drift vs landing) | Same footer vocabulary as landing | #500 |
| S7 Docs article | Tailwind Plus docs | None blocking | Keep the above-article docs menu at phone width | #523 cleared |
| S8 Dense ops | Preline | None blocking | Dense ops list with end-aligned value column at desktop | #525 designation cleared |

**Strongest surfaces.** S6 pricing at 1440 (highlighted middle tier, badge
notch, per-tier CTA, footnote), S7 docs at 1440 (sidebar, callout, code,
table, pager), S4 desktop weighted headline row, and S8 dense purchase-order
list at both widths.

**Where residual work remains.** Marketing footers still present Product /
Company as bordered cards on the landing example and a thinner grouping on
pricing (#500). That is a real Surface differentiation miss, tracked, and not
treated as cleared.

---

## 4. Axis matrix, package-default

| Axis | Rating | Evidence |
|---|---|---|
| Hierarchy | **Pass** | S4 revenue tile leads; S8 PO page title and metric row lead; S5 / S6 heroes remain the marketing focus. |
| Typography | **Pass** | Display serif on titles; UI chrome sans; money and percentage columns end-aligned so figures compare down the column. |
| Spacing rhythm | **Pass** | Marketing section cadence holds; S4 phone stacks tiles instead of squeezing them into a third of the row. |
| Surface differentiation | **Fail (tracked)** | Roles elsewhere distinguish; S5 / S6 footers still disagree with each other and box link groups (#500). |
| Density | **Pass** | Credible filters and multi-row tables on S1 and S8; populated feature / stat / FAQ fixtures on S5 / S6; S8 is a dense list. |
| States | **Pass** | Form errors and help on S3; designed empty / status language elsewhere where the fixture exercises them. Loading states remain lightly evidenced (same as prior reviews; not raised as a new blocker). |
| Navigation / mobile chrome | **Pass** | Visible app drawer icon; marketing toggle shows one icon closed; docs menu discoverable above the article at 375. |
| Forms | **Pass** | Labels, help, errors and a visibly multi-line textarea on S3 at both viewports. |
| Section cadence (marketing) | **Pass** | Hero → logos → features → stats → testimonial → CTA reads as a sequence on populated fixtures. |
| Brandability | **Pass** | Northline stills under `_stills/2026-09-12-resign-northline/`: composition holds; accent shifts to teal; type pairing survives. |

### Brandability row (northline)

| Check | Rating | Evidence |
|---|---|---|
| Composition survives the seven-token override | **Pass** | `s1-light-1440.png` and marketing frames keep structure without reflow. |
| Accent reads as brand | **Pass** | Teal replaces default blue on primary actions and active chrome. |
| Surfaces and borders shift without losing roles | **Pass** | Sidebar, filters and tables stay distinguishable. |
| Type pairing survives | **Pass** | Display serif titles; sans UI chrome. |

---

## 5. Residual fails and their trackers

| Issue | Fail | Owner |
|---|---|---|
| [#500](https://github.com/icvoss/django-brickwork/issues/500) | Landing footer link groups lack a shared marketing-footer vocabulary; shell copy can overstate default layout | Substrate / marketing examples (sev:low) |

Won't fix or consumer-owned:

| Item | Reason |
|---|---|
| Bundled chart engine on ops surfaces | Programme non-goal; empty-state craft is consumer-owned where a chart is absent. S8 no longer depends on a chart placeholder for Density. |
| Sparse hero illustration craft | Consumer-owned artwork; bar asks for composition and rhythm. |
| Full docs table of contents | Archetype coverage (#413); out of scope for this scorecard. |

Closed by remediation and verified clear in this re-sign: #519, #520, #521,
#522, #523, #524, #525, #526.

---

## 6. Claim language

**Beauty claim language may be restored**, subject to honesty rules:

- Cite this dated audit as the evidence for the aim.
- Do **not** claim a house aesthetic (`POSITIONING.md` §10).
- Do **not** name competitors as brickwork's identity (`POSITIONING.md` §9).
- Do **not** say examples alone proved beauty; composition, axe and inventory
  remain separate evidence.
- Fill VISUAL-BAR "Latest completed pass" with a link to this file.

[#498](https://github.com/icvoss/django-brickwork/issues/498) remains the
canon reminder that composition evidence must not be treated as visual-quality
proof; restoring the claim with an audit cite is consistent with that issue,
not a substitute for closing it without review.

---

## 7. Evidence provenance

- Package-only regeneration on tip `e79f828`:
  `npm run visual-bar:fixtures` then
  `VISUAL_BAR_STILLS_DATE=2026-09-12-resign npm run visual-bar:capture`
  (32 PNGs; manifest reports package 3.18.0, brand null, package-only CSS).
- Northline regeneration:
  `npm run visual-bar:fixtures:northline` then
  `VISUAL_BAR_STILLS_DATE=2026-09-12-resign-northline npm run visual-bar:capture:northline`
  (32 PNGs).
- Stills were read with the Read tool in this session. Prior scorecards and
  remediation stills were not trusted as substitutes.
- Kit comparison was look-and-idea only against priority-1 and priority-2
  panel kits. No kit markup, class string or structure was copied.

---

## 8. Non-claims

- This PASS certifies the VISUAL-BAR section 6 done criteria for this tip. It
  does not certify axe gates, archetype inventory counts, or any consumer
  product's finished pages.
- It does not claim a house look. Brand themes remain the consumer's delta.
- Residual #500 is a real miss; a PASS with a tracked fail is not a soft-pass
  of Navigation, Forms or Typography.
