// bwToastRegion + bwToast: the toast stack behaviour (04-interfaces
// section 4b, interactions-2 tranche).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwToastRegion", ...) with no config: the stack manager.
//     No public props, state or methods; it enforces the at-most-three
//     visible rule and drives the shipped "+N more" collapse control.
//   Alpine.data("bwToast", ...) with config
//     { duration: "short"|"normal"|"long"|"persistent" }
//     state   visible, paused
//     method  dismiss(reason)
//     events  bw:toast:show (detail { id, intent }) on arrival and
//             bw:toast:dismiss (detail { id, reason: "timeout"|"dismiss" })
//             just before removal, bubbling CustomEvents dispatched from
//             the toast root (BR-BW-HTMX-004: optional conventions, never
//             load-bearing).
//
// There is NO client-side creation API of any kind (BR-BW-HTMX-007):
// toasts arrive server-rendered, either as hx-swap-oob
// ="afterbegin:#bw-toast-region" wrappers or in a full-page render. The
// region root id #bw-toast-region is stable (BR-BW-HTMX-005). Toasts
// never steal focus on arrival.
//
// DOM contract these components enhance (the template lane renders it):
//   <div id="bw-toast-region" data-bw-toast-region aria-live="polite"
//        x-data="bwToastRegion()">                    stack root
//     <div class="bw-toast bw-toast--<intent>" id="..." data-bw-toast
//          x-data='bwToast({ duration: "normal" })'>  newest FIRST
//       ... .bw-toast__icon / __message / __action / __close
//     <button class="bw-toast-region__more" hidden>   collapse control
//
// Region behaviour: afterbegin insertion keeps the newest toast first in
// DOM order, so the first three [data-bw-toast] toasts stay visible and
// any older ones get the hidden attribute. An hx-swap-oob delivery inserts
// its WRAPPER element into the region (htmx swaps the oob element itself),
// so toasts are matched as descendants, the wrappers are layout-transparent
// in CSS (display: contents), and a wrapper whose toast has gone is pruned.
// The shipped "+N more" button is filled with the overflow count and
// revealed; activating it expands the stack (every toast visible) until
// the count falls back to three or fewer. A childList (subtree, to see
// removals inside wrappers) MutationObserver keeps the stack in step with
// both htmx arrivals and dismissal removals. Hidden toasts keep their timers
// running: a toast that would have timed out on screen times out in the
// overflow too, so the "+N" count drains naturally.
//
// Toast behaviour: on init the root gains data-bw-visible (CSS keys enter
// and exit on it) and bw:toast:show is emitted (intent read from the
// bw-toast--<intent> class). The auto-dismiss timer reads
// --bw-duration-toast-<duration> via getComputedStyle (persistent = no
// timer) and pauses while hovered or focus is within (WCAG 2.2.1),
// resuming with the REMAINING time, never restarting from zero.
// dismiss(reason) removes data-bw-visible, waits for the CSS exit
// transition (transitionend with a timeout fallback, so reduced motion's
// zeroed durations remove instantly), returns focus to the previous
// focusable element in document order when focus was inside
// (BR-BW-JS-006), emits bw:toast:dismiss and removes the element.
//
// Timing note: the auto-dismiss durations and the exit-transition wait are
// wall-clock behaviour, not motion sequencing; the timing tokens stay
// CSS-owned (BR-BW-TOK-009) and are only ever READ here, per the 4b
// amendment that defines them.

// The collapse threshold (04-interfaces 4b: at most 3 toasts visible).
const MAX_VISIBLE_TOASTS = 3;

// Safety margin on the transitionend timeout fallback: covers a
// transitionend swallowed by an interrupted paint or a hidden (never
// painted) toast whose transition can never run. Not motion timing.
const EXIT_FALLBACK_SLACK_MS = 100;

const TOAST_INTENTS = ["success", "warning", "danger", "info"];
const TOAST_DURATIONS = ["short", "normal", "long", "persistent"];
const TOAST_DURATION_FALLBACK_MS = { short: 4000, normal: 6000, long: 10000 };

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Parse a CSS <time> value ("4000ms", "4s", bare number = ms) into ms.
function toMs(value) {
  const trimmed = String(value).trim();
  if (trimmed === "") return NaN;
  const number = parseFloat(trimmed);
  if (!Number.isFinite(number)) return NaN;
  if (trimmed.endsWith("ms")) return number;
  return trimmed.endsWith("s") ? number * 1000 : number;
}

// Read a millisecond token off an element's computed style, with a
// fallback for hosts whose compiled stylesheet predates the token.
function readMsToken(el, name, fallback) {
  const ms = toMs(getComputedStyle(el).getPropertyValue(name));
  return Number.isFinite(ms) ? ms : fallback;
}

// Longest declared transition (duration plus delay) on the element, in
// ms. Max-of-each slightly overestimates mixed lists; it is only ever a
// fallback budget, never a sequencing input.
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
// Reduced motion zeroes the budget (the global reduced-motion floor lives
// in CSS), so removal is instant; otherwise transitionend races a timeout
// fallback so removal is guaranteed even when no event ever fires.
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

// Unique fallback ids so several toasts on one page never collide when a
// template omits the (contractually required) unique id.
let toastCount = 0;

export function toastRegion() {
  return {
    _root: null,
    _more: null,
    _expanded: false,
    _observer: null,

    init() {
      // Captured once (BR-BW-JS-007): Alpine inline x-on expressions scope
      // $el to the element the directive is written on, never the root.
      const root = this.$el;
      this._root = root;
      this._more = root.querySelector(".bw-toast-region__more");
      if (this._more) {
        this._more.addEventListener("click", () => {
          this._expanded = true;
          const firstHidden = this._toasts()[MAX_VISIBLE_TOASTS] || null;
          this._enforce();
          // Expanding hides the activated control, which would drop focus
          // to <body> (BR-BW-JS-006); hand it to the first newly revealed
          // toast's close button (its focusin also pauses that timer).
          const close = firstHidden
            ? firstHidden.querySelector(".bw-toast__close")
            : null;
          if (close) close.focus();
        });
      }
      // childList only: arrivals (htmx oob swaps, full-page renders) and
      // dismissal removals; subtree because a dismissed toast is removed
      // from inside its oob wrapper, not from the region's own child list.
      // Attribute toggles below never re-fire it.
      this._observer = new MutationObserver(() => this._enforce());
      this._observer.observe(root, { childList: true, subtree: true });
      this._enforce();
    },

    destroy() {
      if (this._observer) this._observer.disconnect();
    },

    _toasts() {
      // Descendants, not children: an oob delivery arrives wrapped, a
      // full-page render puts toasts directly in the region; document
      // order keeps the newest first either way (wrappers prepend).
      return Array.from(this._root.querySelectorAll("[data-bw-toast]"));
    },

    _enforce() {
      // Prune emptied oob wrappers (a dismissed toast removes only itself)
      // so a long-lived page never accumulates inert delivery divs.
      for (const child of Array.from(this._root.children)) {
        if (child === this._more || child.hasAttribute("data-bw-toast")) continue;
        if (!child.querySelector("[data-bw-toast]")) child.remove();
      }
      const toasts = this._toasts();
      // Dropping back to the threshold re-arms the collapse for the next
      // overflow; an expanded stack never re-collapses under the user.
      if (toasts.length <= MAX_VISIBLE_TOASTS) this._expanded = false;
      toasts.forEach((toast, index) => {
        const shouldHide = !this._expanded && index >= MAX_VISIBLE_TOASTS;
        // Guarded write: the observer watches this same subtree (childList,
        // subtree), so an unconditional assignment re-fires the callback on
        // every settled call and loops forever. Only mutate on an actual
        // state change.
        if (toast.hidden !== shouldHide) toast.hidden = shouldHide;
      });
      if (!this._more) return;
      const overflow = this._expanded
        ? 0
        : Math.max(0, toasts.length - MAX_VISIBLE_TOASTS);
      if (overflow > 0) {
        // The template ships the translated "+N more" label with a count
        // slot; only the number is filled here so i18n stays server-side.
        const slot = this._more.querySelector("[data-bw-toast-more-count]");
        const text = String(overflow);
        if (slot) {
          // Guarded write: a childList/subtree observer is watching this
          // subtree, so rewriting textContent to the SAME value on every
          // settled call re-fires the callback and never converges (the
          // infinite-loop defect on the 4th toast).
          if (slot.textContent !== text) slot.textContent = text;
        } else if (this._more.textContent !== `+${overflow} more`) {
          this._more.textContent = `+${overflow} more`; // untranslated fallback
        }
        if (this._more.hidden !== false) this._more.hidden = false;
      } else if (this._more.hidden !== true) {
        this._more.hidden = true;
      }
    },
  };
}

export function toast(config = {}) {
  return {
    visible: false,
    paused: false,

    _root: null,
    _duration: "normal",
    _remaining: 0,
    _deadline: 0,
    _timer: null,
    _hovered: false,
    _focused: false,
    _dismissed: false,

    init() {
      // Captured once (BR-BW-JS-007); see the region note above.
      const root = this.$el;
      this._root = root;
      toastCount += 1;
      if (!root.id) root.id = `bw-toast-${toastCount}`;

      this._duration = TOAST_DURATIONS.includes(config.duration)
        ? config.duration
        : "normal";
      if (this._duration !== "persistent") {
        this._remaining = readMsToken(
          root,
          `--bw-duration-toast-${this._duration}`,
          TOAST_DURATION_FALLBACK_MS[this._duration],
        );
      }

      for (const close of root.querySelectorAll(".bw-toast__close")) {
        close.addEventListener("click", () => this.dismiss("dismiss"));
      }

      // Timer pause on hover AND focus-within (WCAG 2.2.1); both flags are
      // tracked so releasing one never resumes past the other.
      root.addEventListener("mouseenter", () => {
        this._hovered = true;
        this._updatePaused();
      });
      root.addEventListener("mouseleave", () => {
        this._hovered = false;
        this._updatePaused();
      });
      root.addEventListener("focusin", () => {
        this._focused = true;
        this._updatePaused();
      });
      root.addEventListener("focusout", (event) => {
        if (!root.contains(event.relatedTarget)) {
          this._focused = false;
          this._updatePaused();
        }
      });

      dispatch(root, "bw:toast:show", { id: root.id, intent: this._intent() });

      // Double rAF: the first frame paints the just-inserted base state,
      // the second flips data-bw-visible so the CSS enter transition
      // actually runs (a same-frame set would jump straight to visible).
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (this._dismissed) return;
          this.visible = true;
          root.setAttribute("data-bw-visible", "");
          if (this._duration !== "persistent" && !this.paused) {
            this._startTimer();
          }
        });
      });
    },

    destroy() {
      if (this._timer) clearTimeout(this._timer);
    },

    dismiss(reason = "dismiss") {
      if (this._dismissed) return;
      this._dismissed = true;
      this.visible = false;
      if (this._timer) clearTimeout(this._timer);
      const root = this._root;
      root.removeAttribute("data-bw-visible");
      afterExit(root, () => {
        // Focus return and the event both happen BEFORE removal: the
        // focus helper needs el in document order, and the event must
        // still bubble through the region (BR-BW-HTMX-004).
        restoreFocusOutside(root);
        dispatch(root, "bw:toast:dismiss", { id: root.id, reason });
        root.remove();
      });
    },

    _intent() {
      for (const intent of TOAST_INTENTS) {
        if (this._root.classList.contains(`bw-toast--${intent}`)) return intent;
      }
      return "info";
    },

    _updatePaused() {
      const paused = this._hovered || this._focused;
      if (paused === this.paused) return;
      this.paused = paused;
      if (this._duration === "persistent" || this._dismissed || !this.visible) {
        return;
      }
      if (paused) this._pauseTimer();
      else this._startTimer();
    },

    _startTimer() {
      this._deadline = Date.now() + this._remaining;
      this._timer = setTimeout(() => this.dismiss("timeout"), this._remaining);
    },

    _pauseTimer() {
      if (this._timer) clearTimeout(this._timer);
      this._timer = null;
      // Resume continues from the remaining time, never from zero.
      this._remaining = Math.max(0, this._deadline - Date.now());
    },
  };
}
