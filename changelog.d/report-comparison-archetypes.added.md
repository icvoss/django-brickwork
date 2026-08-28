- **Two more archetypes for the Data-heavy operations family: a printable
  performance report and a period comparison** (`examples/ops/report.html`,
  `examples/ops/comparison.html`). Both are copy-paste page templates in the
  established shape: they extend `brickwork/shell/app.html`, carry real
  content so they render from a near-empty context, and are deliberately not
  on the template loader path (ADR-056), so you copy them rather than extend
  them.

  The report is long-form and narrative-led: an executive summary in prose,
  headline `_stat.html` figures, a regional breakdown table, a
  `{% bw_ranked_list %}` of top accounts, and a methodology section, the
  document someone actually circulates at month end rather than a dashboard.
  The comparison page is table-led: two measured periods set side by side on
  quantitative metrics with deltas, deliberately distinct from
  `sections/pricing/comparison-table.html` (a marketing tick-or-dash grid
  over plan tiers, not a measurement comparison) and built from ordinary
  tables and `_trend_indicator.html` rather than that section's private
  `bw-pricing-comparison__*` CSS.

  Every delta on both pages renders through `_trend_indicator.html`, which
  always pairs its glyph with visually hidden increased/decreased/unchanged
  text, so meaning never rides on colour alone; each page's own header
  documents the trend-direction-versus-good-news trap this pattern is prone
  to getting backwards. Wide tables sit in their own scrollable,
  keyboard-reachable region (`role="region"` plus `aria-label`,
  `tabindex="0"`) so a narrow viewport never scrolls the whole page
  sideways.
