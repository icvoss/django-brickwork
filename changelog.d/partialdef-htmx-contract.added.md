- The data table's rows are now a semver-public template partial. A consumer driving
  sort, filter or pagination over HTMX can re-render just the rows from the shipped
  component with `render(request, "brickwork/components/_data_table.html#table_rows",
  ctx)`, or include them cross-file, instead of hand-rebuilding `<tbody>` markup and
  duplicating the selection contract, the `data-label` stacking behaviour and the
  row-link logic. The `<tbody>` carries a stable `id="<table_id>-tbody"` as the swap
  target. This completes the stable-id contract BR-BW-HTMX-005 already makes for rows.
