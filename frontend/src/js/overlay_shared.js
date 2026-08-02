// Shared overlay behaviour: the focus-trap-engage race guard and the
// invoker capture/restore machinery common to bwModal and bwSlideOver
// (0.14.0, brickwork#55). NOT itself an Alpine.data component and not
// part of the public JS contract (BR-BW-JS-004/005 names bwModal and
// bwSlideOver, not this module): a private helper factored out because the
// two components would otherwise duplicate the same ~40 lines of trap-guard
// and focus-return logic verbatim (DRY, three-plus near-identical blocks).
//
// Both components still author their own init()/open()/close() bodies (DOM
// hooks, event names and dismissal reasons differ), but delegate the shared
// parts to the helpers below.

export function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Minimum gap between the open and close state flips. The wrapped x-trap
// engages its focus trap ~15ms after the open flip (upstream @alpinejs/
// focus schedules trap.activate() on a timeout, with inert applied after
// activation); a close flip landing inside that window tears down a trap
// that has not engaged yet and leaves an ORPHANED ACTIVE trap stealing
// focus page-wide. Shared by bwModal and bwSlideOver, both of which wrap
// the same x-trap.inert.noscroll directive.
export const TRAP_ENGAGE_GUARD_MS = 50;

// Captures the current active element as the invoker, provided it sits
// outside the overlay root (so re-entrant opens do not capture a control
// inside the overlay itself). Call at the start of open(), before focus
// moves into the dialog.
export function captureInvoker(root, previousInvoker) {
  const active = document.activeElement;
  return active && active !== document.body && !root.contains(active) ? active : previousInvoker;
}

// Runs a close, deferring it past TRAP_ENGAGE_GUARD_MS when the overlay
// only just opened (the race above). `state` carries { openedAt,
// pendingClose } so the caller's own reactive fields stay the source of
// truth; `runClose` performs the actual state flip once the guard clears.
export function guardedClose(state, reason, runClose) {
  const elapsed = Date.now() - state.openedAt;
  if (elapsed < TRAP_ENGAGE_GUARD_MS) {
    state.pendingClose = setTimeout(() => {
      state.pendingClose = null;
      runClose(reason);
    }, TRAP_ENGAGE_GUARD_MS - elapsed);
    return true; // deferred: caller must not run the close synchronously
  }
  return false; // not deferred: caller runs the close synchronously
}

// Restores focus to the captured invoker on the next tick, if it is still
// connected to the document. Call from the tail of _close().
export function restoreInvokerFocus(invoker, nextTick) {
  nextTick(() => {
    if (invoker && invoker.isConnected && typeof invoker.focus === "function") {
      invoker.focus();
    }
  });
}
