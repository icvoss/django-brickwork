// brickwork component registration: the single registration point for the
// interaction set (brickwork-interaction-set plan, section b).
//
// One module per Alpine.data component; the registered names are the
// versioned public JS contract (BR-BW-JS-004). The 0.8.0 tranche registers
// exactly bwDropdown, bwTabs and bwModal; the disclosure ships no JS at
// all (native <details>, see ./disclosure.js), and bwToastRegion/bwToast/
// bwCombobox arrive with the 0.9.0 tranche.

import dropdown from "./dropdown.js";
import tabs from "./tabs.js";
import modal from "./modal.js";

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
}

export default registerBrickworkComponents;
