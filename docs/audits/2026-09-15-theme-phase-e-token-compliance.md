# Theme Phase E: kit token-compliance audit (2026-09-15)

**Issue:** [icvoss/django-brickwork#600](https://github.com/icvoss/django-brickwork/issues/600)  
**Authority:** ADR-110, `docs/THEME.md`, umbrella `docs/plans/brickwork-theme.md` Phase E  
**Scope:** high-traffic kit chrome paint / type / space / elevation / radius  
**Non-goals:** kit craft beauty (beat / beautiful-defaults); public L3/L4 marketing claims (Phase G)

## Method

1. Parse `frontend/src/{components,shell,nav,marketing}.css` for `.bw-btn`, `.bw-card`,
   `.bw-modal`, plus shell / nav / table / empty / filter / marketing peers.
2. Classify each rule: which `--bw-*` axes it reads; whether it adds literal
   `px`/`rem` radius or shadow layers beside tokens.
3. Compare to L3 ladder minimum (`sm`/`md`/`lg` radius; elevation `1` to `3`;
   optional surface ladder) and to the `northline-material` torture pack.

## Gate surfaces (card / modal / button)

| Surface | Paint | Radius | Elevation | Verdict |
|---|---|---|---|---|
| `.bw-btn` | colour tokens | `--bw-component-button-radius` → `--bw-radius-md` | `--bw-elevation-1` on primary/danger/secondary | Compliant. Soft bevel `inset 0 1px` is craft, not a theme dial. |
| `.bw-card` | `--bw-color-surface` (+ raised modifiers) | `--bw-radius-lg` | `--bw-elevation-1` (+ ambient) | Compliant for L3 minimum. Ambient dilutes but does not block elevation change. |
| `.bw-modal__panel` (floor) | `--bw-color-surface-raised` | `--bw-radius-xl` | `--bw-elevation-2` | Elevation and surface move under L3 minimum. **Radius uses `xl`, outside L3 minimum `sm`/`md`/`lg`.** |
| Open `.bw-modal__panel` | (same) | (same) | `--bw-elevation-4` (+ ambient) | **Elevation-4 is outside L3 minimum `1` to `3`.** Floor elevation still proves modal chrome moves. |

## Gap list

### P1: blocks L3 minimum from moving named chrome (fixed this pass)

| ID | Gap | Resolution |
|---|---|---|
| E-1 | L3 torture pack omitted `--bw-radius-xl` and `--bw-elevation-4`, so modal radius and open-modal altitude did not demonstrate the authored material language even though the kit reads those tokens. | Extended `northline-material` (and `northline-dense`) tokens; PROFILE notes overlay steps. |
| E-2 | No automated gate that L3 pack changes measured styles on card / modal / button. | `tests/test_theme_l3_chrome.py` (source wiring) + `a11y/theme_l3_chrome.spec.mjs` (computed-style probe). |

### P2: documented, not fixed (kit already token-true; ladder honesty)

| ID | Gap | Owner |
|---|---|---|
| E-3 | Modal / toast / popover use `--bw-radius-xl`; open modal / slide-over use `--bw-elevation-4`; toast uses `--bw-elevation-5`. L3 *minimum* does not require those steps. Packs that want overlay chrome to move must author them (THEME.md). | Theme docs (this pass); do not widen L3 *required* set without a checker migration. |
| E-4 | Soft ambient `box-shadow` layers on card, open modal, filter bar, data-table wrap, empty-state, feature cards (light theme). Craft from beat / beautiful-defaults so chrome reads on white. Stacks with elevation tokens; dark theme already strips back to plain elevation. | Beat / beautiful-defaults. Do not fold craft into the theme plan. |
| E-5 | Kit space steps (`--bw-space-2` …) are authored literals, not `calc` from `--bw-space-1`. L4 `--bw-space-1` primarily drives Tailwind projection; kit rhythm for chrome is density tokens / `data-density`. | Already stated in THEME.md L4; no Phase E kit rewrite. |

### P3: out of Phase E (inventory only)

| ID | Note |
|---|---|
| E-6 | Marketing CTA / hero / feature-card chrome is largely token-true (`radius-lg`/`xl`, elevation-1/2, surface-raised). Same ambient pattern as E-4. |
| E-7 | Shell topbar uses elevation-1 (+ ambient on light). Sidebar is paint/space only. |

## Acceptance evidence

- Source wiring: card / button / modal rules named above read the listed tokens (pytest).
- Measured styles: with `data-bw-brand="northline-material"` after package CSS, computed
  `border-radius` and `box-shadow` on `.bw-card`, `.bw-btn--primary`, and
  `.bw-modal__panel` differ from base theme on a white canvas (Playwright).

## Coordination

Beat F.2 and beautiful-defaults remain the path for ambient craft and default
beauty. This audit does not claim L3/L4 themes make flat kit chrome beautiful.
