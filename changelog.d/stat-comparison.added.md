- **`_stat_comparison.html` (VIZ-019/020): a this-vs-last-period KPI tile.**
  Stacks an overline label, the current pre-formatted value, a visible
  previous-period caption (`period_label`, e.g. "vs last month"), and an
  optional trend caption. The delta renders via `_trend_indicator.html`
  internally (VIZ-017), never a second copy of its markup, matching
  `_stat.html`'s own composition. VIZ-020 boundary: brickwork does not
  compute the delta. `current`, `previous` and `trend_label` all arrive
  pre-formatted from the caller, and `trend` ("up"/"down"/"flat") is
  caller-supplied rather than derived from `current`/`previous`, following
  the same rule VIZ-002 already sets for every other trend-bearing
  component in the package. Structural, consumed via `{% include %}`, with
  the same `size="sm"|"lg"` seam `_stat.html` ships (VIZ-027).
