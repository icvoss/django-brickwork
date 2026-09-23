- **Section `reveal` axis: CSS-only enter motion** (BR-BW-MKT-009).
  `_hero.html` and `_section.html` accept `reveal="none"` (default,
  byte-identical) or `reveal="enter"` (`bw-hero--reveal-enter` /
  `bw-section--reveal-enter`) for a one-shot enter timed from
  `--bw-duration-slow` / `--bw-ease-out`, gated to
  `prefers-reduced-motion: no-preference`. The no-JS render is the final
  resting state; under `prefers-reduced-motion: reduce` the animation and
  transform are forced off (`!important`, MOT-003). Decorative only, never
  the sole means of revealing content. Example:
  `examples/sections/section/reveal.html`.
