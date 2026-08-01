// bwCombobox: the combobox behaviour (04-interfaces section 4b,
// interactions-2 tranche).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwCombobox", ...) with config
//     { filterMode: "server"|"client", multiple: boolean,
//       allowCreate: boolean }
//   state   isOpen (boolean; see the shape note below), query,
//           activeIndex (index into the VISIBLE option list, -1 = none),
//           selected (array of values, single mode holds at most one)
//   methods open(), close(), select(value), clear()
//   events  bw:combobox:open / bw:combobox:close (detail { id }),
//           bw:combobox:select (detail { value, label }, additions only),
//           bw:combobox:create (detail { query }, allow_create only),
//           bubbling CustomEvents dispatched from the component root
//           (BR-BW-HTMX-004: optional conventions, never load-bearing).
//
// Shape note: 04-interfaces names both a boolean state key `open` and a
// method `open()`. One JS object cannot carry both under one name, so the
// boolean is exposed as `isOpen` and the methods keep their documented
// names (the bwDropdown/bwModal precedent). Flagged for a spec amendment;
// the method surface is authoritative.
//
// DOM contract this module enhances (the template lane renders it;
// BR-BW-HTMX-006). ONE markup serves both legs: the no-JS floor is a
// native <select> (or <select multiple>) built from the field choices,
// and it STAYS the submitted form control at all times:
//
//   <div class="bw-combobox" x-data="bwCombobox({...})" data-bw-combobox>
//     <select class="bw-combobox__floor" name=...>     the form control
//     <div class="bw-combobox__field" hidden>          enhanced UI
//       <input class="bw-combobox__input">             the typing surface
//       <ul class="bw-combobox__listbox"
//           id="bw-listbox-<field id>">                BR-BW-HTMX-005
//         <li class="bw-combobox__option"
//             data-bw-value="...">                     one per choice
//         <li data-bw-combobox-create hidden>          create affordance
//         <li class="bw-combobox__empty" hidden>       empty message
//
// At init JS reveals the field wrapper, hides the floor select, reads the
// initial selection FROM the floor (a failed 422 re-render ships state on
// the floor, so rehydration is free), and upgrades ARIA in place:
// role="combobox", aria-expanded, aria-controls, aria-activedescendant
// and aria-autocomplete="list" on the input; role="listbox" and
// role="option" (with generated ids) below it. Every selection mirrors
// BOTH ways: the floor select always carries form state, and a floor
// option is created on the fly for a server-fetched value the original
// choices never contained.
//
// Keyboard map (WAI-ARIA APG combobox with listbox popup,
// aria-activedescendant, HAND-ROLLED, no @alpinejs/ui; focus never leaves
// the input, options get no roving tabindex; semver-public,
// BR-BW-JS-005): closed: ArrowDown opens with first-or-current active,
// ArrowUp opens with last active, Alt+ArrowDown opens without moving,
// typing opens and filters, Escape clears the query. Open:
// ArrowDown/ArrowUp move the active option with wrap, Enter selects
// (single: select and close; multiple: toggle and stay open), Escape
// closes, Tab closes without selecting and continues, Home/End keep
// native caret behaviour. Multiple: Backspace with an empty query removes
// the last chip; chips render as span.bw-combobox__chip with an icon-only
// button.bw-combobox__chip-remove.
//
// filter_mode="server" (default): the query is debounced at the
// --bw-debounce-search token (read via getComputedStyle; wall-clock
// behaviour, not motion, so BR-BW-TOK-009 is untouched) and then the
// template-wired hx-get is triggered: the template carries
// hx-get/hx-target (the listbox) and hx-trigger="bw:combobox:search" on
// the search source, and this module only fires that event; it never
// hand-builds an htmx request. The response is the option-list partial
// only; htmx:afterSwap on the listbox re-upgrades the fresh options.
// filter_mode="client": pre-rendered options are filtered by
// case-insensitive substring, zero requests.
//
// i18n hooks (server-rendered so no English leaks from JS; the template
// lane supplies them): the allow_create affordance ships IN the listbox as
// the final option (li[data-bw-combobox-create] with a
// [data-bw-combobox-create-query] slot this module fills and re-appends
// after server swaps), and multiple mode ships a
// <template data-bw-combobox-chip-icon> seed carrying the registry close
// icon to clone into JS-built chips plus data-bw-chip-remove-label, the
// translated chip-remove aria-label prefix. Untranslated fallbacks apply
// when a hand-rolled markup omits them.
//
// Motion is CSS-owned: this module toggles state ([data-bw-open] on the
// root, aria-expanded, hidden on options) and never sequences animation
// (BR-BW-TOK-009 lives entirely in the component CSS).

const DEBOUNCE_FALLBACK_MS = 300;

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Parse a CSS <time> value ("300ms", "0.3s", bare number = ms) into ms.
function toMs(value) {
  const trimmed = String(value).trim();
  if (trimmed === "") return NaN;
  const number = parseFloat(trimmed);
  if (!Number.isFinite(number)) return NaN;
  if (trimmed.endsWith("ms")) return number;
  return trimmed.endsWith("s") ? number * 1000 : number;
}

// Unique fallback ids so several comboboxes on one page never collide on
// generated option ids (the tag may omit an explicit root id).
let instanceCount = 0;

export default function combobox(config = {}) {
  return {
    isOpen: false,
    query: "",
    activeIndex: -1,
    selected: [],
    filterMode: config.filterMode === "client" ? "client" : "server",
    multiple: config.multiple === true,
    allowCreate: config.allowCreate === true,

    _id: "",
    _root: null,
    _floor: null,
    _field: null,
    _input: null,
    _listbox: null,
    _empty: null,
    _create: null,
    _chipSeed: null,
    _searchSource: null,
    _debounceMs: DEBOUNCE_FALLBACK_MS,
    _debounceTimer: null,
    _onOutsidePointerDown: null,

    init() {
      // Captured once and reused everywhere below (BR-BW-JS-007): Alpine
      // inline x-on expressions scope $el to the element the directive is
      // written on, never the component root.
      const root = this.$el;
      this._root = root;
      this._floor = root.querySelector(".bw-combobox__floor");
      this._field = root.querySelector(".bw-combobox__field");
      this._input = root.querySelector(".bw-combobox__input");
      this._listbox = root.querySelector(".bw-combobox__listbox");
      this._empty = root.querySelector(".bw-combobox__empty");
      if (!this._floor || !this._field || !this._input || !this._listbox) {
        return; // floor markup absent: stay inert, the native select keeps working
      }
      // Template-shipped affordances (kept across server swaps): the create
      // option and the chip seed (registry close icon + translated remove
      // label) so no English and no artwork ever originate here.
      this._create = this._listbox.querySelector("[data-bw-combobox-create]");
      this._chipSeed = root.querySelector("template[data-bw-combobox-chip-icon]");

      instanceCount += 1;
      this._id = root.id || `bw-combobox-${instanceCount}`;
      if (!this._listbox.id) {
        // BR-BW-HTMX-005 stable id; the template normally ships it.
        this._listbox.id = `bw-listbox-${this._input.id || this._id}`;
      }

      // Progressive-enhancement handover: reveal the enhanced field, hide
      // the floor select. The floor STAYS the submitted form control;
      // every selection below mirrors back into it.
      this._field.removeAttribute("hidden");
      this._floor.hidden = true;

      // Rehydrate from the DOM: the floor select is the single source of
      // truth at init (fresh render and failed-422 re-render alike).
      this.selected = Array.from(this._floor.selectedOptions)
        .map((option) => option.value)
        .filter((value) => value !== "");

      // ARIA upgrade: only under JS, per the progressive-enhancement rule.
      this._input.setAttribute("role", "combobox");
      this._input.setAttribute("aria-expanded", "false");
      this._input.setAttribute("aria-controls", this._listbox.id);
      this._input.setAttribute("aria-autocomplete", "list");
      this._listbox.setAttribute("role", "listbox");
      this._upgradeOptions();
      this._syncOptionSelection();
      this._renderChips();

      // Single mode reflects the current selection's label in the input
      // (APG convention); the floor option text carries the label.
      if (!this.multiple && this.selected.length) {
        const label = this._floorLabel(this.selected[0]);
        if (label) {
          this._input.value = label;
          this.query = label;
        }
      }

      // Server filtering: the template wires hx-get/hx-target/hx-trigger
      // on the search source; this module only fires the trigger event.
      this._searchSource = root.querySelector("[hx-get]") || this._input;
      this._debounceMs = (() => {
        const ms = toMs(
          getComputedStyle(root).getPropertyValue("--bw-debounce-search"),
        );
        return Number.isFinite(ms) ? ms : DEBOUNCE_FALLBACK_MS;
      })();

      this._input.addEventListener("keydown", (event) => this._onKeydown(event));
      this._input.addEventListener("input", () => this._onInput());
      // Option clicks must not blur the input (focus stays on the input,
      // aria-activedescendant carries the active option).
      this._listbox.addEventListener("mousedown", (event) =>
        event.preventDefault(),
      );
      this._listbox.addEventListener("click", (event) =>
        this._onOptionClick(event),
      );
      this._field.addEventListener("click", (event) => this._onChipClick(event));
      root.addEventListener("htmx:afterSwap", (event) => {
        if (event.target === this._listbox) this._onOptionsSwapped();
      });

      this._onOutsidePointerDown = (event) => {
        if (this.isOpen && !root.contains(event.target)) this.close();
      };
      document.addEventListener("pointerdown", this._onOutsidePointerDown);
    },

    destroy() {
      if (this._onOutsidePointerDown) {
        document.removeEventListener("pointerdown", this._onOutsidePointerDown);
      }
      if (this._debounceTimer) clearTimeout(this._debounceTimer);
    },

    open() {
      if (this.isOpen || !this._listbox) return;
      this.isOpen = true;
      this._root.setAttribute("data-bw-open", "");
      this._input.setAttribute("aria-expanded", "true");
      if (this.filterMode === "client") {
        // Opening shows the full list; typing narrows it from here (the
        // input handler re-applies the filter straight after open()).
        for (const option of this._realOptions()) option.hidden = false;
        this._ensureCreateOption();
        this._toggleEmpty();
      }
      dispatch(this._root, "bw:combobox:open", { id: this._id });
    },

    close() {
      if (!this.isOpen) return;
      this.isOpen = false;
      this._root.removeAttribute("data-bw-open");
      this._input.setAttribute("aria-expanded", "false");
      this._resetActive();
      dispatch(this._root, "bw:combobox:close", { id: this._id });
    },

    select(value) {
      // Multiple mode toggles (Enter on a selected option, Backspace on
      // the last chip, a chip-remove click all route through here).
      if (this.multiple && this.selected.includes(value)) {
        this._remove(value);
        return;
      }
      const label = this._optionLabel(value);
      if (this.multiple) {
        this.selected = [...this.selected, value];
        this._ensureFloorOption(value, label);
        this._syncFloor();
        this._renderChips();
        this._syncOptionSelection();
      } else {
        this.selected = [value];
        this._ensureFloorOption(value, label);
        this._syncFloor();
        this._input.value = label;
        this.query = label;
        this._syncOptionSelection();
        this.close();
      }
      dispatch(this._root, "bw:combobox:select", { value, label });
    },

    clear() {
      this.selected = [];
      this._syncFloor();
      this._renderChips();
      this._syncOptionSelection();
      this._clearQuery();
    },

    // ----- keyboard -----

    _onKeydown(event) {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          if (!this.isOpen) {
            this.open();
            // Alt+ArrowDown opens without moving the active option.
            if (!event.altKey) {
              const current = this._indexOfSelected();
              this._setActive(current === -1 ? 0 : current);
            }
          } else if (!event.altKey) {
            this._setActive(this.activeIndex + 1);
          }
          break;
        case "ArrowUp":
          event.preventDefault();
          if (!this.isOpen) {
            this.open();
            this._setActive(-1); // last
          } else {
            this._setActive(this.activeIndex === -1 ? -1 : this.activeIndex - 1);
          }
          break;
        case "Enter":
          if (this.isOpen && this.activeIndex !== -1) {
            event.preventDefault();
            this._activateOption(this._visibleOptions()[this.activeIndex]);
          }
          break;
        case "Escape":
          if (this.isOpen) {
            event.preventDefault();
            this.close();
          } else if (this._input.value !== "" || this.query !== "") {
            event.preventDefault();
            this._clearQuery();
          }
          break;
        case "Tab":
          // Close without selecting; the default Tab continues the
          // sequence from the input (no preventDefault).
          if (this.isOpen) this.close();
          break;
        case "Backspace":
          if (this.multiple && this._input.value === "" && this.selected.length) {
            event.preventDefault();
            this._remove(this.selected[this.selected.length - 1]);
          }
          break;
        // Home/End fall through: native caret behaviour, untouched.
        default:
          break;
      }
    },

    _onInput() {
      // Typing opens and filters; a query change always resets the active
      // option (APG: filtering invalidates the previous active index).
      this.query = this._input.value;
      this._resetActive();
      if (!this.isOpen) this.open();
      if (this.filterMode === "client") {
        this._applyClientFilter();
      } else {
        this._ensureCreateOption();
        this._toggleEmpty();
        this._scheduleServerFilter();
      }
    },

    // ----- filtering -----

    _applyClientFilter() {
      const needle = this.query.trim().toLowerCase();
      for (const option of this._realOptions()) {
        const label = (option.textContent || "").trim().toLowerCase();
        option.hidden = needle !== "" && !label.includes(needle);
      }
      this._ensureCreateOption();
      this._toggleEmpty();
    },

    _scheduleServerFilter() {
      if (this._debounceTimer) clearTimeout(this._debounceTimer);
      this._debounceTimer = setTimeout(() => {
        this._debounceTimer = null;
        // htmx owns the request (the template wired hx-get/hx-target and
        // hx-trigger="bw:combobox:search"); prefer htmx.trigger so the
        // event goes through htmx's own dispatch, with a plain
        // CustomEvent fallback that hx-trigger equally understands.
        const source = this._searchSource;
        if (window.htmx && typeof window.htmx.trigger === "function") {
          window.htmx.trigger(source, "bw:combobox:search", {
            query: this.query,
          });
        } else {
          source.dispatchEvent(
            new CustomEvent("bw:combobox:search", {
              detail: { query: this.query },
              bubbles: true,
            }),
          );
        }
      }, this._debounceMs);
    },

    _onOptionsSwapped() {
      // The option-list partial replaced the listbox contents: fresh
      // elements need ids/roles again, the active index is stale, and the
      // create/empty affordances (kept across swaps) re-attach and
      // recompute against the new list.
      if (this._empty && !this._listbox.contains(this._empty)) {
        this._listbox.appendChild(this._empty);
      }
      this._upgradeOptions();
      this._resetActive();
      this._syncOptionSelection();
      this._ensureCreateOption();
      this._toggleEmpty();
    },

    // ----- options -----

    _options() {
      return Array.from(
        this._listbox.querySelectorAll(".bw-combobox__option"),
      );
    },

    _realOptions() {
      return this._options().filter(
        (option) => !option.hasAttribute("data-bw-combobox-create"),
      );
    },

    _visibleOptions() {
      return this._options().filter((option) => !option.hidden);
    },

    _upgradeOptions() {
      this._options().forEach((option, index) => {
        option.setAttribute("role", "option");
        if (!option.id) option.id = `${this._listbox.id}-option-${index}`;
      });
    },

    _ensureCreateOption() {
      if (!this.allowCreate) return;
      const query = this.query.trim();
      let create = this._create;
      if (query === "") {
        if (create) create.hidden = true;
        return;
      }
      if (!create) {
        // Defensive: the tag always ships the affordance; hand-rolled
        // markup without it still gets a plain (untranslated) create row.
        create = document.createElement("li");
        create.className = "bw-combobox__option bw-combobox__option--create";
        create.setAttribute("data-bw-combobox-create", "");
        create.setAttribute("role", "option");
        create.id = `${this._listbox.id}-option-create`;
        this._create = create;
      }
      // The template ships the translated label with a query slot; only the
      // query is filled here so i18n stays server-side.
      const slot = create.querySelector("[data-bw-combobox-create-query]");
      if (slot) slot.textContent = query;
      else create.textContent = `Create "${query}"`;
      create.hidden = false;
      // Always the FINAL option; appendChild also re-attaches the kept
      // element after a server swap replaced the listbox contents.
      this._listbox.appendChild(create);
    },

    _toggleEmpty() {
      if (!this._empty) return;
      const anyVisible = this._realOptions().some((option) => !option.hidden);
      this._empty.hidden = anyVisible;
    },

    _activateOption(option) {
      if (!option) return;
      if (option.hasAttribute("data-bw-combobox-create")) {
        // The server owns creation (BR-BW-HTMX-007 spirit): emit only.
        dispatch(this._root, "bw:combobox:create", { query: this.query.trim() });
        if (!this.multiple) this.close();
        return;
      }
      this.select(option.getAttribute("data-bw-value") ?? "");
    },

    _onOptionClick(event) {
      const option = event.target.closest(".bw-combobox__option");
      if (!option || !this._listbox.contains(option)) return;
      this._activateOption(option);
    },

    // ----- active option (aria-activedescendant, no roving tabindex) -----

    _setActive(index) {
      const options = this._visibleOptions();
      if (!options.length) return;
      const wrapped = ((index % options.length) + options.length) % options.length;
      this.activeIndex = wrapped;
      this._clearActiveMarker();
      const option = options[wrapped];
      option.setAttribute("data-bw-active", "");
      this._input.setAttribute("aria-activedescendant", option.id);
      if (typeof option.scrollIntoView === "function") {
        option.scrollIntoView({ block: "nearest" });
      }
    },

    _resetActive() {
      this.activeIndex = -1;
      this._input.removeAttribute("aria-activedescendant");
      this._clearActiveMarker();
    },

    _clearActiveMarker() {
      for (const option of this._listbox.querySelectorAll("[data-bw-active]")) {
        option.removeAttribute("data-bw-active");
      }
    },

    _indexOfSelected() {
      return this._visibleOptions().findIndex((option) =>
        this.selected.includes(option.getAttribute("data-bw-value") ?? ""),
      );
    },

    // ----- selection mirroring (the floor select carries form state) -----

    _remove(value) {
      this.selected = this.selected.filter((item) => item !== value);
      this._syncFloor();
      this._renderChips();
      this._syncOptionSelection();
    },

    _syncFloor() {
      for (const option of Array.from(this._floor.options)) {
        option.selected = this.selected.includes(option.value);
      }
      if (!this.multiple && !this.selected.length) this._floor.value = "";
    },

    _ensureFloorOption(value, label) {
      // A server-fetched option may not exist among the original field
      // choices; the floor must still submit it.
      const exists = Array.from(this._floor.options).some(
        (option) => option.value === value,
      );
      if (exists) return;
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      this._floor.appendChild(option);
    },

    _syncOptionSelection() {
      for (const option of this._realOptions()) {
        const value = option.getAttribute("data-bw-value") ?? "";
        option.setAttribute(
          "aria-selected",
          this.selected.includes(value) ? "true" : "false",
        );
      }
    },

    _optionLabel(value) {
      const option = this._options().find(
        (candidate) => (candidate.getAttribute("data-bw-value") ?? "") === value,
      );
      if (option) return (option.textContent || "").trim();
      return this._floorLabel(value) || value;
    },

    _floorLabel(value) {
      const option = Array.from(this._floor.options).find(
        (candidate) => candidate.value === value,
      );
      return option ? (option.textContent || "").trim() : "";
    },

    // ----- chips (multiple mode) -----

    _renderChips() {
      for (const chip of this._field.querySelectorAll(".bw-combobox__chip")) {
        chip.remove();
      }
      if (!this.multiple) return;
      // The chip seed supplies the translated remove-label prefix and the
      // registry close icon to clone (ICO-003: artwork stays the vetted
      // registry's); bare fallbacks cover hand-rolled markup without it.
      const seed = this._chipSeed;
      const removeLabel = (seed && seed.dataset.bwChipRemoveLabel) || "Remove";
      const glyph = seed && seed.content.firstElementChild;
      for (const value of this.selected) {
        const label = this._floorLabel(value) || value;
        const chip = document.createElement("span");
        chip.className = "bw-combobox__chip";
        chip.setAttribute("data-bw-value", value);
        chip.append(document.createTextNode(label));
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "bw-combobox__chip-remove";
        // Icon-only control: the accessible name is enforced here
        // (per-chip so each is distinguishable, ICO-008).
        remove.setAttribute("aria-label", `${removeLabel} ${label}`);
        if (glyph) remove.appendChild(glyph.cloneNode(true));
        chip.appendChild(remove);
        this._field.insertBefore(chip, this._input);
      }
    },

    _onChipClick(event) {
      const button = event.target.closest(".bw-combobox__chip-remove");
      if (!button) return;
      const chip = button.closest(".bw-combobox__chip");
      if (!chip) return;
      event.preventDefault();
      this._remove(chip.getAttribute("data-bw-value") ?? "");
      this._input.focus(); // removal must not drop focus (BR-BW-JS-006)
    },

    _clearQuery() {
      this._input.value = "";
      this.query = "";
      this._resetActive();
      if (this.filterMode === "client") {
        for (const option of this._realOptions()) option.hidden = false;
        this._ensureCreateOption();
        this._toggleEmpty();
      }
    },
  };
}
