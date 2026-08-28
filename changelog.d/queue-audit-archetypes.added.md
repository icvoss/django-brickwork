- **The Data-heavy operations archetype family opens, with a queue and an
  audit trail** (`examples/ops/queue.html`, `examples/ops/audit-trail.html`).
  Both are copy-paste page templates in the established shape: they extend
  `brickwork/shell/app.html`, carry real content so they render from a
  near-empty context, and are deliberately not on the template loader path
  (ADR-056), so you copy them rather than extend them. `docs/CATALOGUE.md`
  previously listed this family as planned and not yet shipped.

  The two pages are structurally different on purpose rather than one table
  page twice. The queue carries triage tabs with counts, a stat row about
  waiting (oldest item, blocked) rather than volume, and a selectable table
  sharing one form with a bulk actions bar, because the bar's buttons submit
  the table's own checkboxes and splitting them into two forms would submit
  nothing. The audit trail has no selection, no row links and no destructive
  actions, because nothing in a trail is actionable; it adds a native
  `<details>` disclosure to expand one entry in place and a ranked list of
  most active accounts. Each page's header states that reasoning, so a
  consumer copying one understands why the shapes differ.

  Status, priority and outcome are badge labels throughout, never colour
  alone, and each header says so at the point of use.

  Known limitation, documented in `queue.html` rather than worked around:
  `_bulk_actions_bar.html` is extends-consumed, so an example cannot fill its
  block with an include. The page documents the small extending template to
  write in your own project and marks where to include it.
