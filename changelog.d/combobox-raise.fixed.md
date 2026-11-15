- **`{% bw_combobox %}` behaves like a native select where it did not**
  (craft contract `docs/components/combobox.md` in `icvoss/brickwork`, CMB-012,
  013, 022, 023, 050). A click or tap on the input now opens the list
  (keyboard focus alone still does not). Choosing, removing a chip, Backspace
  removal and `clear()` now fire a bubbling native `change` event on the floor
  `<select>`, only when the selection actually changed, so dependent fields and
  `hx-trigger="change"` wiring work. In single mode the input text always
  returns to the committed label when focus leaves without a choice (blur, Tab,
  outside press, Escape on a closed list); previously emptying the box or
  pressing Escape left it blank over a retained value that the form still
  submitted. Choosing the blank option now empties the input and is treated as
  no selection, as rehydration already did. Moving the pointer over an option
  makes it the single active row. The enhanced input is named from the floor's
  `<label>` (or `aria-label`) at init when the template supplied no
  `aria-labelledby`, which names the explicit `name=`/`options=` trio path
  when the consumer wrote a plain `<label for>`.
