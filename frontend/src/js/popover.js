// bwPopover: the non-modal popover behaviour (docs/components/popover.md,
// R39 / H15).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwPopover", ...) with config { id }
//   state   isOpen (boolean; the boolean cannot share the name of the open()
//           method, the bwDropdown precedent)
//   methods open(), close(reason), toggle()
//   events  bw:popover:open (detail { id }), bw:popover:close (detail { id,
//           reason }), bubbling CustomEvents dispatched from the component
//           root (BR-BW-HTMX-004: optional conventions, never load-bearing).
//           reason is "escape", "outside", "close-button", "trigger" or
//           "programmatic" (POP-039).
//
// DOM contract this module enhances (_popover.html renders the floor, POP-003).
// The no-JS floor is a native <details> and <summary>:
//
//   <details class="bw-popover" x-data="bwPopover({ id })">  component root
//     <summary data-bw-popover-trigger>      the trigger (bw_button chrome)
//     <div data-bw-popover-panel             the panel: static role="dialog"
//          role="dialog" id="<id>">          and name (POP-051)
//       ... [data-bw-autofocus] ... [data-bw-popover-close]
//
// Missing data attributes fall back to the bw-popover__trigger and
// bw-popover__panel classes, so the module degrades rather than throwing.
//
// Only the trigger's ARIA is upgraded at init: aria-haspopup="dialog",
// aria-expanded and aria-controls (POP-050). The panel's role and name are
// static markup and are never touched here.
//
// Behaviour (POP-030 to POP-039), identical to initPopover in @bwui/js:
//   open       press the trigger; focus moves into the panel (a
//              [data-bw-autofocus] element, else the first focusable that is
//              not the close control, else the close control, else the panel)
//   Escape     with focus on the trigger or inside the panel: close, return
//              focus to the trigger, stop propagation so an enclosing Modal
//              does not also close
//   outside    a pointerdown outside the root closes
//   Tab        never closes; there is no trap, inert, scroll lock or scrim
//   focus      every close returns focus to the trigger only if it was inside
//              the panel or already on the trigger (POP-035)
//
// Reuses dispatch and restoreInvokerFocus from overlay_shared.js (POP-073).
// It does not use captureInvoker (the trigger lives inside the root, which
// captureInvoker ignores by design), nor guardedClose or x-trap: with no focus
// trap there is no engage race to guard.
//
// Motion is CSS-owned: this module toggles state ([data-bw-open] on the root,
// details.open, aria-expanded, hidden on the panel) and never sequences
// animation. No user-visible English originates here (POP-076).

import { dispatch, restoreInvokerFocus } from "./overlay_shared.js";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]';

let instanceCount = 0;

export default function popover(config = {}) {
  return {
    isOpen: false,
    id: config.id ?? "",

    _details: null,
    _trigger: null,
    _panel: null,
    _onOutsidePointerDown: null,

    init() {
      const root = this.$el;
      this._details = root.matches("details") ? root : null;
      this._trigger =
        root.querySelector("[data-bw-popover-trigger]") ||
        root.querySelector(":scope > .bw-popover__trigger");
      this._panel =
        root.querySelector("[data-bw-popover-panel]") ||
        root.querySelector(":scope > .bw-popover__panel");
      if (!this._trigger || !this._panel) return; // floor markup absent: stay inert

      instanceCount += 1;
      if (!this.id) this.id = this._panel.id || `bw-popover-${instanceCount}`;
      if (!this._panel.id) this._panel.id = this.id;

      // ARIA upgrade: the trigger only (POP-050), and only under JS.
      this._trigger.setAttribute("aria-haspopup", "dialog");
      this._trigger.setAttribute("aria-controls", this._panel.id);

      this.isOpen = this._details ? this._details.open : root.hasAttribute("data-bw-open");
      this._syncState();

      this._trigger.addEventListener("click", (event) => {
        event.preventDefault(); // never let native <details> toggling race the state
        this.toggle("trigger");
      });
      root.addEventListener("keydown", (event) => this._onKeydown(event));
      this._panel.addEventListener("click", (event) => {
        const control = event.target.closest("[data-bw-popover-close]");
        if (control && this._panel.contains(control)) this.close("close-button");
      });

      this._onOutsidePointerDown = (event) => {
        if (!this.isOpen || root.contains(event.target)) return;
        this._closeOutside();
      };
      document.addEventListener("pointerdown", this._onOutsidePointerDown);
    },

    destroy() {
      if (this._onOutsidePointerDown) {
        document.removeEventListener("pointerdown", this._onOutsidePointerDown);
      }
    },

    open() {
      if (this.isOpen || !this._panel) return;
      this.isOpen = true;
      this._syncState();
      this._focusIn();
      dispatch(this.$el, "bw:popover:open", { id: this.id });
    },

    // Every close routes through here (POP-035).
    close(reason = "programmatic") {
      if (!this.isOpen) return;
      const active = document.activeElement;
      const restore = active === this._trigger || this._panel.contains(active);
      this.isOpen = false;
      this._syncState();
      if (restore) restoreInvokerFocus(this._trigger, this.$nextTick.bind(this));
      dispatch(this.$el, "bw:popover:close", { id: this.id, reason });
    },

    toggle(reason = "trigger") {
      if (this.isOpen) this.close(reason);
      else this.open();
    },

    // An outside press moves focus after this handler runs. Close without
    // touching focus now; if focus was inside and the press left it nowhere,
    // put it back on the trigger once the press has settled (POP-035).
    _closeOutside() {
      const hadFocus = this._panel.contains(document.activeElement);
      this.isOpen = false;
      this._syncState();
      dispatch(this.$el, "bw:popover:close", { id: this.id, reason: "outside" });
      if (hadFocus) {
        setTimeout(() => {
          const now = document.activeElement;
          if ((!now || now === document.body) && this._trigger.isConnected) {
            this._trigger.focus();
          }
        }, 0);
      }
    },

    _syncState() {
      if (this._details) this._details.open = this.isOpen;
      this._trigger.setAttribute("aria-expanded", this.isOpen ? "true" : "false");
      this._panel.hidden = !this.isOpen;
      if (this.isOpen) this.$el.setAttribute("data-bw-open", "");
      else this.$el.removeAttribute("data-bw-open");
    },

    _focusables() {
      return Array.from(this._panel.querySelectorAll(FOCUSABLE)).filter(
        (el) => !el.closest("[hidden]"),
      );
    },

    // POP-031: [data-bw-autofocus], else the first focusable that is not the
    // close control, else the close control, else the panel itself.
    _focusIn() {
      const marked = this._panel.querySelector("[data-bw-autofocus]");
      const all = this._focusables();
      const others = all.filter((el) => !el.classList.contains("bw-popover__close"));
      const target = marked || others[0] || all[0];
      if (target) {
        target.focus();
        return;
      }
      if (!this._panel.hasAttribute("tabindex")) this._panel.setAttribute("tabindex", "-1");
      this._panel.focus();
    },

    _onKeydown(event) {
      if (event.key !== "Escape" || !this.isOpen) return;
      const active = document.activeElement;
      if (active !== this._trigger && !this._panel.contains(active)) return;
      event.preventDefault();
      event.stopPropagation(); // a popover inside a Modal closes alone (POP-032)
      this.close("escape");
    },
  };
}
