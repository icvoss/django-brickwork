// bwModal: the modal dialog behaviour (04-interfaces section 4b, 0.9.0
// contract; module lands with the 0.8.0 bootstrap so the JS surface ships
// complete and the template lane can wire against it).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwModal", ...) with config
//     { id, backdropDismiss: boolean }
//   state   isOpen (boolean; see the shape note below)
//   methods open(), close(reason)
//   events  bw:modal:open (detail { id }) and bw:modal:close (detail
//           { id, reason: "escape"|"backdrop"|"close-button"|"server"|
//           "programmatic" }), bubbling CustomEvents dispatched from the
//           component root (BR-BW-HTMX-004: optional conventions).
//   listens window "bw:modal:close": an htmx response header
//           HX-Trigger: {"bw:modal:close": {"id": ...}} closes the modal
//           server-side with zero server-authored JavaScript. An event
//           whose detail carries a different id is ignored.
//
// Shape note: 04-interfaces names both a boolean state key `open` and a
// method `open()`. One JS object cannot carry both under one name, so the
// boolean is exposed as `isOpen` and the methods keep their documented
// names. Flagged for a spec amendment; the method surface is authoritative.
//
// Focus trap: wrapped @alpinejs/focus (BR-BW-JS-003). The shipped
// _modal.html emits `x-trap.inert.noscroll="isOpen"` on the dialog panel
// itself; a consumer never authors x-trap. @alpinejs/focus is a HOST-OWNED
// peer: the host applies Alpine.plugin(focus) before calling
// registerBrickworkComponents(Alpine) (BR-BW-JS-001; in this repo it is a
// devDependency for the Playwright harness only). The .noscroll modifier
// carries the body scroll lock; .inert removes the page behind from the
// accessibility tree.
//
// DOM contract this module enhances (the template lane renders it):
//   <div x-data="bwModal({...})">                    component root
//     <div data-bw-modal-scrim>                       the scrim (click = backdrop)
//       <div role="dialog" aria-modal="true"
//            x-trap.inert.noscroll="isOpen" x-show="isOpen">
//         <button data-bw-modal-close>                the always-visible close
//         ...consumer blocks; optionally [data-bw-autofocus] on the element
//            that should receive initial focus.
//
// Two render paths, one partial (BR-BW-HTMX-001/006): on the htmx path the
// partial is swapped into the stable #bw-modal-root container and opens on
// insertion (init below detects that ancestry); on the no-JS floor the
// same consumer content renders as a full page and this module never runs.
//
// Keyboard and focus (WAI-ARIA APG Dialog (Modal) pattern, semver-public):
// on open, focus moves into the dialog (x-trap: the first focusable
// element; [data-bw-autofocus] wins when present); Tab/Shift+Tab cycle
// inside the trap (guaranteed, no opt-out, CBH-002); Escape closes
// unconditionally (CBH-001); the visible close control closes
// (BR-BW-JS-007); scrim click closes when backdropDismiss (CBH-003); and
// focus returns to the invoker on EVERY dismissal route (CBH-004,
// BR-BW-JS-006). Nested modals are unsupported (CBH-005).
//
// Motion is CSS-owned: this module toggles state ([data-bw-open] on the
// root plus the isOpen binding) and never sequences animation or reads
// timing (BR-BW-TOK-009 lives entirely in the component CSS).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Minimum gap between the open and close state flips. The wrapped x-trap
// engages its focus trap ~15ms after the open flip (upstream @alpinejs/
// focus schedules trap.activate() on a timeout, with inert applied after
// activation); a close flip landing inside that window tears down a trap
// that has not engaged yet and leaves an ORPHANED ACTIVE trap stealing
// focus page-wide. Not motion timing (BR-BW-TOK-009 governs CSS); a
// behavioural race guard, invisible to humans.
const TRAP_ENGAGE_GUARD_MS = 50;

export default function modal(config = {}) {
  return {
    isOpen: false,
    id: config.id ?? "",
    backdropDismiss: config.backdropDismiss !== false,

    _root: null,
    _invoker: null,
    _onWindowKeydown: null,
    _onServerClose: null,
    _openedAt: 0,
    _pendingClose: null,

    init() {
      // Captured once and reused everywhere below instead of re-reading
      // this.$el at call time: Alpine's inline x-on expressions (the
      // close_url anchor's x-on:click.prevent="close('close-button')")
      // evaluate with $el scoped to the element the directive is WRITTEN
      // ON, not the component root, so a call arriving through that path
      // would otherwise flip isOpen on the root's reactive state while
      // mutating data-bw-open on the anchor instead (BR-BW-JS-007).
      const root = this.$el;
      this._root = root;
      if (!this.id) this.id = root.id || "bw-modal";

      // [data-bw-autofocus] maps onto the wrapped trap's initial focus:
      // @alpinejs/focus reads the native autofocus attribute when building
      // its trap options (which happens after this init), so mirroring the
      // marker here makes the trap itself land focus on the right element
      // instead of the first focusable (04-interfaces).
      const preferred = root.querySelector("[data-bw-autofocus]");
      if (preferred) preferred.setAttribute("autofocus", "");

      for (const button of root.querySelectorAll("[data-bw-modal-close]")) {
        button.addEventListener("click", () => this.close("close-button"));
      }
      const scrim = root.querySelector("[data-bw-modal-scrim]");
      if (scrim) {
        scrim.addEventListener("click", (event) => {
          if (event.target === scrim && this.backdropDismiss) {
            this.close("backdrop");
          }
        });
      }

      // Escape closes unconditionally (CBH-001). A must-confirm flow routes
      // the resulting bw:modal:close through its own confirm branch; it
      // never disables Escape (BR-BW-JS-007).
      this._onWindowKeydown = (event) => {
        if (event.key === "Escape" && this.isOpen) {
          event.preventDefault();
          this.close("escape");
        }
      };
      window.addEventListener("keydown", this._onWindowKeydown);

      // Server-side dismissal: HX-Trigger fires bw:modal:close from htmx;
      // our own emitted bw:modal:close also bubbles here, but by then
      // isOpen is already false, so close() is a no-op (no recursion).
      this._onServerClose = (event) => {
        const targetId = event.detail && event.detail.id;
        if (targetId && targetId !== this.id) return;
        this.close("server");
      };
      window.addEventListener("bw:modal:close", this._onServerClose);

      // htmx path: the partial swapped into #bw-modal-root opens on
      // insertion (04-interfaces). A modal rendered anywhere else stays
      // closed until open() is called.
      if (root.closest("#bw-modal-root")) {
        this.$nextTick(() => this.open());
      }
    },

    destroy() {
      window.removeEventListener("keydown", this._onWindowKeydown);
      window.removeEventListener("bw:modal:close", this._onServerClose);
      if (this._pendingClose) clearTimeout(this._pendingClose);
    },

    open() {
      if (this.isOpen) return;
      this._openedAt = Date.now();
      // Capture the invoker BEFORE focus moves into the dialog, so every
      // dismissal route can restore it (CBH-004, BR-BW-JS-006). On the
      // htmx path this is the triggering anchor (htmx leaves focus there).
      const active = document.activeElement;
      this._invoker =
        active && active !== document.body && !this._root.contains(active)
          ? active
          : this._invoker;
      this.isOpen = true;
      this._root.setAttribute("data-bw-open", "");
      dispatch(this._root, "bw:modal:open", { id: this.id });
      // x-trap moves focus to the first focusable element; an explicit
      // [data-bw-autofocus] wins when present (04-interfaces).
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          const preferred = this._root.querySelector("[data-bw-autofocus]");
          if (preferred && this.isOpen) preferred.focus();
        });
      });
    },

    close(reason = "programmatic") {
      if (!this.isOpen || this._pendingClose) return;
      const elapsed = Date.now() - this._openedAt;
      if (elapsed < TRAP_ENGAGE_GUARD_MS) {
        // Defer just long enough for the trap to engage before teardown;
        // the close still happens, same reason, same event.
        this._pendingClose = setTimeout(() => {
          this._pendingClose = null;
          this._close(reason);
        }, TRAP_ENGAGE_GUARD_MS - elapsed);
        return;
      }
      this._close(reason);
    },

    _close(reason) {
      if (!this.isOpen) return;
      this.isOpen = false;
      this._root.removeAttribute("data-bw-open");
      dispatch(this._root, "bw:modal:close", { id: this.id, reason });
      // Focus returns to the invoker on EVERY dismissal route. x-trap also
      // restores its own captured element on deactivation; this explicit
      // restore guarantees the contract even when the trap never engaged
      // (e.g. a close arriving before first focus) or was torn down by an
      // htmx swap.
      const invoker = this._invoker;
      this._invoker = null;
      this.$nextTick(() => {
        if (invoker && invoker.isConnected && typeof invoker.focus === "function") {
          invoker.focus();
        }
      });
    },
  };
}
