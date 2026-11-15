- **Combobox status, busy and failure handling** (CMB-019, CMB-052). A visually
  hidden polite `role="status"` region announces the result count, "No matches",
  loading and failure. In server-filter mode the listbox carries `aria-busy`
  while a request is in flight, and a failed request (a non-2xx response or a
  network error) shows a translated error row beside the previous options and
  announces it instead of failing silently; the next query clears it. A
  disabled option (`aria-disabled="true"`, for example from a consumer's
  server-filter partial) is skipped by the arrow keys and cannot be chosen.
  The new `bw-combobox__error`, `bw-combobox__status` and `bw-combobox--multiple`
  hooks are listed in the craft contract; the tag arguments for groups, clear,
  disabled, readonly, `aria_label` and `error_message` remain with
  `icvoss/django-brickwork#742`.
