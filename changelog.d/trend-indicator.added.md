- **`_trend_indicator.html` (VIZ-017): the stat tile's trend caption, now a
  standalone reusable partial.** `_stat.html`'s own trend block (VIZ-002,
  BR-BW-TPL-007) always rendered a directional glyph plus a visually
  hidden text fallback ("increased"/"decreased"/"unchanged") whenever
  `trend` was set, refined by an optional `trend_label`, so direction
  never rode on colour alone. That contract was previously reachable only
  inside the whole KPI tile. `_trend_indicator.html` extracts it unchanged
  behind the same `trend`/`trend_label` context, so a table cell or a
  scorecard can render the same accessible trend caption on its own,
  structural and consumed via `{% include %}` exactly as `_stat.html`
  itself is. The extracted root class is `bw-trend`, not
  `bw-stat__trend`: the shipped name is a BEM element scoped to `.bw-stat`
  and carries no meaning outside it. `_stat.html` is unchanged and keeps
  rendering its own `bw-stat__trend` markup; wiring it to consume the new
  partial is a separate, deliberately follow-up change.
