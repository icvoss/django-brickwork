// bwThemeSwitch: the live root-level control over the shell's axes
// (icvoss/django-brickwork#117, owner ruling 2026-08-07/2026-08-25).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwThemeSwitch", ...) with no config
//   state   none exposed; the DOM (checked radios, <html> attributes) IS
//           the state (mirrors bwTableSelection's "no separate JS store"
//           doctrine)
//   event   bw:theme-switch:change (detail { axis, value }), a bubbling
//           CustomEvent dispatched from the component root whenever an
//           axis changes (BR-BW-HTMX-004: optional convention, never
//           load-bearing).
//
// THE NO-JS FLOOR THIS MODULE ENHANCES (BR-BW-HTMX-001, one deliberate
// departure from the package's usual doctrine, per the #117 ruling): the
// server-rendered page is ALREADY correctly themed, so a theme switch with
// no JS is a control that visibly does nothing, worse than absent. The
// floor here is "render nothing": _theme_switch.html ships the control
// root with the hidden attribute (the same hidden-until-init shape
// dismissible.js already runs for bw_alert/bw_badge's close button), and
// this module's ONLY floor-facing job is removing it at init, exactly the
// reveal step dismissible.js performs.
//
// DOM contract (rendered by _theme_switch.html; never hand-build this):
//
//   <[data-bw-theme-switch] hidden x-data="bwThemeSwitch()">
//     <fieldset data-bw-theme-switch-axis="theme" [data-bw-locked]>
//       <legend>...</legend>
//       <input type=radio data-bw-theme-switch-value value="light" [disabled]>
//       <input type=radio data-bw-theme-switch-value value="dark" [disabled]>
//     ...one fieldset per requested axis...
//
// Persistence (SHL-003, generalised from frontend/src/js/sidebar_collapse.js's
// own rule: "localStorage is this component's own DEFAULT persistence,
// itself overridable by a consumer template override"). Applied per axis:
// - a [data-bw-locked] fieldset (the resolver asserted a real server
//   preference for this axis this request, per bw_theme_locked_axes) never
//   reads or writes localStorage; its radio reflects <html>'s current
//   value and stays disabled, so a client default can never clobber a
//   server preference (the #117 ruling's central precedence rule).
// - every other axis reads its stored preference at init (falling back to
//   <html>'s current attribute value when nothing is stored, so an
//   unvisited axis never guesses), applies it immediately, and writes back
//   to localStorage on every change.
//
// Motion: intentionally none. Flipping data-theme/data-density/dir/data-bw-brand
// is a live token re-resolution; any transition is the CONSUMER's own
// tokens, not something this module sequences.

const STORAGE_PREFIX = "bw-theme-switch-";

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

function storageKey(axis) {
  return `${STORAGE_PREFIX}${axis}`;
}

function readStoredValue(axis) {
  try {
    return window.localStorage.getItem(storageKey(axis));
  } catch {
    return null; // storage unavailable (private mode, disabled, quota): no stored preference
  }
}

function writeStoredValue(axis, value) {
  try {
    window.localStorage.setItem(storageKey(axis), value);
  } catch {
    // storage unavailable: the in-memory state for this page load still works,
    // it just does not persist across page loads. Not a functional failure.
  }
}

// The <html> attribute name for each axis (matching shell/base.html and
// services/tokens.py exactly; brand is the one non-"data-" exception,
// mirroring dir's own bare-attribute shape).
const AXIS_ATTRS = {
  theme: "data-theme",
  density: "data-density",
  dir: "dir",
  brand: "data-bw-brand",
};

export default function themeSwitch() {
  return {
    _root: null,

    init() {
      const root = this.$el;
      this._root = root;
      const groups = root.querySelectorAll("[data-bw-theme-switch-axis]");
      if (!groups.length) return; // floor markup absent: stay inert

      for (const group of groups) {
        this._initGroup(group);
      }

      // Reveal the whole control: it ships hidden so the no-JS floor never
      // shows a control that would do nothing (the #117 ruling's floor
      // rule, mirrored from dismissible.js's close-button reveal).
      root.removeAttribute("hidden");
    },

    _initGroup(group) {
      const axis = group.dataset.bwThemeSwitchAxis;
      const attrName = AXIS_ATTRS[axis];
      if (!attrName) return; // unknown axis (a future addition the JS bundle predates): stay inert for it
      const locked = group.hasAttribute("data-bw-locked");
      const radios = group.querySelectorAll("[data-bw-theme-switch-value]");
      if (!radios.length) return;

      const current = document.documentElement.getAttribute(attrName) || "";
      const initial = locked ? current : readStoredValue(axis) || current;

      if (initial) {
        this._apply(attrName, initial);
      }
      for (const radio of radios) {
        if (radio.value === initial) radio.checked = true;
        if (locked) continue; // disabled in markup already; no listener needed
        radio.addEventListener("change", () => {
          if (!radio.checked) return;
          this._apply(attrName, radio.value);
          writeStoredValue(axis, radio.value);
          dispatch(this._root, "bw:theme-switch:change", { axis, value: radio.value });
        });
      }
    },

    _apply(attrName, value) {
      document.documentElement.setAttribute(attrName, value);
    },
  };
}
