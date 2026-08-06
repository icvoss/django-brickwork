- **BREAKING: one option name per concept, across every component** (ADR-060).
  The package spelled one concept up to four ways, so knowing one component
  taught you nothing about the next. Every rename below is mechanical, and there
  are no aliases or deprecation shims: brickwork has no external consumers.

  | Component | Was | Now |
  |---|---|---|
  | `bw_alert` | `variant="error"` | `variant="danger"` |
  | `bw_tabs` | `style=` | `variant=` |
  | `_disclosure.html` | `style=` | `variant=` |
  | `bw_toast` | `intent=`, `action_url=` | `variant=`, `action_href=` |
  | `bw_dropdown` items | `intent` | `variant` |
  | `_card.html` | `padding=` | `size=` |
  | `_account_menu.html` | `align=` | `placement=` |
  | `_toast_region.html` | `position=` | `placement=` |
  | `_modal.html`, `_slide_over.html` | `close_url` | `close_href` |
  | `_data_table.html` | `scroll_container` (alias) | `sticky_header` only |
  | `_cta.html` | `no_tint=True` | `band="plain"` (default `"tint"`) |
  | `_hero.html`, `_cta.html` | `primary_cta_url`, `secondary_cta_url` | `*_cta_href` |
  | `_pricing_tier.html` | `cta_url` | `cta_href` |

  `bw_alert`'s `"error"` was the sharpest case: every sibling component and the
  whole token layer use `danger`, and because both closed sets were validated,
  each spelling raised on the other component.

  CSS moved in lockstep: `.bw-alert--error` to `.bw-alert--danger`, and
  `.bw-card--padding-*` to `.bw-card--size-*`.

  Deliberately unchanged: `url` inside per-item dicts (nav, dropdown, tabs,
  crumbs, CTA dicts) is consumer data rather than an emitted attribute, and
  `trigger_variant` qualifies a named sub-element rather than the component.
