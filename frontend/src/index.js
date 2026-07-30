// brickwork JS entry: compiled by Vite into the stable-named
// static/brickwork/dist/brickwork.js. Loaded by a consuming project's own Vite
// build alongside the host-owned Alpine + htmx singletons.
//
// brickwork REGISTERS behaviour and never starts Alpine (BR-BW-JS-001/002): the
// host application owns Alpine.start() and the htmx global. This entry exports
// registerBrickworkComponents(Alpine), which a consumer calls after
// Alpine.plugin(ui/focus) and before Alpine.start().
//
// Phase 0: the interaction components (modal, toast, dropdown, combobox) that
// this hook registers land with Task 6; for now it is an empty, safe registrar
// so the no-JS floor holds and a JS-enabled consumer can wire the call site
// once and get components as they ship.

import "./index.css";

/**
 * Register brickwork's Alpine.data() components on a host-owned Alpine instance.
 * Never calls Alpine.start(); the host owns initialisation (BR-BW-JS-002).
 *
 * @param {object} Alpine - the host application's Alpine singleton.
 */
export function registerBrickworkComponents(Alpine) {
  if (!Alpine || typeof Alpine.data !== "function") {
    throw new Error(
      "registerBrickworkComponents(Alpine): pass the host's Alpine instance " +
        "(with Alpine.plugin(ui) and Alpine.plugin(focus) already applied).",
    );
  }
  // Interaction components register here as they land (Task 6, single-consumer).
  // Each is Alpine.data("bwModal", () => ({ ... })) etc. Names are the versioned
  // public JS contract (BR-BW-JS-004).
}

export default registerBrickworkComponents;
