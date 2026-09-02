- **`{% bw_attr %}`, one shared attribute-rendering seam for the whole
  package** (ADR-097). The package previously stopped a consumer value
  breaking out of an HTML attribute four different, partial ways:
  `escape_attribute_value` on the tag path only, the constrain pattern on
  two closed-vocabulary templates, `bw_data_attrs` on `data-*` mappings
  only, and nothing at all on the roughly 28 remaining include-only
  template sites. `bw_attr` is the one mechanism the others fold into: it
  emits a complete `name="value"` attribute or nothing, callable from
  inside an include-only template's own body the way `bw_data_attrs`
  already is. Three modes selected by the value's own nature: the default
  escapes unconditionally (the ADR-083 rule); `allow="a b c"` matches
  against a closed, space-separated vocabulary and omits the attribute
  entirely on an unrecognised value, never raising and never falling back
  to a guessed default; `numeric=True` coerces via `float()` and clamps to
  0-100 for a CSS custom property, since escaping alone is a no-op on a
  numeric payload with no quote, `<` or `&` in it and only a type coercion
  closes that class of injection. Built without `format_html`, which
  honours a `SafeString`'s `__html__` marker by documented contract and so
  passes a `mark_safe`'d attack payload through verbatim: a first spike of
  this seam using `format_html('{}="{}"', name, value)` was exploitable,
  caught by the seam's own tests. `escape_attribute_value` and
  `bw_data_attrs` are unchanged; no existing call site or template migrates
  in this change, which builds the seam and its tests only.
