// brickwork JS entry: compiled by Vite into the stable-named
// static/brickwork/dist/brickwork.js. Loaded by a consuming project's own
// build alongside the host-owned Alpine + htmx singletons.
//
// brickwork REGISTERS behaviour and never starts Alpine (BR-BW-JS-001/002):
// the host application owns Alpine.start() and the htmx global. This entry
// re-exports registerBrickworkComponents(Alpine) from ./js/index.js, which
// a consumer calls after Alpine.plugin(focus) and before Alpine.start().
//
// Consumer import path (owner ruling, interactions-1 build): the shipped
// static ESM file itself; there is no npm publish. From a consuming
// project's own JS:
//
//   import Alpine from "alpinejs";
//   import focus from "@alpinejs/focus";
//   import { registerBrickworkComponents }
//     from "<staticfiles>/brickwork/dist/brickwork.js";
//
//   Alpine.plugin(focus);
//   registerBrickworkComponents(Alpine);
//   Alpine.start();

import "./index.css";

export { registerBrickworkComponents, assertBrickworkRegistered, default } from "./js/index.js";
