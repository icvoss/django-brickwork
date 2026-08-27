- **`{% bw_gauge %}` (VIZ-007/VIZ-010): a radial gauge whose value is always
  readable as text.** Renders an SVG arc for a `value` between `min` and `max`,
  in three fixed sizes (`sm`/`md`/`lg`), with optional `threshold_bands`
  recolouring the arc against the four already-shipped semantic tokens
  (`accent`, `success`, `warning`, `danger`). No new colour token is authored.
  COL-030 is enforced structurally rather than documented: the label falls back
  to the computed percentage whenever `gauge_label` is absent, so there is no
  code path that renders a threshold-coloured arc without its paired visible
  numeric text. Arc geometry is computed in Python and passed as fixed-format
  numbers, so the template never builds a dash string. Adds two dimension
  tokens only (`gauge.diameter.sm/md/lg`, `gauge.stroke-width`).
