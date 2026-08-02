// bwTagInput: the tag/chips input behaviour (BR-BW-INPUT-002, 0.13.0,
// brickwork#57).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwTagInput", ...) with no config
//   state   tags (array of strings)
//   methods add(value), remove(value)
//   events  bw:taginput:add / bw:taginput:remove (detail { value }), bubbling
//           CustomEvents dispatched from the component root (BR-BW-HTMX-004:
//           optional conventions, never load-bearing).
//
// DOM contract this module enhances (_tag_input.html renders the floor;
// BR-BW-HTMX-006). ONE markup serves both legs: the no-JS floor is a plain
// <input type="text"> (or <textarea>, multiline=True) carrying the real
// `name`, whose value IS a comma-separated tag list the server splits; it
// STAYS the submitted form control at all times:
//
//   <div class="bw-tag-input" x-data="bwTagInput()" data-bw-tag-input>
//     <div data-bw-tag-input-chips>            chip run (built here)
//     <input data-bw-tag-input-floor>          the form control, comma text
//
// At init this module reads the floor's comma-separated value into `tags`,
// renders one bw-combobox__chip per tag (the SAME classes the combobox's
// multiple mode uses, CMP-028 precedent, so a tag input and a multi-select
// combobox render identically), and re-serialises `tags` back into the floor
// value (comma-joined) on every add/remove so the floor is always the single
// source of truth a normal POST or a 422 re-render reads from.
//
// Keyboard: Enter or "," commits the current floor text as a tag and clears
// the buffer; Backspace with an empty buffer removes the last tag (the
// combobox's own multiple-mode precedent). A duplicate value is ignored
// (adding an existing tag again is a no-op, not a second chip).
//
// Motion is CSS-owned: this module only appends/removes chip elements and
// never sequences animation (BR-BW-TOK-009 lives entirely in the component
// CSS, matching the combobox chip precedent of no per-chip entrance).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

function splitTags(raw) {
  return raw
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag !== "");
}

export default function tagInput() {
  return {
    tags: [],

    _root: null,
    _chips: null,
    _floor: null,
    _buffer: "",

    init() {
      const root = this.$el;
      this._root = root;
      this._chips = root.querySelector("[data-bw-tag-input-chips]");
      this._floor = root.querySelector("[data-bw-tag-input-floor]");
      if (!this._chips || !this._floor) return; // floor markup absent: stay inert

      this.tags = splitTags(this._floor.value);
      this._renderChips();

      // The floor stays visible and typeable (it is the buffer for the NEXT
      // tag, not hidden like the combobox's select-as-floor pattern), so
      // typing plus Enter/comma is the whole authoring flow with the chip
      // run showing what has already been committed.
      this._floor.addEventListener("keydown", (event) => this._onKeydown(event));
    },

    add(value) {
      const tag = value.trim();
      if (tag === "" || this.tags.includes(tag)) return;
      this.tags = [...this.tags, tag];
      this._syncFloor();
      this._renderChips();
      dispatch(this._root, "bw:taginput:add", { value: tag });
    },

    remove(value) {
      if (!this.tags.includes(value)) return;
      this.tags = this.tags.filter((tag) => tag !== value);
      this._syncFloor();
      this._renderChips();
      dispatch(this._root, "bw:taginput:remove", { value });
    },

    _onKeydown(event) {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        this._commitBuffer();
      } else if (
        event.key === "Backspace" &&
        this._floor.value === "" &&
        this.tags.length
      ) {
        event.preventDefault();
        this.remove(this.tags[this.tags.length - 1]);
      }
    },

    _commitBuffer() {
      // The floor doubles as the typing buffer: committed tags are re-joined
      // back into it below, so clearing to "" here and letting _syncFloor
      // restore the committed list is what removes the just-typed text.
      const value = this._floor.value;
      this._floor.value = "";
      this.add(value);
    },

    _syncFloor() {
      // Preserve any in-progress (uncommitted) text the user is still
      // typing; only the committed portion is replaced.
      const buffer = this._floor.value;
      this._floor.value = this.tags.join(", ") + (buffer ? (this.tags.length ? ", " : "") + buffer : "");
    },

    _renderChips() {
      this._chips.replaceChildren();
      for (const tag of this.tags) {
        const chip = document.createElement("span");
        chip.className = "bw-combobox__chip";
        chip.setAttribute("data-bw-value", tag);
        chip.append(document.createTextNode(tag));
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "bw-combobox__chip-remove";
        // Translated prefix ships server-side on the chip run (i18n stays
        // server-side, the combobox chip-seed precedent); a bare fallback
        // covers hand-rolled markup that omits the data attribute.
        const removeLabel = this._chips.dataset.bwTagRemoveLabel || "Remove";
        remove.setAttribute("aria-label", `${removeLabel} ${tag}`);
        remove.addEventListener("click", () => {
          this.remove(tag);
          this._floor.focus(); // removal must not drop focus (BR-BW-JS-006)
        });
        chip.appendChild(remove);
        this._chips.appendChild(chip);
      }
    },
  };
}
