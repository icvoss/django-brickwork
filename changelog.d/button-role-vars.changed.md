- **Button role-variable rework, mirrored from `icvoss/brickwork` (ADR-126
  sections 3 and 4, `docs/components/button.md` section 13.4).** The vendored
  source mirrors carry the four control role variables (`--bw-control-height`,
  `--bw-control-padding-inline`, `--bw-control-icon-size`, `--bw-control-gap`),
  the `--bw-size-control-icon-<step>` and `--bw-size-control-gap-<step>` tokens,
  the role-variable `.bw-btn` and the `bw-btn--fit-fill` rule. The
  `_button.html` partial emits `bw-btn--fit-fill` when `fit="fill"` is in its
  context, and `_spinner.html` no longer writes an inline `--bw-icon-size`, so
  the spinner follows the button's size step. The shipped `brickwork.css` and
  `tokens.css` carry all of this once the `@bwui/*` pins move past 0.1.4, so
  `fit="fill"` through a direct include has no effect until then, and the
  `bw_button` tag does not take `fit` yet (django-brickwork#748 ships it with
  the pin bump, so the option is never a silent no-op). Behaviour that changes
  for an existing consumer after the pin moves: an `sm` button's icon and
  spinner are 14 px (was 16 px), and an `lg` button's are 18 px with a 12 px
  icon-to-label gap (was 16 px and 8 px). `md` is unchanged.
