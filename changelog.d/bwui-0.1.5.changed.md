- **Vendored substrate moves to `@bwui/tokens` and `@bwui/css` 0.1.5.** The
  wheel's `tokens.css`, `token-manifest.json` and `brickwork.css` now carry the
  Button raise, the control role variables (`--bw-control-height`,
  `--bw-control-padding-inline`, `--bw-control-icon-size`, `--bw-control-gap`)
  and `bw-btn--fit-fill`. Visible on upgrade: an `sm` button's icon and spinner
  are 14 px (was 16 px), and an `lg` button's are 18 px with a 12 px
  icon-to-label gap (was 16 px and 8 px); `md` is unchanged. Pip consumers do
  not run npm; the CSS arrives with the wheel.
