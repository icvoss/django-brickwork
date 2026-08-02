// bwSidebarCollapse: the icon-only sidebar collapse behaviour (SHL-003/004,
// 0.13.0, brickwork#58).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwSidebarCollapse", ...) with no config
//   state   isCollapsed (boolean)
//   methods toggle()
//   events  bw:sidebar:collapse / bw:sidebar:expand (no detail), bubbling
//           CustomEvents dispatched from the component root (BR-BW-HTMX-004:
//           optional conventions, never load-bearing).
//
// DOM contract this module enhances (shell/app.html's sidebar_toggle block
// renders the floor). The no-JS floor (BR-BW-HTMX-001) is a fully expanded,
// fully functional sidebar: the toggle button is real markup, reachable and
// labelled, but does nothing without JS, which is a SAFE resting state (an
// always-expanded, always-usable nav), never a dead control blocking
// navigation:
//
//   <aside class="bw-sidebar" id="bw-sidebar" x-data="bwSidebarCollapse()">
//     <button data-bw-sidebar-toggle
//             aria-expanded="true" aria-controls="bw-sidebar"
//             data-bw-sidebar-collapse-label="..."   translated, server-sourced
//             data-bw-sidebar-expand-label="...">     (i18n stays server-side)
//
// At init this module reads a persisted preference from localStorage
// (SHL-003: persistence is host-owned; localStorage is this component's own
// DEFAULT persistence, itself overridable by a consumer template override,
// BR-BW-TPL-002) and applies it immediately, before paint where possible, so
// there is no flash of the wrong state on a returning visit.
//
// [data-bw-collapsed] on .bw-sidebar is the CSS hook (SHL-004: narrows to
// --bw-density-sidebar-width-collapsed, hides text labels, keeps icons); the
// nav items' accessible names stay in the tree regardless (CSS visually
// hides text, never aria-hides it), so collapsing never removes an item's
// name for assistive tech. The toggle button's OWN accessible name flips
// with state (aria-expanded plus the label text swap) so a screen reader
// user always hears the action the button is about to perform, not a static
// "toggle sidebar".
//
// Motion is CSS-owned: this module only toggles the attribute and never
// sequences the width transition (BR-BW-TOK-009 lives entirely in the
// component CSS, gated behind prefers-reduced-motion like every other
// brickwork transition).

const STORAGE_KEY = "bw-sidebar-collapsed";

function dispatch(el, name) {
  el.dispatchEvent(new CustomEvent(name, { bubbles: true }));
}

function readStoredPreference() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false; // storage unavailable (private mode, disabled, quota): default expanded
  }
}

function writeStoredPreference(collapsed) {
  try {
    window.localStorage.setItem(STORAGE_KEY, collapsed ? "true" : "false");
  } catch {
    // storage unavailable: the in-memory state for this page load still works,
    // it just does not persist across page loads. Not a functional failure.
  }
}

export default function sidebarCollapse() {
  return {
    isCollapsed: false,

    _root: null,
    _toggle: null,

    init() {
      const root = this.$el;
      this._root = root;
      this._toggle = root.querySelector("[data-bw-sidebar-toggle]");
      if (!this._toggle) return; // floor markup absent: stay inert

      this.isCollapsed = readStoredPreference();
      this._apply();

      this._toggle.addEventListener("click", () => this.toggle());
    },

    toggle() {
      this.isCollapsed = !this.isCollapsed;
      writeStoredPreference(this.isCollapsed);
      this._apply();
      dispatch(this._root, this.isCollapsed ? "bw:sidebar:collapse" : "bw:sidebar:expand");
    },

    _apply() {
      if (this.isCollapsed) {
        this._root.setAttribute("data-bw-collapsed", "");
      } else {
        this._root.removeAttribute("data-bw-collapsed");
      }
      this._toggle.setAttribute("aria-expanded", this.isCollapsed ? "false" : "true");
      const label = this.isCollapsed
        ? this._toggle.dataset.bwSidebarExpandLabel
        : this._toggle.dataset.bwSidebarCollapseLabel;
      if (label) this._toggle.setAttribute("aria-label", label);
    },
  };
}
