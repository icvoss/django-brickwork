// brickwork component registration: the single registration point for the
// interaction set (brickwork-interaction-set plan, section b).
//
// One module per Alpine.data component; the registered names are the
// versioned public JS contract (BR-BW-JS-004). The 0.8.0 tranche shipped
// bwDropdown, bwTabs and bwModal; the interactions-2 tranche adds
// bwToastRegion, bwToast, bwCombobox and bwDismissible; the 0.12.0 tranche
// adds bwTooltip; the 0.13.0 tranche adds bwTagInput, bwDropzone and
// bwSidebarCollapse (brickwork#57/#58); the 0.14.0 tranche adds
// bwSlideOver (brickwork#55); the 0.15.0 tranche adds bwTableSelection
// (brickwork#54). The disclosure ships no JS at all (native <details>, see
// ./disclosure.js); the toggle switch likewise ships no JS (native checkbox
// + role=switch, see forms/_field.html / components/_toggle.html); the
// stepper (brickwork#59) ships no JS either (purely structural,
// server-driven step navigation); the whole-form renderer (brickwork#53)
// ships no JS either (structure only, server-driven layout).

import dropdown from "./dropdown.js";
import tabs from "./tabs.js";
import modal from "./modal.js";
import { toastRegion, toast } from "./toast.js";
import combobox from "./combobox.js";
import dismissible from "./dismissible.js";
import tooltip from "./tooltip.js";
import tagInput from "./tag_input.js";
import dropzone from "./dropzone.js";
import sidebarCollapse from "./sidebar_collapse.js";
import slideOver from "./slide_over.js";
import tableSelection from "./table_selection.js";

// The registered-marker attribute (brickwork#87): registerBrickworkComponents
// stamps it on <html> at call time, so the shell's dev-only inline detector
// (shell/base.html) and assertBrickworkRegistered() below can tell "brickwork
// markup present but registration never ran" apart from a correct wiring.
const REGISTERED_ATTR = "data-bw-js-registered";

/**
 * Register brickwork's Alpine.data() components on a host-owned Alpine
 * instance. Never calls Alpine.start(); the host owns initialisation
 * (BR-BW-JS-002), and Alpine, @alpinejs/focus and htmx remain host-owned
 * peers this package never bundles (BR-BW-JS-001). Call after
 * Alpine.plugin(focus) and before Alpine.start().
 *
 * @param {object} Alpine - the host application's Alpine singleton.
 */
export function registerBrickworkComponents(Alpine) {
  if (!Alpine || typeof Alpine.data !== "function") {
    throw new Error(
      "registerBrickworkComponents(Alpine): pass the host's Alpine instance " +
        "(with Alpine.plugin(focus) already applied).",
    );
  }
  // Stamp the marker before the Alpine.data calls: guarded so a non-DOM
  // environment (a bundler's SSR pass, a JS test runner without a document)
  // can still import and call this module.
  if (typeof document !== "undefined" && document.documentElement) {
    document.documentElement.setAttribute(REGISTERED_ATTR, "true");
  }
  Alpine.data("bwDropdown", dropdown);
  Alpine.data("bwTabs", tabs);
  Alpine.data("bwModal", modal);
  Alpine.data("bwToastRegion", toastRegion);
  Alpine.data("bwToast", toast);
  Alpine.data("bwCombobox", combobox);
  Alpine.data("bwDismissible", dismissible);
  Alpine.data("bwTooltip", tooltip);
  Alpine.data("bwTagInput", tagInput);
  Alpine.data("bwDropzone", dropzone);
  Alpine.data("bwSidebarCollapse", sidebarCollapse);
  Alpine.data("bwSlideOver", slideOver);
  Alpine.data("bwTableSelection", tableSelection);
}

/**
 * Throw unless registerBrickworkComponents() has run in this document
 * (brickwork#87). An opt-in hard check for consumers who want their bundle to
 * fail fast on the silent-dead-UI trap (interactive bw markup rendering inert
 * because registration was forgotten before Alpine.start()), rather than rely
 * on the shell's DEBUG-only console warning. Call it after your registration
 * line, or from a smoke test that boots the bundle.
 */
export function assertBrickworkRegistered() {
  const registered =
    typeof document !== "undefined" &&
    document.documentElement &&
    document.documentElement.hasAttribute(REGISTERED_ATTR);
  if (!registered) {
    throw new Error(
      "brickwork: registerBrickworkComponents(Alpine) has not been called in " +
        "this document. Interactive bw components render as dead markup " +
        "without it; call it before starting Alpine. See INTEGRATION.md.",
    );
  }
}

export default registerBrickworkComponents;
