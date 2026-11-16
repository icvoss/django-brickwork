- **`{% bw_button href=... loading=True %}` is no longer a navigable link.** A
  link button that is loading now renders the same non-navigable
  `<span aria-disabled="true" aria-busy="true">` a disabled link button
  renders, because a busy control must not be operable and an anchor stays
  focusable and navigable whatever `aria-disabled` says. Before this it stayed
  a live `<a href>` with a spinner and no `aria-busy`. A link button with
  both `disabled=True` and `loading=True` is busy, not flat. A plain `<button>`
  with `loading=True` is unchanged (`aria-busy` plus `disabled`).
  Mirrored from icvoss/brickwork (Button raise, `docs/components/button.md`,
  `GAP-BTN-5`).
