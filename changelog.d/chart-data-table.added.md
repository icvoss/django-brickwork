- **`{% bw_chart_data_table %}` (CHT-012/CHT-013): the chart's accessible
  fallback table, rendered as a sibling of the mount rather than inside it.**
  Renders `caption`, `columns` and `rows` as a plain semantic table (a real
  `<caption>`, `<th scope="col">` column headers, `<th scope="row">` row
  headers), so the series a canvas or SVG plots reach assistive technology as
  data rather than as one opaque graphical object. `data_table_mode` is a
  closed, validated vocabulary of `hidden` (the default: visually hidden via
  the clip pattern, never `display: none`, so the table stays in the
  accessibility tree), `toggle` (composing `_disclosure.html`'s native
  `<details>`, so the no-JS floor holds by construction) and `visible` (the
  base state, emitting no wrapper). `caption` is required: a fallback table
  with no accessible name is announced as an anonymous grid of numbers.

  The placement is the contract, not an arrangement choice. `bw_chart_mount`
  emits `role="img"`, which makes every descendant presentational, so a table
  rendered inside the mount is unreachable to the assistive technology it
  exists for while still producing valid-looking markup that errors nowhere
  and passes axe. `_chart_card.html` therefore gains a `chart_data_table`
  block and a `data_table` context variable positioned OUTSIDE
  `.bw-chart-card__mount`, and the nesting is pinned by a structural test that
  parses the render rather than matching strings. This does not resolve
  `icvoss/django-brickwork#326`, which is the separate, still-unserved case of
  an interactive chart with traversable focusable children wanting its own
  role and keyboard story; the sibling placement is what lets this ship
  without widening what `role="img"` means.

  `_data_table.html` is deliberately not reused: its rows are dicts carrying
  stable per-row ids for HTMX swap targeting, and it ships sortable headers, a
  bulk-selection contract, an empty-state branch and a scroll/stack responsive
  contract, none of which an inert transcript wants. Its `definition` variant
  is one entity's key/value facts, not a series-by-category matrix. No new
  token is authored.
