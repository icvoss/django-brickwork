### Fixed

- **Feature-row media no longer expands the page** when a consumer
  embeds a wide full-page specimen. `.bw-feature-row` and its copy/media
  cells now set `min-inline-size: 0`, and media scrolls internally
  (`overflow: auto`), so mobile sideways-scroll gates stay honest
  (brickworkui.com sell-pass a11y).
