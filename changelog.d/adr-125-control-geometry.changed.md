- **Control size is now a density base times a named step; `@bwui/tokens` and
  `@bwui/css` pins move to 0.1.4** (ADR-125, icvoss/brickwork#31).
  `--bw-size-control-height-<step>` is computed from the density base and a
  kit-wide step ratio, so a density scoped to a subtree re-resolves the whole
  scale. Upgrade, in your terms: at comfortable density `bw-btn--size-sm`
  goes from 2rem to 2.1875rem and `lg` from 3rem to 2.8125rem; at compact `sm`
  goes from 2rem to 1.75rem and `lg` from 3rem to 2.25rem; at spacious `sm`
  goes from 2rem to 2.625rem and `lg` from 3rem to 3.375rem. `md` does not
  move. Small and large button padding follows the same ratio, and anything
  sized from `--bw-size-control-height-sm` or `-lg` (avatar, stepper marker,
  toggle track offset) moves with it. A brand that overrode
  `--bw-size-control-height-*` directly should override the density base
  (`--bw-density-control-height`) or `--bw-size-step-*` instead. The token
  manifest now lists 325 overridable names (was 313): the `xs` and `xl` height
  and padding tokens and the five `--bw-size-step-*` ratios.
- **One size class grammar, `bw-<component>--size-<step>`** (ADR-125 section 6,
  icvoss/django-brickwork#744). Templates and tags now emit
  `bw-btn--size-sm`, `bw-gauge--size-md`, `bw-modal--size-full`,
  `bw-slide-over--size-lg`, `bw-stat--size-sm` and
  `bw-stat-comparison--size-lg` (avatar, button group, card, chip and empty
  state already did). The bare spelling (`bw-btn--sm`) is **deprecated**:
  the vendored stylesheet keeps both selectors in one grouped rule for the
  deprecation window, so your own CSS or raw HTML written against the bare
  classes keeps working. The bare selectors are removed in the next major of
  django-brickwork. Selectors in your tests or brand CSS that target the emitted
  bare class names need to move to `--size-<step>`.
- **One shared size grammar and one shared density axis**
  (icvoss/django-brickwork#744). `brickwork.appearance.SIZE_STEPS` is the
  closed five-step set `xs`, `sm`, `md`, `lg`, `xl`. It is a ceiling, not a
  default: every component declares the subset it renders
  (`COMPONENT_OPTIONS`, `BUTTON_SIZES`, `GAUGE_SIZES`, `AVATAR_SIZES`, built
  with `size_subset()`), and `{% bw_options size= %}` on a component that
  declares none now raises instead of inheriting `sm`, `md`, `lg`. `xs` and
  `xl` are not accepted on any component yet, because none ships them.
  `brickwork.appearance.SIZES` is removed (it was `sm`, `md`, `lg`); import
  `SIZE_STEPS` or the component's own subset. `DENSITIES` is now the three-value
  `comfortable`, `compact`, `spacious` axis shared by `{% bw_options %}` and
  `{% bw_form density= %}`; the data table and list item declare
  `comfortable` and `compact` only (their stylesheet renders nothing for
  `spacious`) and reject `spacious` rather than ignore it.
