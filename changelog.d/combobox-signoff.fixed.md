- **Combobox and `bw-input` visual repairs, mirrored from `icvoss/brickwork` (c7b19b6)
  (combobox sign-off, wave 1).** The vendored `components.css` source mirror
  now carries the repairs; the shipped `brickwork.css` carries them once the
  `@bwui/css` pin moves to the release that includes them (a later pin bump,
  not this change). In the combobox: the placeholder uses `--bw-color-fg-muted`
  (it measured 2.62:1 light and 3.84:1 dark as `fg-subtle`, under the 4.5:1
  text floor), the chip remove control uses `--bw-color-fg-muted` (it measured
  2.39:1 light as `icon-muted`, under the 3:1 non-text floor), a disabled
  combobox input prompts in the disabled ink, and the multiple-mode typing run
  basis grows from 4rem to 6rem so a short placeholder wraps to its own line
  instead of being clipped. Every `bw-input` state rule for `[readonly]` and
  `:disabled` now sets `background-color` rather than the `background`
  shorthand, so a disabled `select.bw-input` keeps its chevron. In the
  upstream `@bwui/css` the document-level input fallback is now zero
  specificity, so disabled and read-only text inputs paint their own fill and
  ink, and the page ground uses the defined surface token (icvoss/brickwork#25,
  #26).
- **`{% bw_combobox %}` empty and failure rows are `aria-disabled` options.**
  Both rows were `role="presentation"`, so when no option matched (or an
  options request failed) the visible listbox owned no option and axe reported
  `aria-required-children`. They are now `role="option" aria-disabled="true"`:
  announced as unavailable, never chosen, never reached by the arrow keys (the
  script still selects options by class). A consumer that counted
  `[role="option"]` rows to count choices should count `.bw-combobox__option`
  instead.
