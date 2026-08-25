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
// VALIDATION (review fix, #117): a rendered group's own radios ARE its
// closed value set (there is exactly one copy of the vocabulary, the DOM;
// the theme/density/dir sets and the caller-supplied brand slugs are all
// covered by construction, with no separate list to keep in sync). Every
// value this module is about to apply to <html> or persist is checked
// against that set first, whether it came from localStorage (a stale
// build's value, a corrupted write, or a value edited by hand or another
// script/extension) or from a radio's own .value at change time (also a
// mutable DOM property, not a trusted input). An invalid stored value is
// discarded AND removed from storage, rather than applied, so it does not
// keep failing validation on every future load; an invalid change event is
// simply ignored (neither applied nor persisted).
//
// CROSS-TAB (review concern, #117, decided not implemented): this module
// does not listen for the storage event, so a change made in one open tab
// does not live-update a theme switch rendered in another open tab of the
// same site; the second tab's own control still reflects whatever it read
// at ITS OWN init (server render or its own stored value), and only
// catches up on its own next full navigation. This mirrors
// sidebar_collapse.js's existing precedent, which makes the same choice
// for the same persistence pattern: no brickwork interaction currently
// synchronises live across tabs, and adding it here would be new
// behaviour for the whole persistence family, not a fix scoped to this
// component. A consumer wanting live cross-tab sync adds their own
// `window.addEventListener("storage", ...)` bridge (BRANDING.md documents
// this as the accepted trade-off, not a silent gap).
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

function clearStoredValue(axis) {
  try {
    window.localStorage.removeItem(storageKey(axis));
  } catch {
    // storage unavailable: nothing to clear.
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

      // The group's OWN rendered radios are the closed value set: server
      // and client can never disagree on vocabulary because there is only
      // one copy of it, the DOM. Every value this module applies or
      // persists is checked against this set, never trusted as-is, whether
      // it came from localStorage (which a stale build, a corrupted write,
      // or a hand-edited value in devtools/another extension can hold
      // anything in) or from a radio's own .value at change time (a
      // read/write DOM property another script could have mutated between
      // render and the change event firing).
      const validValues = new Set(Array.from(radios, (radio) => radio.value));
      const isValid = (value) => validValues.has(value);

      const current = document.documentElement.getAttribute(attrName) || "";
      let initial = current;
      if (!locked) {
        const stored = readStoredValue(axis);
        if (stored !== null) {
          if (isValid(stored)) {
            initial = stored;
          } else {
            // Invalid stored value (corrupted, stale from a retired
            // vocabulary, or tampered with): discard it rather than apply
            // it to <html>, and remove the bad entry so it does not keep
            // failing validation on every future load.
            clearStoredValue(axis);
          }
        }
      }

      if (initial) {
        this._apply(attrName, initial);
      }
      for (const radio of radios) {
        if (radio.value === initial) radio.checked = true;
        if (locked) continue; // disabled in markup already; no listener needed
        radio.addEventListener("change", () => {
          if (!radio.checked) return;
          if (!isValid(radio.value)) return; // tampered value: never apply or persist it
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
