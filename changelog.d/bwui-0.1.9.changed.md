- **Vendored substrate moves to `@bwui/tokens` and `@bwui/css` 0.1.9, the
  ADR-127 computed type scale.** The type scale is now a type base times a
  multiplier (`--bw-font-size-base`, `--bw-font-scale-<step>`), the
  `bw-text-xs` to `bw-text-xl` size utilities ship, and the control font size
  (`--bw-control-font-size`) resolves onto the same ladder for Button and
  Combobox. Visible on upgrade, in consumer terms: density now scales type
  slightly (body text is 15 px at compact, 16 px at comfortable, 17 px at
  spacious; comfortable roles are unchanged); the raw `--bw-font-size-xl` to
  `-5xl` names moved up one step (`xl` 1.25rem, `2xl` 1.5rem, `3xl` 2rem, `4xl`
  2.5rem, `5xl` 3rem, and `6xl` is new at 3.75rem), so a brand that reads or
  overrides those raw names directly should re-pick them; a Button or Combobox
  `md` label is 16 px (was 14 px) with `xs` 12, `sm` 14, `lg` 18 and `xl` 20 px
  at comfortable; the legacy `bw-text-display-md`, `bw-text-title-*`,
  `bw-text-body-*` and `bw-text-label-md` aliases are deprecated and removed in
  the next major release (no django-brickwork template emits them). The source
  mirrors (tokens, CSS layers) move with it. Pip consumers do not run npm; the
  CSS arrives with the wheel (icvoss/django-brickwork#752).
