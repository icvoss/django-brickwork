// brickwork component registration: the single registration point for the
// interaction set (brickwork-interaction-set plan, section b).
//
// One module per Alpine.data component; the registered names are the
// versioned public JS contract (BR-BW-JS-004). The 0.8.0 tranche shipped
// bwDropdown, bwTabs and bwModal; the interactions-2 tranche adds
// bwToastRegion, bwToast, bwCombobox and bwDismissible; the 0.12.0 tranche
// adds bwTooltip; the 0.13.0 tranche adds bwTagInput, bwDropzone and
// bwSidebarCollapse (brickwork#57/#58); the 0.14.0 tranche adds
// bwSlideOver (brickwork#55). The disclosure ships no JS at all (native
// <details>, see ./disclosure.js); the toggle switch likewise ships no JS
// (native checkbox + role=switch, see forms/_field.html /
// components/_toggle.html); the stepper (brickwork#59) ships no JS either
// (purely structural, server-driven step navigation).

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
}

export default registerBrickworkComponents;
