// bwSlideOver: the slide-over / side panel behaviour (04-interfaces section
// 4b, 0.14.0, brickwork#55). An edge-anchored sibling of bwModal: same
// dialog semantics and focus-trap contract, different chrome (a scrim plus
// a panel anchored to the inline edge instead of centred).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwSlideOver", ...) with config
//     { id, backdropDismiss: boolean }
//   state   isOpen (boolean; see the shape note below)
//   methods open(), close(reason)
//   events  bw:slide-over:open (detail { id }) and bw:slide-over:close
//           (detail { id, reason: "escape"|"backdrop"|"close-button"|
//           "server"|"programmatic" }), bubbling CustomEvents dispatched
//           from the component root (BR-BW-HTMX-004: optional conventions).
//   listens window "bw:slide-over:close": an htmx response header
//           HX-Trigger: {"bw:slide-over:close": {"id": ...}} closes the
//           panel server-side with zero server-authored JavaScript. An
//           event whose detail carries a different id is ignored.
//
// Shape note: mirrors bwModal's own naming (04-interfaces names both a
// state key `open` and a method `open()`; one JS object cannot carry both
// under one name, so the boolean is exposed as `isOpen`).
//
// Focus trap: wrapped @alpinejs/focus (BR-BW-JS-003), identical contract to
// bwModal. The shipped _slide_over.html emits the same
// `x-trap.inert.noscroll="isOpen"` on the panel; a consumer never authors
// x-trap. The trap-engage race guard and invoker capture/restore are
// SHARED with bwModal via overlay_shared.js (both wrap the same directive
// and need identical close-timing protection); everything else here
// (DOM hooks, event names, dismissal reasons) is authored per-component
// because the public shapes differ (BR-BW-HTMX-004).
//
// DOM contract this module enhances (the template lane renders it):
//   <div x-data="bwSlideOver({...})">                component root
//     <div data-bw-slide-over-scrim>                  the scrim (click = backdrop)
//       <div role="dialog" aria-modal="true"
//            x-trap.inert.noscroll="isOpen">
//         <button data-bw-slide-over-close>            the always-visible close
//         ...consumer blocks; optionally [data-bw-autofocus] on the element
//            that should receive initial focus.
//
// Two render paths, one partial (BR-BW-HTMX-001/006): on the htmx path the
// partial is swapped into the stable #bw-slide-over-root container (a
// DEDICATED root, separate from #bw-modal-root, so a modal and a slide-over
// can be open at once, e.g. a split-shell detail screen's side panel beside
// content) and opens on insertion (init below detects that ancestry); on
// the no-JS floor the same consumer content renders as a full page and this
// module never runs.
//
// Keyboard and focus (WAI-ARIA APG Dialog (Modal) pattern, semver-public):
// on open, focus moves into the dialog (x-trap: the first focusable
// element; [data-bw-autofocus] wins when present); Tab/Shift+Tab cycle
// inside the trap (guaranteed, no opt-out, CBH-002); Escape closes
// unconditionally (CBH-001); the visible close control closes
// (BR-BW-JS-007); scrim click closes when backdropDismiss (CBH-003); and
// focus returns to the invoker on EVERY dismissal route (CBH-004,
// BR-BW-JS-006).
//
// Motion is CSS-owned: this module toggles state ([data-bw-open] on the
// root plus the isOpen binding) and never sequences animation or reads
// timing (BR-BW-TOK-009 lives entirely in the component CSS).

import { dispatch, captureInvoker, guardedClose, restoreInvokerFocus } from "./overlay_shared.js";

export default function slideOver(config = {}) {
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
      // See modal.js: captured once so inline x-on expressions (the
      // close_url anchor) resolve against the component root, not $el
      // scoped to the element the directive is written on.
      const root = this.$el;
      this._root = root;
      if (!this.id) this.id = root.id || "bw-slide-over";

      const preferred = root.querySelector("[data-bw-autofocus]");
      if (preferred) preferred.setAttribute("autofocus", "");

      for (const button of root.querySelectorAll("[data-bw-slide-over-close]")) {
        button.addEventListener("click", () => this.close("close-button"));
      }
      const scrim = root.querySelector("[data-bw-slide-over-scrim]");
      if (scrim) {
        scrim.addEventListener("click", (event) => {
          if (event.target === scrim && this.backdropDismiss) {
            this.close("backdrop");
          }
        });
      }

      // Escape closes unconditionally (CBH-001).
      this._onWindowKeydown = (event) => {
        if (event.key === "Escape" && this.isOpen) {
          event.preventDefault();
          this.close("escape");
        }
      };
      window.addEventListener("keydown", this._onWindowKeydown);

      // Server-side dismissal: HX-Trigger fires bw:slide-over:close from
      // htmx; our own emitted bw:slide-over:close also bubbles here, but by
      // then isOpen is already false, so close() is a no-op (no recursion).
      this._onServerClose = (event) => {
        const targetId = event.detail && event.detail.id;
        if (targetId && targetId !== this.id) return;
        this.close("server");
      };
      window.addEventListener("bw:slide-over:close", this._onServerClose);

      // htmx path: the partial swapped into #bw-slide-over-root opens on
      // insertion. A slide-over rendered anywhere else stays closed until
      // open() is called.
      if (root.closest("#bw-slide-over-root")) {
        this.$nextTick(() => this.open());
      }
    },

    destroy() {
      window.removeEventListener("keydown", this._onWindowKeydown);
      window.removeEventListener("bw:slide-over:close", this._onServerClose);
      if (this._pendingClose) clearTimeout(this._pendingClose);
    },

    open() {
      if (this.isOpen) return;
      this._openedAt = Date.now();
      this._invoker = captureInvoker(this._root, this._invoker);
      this.isOpen = true;
      this._root.setAttribute("data-bw-open", "");
      dispatch(this._root, "bw:slide-over:open", { id: this.id });
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          const preferred = this._root.querySelector("[data-bw-autofocus]");
          if (preferred && this.isOpen) preferred.focus();
        });
      });
    },

    close(reason = "programmatic") {
      if (!this.isOpen || this._pendingClose) return;
      const deferred = guardedClose(this, reason, (deferredReason) => this._close(deferredReason));
      if (!deferred) this._close(reason);
    },

    _close(reason) {
      if (!this.isOpen) return;
      this.isOpen = false;
      this._root.removeAttribute("data-bw-open");
      dispatch(this._root, "bw:slide-over:close", { id: this.id, reason });
      const invoker = this._invoker;
      this._invoker = null;
      restoreInvokerFocus(invoker, this.$nextTick.bind(this));
    },
  };
}
