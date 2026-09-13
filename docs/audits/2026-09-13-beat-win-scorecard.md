# Beat Phase F.2 win scorecard: FAIL

**Verdict:** **FAIL** against Beat Phase F.2 (`docs/plans/brickwork-beat-tailwind-plus.md`
Phase F) and the win bar in programme definition of done item 1.

Brickwork does **not** honestly lead or tie Tailwind Plus on at least six of
eight VISUAL-BAR surfaces from stills this reviewer saw. Package-default craft
holds the meet-bar substrate axes checked below, and brand torture shows no
substrate-owned ugliness, but the **beat** threshold is not met.

**Reviewer independence:** Independent design reviewer for F.2 only. Did not
author Beat Phases A to D craft, appearance suite work, journey contracts, or
the F.1 harness. Did not write
[2026-09-13-beat-phase-a-defaults-spotcheck.md](2026-09-13-beat-phase-a-defaults-spotcheck.md)
or
[2026-09-13-beat-phase-f1-brand-torture.md](2026-09-13-beat-phase-f1-brand-torture.md).
Clean-room throughout: look and idea only; no kit markup, class strings or
structure read into package files.

| Item | Value |
|---|---|
| Package under test | django-brickwork **3.25.0** |
| Branch / tip | `feat/beat-phase-f` @ `7ba7068` (F.1 harness on tip; craft from A to D already on ancestry through `e5f8cee`) |
| Render mode | Package-default CSS only for the win table |
| Package stills | `docs/audits/_stills/2026-09-13-beat-f2-package/` (32 PNGs, S1 to S8 × light/dark × 1440/375) |
| Brand torture stills | `docs/audits/_stills/2026-09-13-beat-f1-{northline,harbour,folio}[-compact]/` (S1, S3, S5) |
| Normative bar | [VISUAL-BAR.md](../VISUAL-BAR.md) |
| Prior meet-bar PASS | [2026-09-12-visual-bar-signoff-pass.md](2026-09-12-visual-bar-signoff-pass.md) |
| Soft-pass | Forbidden; every lead/tie/lose cites stills actually read |

---

## 1. F.2 done checks

| # | Criterion | Verdict |
|---|---|---|
| 1 | Independent review fills S1 to S8 (light/dark, 1440/375) with an explicit **lead kit** column | **Met** (table below) |
| 2 | Brickwork leads or ties **Tailwind Plus** on ≥6/8 surfaces on package-default CSS | **Not met** (explicit count: **2/8** lead or tie vs Plus stills seen; see §4) |
| 3 | Does not lose Navigation, Typography, Forms, Density, or Spacing rhythm for **substrate** reasons | **Met** (no blocking substrate fail on those five axes) |
| 4 | Brand torture: no substrate-owned ugliness across three packs × themes × densities on S1/S3/S5 | **Met** (summary §3) |

F.2 PASS requires all four. Criterion 2 fails, so overall **FAIL**. Do not run
F.4 claim language from this audit.

---

## 2. Plus evidence limits (honesty)

Local Plus / Idea refs actually opened with the Read tool for this review:

| Source | Files read | Surfaces they inform |
|---|---|---|
| Tailwind Plus Salient | `payroll.png`, `expenses.png`, `profit-loss.png`, `reporting.png` | S1 list craft; S4 dashboard craft; S8 dense-table adjacent |
| Tailwind Plus Radiant | `app.png`, `engagement.png` | Product chrome taste (pipeline / tool card), not a 1:1 S-map |
| Forge UI kit (secondary Idea-ref only) | `01-home.png`, `04-blocks.png`, `07-dashboard.png`, `08-forms.png`, `09-settings.png` | Clarifies "finished" for S5 / S6 / S4 / S3 / S2; **not** a Plus lead |

**Not available as matched local stills:** Plus marketing landing (S5), Plus
pricing page (S6), Plus docs article / Syntax (S7), Plus create-form page
matching S3, Plus detail / settings page matching S2, Plus dense-ops list
matching S8. Commit / Primer marketing assets in the tree are not surface-mapped
stills for this scorecard and were not used as fake S5/S6 proof.

Per the F.2 brief: where Plus comparison is limited by missing local stills,
score craft against the prior meet-bar PASS plus judgment, **state the limit**,
and **do not claim F.2 PASS**. That rule is applied here. Forge may clarify a
miss; it does not count as a Plus lead/tie for criterion 2.

---

## 3. Brand torture summary (F.1 stills)

Read sample: harbour S1 and S5 light 1440; harbour-compact S1 light 1440;
folio S3 and S5 light 1440; folio-compact S5 dark 1440; northline S3 dark 375;
northline-compact S3 dark 375. Cross-checked against F.1 capture note.

| Check | Result |
|---|---|
| Composition holds under seven-token packs | **Pass.** Sidebar / list / form / marketing section stack survive harbour (warm amber), folio (forest), northline (teal). |
| Accent reads as brand | **Pass.** Primary buttons, active nav and marketing CTAs shift with the pack; no leftover package-default blue forcing through. |
| Dark theme | **Pass.** Folio-compact S5 dark and northline S3 dark keep contrast; errors remain red; primary stays brand-coloured. |
| Density axis | **Pass for ugliness.** Compact cells remain coherent; no collapsed chrome or unstyled dump. Comfortable vs compact delta is subtle on S3 phone (not a substrate fail). |
| Substrate-owned ugliness | **None found** on S1 / S3 / S5 across the three packs × themes × densities sampled. |

Brand torture clears F.2 criterion 4. It does not repair the Plus lead/tie count.

---

## 4. Win scorecard (package-default)

**Lead kit** means the kit that sets the craft ceiling for that surface in this
review. **Brickwork vs Plus** is only `Lead`, `Tie`, `Lose`, or `N/S` (not
scored vs Plus: matched Plus still missing). Forge appears only in notes.

| Surface | Lead kit | Brickwork vs Plus | Axes notes | Substrate fail? |
|---|---|---|---|---|
| S1 App list | Salient (Plus) / Preline | **Tie** | Filter bar, end-aligned amounts, serif page title, phone hamburger + stacked label/value rows (`s1-light-1440`, `s1-light-375`). Matches Salient payroll/expenses craft for the list job without matching Plus's quieter minimalism. | No |
| S2 App detail | Forge settings (Idea-ref); Plus N/S | **N/S** (Lose vs finished detail craft) | Breadcrumb, header actions, meta card, danger zone clear (`s2-light-1440`, `s2-light-375`). Main body still reads as a related-invoice **list** (NUMBER / ACCOUNT / AMOUNT), not invoice line items. Forge `09-settings.png` is a much denser finished detail. No matched Plus detail still. | No on Navigation / Typography / Forms / Density / Spacing |
| S3 App form | Forge forms (Idea-ref); Plus N/S | **N/S** (Lose vs finished form craft) | Labels, help, errors, multi-line memo, primary/secondary actions clear at 1440 and 375 (`s3-light-1440`, `s3-light-375`). Sparse single column vs Forge multi-step / summary / character counter. Forms **axis** passes; beat craft depth does not. | No |
| S4 App dashboard | Salient reporting (Plus) | **Lose** | Weighted revenue tile + two companions + table (`s4-light-1440`, `s4-dark-1440`). Salient `reporting.png` ships chart, summary strip, tabs and transaction list. Forge `07-dashboard.png` reinforces the same miss (sparklines, activity + table). Hierarchy/spacing hold; surface argument is thinner. | No |
| S5 Marketing landing | Prior meet-bar: Plus / Preline | **N/S** | Strong section cadence, serif/sans pairing, hero placeholder, features, stats, testimonial, CTA, footer link columns (`s5-light-1440`, `s5-dark-1440`, `s5-light-375`). Footer no longer elevated boxed groups (#500 closed). No Plus landing still to claim lead/tie. | No |
| S6 Marketing pricing | Prior meet-bar: Plus / Preline; Forge blocks pricing clarifies | **N/S** | Highlighted middle tier, badge notch, per-tier CTA, FAQ, CTA band, footnote (`s6-light-1440`, `s6-light-375`). At parity with Forge `04-blocks.png` pricing preview; that is Idea-ref only. No Plus pricing still. | No |
| S7 Docs article | Prior meet-bar: Plus docs | **N/S** | Sidebar, callout, code, table, pager at 1440; "Documentation menu" above article at 375 (`s7-light-1440`, `s7-light-375`). Looks meet-bar finished. No Syntax / Plus docs still opened. | No |
| S8 Dense ops | Salient list surfaces (Plus) | **Tie** | Four metric tiles, filters, checkbox table, status column, end-aligned value (`s8-light-1440`, `s8-dark-1440`). Denser job than Salient expenses; comparable table craft to Salient payroll. Counts as tie on the dense-list job. | No |

### Explicit lead/tie count vs Tailwind Plus

Surfaces where Brickwork **leads or ties Plus** from Plus stills actually seen:

1. S1 App list: **Tie**
2. S8 Dense ops: **Tie**

**Count: 2 / 8.** Required: **≥ 6 / 8.**

Surfaces scored **Lose** vs Plus stills: **S4** (1).

Surfaces **N/S** (cannot claim lead/tie without inventing Plus screenshots):
S2, S3, S5, S6, S7 (5). Even if an optimistic reader reclassified every N/S as
Tie from craft judgment alone, S4 remains a Lose and the brief forbids claiming
PASS when Plus comparison is limited by missing local stills.

---

## 5. Substrate axes (package-default)

Checked against F.2 package stills and the five axes named in the win bar.

| Axis | Rating | Evidence |
|---|---|---|
| Navigation / mobile chrome | Pass | App hamburger on S1/S3 375; marketing hamburger alone when closed on S5/S6 375; docs menu discoverable on S7 375. |
| Typography | Pass | Display serif on app and marketing titles; sans UI chrome; money columns end-aligned. |
| Forms | Pass | S3 errors, help and multi-line textarea at both viewports. |
| Density | Pass | Credible filters and rows on S1/S8; marketing air intentional; S8 is dense-list. |
| Spacing rhythm | Pass | Consistent section and card cadence; no accidental voids that fail the axis. |

Residual taste (not substrate axis fails for this gate): S2 list-shaped detail
body; S4 missing chart/activity depth vs Plus.

---

## 6. Gaps to reopen before a re-run

1. **Capture or stage matched Plus stills** for S2, S3, S5, S6 and S7 under the
   gitignored Idea-ref tree (or an agreed Plus template map), then re-score.
   Without them F.2 cannot PASS under the brief's honesty rule.
2. **S4 dashboard depth:** package composition needs a finished argument next to
   Salient reporting / Forge overview (chart or activity + table split), not
   metrics + table alone, if the win claim depends on tying Plus here.
3. **S2 detail grammar:** stop scoring a related-invoice list as invoice detail;
   fixture or example should show line items and keep the danger zone.
4. **S3 form depth (optional for beat):** character counter, grouped sections or
   summary rail if the bar is "prefer vs Plus paste forms", not only Forms axis
   pass.
5. Re-run this audit only after those gaps have evidence; keep F.4 claim cite
   gated on a future **PASS**.

---

## 7. Claim language

**Do not** update POSITIONING.md or README beat/prefer claims from this file.
F.4 stays closed until an independent win scorecard returns PASS with ≥6/8
lead/tie vs Plus stills that were actually seen.

Meet-bar evidence in
[2026-09-12-visual-bar-signoff-pass.md](2026-09-12-visual-bar-signoff-pass.md)
remains the last PASS for section 6 of VISUAL-BAR.md. This audit does not revoke
that meet-bar PASS; it only fails the **beat** win threshold.
