// Disclosure: deliberately JS-free (04-interfaces section 4b, 0.8.0).
//
// _disclosure.html is a native <details>/<summary> element, so the no-JS
// floor holds by construction (BR-BW-HTMX-001/006):
//
// - single-open accordion grouping uses the native `name` attribute
//   (exclusive <details> groups, Baseline 2024; CBH-016);
// - open/close animation is pure CSS (grid-template-rows 0fr -> 1fr at
//   --bw-duration-normal / --bw-ease-standard, MOT-008, under the global
//   reduced-motion floor);
// - the native `toggle` event already fires for any consumer wanting a
//   hook, so brickwork registers no Alpine.data component and re-emits no
//   bw: event for this component.
//
// This file is reserved for future enhancement only (e.g. coordination
// across <details> groups beyond what `name` provides). It is not
// imported by js/index.js and ships no behaviour; registering anything
// here would be a MINOR semver event (BR-BW-JS-004).

export {};
