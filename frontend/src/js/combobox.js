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
// typing opens and filters, a click on the input opens (CMB-022; keyboard
// focus alone does not), Escape clears an uncommitted query (single mode
// restores the committed label instead, CMB-013). Open:
// ArrowDown/ArrowUp move the active option with wrap and skip disabled
// options (aria-disabled="true", CMB-016), Enter selects
// (single: select and close; multiple: toggle and stay open), Escape
// closes, Tab closes without selecting and continues, Home/End keep
// native caret behaviour. Single mode restores the committed label whenever
// focus leaves without a commit (blur, Tab, outside press, Escape on a
// closed list), so the input text never sits blank over a retained value. Multiple: Backspace with an empty query removes
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
// The floor select receives a bubbling native `change` event whenever a
// selection actually changes (choose, remove, clear), so dependent fields and
// htmx `hx-trigger="change"` wiring behave as with a native select (CMB-012).
//
// Accessible name (CMB-050): the label's `for` targets the hidden floor, so at
// init the enhanced input is named from the floor's labels (aria-labelledby)
// or the floor's aria-label when the template did not already supply one.
// A polite role="status" region ([data-bw-combobox-status], template-supplied
// strings) announces the result count, "No matches", loading and failure
// (CMB-052). Server mode sets aria-busy on the listbox while a request is in
// flight and shows the template-supplied error row ([data-bw-combobox-error])
// when the request fails, keeping the previous options (CMB-019).
//
// Completion (docs/components/combobox.md, nothing deferred): a clear control
// ([data-bw-combobox-clear], hidden until there is a value or a query on an
// operable control, CMB-015); groups (.bw-combobox__group wrappers hidden while
// none of their options is visible, CMB-017); readonly and disabled controls
// (the input is readonly or disabled, so the list never opens and chips cannot
// be removed, CMB-024 and CMB-025); and the multiple-mode "added", "removed"
// and "cleared" announcements through the status region (CMB-052).
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
    _error: null,
    _clearButton: null,
    _status: null,
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
      this._error = this._listbox.querySelector("[data-bw-combobox-error]");
      this._status = root.querySelector("[data-bw-combobox-status]");
      this._clearButton = root.querySelector("[data-bw-combobox-clear]");

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
      this._nameInput();
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

      if (this._clearButton) {
        // Keep focus on the input while the control is pressed (CMB-010).
        this._clearButton.addEventListener("mousedown", (event) =>
          event.preventDefault(),
        );
        this._clearButton.addEventListener("click", () => {
          if (!this._operable()) return;
          this.clear();
          this._input.focus();
        });
      }
      this._updateClear();
      this._syncGroups();

      this._input.addEventListener("keydown", (event) => this._onKeydown(event));
      this._input.addEventListener("input", () => this._onInput());
      // A click or tap on the input opens the list (CMB-022); keyboard focus
      // alone never does.
      this._input.addEventListener("click", () => this.open());
      // Focus leaving the component without a commit closes the list and, in
      // single mode, restores the committed label (CMB-013).
      this._input.addEventListener("blur", (event) => {
        if (event.relatedTarget && root.contains(event.relatedTarget)) return;
        this.close();
        this._restoreText();
      });
      // Option clicks must not blur the input (focus stays on the input,
      // aria-activedescendant carries the active option).
      this._listbox.addEventListener("mousedown", (event) =>
        event.preventDefault(),
      );
      this._listbox.addEventListener("click", (event) =>
        this._onOptionClick(event),
      );
      // One highlight (CMB-023): moving the pointer over an enabled option
      // makes it the active option, so hover and keyboard never disagree.
      this._listbox.addEventListener("mousemove", (event) =>
        this._onOptionPointerMove(event),
      );
      this._field.addEventListener("click", (event) => this._onChipClick(event));
      root.addEventListener("htmx:afterSwap", (event) => {
        if (event.target === this._listbox) this._onOptionsSwapped();
      });
      // Server-filter request lifecycle (CMB-019): busy while in flight, an
      // error row when it fails. htmx fires afterRequest for every outcome.
      root.addEventListener("htmx:beforeRequest", (event) => {
        if (event.target !== this._input) return;
        this._hideError();
        this._listbox.setAttribute("aria-busy", "true");
        this._announce(this._statusText("loading"));
      });
      root.addEventListener("htmx:afterRequest", (event) => {
        if (event.target !== this._input) return;
        this._listbox.removeAttribute("aria-busy");
        const detail = event.detail || {};
        if (detail.failed === true || detail.successful === false) {
          this._showError();
        }
      });
      // Network failures, timeouts and HTTP error responses fire their own
      // events and do not always flag afterRequest as failed. An abort
      // (htmx:abort / a superseded request) is deliberately not an error.
      ["htmx:sendError", "htmx:timeout", "htmx:responseError"].forEach(
        (name) => {
          root.addEventListener(name, (event) => {
            if (event.target !== this._input) return;
            this._listbox.removeAttribute("aria-busy");
            this._showError();
          });
        },
      );

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

    // Operable: neither disabled nor read-only (CMB-024, CMB-025).
    _operable() {
      return !this._input.disabled && !this._input.readOnly;
    },

    // The clear control shows while the control is operable and holds a value
    // or a non-empty query (CMB-015); otherwise it is not rendered.
    _updateClear() {
      if (!this._clearButton) return;
      const has = this.selected.length > 0 || this._input.value !== "";
      this._clearButton.hidden = !(this._operable() && has);
    },

    open() {
      if (this.isOpen || !this._listbox) return;
      if (!this._operable()) return;
      this.isOpen = true;
      this._root.setAttribute("data-bw-open", "");
      this._input.setAttribute("aria-expanded", "true");
      if (this.filterMode === "client") {
        // Opening shows the full list; typing narrows it from here (the
        // input handler re-applies the filter straight after open()).
        for (const option of this._realOptions()) option.hidden = false;
        this._syncGroups();
        this._ensureCreateOption("");
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
      const before = this._selectionKey();
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
        this._emitChange(before);
        this._announce(this._labelled("added", label));
      } else {
        // A blank value is "no selection", matching how init rehydrates the
        // floor (a blank option never counts as selected).
        this.selected = value === "" ? [] : [value];
        if (value !== "") this._ensureFloorOption(value, label);
        this._syncFloor();
        this._restoreText();
        this._syncOptionSelection();
        this._emitChange(before);
        this.close();
      }
      this._updateClear();
      dispatch(this._root, "bw:combobox:select", { value, label });
    },

    clear() {
      if (!this._operable()) return;
      const before = this._selectionKey();
      this.selected = [];
      this._syncFloor();
      this._renderChips();
      this._syncOptionSelection();
      this._clearQuery();
      this._emitChange(before);
      this.close();
      this._updateClear();
      this._announce(this._statusText("cleared"));
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
            this._setActive(this.activeIndex + 1, 1);
          }
          break;
        case "ArrowUp":
          event.preventDefault();
          if (!this.isOpen) {
            this.open();
            this._setActive(-1, -1); // last enabled
          } else {
            this._setActive(
              this.activeIndex === -1 ? -1 : this.activeIndex - 1,
              -1,
            );
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
          } else if (!this.multiple) {
            // Single mode: the input text is the committed label (CMB-013),
            // so Escape reverts an uncommitted edit instead of blanking the
            // box over a retained value.
            if (this._input.value !== this._committedLabel()) {
              event.preventDefault();
              this._restoreText();
            }
          } else if (this._input.value !== "" || this.query !== "") {
            event.preventDefault();
            this._clearQuery();
          }
          break;
        case "Tab":
          // Close without selecting; the default Tab continues the
          // sequence from the input (no preventDefault).
          if (this.isOpen) this.close();
          this._restoreText();
          break;
        case "Backspace":
          if (
            this.multiple &&
            this._operable() &&
            this._input.value === "" &&
            this.selected.length
          ) {
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
      this._updateClear();
      this._resetActive();
      if (!this.isOpen) this.open();
      if (this.filterMode === "client") {
        this._applyClientFilter();
        this._announceResults();
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
      this._syncGroups();
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
      if (this._error && !this._listbox.contains(this._error)) {
        this._listbox.appendChild(this._error);
      }
      this._hideError();
      this._upgradeOptions();
      this._syncGroups();
      this._resetActive();
      this._syncOptionSelection();
      this._ensureCreateOption();
      this._toggleEmpty();
      this._announceResults();
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

    // A group wrapper is hidden while none of its options is visible
    // (CMB-017), so a heading never sits over an empty run. Arrow movement
    // skips headings because they are not options.
    _syncGroups() {
      for (const group of this._listbox.querySelectorAll(".bw-combobox__group")) {
        const options = group.querySelectorAll(".bw-combobox__option");
        group.hidden = !Array.from(options).some((option) => !option.hidden);
      }
    },

    _upgradeOptions() {
      this._options().forEach((option, index) => {
        option.setAttribute("role", "option");
        if (!option.id) option.id = `${this._listbox.id}-option-${index}`;
      });
    },

    // The create row follows the text the user typed (`text`), never the
    // committed label restored into the input after a choice (CMB-020).
    _ensureCreateOption(text) {
      if (!this.allowCreate) return;
      const query = (text === undefined ? this.query : text).trim();
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
      // A failed request shows the error row instead of "No matches".
      const failed = this._error !== null && !this._error.hidden;
      this._empty.hidden = anyVisible || failed;
    },

    // ----- status, busy and failure (CMB-019, CMB-052) -----

    _statusText(key) {
      if (!this._status) return "";
      const map = {
        loading: this._status.dataset.bwStatusLoading,
        cleared: this._status.dataset.bwStatusCleared,
        one: this._status.dataset.bwStatusOne,
        other: this._status.dataset.bwStatusOther,
      };
      return map[key] || "";
    },

    // A status string with {label} filled in (multiple-mode added/removed).
    _labelled(key, label) {
      const map = {
        added: this._status && this._status.dataset.bwStatusAdded,
        removed: this._status && this._status.dataset.bwStatusRemoved,
      };
      return (map[key] || "").replace("{label}", label);
    },

    _announce(text) {
      if (this._status && text) this._status.textContent = text;
    },

    _announceResults() {
      const count = this._realOptions().filter((option) => !option.hidden).length;
      if (count === 0) {
        this._announce(this._empty ? (this._empty.textContent || "").trim() : "");
      } else if (count === 1) {
        this._announce(this._statusText("one"));
      } else {
        this._announce(this._statusText("other").replace("{count}", String(count)));
      }
    },

    _showError() {
      if (!this._error) return;
      // The failed request never swapped, so the previous options are still
      // in the listbox; the row is shown beside them, never silently.
      if (!this._listbox.contains(this._error)) {
        this._listbox.appendChild(this._error);
      }
      this._error.hidden = false;
      if (this._empty) this._empty.hidden = true;
      this._announce((this._error.textContent || "").trim());
    },

    _hideError() {
      if (this._error) this._error.hidden = true;
    },

    _isDisabled(option) {
      return option.getAttribute("aria-disabled") === "true";
    },

    _activateOption(option) {
      if (!option || this._isDisabled(option)) return;
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

    _onOptionPointerMove(event) {
      // Browsers fire synthetic mousemoves when keyboard scrolling slides a
      // row under a still pointer; a real move has a non-zero delta.
      if (event.movementX === 0 && event.movementY === 0) return;
      const option = event.target.closest(".bw-combobox__option");
      if (!option || !this._listbox.contains(option)) return;
      if (this._isDisabled(option) || option.hasAttribute("data-bw-active")) return;
      const index = this._visibleOptions().indexOf(option);
      if (index !== -1) this._setActive(index, 1, false);
    },

    // ----- active option (aria-activedescendant, no roving tabindex) -----

    // `step` is the direction of travel (1 or -1): a disabled target is
    // skipped in that direction, wrapping (CMB-016).
    _setActive(index, step = 1, scroll = true) {
      const options = this._visibleOptions();
      const count = options.length;
      if (!count) return;
      let wrapped = ((index % count) + count) % count;
      for (let tried = 0; tried < count && this._isDisabled(options[wrapped]); tried += 1) {
        wrapped = (wrapped + step + count) % count;
      }
      if (this._isDisabled(options[wrapped])) return; // every option disabled
      this.activeIndex = wrapped;
      this._clearActiveMarker();
      const option = options[wrapped];
      option.setAttribute("data-bw-active", "");
      this._input.setAttribute("aria-activedescendant", option.id);
      if (scroll && typeof option.scrollIntoView === "function") {
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
      if (!this._operable()) return;
      const before = this._selectionKey();
      const label = this._floorLabel(value) || value;
      this.selected = this.selected.filter((item) => item !== value);
      this._syncFloor();
      this._renderChips();
      this._syncOptionSelection();
      this._emitChange(before);
      this._updateClear();
      this._announce(this._labelled("removed", label));
    },

    _selectionKey() {
      return JSON.stringify(this.selected);
    },

    // Native `change` on the floor, only when the selection really changed
    // (a native select never fires change for a no-op), so dependent fields
    // and htmx change triggers see the new value (CMB-012).
    _emitChange(before) {
      if (this._selectionKey() === before) return;
      this._floor.dispatchEvent(new Event("change", { bubbles: true }));
    },

    // Single mode only: the committed option's label, "" when nothing (or a
    // blank option) is committed.
    _committedLabel() {
      if (this.multiple || !this.selected.length) return "";
      return this._floorLabel(this.selected[0]) || this.selected[0];
    },

    // Single mode: put the committed label back in the input (CMB-013).
    _restoreText() {
      if (this.multiple) return;
      const label = this._committedLabel();
      if (this._input.value !== label) this._input.value = label;
      this.query = label;
      this._updateClear();
    },

    // The label's `for` targets the hidden floor, so name the enhanced input
    // from the floor's labels (or its aria-label) unless the template did
    // (CMB-050). Labels without an id get a stable generated one.
    _nameInput() {
      if (
        this._input.hasAttribute("aria-labelledby") ||
        this._input.hasAttribute("aria-label")
      ) {
        return;
      }
      const ids = Array.from(this._floor.labels || []).map((label, index) => {
        if (!label.id) label.id = `${this._floor.id || this._id}-label-${index}`;
        return label.id;
      });
      if (ids.length) {
        this._input.setAttribute("aria-labelledby", ids.join(" "));
      } else if (this._floor.hasAttribute("aria-label")) {
        this._input.setAttribute("aria-label", this._floor.getAttribute("aria-label"));
      }
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
      if (!button || !this._operable()) return;
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
      this._updateClear();
      if (this.filterMode === "client") {
        for (const option of this._realOptions()) option.hidden = false;
        this._syncGroups();
        this._ensureCreateOption();
        this._toggleEmpty();
      }
    },
  };
}
