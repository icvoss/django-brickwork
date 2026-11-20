// bwDisclosure: close behaviour for a native <details> disclosure
// (icvoss/brickwork#233, icvoss/django-brickwork#762).
//
// Public shape (semver-public, BR-BW-JS-004):
//   Alpine.data("bwDisclosure", ...)
//   config  { dismiss: true } by default. Pass { dismiss: false } for an
//           in-flow content disclosure: the summary still toggles, and the
//           close animates, but a pointer outside and Escape do not dismiss
//           it. The account menu uses the default.
//
// The no-JS floor is the native summary toggle. This module only enhances
// a disclosure the browser can already open and close. It does not add
// role="menu" or arrow-key handling.
//
// Exit motion cannot be a transition on a closed details: the UA hides
// non-summary children with display:none the moment open is removed, and
// an enter-only keyframe does not play backwards. The close path keeps
// open set, adds bw-disclosure-closing, and removes open when the panel's
// exit animation ends. prefers-reduced-motion: reduce closes immediately,
// without waiting for animationend. A computed animation-name of none
// (the published stylesheet has not caught up yet) also closes immediately.

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

export default function disclosure(config = {}) {
  const dismiss = !config || config.dismiss !== false;
  return {
    _details: null,
    _summary: null,
    _panel: null,
    _onSummaryClick: null,
    _onKeydown: null,
    _onOutside: null,
    _closing: false,

    init() {
      const root = this.$el;
      this._details = root.matches("details") ? root : root.querySelector("details");
      if (!this._details) return;
      this._summary = this._details.querySelector("summary");
      this._panel = this._details.querySelector("[data-bw-disclosure-panel]");
      if (this._summary) {
        this._onSummaryClick = (event) => {
          if (!this._details.open || this._closing) return;
          event.preventDefault();
          this._close(false);
        };
        this._summary.addEventListener("click", this._onSummaryClick);
      }
      if (!dismiss) return;
      this._onKeydown = (event) => {
        if (event.key !== "Escape" || !this._details.open || this._closing) return;
        event.preventDefault();
        this._close(true);
      };
      this._details.addEventListener("keydown", this._onKeydown);
      this._onOutside = (event) => {
        if (!this._details.open || this._closing) return;
        if (this._details.contains(event.target)) return;
        this._close(false);
      };
      document.addEventListener("pointerdown", this._onOutside);
    },

    _close(focusTrigger) {
      const details = this._details;
      if (!details || !details.open || this._closing) return;
      const finish = () => {
        this._closing = false;
        details.classList.remove("bw-disclosure-closing");
        details.open = false;
        if (focusTrigger && this._summary) this._summary.focus();
      };
      const reduce = window.matchMedia(REDUCED_MOTION).matches;
      const panel = this._panel;
      if (reduce || !panel) {
        finish();
        return;
      }
      this._closing = true;
      details.classList.add("bw-disclosure-closing");
      const animationName = window.getComputedStyle(panel).animationName;
      if (!animationName || animationName === "none") {
        finish();
        return;
      }
      let settled = false;
      const settle = () => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        panel.removeEventListener("animationend", onEnd);
        finish();
      };
      const onEnd = (event) => {
        if (event.target !== panel) return;
        settle();
      };
      const timer = window.setTimeout(settle, 400);
      panel.addEventListener("animationend", onEnd);
    },

    destroy() {
      if (this._summary && this._onSummaryClick) {
        this._summary.removeEventListener("click", this._onSummaryClick);
      }
      if (this._details && this._onKeydown) {
        this._details.removeEventListener("keydown", this._onKeydown);
      }
      if (this._onOutside) {
        document.removeEventListener("pointerdown", this._onOutside);
      }
    },
  };
}
