// bwDismissible: the dismiss behaviour for bw_alert and bw_badge
// (04-interfaces section 4b, dismissible amendment adopted from the
// CMP-010/012 landing; interactions-2 tranche).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwDismissible", ...) with no config
//   state   visible
//   method  dismiss()
//   event   bw:dismiss (detail { id }), a bubbling CustomEvent dispatched
//           from the component root just before removal (BR-BW-HTMX-004:
//           optional convention, never load-bearing).
//
// DOM contract this module enhances (the template lane renders it): the
// alert or badge root carries x-data="bwDismissible()" and an icon-only
// close button [data-bw-dismiss] (translated enforced aria-label) shipped
// WITH the hidden attribute, so the no-JS floor shows no dead control;
// init reveals it. Dismissal removes the element from the DOM; there is
// no persistence and no re-show API.
//
// Motion is CSS-owned (BR-BW-TOK-009): dismiss() only sets
// [data-bw-dismissing] on the root; the CSS lane keys the exit on it at
// --bw-duration-fast / --bw-ease-in, and the global reduced-motion floor
// zeroes it. This module waits for that exit (transitionend with a
// timeout fallback computed from the element's own transition style, so
// reduced motion removes instantly) before removing the element, and
// returns focus to the previous focusable element in document order when
// focus was inside (BR-BW-JS-006, the toast contract's rule).

// Safety margin on the transitionend timeout fallback: covers a
// transitionend swallowed by an interrupted paint or an unpainted
// element whose transition can never run. Not motion timing.
const EXIT_FALLBACK_SLACK_MS = 100;

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Parse a CSS <time> value ("150ms", "0.15s", bare number = ms) into ms.
function toMs(value) {
  const trimmed = String(value).trim();
  if (trimmed === "") return NaN;
  const number = parseFloat(trimmed);
  if (!Number.isFinite(number)) return NaN;
  if (trimmed.endsWith("ms")) return number;
  return trimmed.endsWith("s") ? number * 1000 : number;
}

// Longest declared transition (duration plus delay) on the element, in
// ms; only ever a fallback budget, never a sequencing input.
function exitBudgetMs(el) {
  const style = getComputedStyle(el);
  const max = (list) =>
    list
      .split(",")
      .map(toMs)
      .reduce((best, ms) => (Number.isFinite(ms) && ms > best ? ms : best), 0);
  return max(style.transitionDuration) + max(style.transitionDelay);
}

// Wait for the element's exit transition, then run done() exactly once.
function afterExit(el, done) {
  const budget = exitBudgetMs(el);
  if (budget <= 0) {
    done();
    return;
  }
  let settled = false;
  let timer = 0;
  const finish = () => {
    if (settled) return;
    settled = true;
    el.removeEventListener("transitionend", onEnd);
    clearTimeout(timer);
    done();
  };
  const onEnd = (event) => {
    if (event.target === el) finish();
  };
  el.addEventListener("transitionend", onEnd);
  timer = setTimeout(finish, budget + EXIT_FALLBACK_SLACK_MS);
}

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  'input:not([disabled]):not([type="hidden"])',
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

// If focus is inside el, return it to the previous focusable element in
// document order (the nearest following one as a fallback), so removing
// el never drops focus to <body> (BR-BW-JS-006). Runs BEFORE removal so
// document order still includes el.
function restoreFocusOutside(el) {
  if (!el.contains(document.activeElement)) return;
  let previous = null;
  let next = null;
  for (const candidate of document.querySelectorAll(FOCUSABLE_SELECTOR)) {
    if (el.contains(candidate)) continue;
    if (!candidate.getClientRects().length) continue; // display:none never takes focus
    if (el.compareDocumentPosition(candidate) & Node.DOCUMENT_POSITION_PRECEDING) {
      previous = candidate; // the LAST preceding candidate wins
    } else {
      next = candidate; // document order: first non-preceding is nearest following
      break;
    }
  }
  const target = previous || next;
  if (target) target.focus();
}

// Unique fallback ids so several dismissibles on one page never collide
// in the bw:dismiss detail (alerts and badges often omit an id).
let instanceCount = 0;

export default function dismissible() {
  return {
    visible: true,

    _id: "",
    _root: null,
    _dismissing: false,

    init() {
      // Captured once and reused everywhere below (BR-BW-JS-007): Alpine
      // inline x-on expressions scope $el to the element the directive is
      // written on, never the component root.
      const root = this.$el;
      this._root = root;
      instanceCount += 1;
      this._id = root.id || `bw-dismissible-${instanceCount}`;

      // Reveal the close control: it ships hidden so the no-JS floor
      // never shows a dead button (04-interfaces dismissible amendment).
      for (const control of root.querySelectorAll("[data-bw-dismiss]")) {
        control.removeAttribute("hidden");
        control.addEventListener("click", () => this.dismiss());
      }
    },

    dismiss() {
      if (this._dismissing) return;
      this._dismissing = true;
      this.visible = false;
      const root = this._root;
      root.setAttribute("data-bw-dismissing", "");
      afterExit(root, () => {
        // Focus return and the event both happen BEFORE removal: the
        // focus helper needs the element in document order, and the
        // event must still bubble to its ancestors.
        restoreFocusOutside(root);
        dispatch(root, "bw:dismiss", { id: this._id });
        root.remove();
      });
    },
  };
}
