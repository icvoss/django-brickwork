// bwTooltip: the tooltip bubble behaviour (0.12.0, #56, supersedes STA-015's
// title-only baseline).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwTooltip", ...) with config { id }
//   state   isOpen (boolean)
//   methods open(), close()
//   events  bw:tooltip:show, bw:tooltip:hide (detail { id }), bubbling
//           CustomEvents dispatched from the component root (BR-BW-HTMX-004:
//           optional conventions, never load-bearing).
//
// DOM contract this module enhances (_tooltip.html renders the floor;
// BR-BW-HTMX-006). The no-JS floor is a native title attribute on the
// trigger, so a tooltip with no JavaScript still has SOME accessible hint
// (the browser's own title tooltip), never a silently absent one:
//
//   <span x-data="bwTooltip({ id })">     component root
//     <span data-bw-tooltip-trigger        the trigger (consumer's
//           title="...">                   tooltip_trigger block content)
//     <span data-bw-tooltip-bubble          the bubble (role=tooltip, hidden)
//       role="tooltip" id="<id>" hidden>
//
// A tooltip is not a dialog (WAI-ARIA APG Tooltip pattern): it never traps
// focus, never receives focus itself, and never blocks the trigger's own
// click/keyboard behaviour. Shows on mouseenter or focus of the trigger,
// hides on mouseleave, blur, or Escape (Escape leaves focus on the trigger,
// since it never moved into the bubble).
//
// Motion is CSS-owned: this module toggles the hidden attribute and
// [data-bw-open] and never sequences animation or reads timing
// (BR-BW-TOK-009 lives entirely in the component CSS).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

let instanceCount = 0;

export default function tooltip(config = {}) {
  return {
    isOpen: false,
    id: config.id ?? "",

    _trigger: null,
    _bubble: null,

    init() {
      const root = this.$el;
      this._trigger = root.querySelector("[data-bw-tooltip-trigger]");
      this._bubble = root.querySelector("[data-bw-tooltip-bubble]");
      if (!this._trigger || !this._bubble) return; // floor markup absent: stay inert

      instanceCount += 1;
      if (!this.id) this.id = root.id || `bw-tooltip-${instanceCount}`;

      this._trigger.addEventListener("mouseenter", () => this.open());
      this._trigger.addEventListener("mouseleave", () => this.close());
      // focus/blur do not bubble, so a focusable element nested inside the
      // trigger (the documented usage, e.g. a real <button> in the trigger
      // block) would never reach a listener bound on the wrapper itself.
      // focusin/focusout bubble, mirroring how mouseenter/mouseleave already
      // reach the wrapper from descendants (#355).
      this._trigger.addEventListener("focusin", () => this.open());
      this._trigger.addEventListener("focusout", (event) => {
        // Only close when focus genuinely leaves the trigger subtree: a
        // relatedTarget still inside the trigger (focus moving between
        // elements within it) must not flicker the bubble closed.
        if (!event.relatedTarget || !this._trigger.contains(event.relatedTarget)) {
          this.close();
        }
      });
      this._trigger.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && this.isOpen) {
          event.preventDefault();
          this.close();
        }
      });
    },

    open() {
      if (this.isOpen || !this._bubble) return;
      this.isOpen = true;
      this._bubble.removeAttribute("hidden");
      this.$el.setAttribute("data-bw-open", "");
      dispatch(this.$el, "bw:tooltip:show", { id: this.id });
    },

    close() {
      if (!this.isOpen) return;
      this.isOpen = false;
      this._bubble.setAttribute("hidden", "");
      this.$el.removeAttribute("data-bw-open");
      dispatch(this.$el, "bw:tooltip:hide", { id: this.id });
    },
  };
}
