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
// is the submitted form control with no JS present:
//
//   <div class="bw-tag-input" x-data="bwTagInput()" data-bw-tag-input>
//     <div data-bw-tag-input-chips>            chip run (built here)
//     <input data-bw-tag-input-floor>          no-JS: the form control
//
// At init this module reads the floor's comma-separated value into `tags`,
// renders one bw-combobox__chip per tag (the SAME classes the combobox's
// multiple mode uses, CMP-028 precedent, so a tag input and a multi-select
// combobox render identically), then performs a CARRIER TAKEOVER
// (icvoss/django-brickwork#237): a hidden <input type="hidden"> is created,
// takes the floor's `name` (the floor loses it), and becomes the serialised
// carrier of the committed, comma-joined tag list. From that point on the
// visible floor is a buffer for the text of the NEXT tag only; it never
// again shows already-committed tags, so there is exactly one visible
// representation of each tag (the chip) instead of the chip plus a
// duplicate comma-joined copy in the floor. The hidden carrier is what a
// normal POST or a 422 re-render reads the tag list from; init still parses
// the server-rendered floor value into `tags` first (the 422 re-render
// contract is unchanged), and the takeover happens after that parse.
//
// Keyboard: Enter or "," commits the current floor text as a tag and clears
// the buffer; Backspace with an empty buffer removes the last tag (the
// combobox's own multiple-mode precedent). A duplicate value is ignored
// (adding an existing tag again is a no-op, not a second chip). Submitting
// the owning form with text left in the buffer (no Enter/comma pressed)
// commits that text as a final tag first, so nothing a user typed is lost
// on submit; a component mounted outside a form has no submit to listen for
// and behaves exactly as before.
//
// Motion is CSS-owned: this module only appends/removes chip elements and
// never sequences animation (BR-BW-TOK-009 lives entirely in the component
// CSS, matching the combobox chip precedent of no per-chip entrance).
//
// Re-init (icvoss/django-brickwork#244): a second init() on the SAME root
// (an Alpine re-mount, or a content-only htmx swap that keeps the root and
// re-runs x-data without replacing it) finds the carrier already created by
// the first init() (marked with data-bw-tag-input-carrier) and re-syncs
// `tags` FROM that carrier's value instead of repeating the takeover, so
// chips are rebuilt without wiping state or creating a second, wrongly
// unnamed carrier. destroy() (Alpine's own teardown hook, matching
// bwDropdown's convention) removes the submit listener init() attached to
// the owning form, so a genuine unmount-then-remount never stacks a second
// listener there.

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

function splitTags(raw) {
  return raw
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag !== "");
}

// Marks the hidden carrier so a second init() on the same root (Alpine
// re-mount, or a content-only htmx swap that keeps the root and re-runs
// x-data) can detect the takeover already happened, instead of reading the
// already-cleared floor as empty and wiping the chips.
const CARRIER_ATTR = "data-bw-tag-input-carrier";

export default function tagInput() {
  return {
    tags: [],

    _root: null,
    _chips: null,
    _floor: null,
    _carrier: null,
    _buffer: "",
    _form: null,
    _onSubmit: null,

    init() {
      const root = this.$el;
      this._root = root;
      this._chips = root.querySelector("[data-bw-tag-input-chips]");
      this._floor = root.querySelector("[data-bw-tag-input-floor]");
      if (!this._chips || !this._floor) return; // floor markup absent: stay inert

      // Re-init guard (icvoss/django-brickwork#244): a second init() on the
      // SAME root (an Alpine re-mount, or a content-only htmx swap that
      // keeps the root and re-runs x-data) finds the carrier already
      // created by a prior init(). Re-syncing FROM that carrier's value,
      // rather than repeating the takeover, is the only safe path: the
      // floor's own value was already cleared to "" by the first init(), so
      // reading it again would wipe every committed tag, and creating a
      // SECOND hidden carrier would leave the original (still named, still
      // in the form) carrier orphaned from `tags` while a second, wrongly
      // empty-named carrier sits beside it.
      const existingCarrier = root.querySelector(`[${CARRIER_ATTR}]`);
      if (existingCarrier) {
        this._carrier = existingCarrier;
        this.tags = splitTags(existingCarrier.value);
        this._renderChips();
        this._attachFloorListener();
        this._attachSubmitListener(root);
        return;
      }

      // Parse the server-rendered value BEFORE the carrier takeover below,
      // so a 422 re-render (which fills the floor with the posted value)
      // still seeds `tags` correctly.
      this.tags = splitTags(this._floor.value);
      this._renderChips();

      // Carrier takeover (#237): the hidden carrier becomes the submitted
      // control under the real `name`; the floor loses `name` and becomes
      // the buffer for the next tag only, so committed tags render exactly
      // once (as chips), never a second time as floor text.
      const carrier = document.createElement("input");
      carrier.type = "hidden";
      carrier.name = this._floor.name;
      carrier.setAttribute(CARRIER_ATTR, "");
      this._floor.removeAttribute("name");
      this._floor.value = "";
      this._floor.insertAdjacentElement("afterend", carrier);
      this._carrier = carrier;
      this._syncFloor();

      // The floor stays visible and typeable as the buffer for the NEXT tag
      // (not hidden like the combobox's select-as-floor pattern), so typing
      // plus Enter/comma is the whole authoring flow with the chip run
      // showing what has already been committed.
      this._attachFloorListener();

      // Data-loss guard (owner ruling, #237): a user who types a tag and
      // submits WITHOUT pressing Enter/comma still gets that text posted,
      // matching the pre-#237 behaviour where the buffer was appended into
      // the floor value. A component mounted outside a <form> has nothing
      // to listen for and stays exactly as it was.
      this._attachSubmitListener(root);
    },

    destroy() {
      // Mirrors bwDropdown's destroy() convention: undo exactly what init()
      // attached outside the component root, so a re-mount after teardown
      // (rather than the re-init takeover above) never stacks a second
      // submit listener on the form.
      if (this._form && this._onSubmit) {
        this._form.removeEventListener("submit", this._onSubmit);
      }
      this._form = null;
      this._onSubmit = null;
    },

    _attachFloorListener() {
      this._floor.addEventListener("keydown", (event) => this._onKeydown(event));
    },

    _attachSubmitListener(root) {
      // Idempotent per component instance: init() only reaches here once
      // per fresh mount (the re-init branch above returns early), and
      // destroy() removes the listener it registers, so a re-mount never
      // stacks a second listener on the form.
      const form = root.closest("form");
      if (!form) return;
      this._form = form;
      this._onSubmit = () => this._commitOnSubmit();
      form.addEventListener("submit", this._onSubmit);
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
      // The floor holds only the in-progress buffer (#237 carrier
      // takeover): clear it up front and let add() decide whether the text
      // becomes a tag.
      const value = this._floor.value;
      this._floor.value = "";
      this.add(value);
    },

    _commitOnSubmit() {
      // Data-loss guard: fold any text left in the buffer into the
      // serialised carrier as a final committed tag before the form's own
      // submission proceeds (the listener does not preventDefault).
      if (this._floor.value.trim() !== "") {
        this._commitBuffer();
      }
    },

    _syncFloor() {
      // The carrier alone holds the committed, comma-joined tag list; the
      // floor is left untouched so any in-progress text the user is typing
      // is never rewritten or duplicated.
      this._carrier.value = this.tags.join(", ");
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
