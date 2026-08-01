// bwDropdown: the dropdown menu behaviour (04-interfaces section 4b, 0.8.0).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwDropdown", ...) with config
//     { id, triggerMode: "click"|"hover", closeOnSelect: boolean }
//   state   isOpen (boolean; see the shape note below)
//   methods open(), close(), toggle()
//   events  bw:dropdown:open, bw:dropdown:close (detail { id }), bubbling
//           CustomEvents dispatched from the component root (BR-BW-HTMX-004:
//           optional conventions, never load-bearing).
//
// Shape note: 04-interfaces names both a boolean state key `open` and a
// method `open()`. One JS object cannot carry both under one name, so the
// boolean is exposed as `isOpen` and the methods keep their documented
// names. Flagged for a spec amendment; the method surface is authoritative.
//
// DOM contract this module enhances (_dropdown.html renders the floor;
// BR-BW-HTMX-006). The no-JS floor is a <details> disclosure of plain links
// with NO ARIA menu roles (the _account_menu.html doctrine run forwards):
//
//   <details x-data="bwDropdown({...})">      component root IS the details
//     <summary data-bw-dropdown-trigger>      the trigger (bw_button chrome)
//     <nav data-bw-dropdown-panel>            the menu panel (labelled nav)
//       <a data-bw-dropdown-item href=...>    each actionable item
//       <hr>                                  dividers (implicit separator)
//
// Missing data attributes fall back to details/summary/first non-summary
// child lookup, so the module degrades gracefully rather than throwing.
//
// At init the markup is upgraded in place: role="button", aria-haspopup
// ="menu", aria-expanded on the trigger; role="menu" on the panel;
// role="menuitem" + tabindex="-1" on items; role="separator" on dividers.
// Menu semantics therefore only ever appear when the behaviour they
// promise is running (04-interfaces progressive-enhancement rule).
//
// Keyboard map (WAI-ARIA APG Menu Button pattern, semver-public,
// BR-BW-JS-005): trigger Enter/Space/ArrowDown open + focus first item,
// ArrowUp opens + focuses last. In the menu: ArrowDown/ArrowUp move with
// wrap, Home/End jump, printable characters typeahead, Enter/Space
// activates, Escape closes + returns focus to the trigger (CBH-008),
// Tab/Shift+Tab close and continue the tab sequence. Click-outside closes.
// Focus returns to the trigger on every dismissal route that would
// otherwise drop focus (BR-BW-JS-006).
//
// Motion is CSS-owned: this module toggles state ([data-bw-open] on the
// root, details.open, aria-expanded) and never sequences animation or
// reads timing (BR-BW-TOK-009 lives entirely in the component CSS).

// Typeahead input-buffer window. Not motion timing (BR-BW-TOK-009 governs
// CSS transition/animation timing); this is the APG-conventional keyboard
// buffer reset, a fixed behavioural constant.
const TYPEAHEAD_RESET_MS = 500;

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Unique fallback ids so several dropdowns on one page never collide on
// the generated trigger id (the tag may omit an explicit id).
let instanceCount = 0;

export default function dropdown(config = {}) {
  return {
    isOpen: false,
    id: config.id ?? "",
    triggerMode: config.triggerMode === "hover" ? "hover" : "click",
    closeOnSelect: config.closeOnSelect !== false,

    _details: null,
    _trigger: null,
    _panel: null,
    _typeahead: "",
    _typeaheadAt: 0,
    _onOutsidePointerDown: null,

    init() {
      const root = this.$el;
      this._details = root.matches("details")
        ? root
        : root.querySelector("details");
      this._trigger =
        root.querySelector("[data-bw-dropdown-trigger]") ||
        (this._details ? this._details.querySelector("summary") : null);
      this._panel =
        root.querySelector("[data-bw-dropdown-panel]") ||
        (this._details
          ? this._details.querySelector(":scope > *:not(summary)")
          : null);
      if (!this._trigger || !this._panel) return; // floor markup absent: stay inert

      instanceCount += 1;
      if (!this.id) this.id = root.id || `bw-dropdown-${instanceCount}`;
      if (!this._trigger.id) this._trigger.id = `${this.id}-trigger`;

      // ARIA upgrade: only under JS, per the progressive-enhancement rule.
      this._trigger.setAttribute("role", "button");
      this._trigger.setAttribute("aria-haspopup", "menu");
      this._trigger.setAttribute("aria-expanded", "false");
      this._panel.setAttribute("role", "menu");
      this._panel.setAttribute("aria-labelledby", this._trigger.id);
      this._upgradeItems();

      this._trigger.addEventListener("click", (event) => {
        event.preventDefault(); // never let native <details> toggling race the state
        this.toggle();
      });
      this._trigger.addEventListener("keydown", (event) =>
        this._onTriggerKeydown(event),
      );
      this._panel.addEventListener("keydown", (event) =>
        this._onMenuKeydown(event),
      );
      this._panel.addEventListener("click", (event) => this._onItemClick(event));

      this._onOutsidePointerDown = (event) => {
        if (this.isOpen && !root.contains(event.target)) this.close();
      };
      document.addEventListener("pointerdown", this._onOutsidePointerDown);

      if (this.triggerMode === "hover") {
        // Keyboard and click always work in hover mode (CBH-006); hover only
        // adds pointer affordance on the whole root (trigger + panel).
        root.addEventListener("mouseenter", () => this.open());
        root.addEventListener("mouseleave", () => this.close());
      }
    },

    destroy() {
      if (this._onOutsidePointerDown) {
        document.removeEventListener("pointerdown", this._onOutsidePointerDown);
      }
    },

    open() {
      if (this.isOpen || !this._panel) return;
      this.isOpen = true;
      this._upgradeItems(); // items may have been swapped in via a consumer's hx-* wiring
      this._syncState();
      dispatch(this.$el, "bw:dropdown:open", { id: this.id });
    },

    close() {
      if (!this.isOpen) return;
      this.isOpen = false;
      // BR-BW-JS-006: never drop focus to the document. Restore to the
      // trigger only when focus was inside the menu (Escape, selection,
      // keyboard-then-click-outside); a hover close or an outside click on
      // a focusable control keeps the user's own focus target.
      const active = document.activeElement;
      if (this._panel.contains(active)) this._trigger.focus();
      this._syncState();
      dispatch(this.$el, "bw:dropdown:close", { id: this.id });
    },

    toggle() {
      if (this.isOpen) this.close();
      else this.open();
    },

    _syncState() {
      if (this._details) this._details.open = this.isOpen;
      this._trigger.setAttribute("aria-expanded", this.isOpen ? "true" : "false");
      if (this.isOpen) this.$el.setAttribute("data-bw-open", "");
      else this.$el.removeAttribute("data-bw-open");
    },

    _items() {
      return Array.from(
        this._panel.querySelectorAll("[data-bw-dropdown-item]"),
      ).filter(
        (item) =>
          !item.hasAttribute("disabled") &&
          item.getAttribute("aria-disabled") !== "true",
      );
    },

    _upgradeItems() {
      for (const item of this._panel.querySelectorAll("[data-bw-dropdown-item]")) {
        item.setAttribute("role", "menuitem");
        item.setAttribute("tabindex", "-1");
      }
      // Dividers are plain <hr> elements (implicit separator role); the
      // explicit role keeps the upgraded menu's children unambiguous.
      for (const divider of this._panel.querySelectorAll("hr")) {
        divider.setAttribute("role", "separator");
      }
    },

    _focusItem(index) {
      const items = this._items();
      if (!items.length) return;
      const wrapped = (index + items.length) % items.length;
      items[wrapped].focus();
    },

    _openAndFocus(index) {
      // Synchronous on purpose: open() flips details.open in the same
      // task, so the items are already focusable, and an async gap here
      // would let a fast follow-up keystroke land on the trigger instead
      // of the intended item.
      this.open();
      this._focusItem(index);
    },

    _onTriggerKeydown(event) {
      switch (event.key) {
        case "Enter":
        case " ":
        case "ArrowDown":
          event.preventDefault();
          this._openAndFocus(0);
          break;
        case "ArrowUp":
          event.preventDefault();
          this._openAndFocus(-1);
          break;
        case "Escape":
          if (this.isOpen) {
            event.preventDefault();
            this.close();
          }
          break;
        default:
          break;
      }
    },

    _onMenuKeydown(event) {
      const items = this._items();
      const current = items.indexOf(document.activeElement);
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          this._focusItem(current + 1);
          break;
        case "ArrowUp":
          event.preventDefault();
          this._focusItem(current - 1);
          break;
        case "Home":
          event.preventDefault();
          this._focusItem(0);
          break;
        case "End":
          event.preventDefault();
          this._focusItem(-1);
          break;
        case "Escape":
          event.preventDefault();
          this.close(); // focus restore handled in close(): CBH-008 guarantee
          break;
        case "Tab":
          // Close, put focus on the trigger, and let the browser's default
          // Tab (or Shift+Tab) continue the sequence from there, so items
          // are only ever reached by arrow keys (APG Menu Button).
          this.close();
          this._trigger.focus();
          break;
        case "Enter":
          if (current !== -1) {
            event.preventDefault();
            items[current].click();
          }
          break;
        case " ":
          if (current !== -1) {
            event.preventDefault();
            items[current].click();
          }
          break;
        default:
          this._onTypeahead(event, items, current);
          break;
      }
    },

    _onTypeahead(event, items, current) {
      if (event.key.length !== 1 || event.ctrlKey || event.altKey || event.metaKey) {
        return;
      }
      if (!/\S/.test(event.key)) return;
      const now = Date.now();
      if (now - this._typeaheadAt > TYPEAHEAD_RESET_MS) this._typeahead = "";
      this._typeaheadAt = now;
      const char = event.key.toLowerCase();
      const sameCharRun =
        this._typeahead.length > 0 &&
        this._typeahead.split("").every((c) => c === char);
      this._typeahead += char;
      // A repeated single character cycles through items sharing that
      // initial; a growing prefix narrows the match (APG typeahead).
      const query = sameCharRun ? char : this._typeahead;
      const startFrom = sameCharRun ? current + 1 : Math.max(current, 0);
      for (let step = 0; step < items.length; step += 1) {
        const candidate = items[(startFrom + step) % items.length];
        const label = (candidate.textContent || "").trim().toLowerCase();
        if (label.startsWith(query)) {
          candidate.focus();
          return;
        }
      }
    },

    _onItemClick(event) {
      const item = event.target.closest("[data-bw-dropdown-item]");
      if (!item || !this._panel.contains(item)) return;
      if (this.closeOnSelect) this.close(); // focus returns to trigger, BR-BW-JS-006
    },
  };
}
