- **Button `fit` and spinner sizing on the template mirror, from
  `icvoss/brickwork` (ADR-126 sections 3 and 4, `docs/components/button.md`
  section 13.4).** `_button.html` emits `bw-btn--fit-fill` when `fit="fill"` is
  in its context, after the icon-only class, and `_spinner.html` no longer
  writes an inline `--bw-icon-size`, so the spinner can follow the button's
  size step. The matching CSS and tokens (the four `--bw-control-*` role
  variables, the `--bw-size-control-icon-<step>` and
  `--bw-size-control-gap-<step>` tokens, `bw-btn--fit-fill`) are held back from
  the vendored source mirrors until the `@bwui/tokens` and `@bwui/css` pins move
  past 0.1.4, because the token-derivation test rightly refuses CSS that names
  a token the shipped `tokens.css` does not emit. Until then the shipped
  spinner keeps its 1 rem default, `fit="fill"` through a direct include has no
  effect, and the `bw_button` tag does not take `fit` (django-brickwork#748
  ships it with the pin bump, so the option is never a silent no-op). Behaviour
  that changes for an existing consumer after the pin moves: an `sm` button's
  icon and spinner are 14 px (was 16 px), and an `lg` button's are 18 px with a
  12 px icon-to-label gap (was 16 px and 8 px). `md` is unchanged.
