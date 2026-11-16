- **Button gets `xs`, `xl` and size-following text from `@bwui/tokens` and
  `@bwui/css` 0.1.7 (shipped in the 0.1.8 pins).** The
  wheel's `tokens.css`, `token-manifest.json` and `brickwork.css` now carry
  the Button `xs` and `xl` size steps and a fifth control role variable,
  `--bw-control-font-size` (ADR-125, ADR-126 section 4). Button text now
  resizes with the step instead of staying at the label size: `xs` 12.25 px,
  `sm` 13.125 px, `md` 14 px, `lg` 15.75 px, `xl` 17.5 px, the same at every
  density, never below the 12 px legibility floor. Visible on upgrade: an `sm`
  button's label is 13.125 px (was 14 px) and an `lg` button's is 15.75 px
  (was 14 px); `md` is unchanged. The overridable token count moves from 339
  to 350 (Button part of the 0.1.8 total). Pip consumers do not run npm; the CSS arrives with the wheel.
