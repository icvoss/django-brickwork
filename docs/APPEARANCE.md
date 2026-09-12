# Appearance grammar: closed options for beautiful defaults

**Status:** active (Phase 0 of the beautiful-defaults suite,
icvoss/django-brickwork#533 / #534).  
**Governs:** closed appearance axes on brickwork components.  
**Companions:** [DESIGN.md](DESIGN.md) (tokens), [VISUAL-BAR.md](VISUAL-BAR.md)
(craft bar), ADR-057 §1a (section arrangement axes), ADR-060 (one name per
concept), ADR-056 (pages stay consumer-owned).

## Goal

A consumer composes finished interfaces from brickwork alone: every component
is beautiful at its default, and where chrome must vary they pick **closed
options**, never hand-written layout CSS or one-off HTML wrappers.

Site composition remains ADR-056 page assembly (which sections, order, copy,
brand tokens). Site composition does **not** invent component chrome.

## Two option classes

| Class | Examples | Mechanism |
|---|---|---|
| **CSS-only** | `surface`, `elevation`, `size`, `radius`, `band`, `width` | Root modifier classes only (ADR-057). No markup forks. |
| **Region recipes** | `header_recipe`, `footer_recipe`, `media_recipe` | Package may emit region chrome for the common flat case. Root also carries a modifier so consumer-owned `.bw-*__header` / `__footer` / `__media` wrappers share the same look. `{% extends %}` blocks still win for rich content. |

Brand colour stays in tokens. `surface="inverse"` uses
`--bw-color-surface-inverse` / `--bw-color-fg-on-inverse`, never a hex string.
Open colour strings and arbitrary CSS class dumps are refused.

## Shared axes

Components adopt only the axes that apply. Silence in a template header means
unsupported, never ignored.

| Axis | Closed values | Meaning |
|---|---|---|
| `surface` | `default` \| `raised` \| `tint` \| `inverse` \| `muted` | Fill family from `--bw-color-surface*` / marketing tint / inverse |
| `elevation` | `0` \| `1` \| `2` \| `3` | Shadow ladder (`--bw-elevation-*`). Default per component stays authored |
| `size` | `sm` \| `md` \| `lg` (+ component extras e.g. modal `full`) | Scale; already common |
| `radius` | `default` \| `sm` \| `lg` \| `xl` \| `none` | Corner scale via `--bw-card-radius` (card). `default` / `lg` omit the modifier |
| `header_recipe` | `none` \| `plain` \| `bordered` \| `muted` \| `inverse` \| `accent` | Header region recipe (not the `header` **block**) |
| `footer_recipe` | `none` \| `plain` \| `muted` \| `actions` | Footer region recipe (not the `footer` **block**) |
| `media_recipe` | `none` \| `bleed` \| `inset` \| `icon` | Media region recipe (not the `media` **block**) |
| `band` | `tint` \| `plain` | Marketing band background (ADR-057) |
| `width` | `contained` \| `bleed` | Marketing measure vs full bleed (ADR-057) |
| `variant` | per-component | Status / behavioural treatment stays local |
| `align` / `placement` / `media_placement` | existing | Layout axes unchanged (ADR-060) |

**Naming.** Region **blocks** stay `media`, `header`, `footer`, `title`,
`actions`, `body` (ADR-077). Region **recipes** use the `_recipe` suffix so one
word never means both "content slot" and "appearance treatment" (ADR-060).

## Validation

Include-consumed components cannot raise from plain HTML. They call
`{% bw_options %}` (backed by `brickwork.appearance.validate_options`), which
raises `TemplateSyntaxError` on an unknown axis or value. Omitted options use
the component's authored default and stay silent.

Tag-backed components keep validating in their own Python signatures; shared
vocabularies live in `brickwork.appearance` so spellings do not drift.

## Composition contract (card, finished)

`_card.html` is complete for appearance. No further axes are planned on card.

1. **CSS-only axes** (`surface`, `elevation`, `size`, `radius`) always apply as
   root modifiers, including when a consumer uses an extend-and-include filler
   (kwargs pass through).
2. **Recipes** emit package-owned chrome for the common flat include case.
   Unfilled regions still emit no empty markup (AC-BW-070). Optional escaped
   `body` and `caption` strings cover the one-paragraph include path.
3. **Include-path header action:** `action_label` (+ optional `action_href`)
   emits a ghost sm button in the header. Suppressed when the whole card is an
   `href` link (no nested interactive content).
4. **Include-path media:** `media_recipe` with `media_src` / `media_alt` (bleed
   or inset) or `media_icon` (icon). Rich media stays `{% block media %}`.
5. **`{% block %}` wins** for rich content. Root recipe modifiers still style
   consumer-owned `.bw-card__header` / `__footer` / `__media` when present.
6. **Rich body, forms, multi-action clusters** stay extends-only. Prefer
   `footer_recipe="muted"` (or `plain`) with `caption` for metadata; use
   `footer_recipe="actions"` with an extends filler that places real buttons
   in `{% block footer %}`.

## Defaults and VISUAL-BAR

Defaults must pass [VISUAL-BAR.md](VISUAL-BAR.md) on package-default theme (no
brand pack) for the surfaces each component appears on. Default craft changes
are consumer-visible: name them in CHANGELOG in consumer terms.

## Adoption note

Card is the finished first adopter (icvoss/django-brickwork#535). Later phases
extend the same grammar across the catalogue; axes that do not apply stay
explicitly N/A rather than inventing a local spelling.
