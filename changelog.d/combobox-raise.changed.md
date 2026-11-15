- **Multiple-mode combobox: one frame for chips and input** (CMB-031,
  deliberate break). `{% bw_combobox multiple=True %}` now renders
  `bw-combobox--multiple` on the root. Once the vendored `@bwui/css` carries
  the matching rules (the next pin bump; this release's CSS is unchanged), the
  frame moves from the input to the field wrapper, the input becomes
  borderless, the frame grows with wrapped chips, and chips shrink to fit the
  control height (the remove control is 1.5rem, no longer 2.75rem). A consumer
  that styles the multiple-mode chip row or the input border will see a layout
  change. Single mode is unaffected. Until the pin is bumped the markup keeps
  its previous appearance.
