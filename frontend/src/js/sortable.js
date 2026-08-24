// bwSortable: drag/keyboard list reordering, then server persistence
// (icvoss/django-brickwork#214).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwSortable", ...) with config
//     { url: string, itemSelector: string (default "[data-bw-sort-id]") }
//   state   none exposed; the DOM order IS the state (mirrors
//           bwTableSelection's "no separate JS store" doctrine, so this
//           module can never desync from what gets persisted)
//   event   bw:sortable:reorder (detail { ids: [...] }), a bubbling
//           CustomEvent dispatched from the component root once a move
//           (drag or keyboard) settles and the persist request is sent
//           (BR-BW-HTMX-004: optional convention, never load-bearing).
//
// THE NO-JS FLOOR THIS MODULE ENHANCES, NEVER REPLACES (BR-BW-HTMX-001).
// One consumer has already shipped a reorder endpoint with no floor at all
// (icvoss/django-brickwork#214's evidence table), so this is asserted
// deliberately: bwSortable assumes every item already carries two real,
// independently working controls before any JS runs, typically move-up /
// move-down submit buttons inside the item's own small <form
// method="post">, each posting to the same persistence endpoint this module
// calls. bwSortable adds NOTHING to the floor markup itself (no injected
// button, no injected handle): it only listens for drag/keyboard events on
// the existing items and, on a JS-disabled page, every one of its listeners
// simply never attaches.
//
// DOM contract (consumer-owned, no brickwork template ships this: unlike
// _data_table.html this is a bare list the caller already renders, per the
// issue's own suggested shape). data-bw-sort-status is looked up from the
// ROOT'S PARENT, deliberately, never inside the root itself: the root is
// ordinarily a <ul>, and a <div> is not valid <ul> content, so requiring it
// as a child would make the documented markup invalid HTML by construction.
// A sibling of the root is the only placement that is both valid and still
// inside the same wrapping container a consumer already has:
//
//   <div>                                                   any wrapper
//     <ul x-data="bwSortable({ url: '{% url "..." %}' })">  component root
//       <li data-bw-sort-id="{{ row.pk }}">                 one per item
//         ...move-up / move-down buttons (the no-JS floor)...
//       </li>
//     </ul>
//     <div data-bw-sort-status aria-live="polite"
//          class="bw-visually-hidden">                      optional, see below
//
// WIRE CONTRACT (settled by precedent, icvoss/django-brickwork#214): a
// single POST of the full ordered id list, one call, matching what all
// three known consumers (brickworkui, Magmify, icv-cms) already implement
// server-side. Sent via
// htmx.ajax (never a bare fetch): htmx is already the documented host-owned
// peer this package assumes for any component that talks to the network
// (bwCombobox's server-filter leg is the existing precedent), so this module
// stays inert, by the same BR-BW-JS-001 guard, on a page that never wires
// htmx in. The response REPLACES the component root (outerHTML), so server
// truth wins over the client's own optimistic DOM guess (two editors
// reordering concurrently resolve to whatever the server actually persisted,
// exactly as the reference implementation this behaviour supersedes did).
// No explicit re-init call is needed after the swap: htmx's own swap
// pipeline processes any hx-* directives in the returned partial, and
// Alpine v3's global MutationObserver independently detects the new
// x-data="bwSortable(...)" root and boots it, so the swapped-in list is a
// fresh, fully working bwSortable instance with no extra wiring.
//
// KEYBOARD PATH (WCAG 2.2 AA: native HTML5 drag-and-drop is mouse-only,
// so a keyboard-only user needs an equivalent). Roving tabindex over the
// items themselves (the bwTabs precedent): Tab enters the list on exactly
// one item; Alt+ArrowUp / Alt+ArrowDown moves the FOCUSED item one position
// and keeps focus on it (plain ArrowUp/ArrowDown is deliberately left alone,
// since it collides with a screen reader's own line navigation and with
// browse-mode virtual cursor movement over a list of readable content);
// Alt+Home / Alt+End move it to the top/bottom. Every move updates an
// aria-live region so the new position is announced without moving focus
// away from the item (data-bw-sort-status, i18n'd the bwTableSelection way:
// a server-rendered `data-bw-sort-status-template` string with a literal
// "{position}"/"{count}" placeholder pair, since this module hardcodes no
// English copy). A keyboard move persists exactly like a drop: one POST once
// the move settles.
//
// DRAG PATH: native HTML5 DnD (no dependency), the same insertion-preview
// technique as the proven reference implementation
// (sites/brickworkui.com/frontend/js/main.js Alpine.data('blockReorder')):
// dragover computes above/below the pointer's target and moves the dragged
// node in the live DOM, so the visual order at drop time IS the order sent.
//
// Presentational hooks (bw-sortable-* CSS, shipped alongside this module):
// [data-bw-dragging] on the item currently being dragged (elevation +
// reduced opacity), [data-bw-drag-over] on the item the pointer is over.
// Shipping the CSS here rather than leaving it to each consumer is a
// deliberate call (icvoss/django-brickwork#214): the affordance is generic
// enough not to be product-specific, and leaving it unstyled reproduces the
// issue's own defect one layer down (three consumers re-authoring the same
// grab cursor / insertion line and drifting). Motion is CSS-owned as usual
// (BR-BW-TOK-009): this module only toggles the two state attributes above.

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

export default function sortable(config = {}) {
  return {
    url: config.url || "",
    itemSelector: config.itemSelector || "[data-bw-sort-id]",

    _root: null,
    _status: null,
    _statusTemplate: "{position} of {count}",
    _draggingId: null,

    init() {
      const root = this.$el;
      this._root = root;
      // A sibling of the root, never a descendant: see the header comment's
      // DOM contract (a <div> cannot validly live inside a <ul>).
      this._status = root.parentElement?.querySelector("[data-bw-sort-status]") || null;
      this._statusTemplate = this._status?.dataset.bwSortStatusTemplate || this._statusTemplate;

      const items = this._items();
      if (!items.length) return; // floor markup absent: stay inert

      // Roving tabindex (bwTabs precedent): only the first item is a tab
      // stop at rest; the rest join the order as the user arrives.
      this._setRoving(items[0]);

      root.addEventListener("dragstart", (event) => this._onDragStart(event));
      root.addEventListener("dragover", (event) => this._onDragOver(event));
      root.addEventListener("drop", (event) => this._onDrop(event));
      root.addEventListener("keydown", (event) => this._onKeydown(event));
      root.addEventListener("focusin", (event) => {
        const item = event.target.closest(this.itemSelector);
        if (item) this._setRoving(item);
      });
    },

    _items() {
      return Array.from(this._root.querySelectorAll(this.itemSelector));
    },

    _setRoving(focusItem) {
      for (const item of this._items()) {
        item.setAttribute("tabindex", item === focusItem ? "0" : "-1");
      }
    },

    // --- drag path -----------------------------------------------------

    _onDragStart(event) {
      const item = event.target.closest(this.itemSelector);
      if (!item) return;
      this._draggingId = item.dataset.bwSortId;
      item.setAttribute("data-bw-dragging", "");
      event.dataTransfer.effectAllowed = "move";
    },

    _onDragOver(event) {
      const target = event.target.closest(this.itemSelector);
      if (!target || !this._draggingId || target.dataset.bwSortId === this._draggingId) return;
      event.preventDefault(); // required for drop to fire at all
      const dragging = this._root.querySelector(`[data-bw-sort-id="${this._draggingId}"]`);
      if (!dragging) return;
      for (const item of this._items()) item.removeAttribute("data-bw-drag-over");
      target.setAttribute("data-bw-drag-over", "");
      const rect = target.getBoundingClientRect();
      const before = event.clientY - rect.top < rect.height / 2;
      target.parentElement.insertBefore(dragging, before ? target : target.nextSibling);
    },

    _onDrop(event) {
      if (!this._draggingId) return;
      event.preventDefault();
      const dragged = this._root.querySelector(`[data-bw-sort-id="${this._draggingId}"]`);
      dragged?.removeAttribute("data-bw-dragging");
      for (const item of this._items()) item.removeAttribute("data-bw-drag-over");
      this._draggingId = null;
      this._persist();
    },

    // --- keyboard path ---------------------------------------------------

    _onKeydown(event) {
      if (!event.altKey) return;
      const item = event.target.closest(this.itemSelector);
      if (!item) return;
      switch (event.key) {
        case "ArrowUp":
          event.preventDefault();
          this._move(item, item.previousElementSibling);
          break;
        case "ArrowDown":
          event.preventDefault();
          this._move(item, item.nextElementSibling);
          break;
        case "Home":
          event.preventDefault();
          this._move(item, this._items()[0], /* toStart */ true);
          break;
        case "End":
          event.preventDefault();
          this._move(item, this._items().at(-1), /* toEnd */ true);
          break;
        default:
          break;
      }
    },

    // Moves `item` next to `reference` (before it moving up, after it moving
    // down); toStart/toEnd reposition at the list boundary for Home/End,
    // where `reference` IS the current boundary item itself. A no-op at
    // either end of the list (no previous/next sibling, or already there)
    // announces nothing and persists nothing, matching bwTabs' bounded
    // (non-wrapping) roving-focus precedent for this modifier map.
    _move(item, reference, atBoundary = false) {
      if (!reference || reference === item) return;
      if (atBoundary) {
        if (reference === this._items()[0]) reference.parentElement.insertBefore(item, reference);
        else reference.parentElement.insertBefore(item, reference.nextSibling);
      } else if (reference === item.previousElementSibling) {
        reference.parentElement.insertBefore(item, reference);
      } else {
        reference.parentElement.insertBefore(item, reference.nextSibling);
      }
      item.focus();
      this._setRoving(item);
      this._announce(item);
      this._persist();
    },

    _announce(item) {
      if (!this._status) return;
      const items = this._items();
      const position = items.indexOf(item) + 1;
      this._status.textContent = this._statusTemplate
        .replace("{position}", String(position))
        .replace("{count}", String(items.length));
    },

    // --- persistence -------------------------------------------------------

    _persist() {
      const ids = this._items().map((item) => item.dataset.bwSortId);
      dispatch(this._root, "bw:sortable:reorder", { ids });
      if (!this.url || !window.htmx) return;
      window.htmx.ajax("POST", this.url, {
        source: this._root,
        target: this._root,
        swap: "outerHTML",
        values: { bw_sort_ids: ids },
      });
    },
  };
}
