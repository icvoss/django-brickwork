// bwCodeCopy: the copy-to-clipboard control for the code display panel
// (icvoss/django-brickwork#259, Wave 2 content primitives).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwCodeCopy", ...) with no config
//   state   none exposed; copied/failed is communicated through the DOM
//           (the status element's text, never a JS-held flag a consumer
//           would need to read)
//   event   bw:code-copy (detail { id, ok }), a bubbling CustomEvent
//           dispatched from the component root after every copy attempt,
//           successful or not (BR-BW-HTMX-004: optional convention, never
//           load-bearing).
//
// DOM contract this module enhances (_code.html renders the floor;
// BR-BW-HTMX-006). The no-JS floor is the real, unobscured <pre><code>:
// a JS-disabled reader selects and copies the text by hand exactly as they
// would from any other code block, so the control is a convenience layered
// on a floor that already works, never the only way to get the text out.
//
//   <div class="bw-code" x-data="bwCodeCopy()">        component root
//     <button data-bw-code-copy hidden>                 the control (ships
//                                                        hidden; see below)
//     <p data-bw-code-copy-status
//        data-bw-code-copy-success-template="..."       translated, see
//        data-bw-code-copy-error-template="..."         below
//        aria-live="polite">                             the announcement
//     <code data-bw-code-copy-source>...</code>          the text copied
//
// Reveals the control at init() (the bwDismissible precedent,
// dismissible.js): the button ships the hidden attribute so the no-JS
// floor never shows a control with no working behaviour behind it.
//
// i18n stays server-side (matching _bulk_actions_bar.html's
// data-bw-selection-count-template convention): the status element carries
// both the translated "Copied" and "Copy failed" strings as data
// attributes, and this module only chooses which one to write in, never
// hardcoding English text of its own.
//
// COPY MECHANISM, IN ORDER (fail explicitly: no silent swallow). 1) the
// async Clipboard API (navigator.clipboard.writeText), the modern path,
// available in secure contexts (HTTPS or localhost). 2) a real fallback for
// everything else (an insecure origin, or a browser too old for the async
// API): an off-screen, non-editable-looking <textarea> is inserted holding
// the same text, selected, copied via the synchronous
// document.execCommand("copy") and removed immediately after. Both paths
// end the same way: success writes the translated "Copied" text into the
// status element; EVERY failure (the Clipboard API rejecting,
// execCommand("copy") returning false or throwing, or neither mechanism
// existing at all) writes the translated "Copy failed" text rather than
// leaving the reader guessing why nothing happened.
//
// REPEAT ANNOUNCEMENTS. An aria-live region is announced when its contents
// CHANGE, so writing the same "Copied" string a second time is not a change
// and a reader who copies twice hears the confirmation only once. Every
// write therefore goes through _announce(), which clears the region and
// writes on the next frame, so a repeated message is still two observable
// mutations. The other shipped live regions do not need this because their
// text always differs (bwSortable announces a new position, bwTableSelection
// a new count); this control is the first whose message repeats verbatim.
//
// Motion is CSS-owned where it exists at all: this module writes text into
// the status element and toggles nothing that this component's own CSS
// keys motion on (BR-BW-TOK-009).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

// Synchronous fallback for contexts with no async Clipboard API (an
// insecure origin, or a browser predating it). Returns a boolean rather
// than throwing so the caller has one success/failure shape to branch on
// regardless of which mechanism ran.
function copyViaExecCommand(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  // Off-screen rather than hidden: a hidden or display:none element cannot
  // be selected, which would make the fallback silently do nothing.
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "-9999px";
  textarea.setAttribute("readonly", "");
  document.body.appendChild(textarea);
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  } finally {
    document.body.removeChild(textarea);
  }
  return ok;
}

let instanceCount = 0;

export default function codeCopy() {
  return {
    _id: "",
    _root: null,
    _button: null,
    _status: null,
    _source: null,

    init() {
      // Captured once and reused everywhere below (BR-BW-JS-007): Alpine
      // inline x-on expressions scope $el to the element the directive is
      // written on, never the component root.
      const root = this.$el;
      this._root = root;
      instanceCount += 1;
      this._id = root.id || `bw-code-copy-${instanceCount}`;

      this._button = root.querySelector("[data-bw-code-copy]");
      this._status = root.querySelector("[data-bw-code-copy-status]");
      this._source = root.querySelector("[data-bw-code-copy-source]");
      if (!this._button || !this._status || !this._source) return;

      // Reveal the control: it ships hidden so the no-JS floor never shows
      // a dead button (dismissible.js's reveal-at-init pattern).
      this._button.removeAttribute("hidden");
      this._button.addEventListener("click", () => this.copy());
    },

    async copy() {
      const text = this._source.textContent;
      let ok = false;
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        try {
          await navigator.clipboard.writeText(text);
          ok = true;
        } catch {
          ok = false;
        }
      }
      if (!ok && typeof document.execCommand === "function") {
        ok = copyViaExecCommand(text);
      }
      const template = ok
        ? this._status.getAttribute("data-bw-code-copy-success-template")
        : this._status.getAttribute("data-bw-code-copy-error-template");
      this._announce(template || "");
      dispatch(this._root, "bw:code-copy", { id: this._id, ok });
    },

    // Write a message into the live region so it is announced EVERY time,
    // including when the same message repeats. An aria-live region is
    // announced on mutation, so assigning the identical string a second
    // time changes nothing and a reader copying twice hears the
    // confirmation only once. Clearing first, then writing on the next
    // frame, produces two observable mutations and a reliable second
    // announcement. requestAnimationFrame rather than a bare assignment
    // because the two writes must land in separate frames to be seen as
    // separate changes; without it they coalesce back into no change.
    _announce(message) {
      const status = this._status;
      status.textContent = "";
      if (!message) return;
      if (typeof requestAnimationFrame !== "function") {
        status.textContent = message;
        return;
      }
      requestAnimationFrame(() => {
        status.textContent = message;
      });
    },
  };
}
