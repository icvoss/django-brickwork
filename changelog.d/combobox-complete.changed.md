- **Combobox markup and styling change on upgrade** (in consumer terms). The
  root now always carries a size class (`bw-combobox--size-md` by default), so a
  stylesheet that matched the bare class list is unaffected but one that matched
  the exact `class` string is not. The input and the option rows take the
  control font size (`--bw-control-font-size`), so a brand that overrode
  `--bw-text-label-size` moves them in proportion; at `md` the text is 14 px as
  before. A chevron and, while there is a value or a query, a clear control now
  sit at the inline end of the field; the clear control is a Tab stop after the
  input. A bound field with optgroup choices now renders groups (it was
  flattened). Needs the `@bwui/css` 0.1.7 pin carried by this release; the
  markup keeps its previous appearance on an older stylesheet.
