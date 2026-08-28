- **`_scorecard.html` (VIZ-011/VIZ-012): a responsive grid arranging N
  pre-rendered cards.** Structural, consumed via `{% include %}` with
  `items=` (a list of `{content, span?}` mappings, each `content` a
  caller-rendered card such as a `_stat.html` tile or a `_chart_card.html`
  card, marked safe). Column count steps at `--bw-component-scorecard-columns-base/-sm/-lg`
  (1 -> 2 -> 4 across the shared breakpoints); gap reuses the density-aware
  `--bw-density-stack-gap` token, no scorecard-specific gap is authored. Per
  VIZ-012, `span=2|3|4` widens an individual item via a closed CSS-class
  vocabulary (`bw-scorecard__item--span-<n>`), equal by default. Per CHT-026
  this is the SAME grid a dashboard composes stat tiles and chart cards
  into: it never imports or special-cases either component, so there is no
  chart-specific grid duplicate. Adds one number token family
  (`scorecard.columns.base/sm/lg`) only.
