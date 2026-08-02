// bwTableSelection: the enhanced layer over _data_table.html's selectable
// rows and _bulk_actions_bar.html's live count (brickwork#54).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwTableSelection", ...) with no config
//   state   count (number of currently-checked [data-bw-row-select] boxes)
//   method  toggleAll(checked)
//   event   bw:table-selection:change (detail { count }), a bubbling
//           CustomEvent dispatched from the component root whenever the
//           checked set changes (BR-BW-HTMX-004: optional convention,
//           never load-bearing).
//
// THE SELECTION CONTRACT this module enhances (never replaces): every row
// checkbox is a native <input type="checkbox" name="selected" value="...">
// inside the consumer's own <form> (see _data_table.html's docstring). This
// module reads those checkboxes as the SOLE source of truth; it holds no
// separate JS array of selected ids, so it can never desync from what the
// form will actually submit. It only ever READS .checked and toggles it on
// the header/row boxes; it adds no hidden inputs and changes no name/value.
//
// DOM contract (rendered by _data_table.html / _bulk_actions_bar.html; the
// no-JS floor is real, individually-labelled checkboxes, all working with
// zero JS):
//
//   <form x-data="bwTableSelection()">           the component root
//     ...bulk-actions bar...
//       <[data-bw-selection-count]                live count text (aria-live)
//        data-bw-selection-count-template="{count} selected">
//     ...table...
//       <input data-bw-select-all>                header "select all"
//       <input data-bw-row-select value="...">    one per row
//
// i18n stays server-side (the bwSidebarCollapse convention): the count copy
// is read from data-bw-selection-count-template (a translated string with a
// literal "{count}" placeholder), never hardcoded in this module.
//
// Progressive enhancement only: absent Alpine, every checkbox above is a
// plain, independently working native control (BR-BW-HTMX-001).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

export default function tableSelection() {
  return {
    count: 0,

    _root: null,
    _selectAll: null,
    _countEl: null,
    _countTemplate: "",

    init() {
      const root = this.$el;
      this._root = root;
      this._selectAll = root.querySelector("[data-bw-select-all]");
      this._countEl = root.querySelector("[data-bw-selection-count]");
      this._countTemplate = this._countEl?.dataset.bwSelectionCountTemplate || "{count}";

      root.addEventListener("change", (event) => {
        if (event.target.matches("[data-bw-row-select]")) this._recount();
        else if (event.target === this._selectAll) this.toggleAll(this._selectAll.checked);
      });

      this._recount(); // initial state: reflects any server-rendered checked rows
    },

    // Checks or unchecks every row box to match `checked`, then recounts.
    // Called both from the select-all checkbox's own change event and
    // available for a consumer's own "select all matching" control.
    toggleAll(checked) {
      for (const box of this._rowBoxes()) {
        box.checked = checked;
      }
      this._recount();
    },

    _rowBoxes() {
      return Array.from(this._root.querySelectorAll("[data-bw-row-select]"));
    },

    _recount() {
      const boxes = this._rowBoxes();
      const checked = boxes.filter((box) => box.checked).length;
      this.count = checked;

      if (this._selectAll) {
        this._selectAll.checked = boxes.length > 0 && checked === boxes.length;
        this._selectAll.indeterminate = checked > 0 && checked < boxes.length;
      }

      if (this._countEl) {
        this._countEl.textContent = checked === 0 ? "" : this._countTemplate.replace("{count}", String(checked));
      }

      dispatch(this._root, "bw:table-selection:change", { count: checked });
    },
  };
}
