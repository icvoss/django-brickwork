// bwCommand: command palette (cmdk) behaviour (icvoss/django-brickwork#156).
//
// Progressive enhancement over {% bw_search %}. The palette is display:none
// until [data-bw-open] is set, so with JavaScript off the plain search GET
// form remains the whole experience. This module must never be the only
// way to search.
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwCommand", ...) with config
//     { id, action: string, name: string (query field, default "q") }
//   state   isOpen (boolean; see the shape note below), query, activeIndex
//   methods open(), close(reason), filter(), runActive()
//   events  bw:command:open (detail { id }) and bw:command:close
//           (detail { id, reason: "escape"|"backdrop"|"shortcut"|
//           "select"|"programmatic" }), bubbling CustomEvents from the
//           component root (BR-BW-HTMX-004: optional conventions).
//
// Shape note: matching bwModal/bwCombobox, the boolean is isOpen because
// a method named open() cannot share the name.
//
// DOM contract this module enhances (the template lane renders it):
//   <div class="bw-cmdk" x-data="bwCommand({...})">     component root
//     <div class="bw-cmdk__scrim" data-bw-command-scrim>
//     <div class="bw-cmdk__panel" x-trap.inert.noscroll="isOpen">
//       <input class="bw-cmdk__input" data-bw-autofocus>
//       <ul class="bw-cmdk__list" role="listbox">
//         <li class="bw-cmdk__group-label">...</li>
//         <li class="bw-cmdk__item" role="option" data-bw-href="...">
//         <li class="bw-cmdk__item" data-bw-command-search hidden>
//         <li class="bw-cmdk__empty" hidden>
//
// Keyboard: Cmd/Ctrl+K toggles the palette (document listener). While open,
// ArrowUp/ArrowDown move the active option, Enter runs it, Escape closes.
// Clicking [data-bw-cmdk-open] anywhere opens (craft kit parity). Scrim
// click closes. Focus trap is the host-owned @alpinejs/focus plugin via
// x-trap on the panel (BR-BW-JS-003); a consumer never authors x-trap.
//
// Filtering is client-side substring match against each item's textContent
// plus optional data-bw-keywords. Group labels hide when every item in that
// group is hidden. When config.action is set and the query is non-empty, a
// search row appears that navigates to action?name=query, tying the palette
// to the same GET surface as {% bw_search %}.
//
// Motion is CSS-owned: this module toggles [data-bw-open] / isOpen only
// (BR-BW-TOK-009).

import { dispatch, captureInvoker, guardedClose, restoreInvokerFocus } from "./overlay_shared.js";

function itemMatches(el, q) {
  if (!q) return true;
  const text = (el.textContent || "").toLowerCase();
  const keywords = (el.getAttribute("data-bw-keywords") || "").toLowerCase();
  return text.includes(q) || keywords.includes(q);
}

export default function command(config = {}) {
  return {
    isOpen: false,
    id: config.id ?? "",
    action: typeof config.action === "string" ? config.action : "",
    name: typeof config.name === "string" && config.name ? config.name : "q",
    query: "",
    activeIndex: 0,

    _root: null,
    _input: null,
    _invoker: null,
    _onWindowKeydown: null,
    _onOpenClick: null,
    _openedAt: 0,
    _pendingClose: null,

    init() {
      const root = this.$el;
      this._root = root;
      if (!this.id) this.id = root.id || "bw-command";
      this._input = root.querySelector(".bw-cmdk__input");
      root.setAttribute("aria-hidden", "true");

      const preferred = root.querySelector("[data-bw-autofocus]");
      if (preferred) preferred.setAttribute("autofocus", "");

      const scrim = root.querySelector("[data-bw-command-scrim]");
      if (scrim) {
        scrim.addEventListener("click", () => this.close("backdrop"));
      }

      root.querySelectorAll(".bw-cmdk__item").forEach((el) => {
        el.addEventListener("click", (event) => {
          if (el.hidden) return;
          event.preventDefault();
          this.activeIndex = this._visibleItems().indexOf(el);
          this.runActive();
        });
        el.addEventListener("mousemove", () => {
          if (el.hidden) return;
          this.activeIndex = this._visibleItems().indexOf(el);
          this._paintActive();
        });
      });

      if (this._input) {
        this._input.addEventListener("input", () => {
          this.query = this._input.value;
          this.filter();
        });
        this._input.addEventListener("keydown", (event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            this._moveActive(1);
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            this._moveActive(-1);
          } else if (event.key === "Enter") {
            event.preventDefault();
            this.runActive();
          } else if (event.key === "Escape") {
            event.preventDefault();
            this.close("escape");
          }
        });
      }

      this._onWindowKeydown = (event) => {
        const isK = event.key === "k" || event.key === "K";
        const mod = event.metaKey || event.ctrlKey;
        if (mod && isK) {
          event.preventDefault();
          if (this.isOpen) this.close("shortcut");
          else this.open();
          return;
        }
        if (event.key === "Escape" && this.isOpen) {
          event.preventDefault();
          this.close("escape");
        }
      };
      window.addEventListener("keydown", this._onWindowKeydown);

      this._onOpenClick = (event) => {
        const trigger = event.target.closest("[data-bw-cmdk-open]");
        if (!trigger) return;
        event.preventDefault();
        this.open();
      };
      document.addEventListener("click", this._onOpenClick);

      this.filter();
    },

    destroy() {
      window.removeEventListener("keydown", this._onWindowKeydown);
      document.removeEventListener("click", this._onOpenClick);
      if (this._pendingClose) clearTimeout(this._pendingClose);
    },

    open() {
      if (this.isOpen) return;
      this._openedAt = Date.now();
      this._invoker = captureInvoker(this._root, this._invoker);
      this.isOpen = true;
      this._root.setAttribute("data-bw-open", "");
      this._root.setAttribute("aria-hidden", "false");
      this.query = "";
      if (this._input) this._input.value = "";
      this.filter();
      dispatch(this._root, "bw:command:open", { id: this.id });
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          if (this._input && this.isOpen) this._input.focus();
        });
      });
    },

    close(reason = "programmatic") {
      if (!this.isOpen || this._pendingClose) return;
      const deferred = guardedClose(this, reason, (deferredReason) => this._close(deferredReason));
      if (!deferred) this._close(reason);
    },

    _close(reason) {
      if (!this.isOpen) return;
      this.isOpen = false;
      this._root.removeAttribute("data-bw-open");
      this._root.setAttribute("aria-hidden", "true");
      dispatch(this._root, "bw:command:close", { id: this.id, reason });
      const invoker = this._invoker;
      this._invoker = null;
      restoreInvokerFocus(invoker, this.$nextTick.bind(this));
    },

    filter() {
      const q = (this.query || "").trim().toLowerCase();
      const items = [...this._root.querySelectorAll(".bw-cmdk__item")].filter(
        (el) => !el.hasAttribute("data-bw-command-search"),
      );
      items.forEach((el) => {
        el.hidden = Boolean(q) && !itemMatches(el, q);
      });

      this._syncGroupLabels();
      this._syncSearchRow(q);
      const empty = this._root.querySelector(".bw-cmdk__empty");
      if (empty) empty.hidden = this._visibleItems().length > 0;
      this.activeIndex = 0;
      this._paintActive();
    },

    runActive() {
      const list = this._visibleItems();
      const el = list[this.activeIndex];
      if (!el) {
        if (this.action && (this.query || "").trim()) {
          this._navigateSearch();
        }
        return;
      }
      if (el.hasAttribute("data-bw-command-search")) {
        this._navigateSearch();
        return;
      }
      const href = el.getAttribute("data-bw-href") || el.getAttribute("href");
      this.close("select");
      dispatch(this._root, "bw:command:select", { id: this.id, href: href || "" });
      if (href) {
        window.location.href = href;
      }
    },

    _navigateSearch() {
      if (!this.action) return;
      const q = (this.query || "").trim();
      const url = new URL(this.action, window.location.href);
      if (q) url.searchParams.set(this.name, q);
      this.close("select");
      window.location.href = url.pathname + url.search + url.hash;
    },

    _visibleItems() {
      return [...this._root.querySelectorAll(".bw-cmdk__item")].filter((el) => !el.hidden);
    },

    _moveActive(delta) {
      const list = this._visibleItems();
      if (!list.length) return;
      const next = (this.activeIndex + delta + list.length) % list.length;
      this.activeIndex = next;
      this._paintActive();
    },

    _paintActive() {
      const list = this._visibleItems();
      list.forEach((el, idx) => {
        if (idx === this.activeIndex) {
          el.setAttribute("data-bw-active", "");
          el.scrollIntoView({ block: "nearest" });
        } else {
          el.removeAttribute("data-bw-active");
        }
      });
    },

    _syncGroupLabels() {
      const children = [...this._root.querySelectorAll(".bw-cmdk__list > *")];
      let pendingLabel = null;
      children.forEach((el) => {
        if (el.classList.contains("bw-cmdk__group-label")) {
          pendingLabel = el;
          el.hidden = true;
          return;
        }
        if (el.classList.contains("bw-cmdk__item") && !el.hasAttribute("data-bw-command-search")) {
          if (pendingLabel && !el.hidden) {
            pendingLabel.hidden = false;
            pendingLabel = null;
          }
        }
      });
    },

    _syncSearchRow(q) {
      const row = this._root.querySelector("[data-bw-command-search]");
      if (!row) return;
      const show = Boolean(this.action) && Boolean(q);
      row.hidden = !show;
      const label = row.querySelector("[data-bw-command-search-label]");
      if (label && show) {
        const template =
          row.getAttribute("data-bw-command-search-template") || 'Search for "{query}"';
        label.textContent = template.replace("{query}", this.query.trim());
      }
    },
  };
}
