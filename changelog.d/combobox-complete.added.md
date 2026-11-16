- **Combobox: the whole craft contract** (owner ruling 2026-11-16, nothing
  deferred; closes `icvoss/django-brickwork#742`). `{% bw_combobox %}` gains
  `size` (`xs`, `sm`, `md`, `lg`, `xl`; default `md`), `disabled`, `readonly`
  (shown and submitted, not editable: a disabled floor plus hidden inputs),
  `disabled_options` (values; an options mapping may also carry
  `"disabled": True` and `"group": "Label"`), `aria_label` and
  `error_message`. A bound field's optgroup choices render as listbox groups
  (a heading and a `role="group"` list) and floor `<optgroup>`s instead of
  being flattened. Every combobox carries a clear control (hidden until a
  value or query, a Tab stop after the input) and a chevron, a multiple-mode
  chosen row shows a check, and multiple mode announces "added", "removed"
  and "cleared" through the status region. A bound field with no label and no
  `aria_label` raises. The text, frame, chips, rows and icons follow the size
  step through the control role variables, so text scales with the size.
