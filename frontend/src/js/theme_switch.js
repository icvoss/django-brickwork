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
// floor here is "render nothing VISIBLE": _theme_switch.html ships the
// control root with the bw-theme-switch--pre-init class (icvoss/django-
// brickwork#272, supersedes the unconditional hidden attribute this
// shipped with through 3.11.0), and this module's ONLY floor-facing job is
// swapping that class off at init.
//
// Reserved pre-init state (#272): bw-theme-switch--pre-init sets
// visibility: hidden rather than removing the box from flow, so the
// control's own true, label-dependent footprint is already reserved at
// first paint; init only changes visibility, never geometry, so the reveal
// produces no layout-shift entry. Class-based, not attribute-based, and
// this is load-bearing, not a style choice, but the reason is GEOMETRY, not
// cascade priority: the hidden attribute is display: none in the UA sheet,
// out of flow by definition, so no attribute-only shape can reserve space
// while hiding. Only a class (or inline style) carries visibility: hidden
// here. components.css's own !important on this class is the same
// scoped-floor pattern index.css already uses for [hidden] ("hidden always
// means hidden without a consumer preflight"), not a claim about beating
// Tailwind's layered preflight rule (a different rule entirely, on the
// attribute this class no longer uses): this package's own compiled CSS
// carries no @layer at all, so an ordinary unlayered consumer rule could
// otherwise override a bare visibility: hidden on a descendant (the compact
// trigger, say) and leave part of the control visible and focusable while
// pre-init.
//
// That descendant gap is real regardless of layering (#272 review):
// visibility only INHERITS, and an inherited value always loses to a value
// specified on the element itself, ancestor !important notwithstanding
// (!important only arbitrates between rules matching the SAME element,
// never against inheritance from elsewhere). components.css's
// .bw-theme-switch--pre-init rule therefore also matches every descendant
// (.bw-theme-switch--pre-init *), forcing each one's OWN visibility rather
// than relying on inheritance, so a single ordinary consumer rule on
// .bw-theme-switch__trigger has nothing weaker to beat. This module never
// has to reason about that: it only ever adds or removes the one class on
// the root, and the CSS rule covers the whole subtree.
//
// DOM contract (rendered by _theme_switch.html; never hand-build this):
//
//   <[data-bw-theme-switch].bw-theme-switch--pre-init x-data="bwThemeSwitch()"
//                           data-bw-theme-switch-values="<id>-values">
//     <script id="<id>-values" type="application/json">{"theme": [...], ...}</script>
//     <fieldset data-bw-theme-switch-axis="theme" [data-bw-locked]>
//       <legend>...</legend>
//       <input type=radio data-bw-theme-switch-value value="light" [disabled] [checked]>
//       <input type=radio data-bw-theme-switch-value value="dark" [disabled] [checked]>
//     ...one fieldset per requested axis... (a locked group's checked radio
//     is the server-resolved value; an unlocked group renders none checked,
//     this module resolves the initial checked state itself)
//
// Persistence (SHL-003, generalised from frontend/src/js/sidebar_collapse.js's
// own rule: "localStorage is this component's own DEFAULT persistence,
// itself overridable by a consumer template override"). Applied per axis:
// - a [data-bw-locked] fieldset (the resolver asserted a real server
//   preference for this axis this request, per bw_theme_locked_axes) never
//   reads <html> or localStorage to decide its own state: its matching
//   radio is checked SERVER-SIDE (group.locked_value in
//   _theme_switch.html, resolved from the same bw_theme/bw_density/bw_dir/
//   bw_brand context vars the shell itself reads), and this module applies
//   nothing to <html> for it. Reading the live <html> attribute at JS init
//   time would be order-dependent when more than one switch instance
//   shares an axis on one page (ordinary, not a misuse): an
//   earlier-initialising UNLOCKED sibling on the same axis can already
//   have changed <html> by the time a locked instance's own init runs.
// - every other axis reads its stored preference at init (falling back to
//   <html>'s current attribute value when nothing is stored, so an
//   unvisited axis never guesses), applies it immediately, and writes back
//   to localStorage on every change.
//
// VALIDATION (review fix, #117): the SERVER-EMITTED closed set per axis
// (a json_script sibling of the control root, read via readValidValues
// below), never the DOM's own rendered radios: a consumer's mistaken
// override of _theme_switch.html rendering a wrong or extra <input> must
// not widen what this module accepts, which validating against the live
// DOM could not catch. Every value this module is about to apply to
// <html> or persist is checked against that payload first, whether it
// came from localStorage (a stale build's value, a corrupted write, or a
// value edited by hand or another script/extension), from <html>'s own
// current attribute (a consumer template mistake, never assumed correct
// just because it is already there), or from a radio's own .value at
// change time (also a mutable DOM property, not a trusted input). An
// invalid stored value is discarded AND removed from storage, rather than
// applied, so it does not keep failing validation on every future load
// (locked groups clean up an INVALID stored entry too, but never touch a
// VALID one, which may legitimately belong to an unlocked sibling instance
// sharing the same axis); an invalid change event is simply ignored
// (neither applied nor persisted); an invalid <html> attribute is treated
// as absent, never adopted as this axis's state.
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
//
// layout="compact" (icvoss/django-brickwork#235): the fieldsets above are
// wrapped in a native <details class="bw-theme-switch__disclosure">, an APG
// Disclosure with deliberately NO ARIA menu roles (the _account_menu.html
// doctrine: role="menu" mandates arrow-key handling this module never
// provides here). The disclosure already opens/closes with no JS at all
// (native <details>/<summary>); this module's ONLY job for it is adding the
// three dismissal routes bwDropdown's own panel offers (Escape with focus
// returned to the trigger, and click/tap outside), each wired once at init
// and removed in destroy(), mirroring bwDropdown's own
// document-pointerdown-listener lifecycle
// (frontend/src/js/dropdown.js). Selecting a radio inside the panel never
// closes it: unlike a command menu (bwDropdown's closeOnSelect), a visitor
// may want to flip more than one axis in a single visit, so the panel stays
// open until one of the three dismissal routes fires.

const STORAGE_PREFIX = "bw-theme-switch-";

// The reserved pre-init state (#272): visibility: hidden, in flow, never
// display:none, so the control's own box is already reserved at first
// paint. init() swaps this off; destroy() restores it, so a control
// re-mounted into a fresh root (never a re-init of a live one, see
// destroy()'s own note below) starts from the same floor a first render
// would.
const PRE_INIT_CLASS = "bw-theme-switch--pre-init";

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
// mirroring dir's own bare-attribute shape). Object.create(null) rather
// than a plain object literal (review fix, #117): a plain {} inherits from
// Object.prototype, so AXIS_ATTRS["toString"] or AXIS_ATTRS["constructor"]
// resolves to an inherited function rather than undefined, which a crafted
// or merely typo'd axis (from the rendered data-bw-theme-switch-axis
// attribute, itself server-controlled but treated here as untrusted input
// on principle) must never be able to reach. A null-prototype object has
// no inherited properties at all, so a bracket lookup for any name not
// explicitly assigned below is genuinely undefined.
const AXIS_ATTRS = Object.assign(Object.create(null), {
  theme: "data-theme",
  density: "data-density",
  dir: "dir",
  brand: "data-bw-brand",
});

// Read the closed value set the server emitted for this instance (review
// fix, #117): a json_script sibling of the control root, referenced by
// data-bw-theme-switch-values, never the DOM's own rendered radios. This
// is the validation contract's actual source of truth: it holds even if a
// consumer's own override of _theme_switch.html renders a different, wrong
// or incomplete set of <input>s, which validating against the live DOM
// could not catch (the consumer-mistake case the review named explicitly).
// Returns a null-prototype object ({axis: [value, ...]}) so a later
// own-property lookup can never resolve to an inherited member either;
// malformed JSON (a corrupted script tag, a hand-edited page) yields an
// empty payload rather than throwing, so init() degrades to "nothing
// validates as valid" rather than crashing the whole component.
function readValidValues(root) {
  const elementId = root.dataset.bwThemeSwitchValues;
  const script = elementId ? document.getElementById(elementId) : null;
  if (!script) return Object.create(null);
  try {
    const parsed = JSON.parse(script.textContent);
    return Object.assign(Object.create(null), parsed);
  } catch {
    return Object.create(null); // malformed payload: validate against nothing, not everything
  }
}

export default function themeSwitch() {
  return {
    _root: null,
    _removedPreInitClass: false,
    _disclosure: null,
    _disclosureTrigger: null,
    _onDisclosureKeydown: null,
    _onOutsidePointerDown: null,

    init() {
      const root = this.$el;
      this._root = root;
      const groups = root.querySelectorAll("[data-bw-theme-switch-axis]");
      if (!groups.length) return; // floor markup absent: stay inert

      const validValues = readValidValues(root);
      for (const group of groups) {
        this._initGroup(group, validValues);
      }

      // Reveal the whole control: it ships pre-init (visibility: hidden,
      // in flow) so the no-JS floor never shows a control that would do
      // nothing (the #117 ruling's floor rule), while its box is already
      // reserved (#272) so this class swap changes appearance only, never
      // geometry. Record whether THIS init actually removed the class
      // (#272 review): a consumer whose markup never carried it (hand-
      // written from the docs, or legacy markup predating this change)
      // must not have destroy() add a class init never took away, which
      // would leave that control permanently invisible with no init having
      // run against it at all.
      this._removedPreInitClass = root.classList.contains(PRE_INIT_CLASS);
      root.classList.remove(PRE_INIT_CLASS);

      this._initCompactDisclosure(root);
    },

    // layout="compact" (#235): the disclosure already opens/closes with no
    // JS (native <details>/<summary>); this only adds the dismissal routes
    // a bare <details> does not provide on its own (Escape, click/tap
    // outside), mirroring bwDropdown's own listener shape
    // (frontend/src/js/dropdown.js). Absent on layout="inline" (no
    // .bw-theme-switch__disclosure in the markup at all), so this stays
    // inert for the pre-existing render.
    _initCompactDisclosure(root) {
      const disclosure = root.querySelector(":scope > .bw-theme-switch__disclosure");
      if (!disclosure) return;
      const trigger = disclosure.querySelector(":scope > .bw-theme-switch__trigger");
      if (!trigger) return;

      this._disclosure = disclosure;
      this._disclosureTrigger = trigger;

      this._onDisclosureKeydown = (event) => {
        if (event.key !== "Escape" || !disclosure.open) return;
        event.preventDefault();
        disclosure.open = false;
        trigger.focus(); // BR-BW-JS-006: never drop focus on a dismissal route
      };
      disclosure.addEventListener("keydown", this._onDisclosureKeydown);

      this._onOutsidePointerDown = (event) => {
        if (disclosure.open && !disclosure.contains(event.target)) {
          disclosure.open = false;
        }
      };
      document.addEventListener("pointerdown", this._onOutsidePointerDown);

      // Deliberately no listener on radio change: unlike a command menu
      // (bwDropdown's closeOnSelect), a visitor may want to flip more than
      // one axis in a single visit, so selecting a radio never closes the
      // panel; only the summary toggle, Escape, and click/tap outside do.
    },

    destroy() {
      // Restore the pre-init class (#272), but ONLY if this instance's own
      // init() actually removed it: restoring unconditionally regressed a
      // consumer whose markup never carried the class in the first place
      // (hand-written from the docs, or legacy markup predating this
      // change) into a control that rendered visible, worked, and then
      // went permanently invisible on teardown, having never been in the
      // reserved pre-init state to begin with. This guards the root itself,
      // never a live re-init of it: Alpine v3's initTree() skips any root
      // already carrying its own internal _x_marker, so a removed-and-
      // reinserted root is never re-initialised by Alpine at all, only a
      // genuinely fresh server-rendered root (which already ships the
      // class, and whose own init() sets _removedPreInitClass again) is.
      // Restoring it here is the defensive floor for the node THIS
      // instance owned, not a re-init mechanism.
      if (this._root && this._removedPreInitClass) {
        this._root.classList.add(PRE_INIT_CLASS);
      }
      if (this._disclosure && this._onDisclosureKeydown) {
        this._disclosure.removeEventListener("keydown", this._onDisclosureKeydown);
      }
      if (this._onOutsidePointerDown) {
        document.removeEventListener("pointerdown", this._onOutsidePointerDown);
      }
    },

    _initGroup(group, validValues) {
      const axis = group.dataset.bwThemeSwitchAxis;
      // Object.hasOwn (own-property only, review fix #117): AXIS_ATTRS and
      // validValues are both null-prototype, so a plain `in` or bracket
      // check would already be safe here too, but hasOwn is the explicit,
      // unambiguous statement of intent and costs nothing.
      if (!Object.hasOwn(AXIS_ATTRS, axis)) return; // unknown axis (a future addition the JS bundle predates): stay inert for it
      const attrName = AXIS_ATTRS[axis];
      const locked = group.hasAttribute("data-bw-locked");
      const radios = group.querySelectorAll("[data-bw-theme-switch-value]");
      if (!radios.length) return;

      const axisValues = Object.hasOwn(validValues, axis) ? validValues[axis] : [];
      const validSet = new Set(Array.isArray(axisValues) ? axisValues : []);
      const isValid = (value) => validSet.has(value);

      if (locked) {
        // A locked axis's state is resolved SERVER-SIDE (the checked
        // attribute on the matching radio, from group.locked_value in
        // _theme_switch.html) and this branch never reads <html> or
        // localStorage to decide it. That is deliberate, not an
        // optimisation: reading the live document.documentElement
        // attribute here would be order-dependent when more than one
        // switch instance shares an axis on the same page (an ordinary,
        // documented pattern, not a misuse), since an earlier-initialising
        // UNLOCKED sibling on the same axis can already have called
        // _apply() and changed <html> by the time this instance's own
        // init() runs, which would make a locked group silently show the
        // wrong value. Nothing here needs to be applied to <html> either:
        // the server already rendered <html> from the SAME context value
        // this radio's checked state came from, so writing it again would
        // be redundant at best.
        //
        // An INVALID stored entry (review fix #117: this cleanup was
        // previously unlocked-only) is still cleaned up here, exactly as
        // the unlocked branch below does: a stale value from a retired
        // vocabulary, a corrupted write, or one hand-edited in devtools
        // must not keep failing validation forever. A VALID stored value
        // is left untouched, deliberately: storage is scoped per axis, not
        // per instance, so a genuinely valid entry here may belong to
        // another switch instance on the SAME page that still has this
        // axis unlocked (a deliberate, if unusual, per-instance override of
        // locked_axes=); this locked instance has no way to tell "stale
        // from before I was locked" apart from "currently valid for a
        // sibling", and only the latter is provably safe to leave alone.
        const stored = readStoredValue(axis);
        if (stored !== null && !isValid(stored)) clearStoredValue(axis);
        return; // disabled in markup already; no listener needed, nothing to apply
      }

      const rawCurrent = document.documentElement.getAttribute(attrName) || "";
      // The root's OWN current attribute value is validated too (review
      // fix #117), not trusted just because it is already on <html>: a
      // consumer template mistake (a stray or mistyped data-theme value)
      // must not be adopted as this axis's state, offered as a checked
      // radio, or become the fallback a later stored-value read defers to.
      const current = rawCurrent && isValid(rawCurrent) ? rawCurrent : "";

      let initial = current;
      const stored = readStoredValue(axis);
      if (stored !== null) {
        if (isValid(stored)) {
          initial = stored;
        } else {
          // Invalid stored value (corrupted, stale from a retired
          // vocabulary, or tampered with): discard it rather than apply it
          // to <html>, and remove the bad entry so it does not keep
          // failing validation on every future load.
          clearStoredValue(axis);
        }
      }

      if (initial) {
        this._apply(attrName, initial);
      }
      for (const radio of radios) {
        if (radio.value === initial) radio.checked = true;
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
