// bwNavFlyout: rail menu_trigger companion (brickwork#758).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwNavFlyout", ...) with no required config
//   state   isOpen (boolean), activeKey (string | null)
//   methods open(key), close(reason), toggle(key)
//   events  bw:flyout:open (detail { key }), bw:flyout:close (detail { key,
//           reason }), bubbling CustomEvents from the component root
//           (BR-BW-HTMX-004). reason is "escape", "outside", "trigger" or
//           "programmatic".
//
// DOM contract this module enhances (_flyout.html renders the floor):
//
//   <div class="bw-flyout" x-data="bwNavFlyout()" x-cloak x-show="isOpen">
//     <div class="bw-flyout__panel" data-bw-flyout-panel="<key>" ...>
//
// Triggers live outside this root on the rail:
//   <button data-bw-nav-menu-trigger="<key>" aria-haspopup="menu"
//           aria-expanded="false">
//
// Behaviour:
//   open       click a matching trigger; set aria-expanded on that button
//   toggle     click the open trigger again to close
//   Escape     closes and clears aria-expanded
//   outside    pointerdown outside the root and outside any menu trigger
//              closes
//
// The no-JS floor is the mobile drawer {% bw_nav %} tree, not this panel
// (BR-BW-HTMX-001). Without Alpine the root stays cloaked/hidden.

import { dispatch } from "./overlay_shared.js";

export default function navFlyout() {
  return {
    isOpen: false,
    activeKey: null,

    _onTriggerClick: null,
    _onOutsidePointerDown: null,

    init() {
      this._onTriggerClick = (event) => {
        const trigger = event.target.closest("[data-bw-nav-menu-trigger]");
        if (!trigger) return;
        event.preventDefault();
        const key = trigger.getAttribute("data-bw-nav-menu-trigger");
        if (!key) return;
        this.toggle(key, "trigger");
      };
      document.addEventListener("click", this._onTriggerClick);

      this._onOutsidePointerDown = (event) => {
        if (!this.isOpen) return;
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (this.$el.contains(target)) return;
        if (target.closest("[data-bw-nav-menu-trigger]")) return;
        this.close("outside");
      };
      document.addEventListener("pointerdown", this._onOutsidePointerDown);
    },

    destroy() {
      if (this._onTriggerClick) {
        document.removeEventListener("click", this._onTriggerClick);
      }
      if (this._onOutsidePointerDown) {
        document.removeEventListener("pointerdown", this._onOutsidePointerDown);
      }
    },

    open(key, reason = "programmatic") {
      if (!key) return;
      this._syncTriggers(key);
      this.activeKey = key;
      this.isOpen = true;
      dispatch(this.$el, "bw:flyout:open", { key });
      void reason;
    },

    close(reason = "programmatic") {
      if (!this.isOpen && this.activeKey === null) return;
      const key = this.activeKey;
      this.isOpen = false;
      this.activeKey = null;
      this._syncTriggers(null);
      dispatch(this.$el, "bw:flyout:close", { key, reason });
    },

    toggle(key, reason = "trigger") {
      if (this.isOpen && this.activeKey === key) {
        this.close(reason);
        return;
      }
      this.open(key, reason);
    },

    _syncTriggers(activeKey) {
      document.querySelectorAll("[data-bw-nav-menu-trigger]").forEach((btn) => {
        const key = btn.getAttribute("data-bw-nav-menu-trigger");
        btn.setAttribute("aria-expanded", key === activeKey ? "true" : "false");
      });
    },
  };
}
