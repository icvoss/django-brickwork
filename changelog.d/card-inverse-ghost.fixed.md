- **Inverse header ghost actions meet WCAG AA** (brickworkui.com gallery
  regression). Include-path `action_label` on `header_recipe="inverse"` or
  `surface="inverse"` now paints the ghost button with
  `--bw-color-fg-on-inverse` instead of `fg-muted`, which failed contrast on
  the inverse fill (~3:1). Package a11y fixtures cover the pairing.
