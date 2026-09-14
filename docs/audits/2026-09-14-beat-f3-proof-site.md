# Beat Phase F.3 proof site gate

**Canonical site copy:** `icvoss/brickworkui.com` `docs/reviews/2026-09-14-beat-f3-proof-site.md`.

**Verdict:** **PASS** against programme F.3
(`docs/plans/brickwork-beat-tailwind-plus.md` Phase F step F.3): homepage + one
app archetype compose with package options + brand tokens only.

| Item | Value |
|---|---|
| Site tip | `106ef62` (`chore: pin django-brickwork 3.26.0 (F.3 proof) (#199)`) |
| Live release | `20260914T075250Z` (deploy succeeded; footer reads 3.26.0) |
| Package pin | django-brickwork **3.26.0** (PyPI) |
| Package tip cited | `d104988` (release tag `v3.26.0`) |
| Brand pack | kiln (`BRICKWORK_DEFAULT_BRAND`; `frontend/brands/kiln/tokens.css`) |
| Win scorecard | Prior F.2 [2026-09-14-beat-win-scorecard-s5s7.md](2026-09-14-beat-win-scorecard-s5s7.md) (F.2 PASS 6/8; separate from F.3) |

---

## 1. Homepage

**URL:** `/` (`marketing/views.py` `LandingView`;
`templates/marketing/landing.html`).

**Composition:** body is package `brickwork_marketing` includes only:

- `_hero.html` (`media_placement="beside"`)
- `_stat_band.html`
- four `_feature_grid.html` (columns 3 / 2 / 4 / 3)
- `_cta.html` (`band="tint"`)

Hero media is the live package `app/dashboard` example rendered through the
ADR-056 examples engine, wrapped in the existing gallery preview frame so a
full-page specimen fits the media slot (`_homepage_hero_media.html`). That
frame is site glue for embedding, not kit chrome reinventing hero / feature /
CTA craft. Kit surface CSS for those sections was deferred to the package from
3.22.0 (`frontend/css/main.css` "Homepage kit surfaces" comment).

**Brand:** kiln token overrides on `--bw-*` only. `.bw-body { background:
var(--bw-color-surface); }` is a brand canvas token application, not invented
component paint.

**Residual site CSS (honest inventory, not soft-pass of kit invention):**

| Role | Selectors (representative) | F.3 reading |
|---|---|---|
| Brand canvas | `.bw-body` | Allowed (brand tokens) |
| Site brand lockup | `.bw-brand*` | Site identity in shell slots |
| Marketing header mobile / nav composition | `.bw-mobile-nav-toggle*`, `.bw-marketing-header__nav .bw-nav__list` | Shell integration; package marketing header still needs site drawer composition |
| Hero specimen glue | `.bw-gallery-preview-frame*` | Embedding glue for live example, not section craft |

No site rules reimplement `.bw-hero`, feature-card, or tinted CTA/stat band
kit look.

---

## 2. One app archetype

**URL:** `/demos/saas/dashboard/` (Waypoint SaaS console).

**Composition:** extends `brickwork/shell/app.html` via
`templates/demos/saas/console_base.html`; page body uses package
`_page_header`, `_stat`, and `_data_table` only
(`templates/demos/saas/dashboard.html`). Brand axis locks to `demo-saas`
tokens (`frontend/brands/demo-saas/tokens.css`).

**Site chrome around the demo (outside the archetype surface):**
`.bw-demo-showcase-bar*` and `.bw-demo-saas-brand*` are demo-product chrome
(back to demos index, brand mark sizing). They do not invent dashboard kit
craft. The scored composition surface remains package components + demo brand
tokens.

**Secondary proof:** `/examples/app/dashboard/` renders the same package
archetype from the installed 3.26.0 wheel (richer Overview: scorecard, trend
chart card, ranked list, activity table). Gallery chrome wraps the preview;
the example source and markers are package-owned.

---

## 3. F.3 done checks

| # | Criterion | Verdict |
|---|---|---|
| 1 | Homepage composes with package options + brand tokens | **Met** |
| 2 | One app archetype composes with package options + brand tokens | **Met** (SaaS dashboard; examples Overview as secondary) |
| 3 | No site kit chrome CSS inventing those surfaces | **Met** (residuals are shell / embed / demo chrome, inventoried above) |

F.4 claim cite remains a separate package POSITIONING/README step and must
cite the F.2 win audit with honesty (S5 Lose; S3 N/S).

---

## 4. How verified

- Template inventory of `templates/marketing/landing.html` and
  `templates/demos/saas/dashboard.html` against package includes.
- CSS sweep of `frontend/css/main.css` for homepage kit selectors and residual
  shell/demo rules.
- Live footer pin after deploy must read `Built on django-brickwork 3.26.0`
  (recorded at deploy time).
