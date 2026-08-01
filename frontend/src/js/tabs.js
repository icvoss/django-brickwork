// bwTabs: the tabs behaviour (04-interfaces section 4b, 0.8.0).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwTabs", ...) with config
//     { id, active: string, urlSync: boolean, lazyLoad: boolean }
//   state   active (the selected tab's key)
//   method  select(key)
//   event   bw:tabs:change (detail { id, key }), a bubbling CustomEvent
//           dispatched from the component root on activation only
//           (BR-BW-HTMX-004: optional convention, never load-bearing).
//
// Activation is MANUAL (adopted ruling, interactions-1 build): arrow keys
// move focus only; Enter/Space (or click) activates the focused tab. This
// keeps arrow-key browsing free of side effects on every panel shape,
// including lazy_load panels where activation triggers a server request.
// 04-interfaces' automatic-when-local wording is superseded by the ruling;
// flagged in the build report for the spec amendment.
//
// DOM contract this module enhances (_tabs.html renders the floor;
// BR-BW-HTMX-006). The no-JS floor is real anchor links, server-selected
// active tab, NO tab roles (roles arrive with the behaviour they promise):
//
//   <div x-data="bwTabs({...})">                    component root
//     <nav data-bw-tablist>                          the tablist container
//       <a data-bw-tab-key="<key>"
//          data-bw-tab-panel-id="bw-tabpanel-<id>-<key>"
//          href="?tab=<key>">                        one anchor per tab
//   ...panels elsewhere in consumer markup, wrapped by the shipped
//   {% partialdef tab_panel %}, ids bw-tabpanel-<id>-<key> (BR-BW-HTMX-005;
//   data-bw-tab-panel-id is authoritative, the convention is the fallback).
//
// At init the markup is upgraded in place: role="tablist" on the
// container; role="tab", aria-selected, aria-controls and roving tabindex
// on each anchor; inactive panels get hidden. Panels' role="tabpanel" /
// aria-labelledby / tabindex="0" arrive server-rendered via the partial.
//
// Keyboard map (WAI-ARIA APG Tabs pattern, roving tabindex, semver-public,
// BR-BW-JS-005): Tab enters the tablist on the active tab only;
// ArrowRight/ArrowLeft move focus wrapping (mirrored under dir="rtl");
// Home/End jump to first/last; Enter/Space activates (manual activation);
// Tab from the tablist moves into the active panel, never the next tab
// (CBH-015: the active panel is the next tabbable in DOM order because
// inactive tabs are tabindex="-1" and inactive panels are hidden).
//
// url_sync (CBH-013, default on): activation rewrites ?tab=<key> on the
// current URL via history.replaceState, so the JS leg and the no-JS floor
// share one URL scheme.
//
// Motion is CSS-owned: this module toggles state (aria-selected, hidden,
// [data-bw-active] on tabs) and never sequences animation or reads timing
// (BR-BW-TOK-009 lives entirely in the component CSS).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

export default function tabs(config = {}) {
  return {
    id: config.id ?? "",
    active: config.active ?? "",
    urlSync: config.urlSync !== false,
    lazyLoad: config.lazyLoad === true,

    _tablist: null,

    init() {
      const root = this.$el;
      if (!this.id) this.id = root.id || "bw-tabs";
      this._tablist = root.querySelector("[data-bw-tablist]") || root;

      const tabEls = this._tabEls();
      if (!tabEls.length) return; // floor markup absent: stay inert
      if (!tabEls.some((el) => el.dataset.bwTabKey === this.active)) {
        this.active = tabEls[0].dataset.bwTabKey;
      }

      // ARIA upgrade: only under JS, per the progressive-enhancement rule.
      this._tablist.setAttribute("role", "tablist");
      for (const el of tabEls) {
        const key = el.dataset.bwTabKey;
        el.setAttribute("role", "tab");
        if (!el.id) el.id = `bw-tab-${this.id}-${key}`;
        el.setAttribute("aria-controls", this._panelId(el));
        // aria-selected carries the state under tab semantics; the server's
        // no-JS markers (aria-current="page" and the --active class) would
        // go stale client-side, where data-bw-active takes over the visual.
        el.removeAttribute("aria-current");
        el.classList.remove("bw-tabs__tab--active");
        el.addEventListener("click", (event) => {
          event.preventDefault(); // the href stays the no-JS floor
          this.select(key);
        });
      }

      this._tablist.addEventListener("keydown", (event) =>
        this._onKeydown(event),
      );
      // Leaving the tablist parks the roving tabindex back on the ACTIVE
      // tab, so re-entering by Tab always lands on the active tab
      // (AC-BW-083: only the active tab is in the tab order at rest).
      this._tablist.addEventListener("focusout", (event) => {
        if (!this._tablist.contains(event.relatedTarget)) {
          this._setRoving(this.active);
        }
      });

      this._apply(this.active); // initial state: no bw:tabs:change emitted
    },

    select(key) {
      if (key === this.active) return;
      if (!this._tabEls().some((el) => el.dataset.bwTabKey === key)) return;
      this.active = key;
      this._apply(key);
      this._syncUrl(key);
      dispatch(this.$el, "bw:tabs:change", { id: this.id, key });
    },

    _tabEls() {
      return Array.from(
        (this._tablist || this.$el).querySelectorAll("[data-bw-tab-key]"),
      );
    },

    _panelId(el) {
      return (
        el.dataset.bwTabPanelId ||
        `bw-tabpanel-${this.id}-${el.dataset.bwTabKey}`
      );
    },

    _apply(activeKey) {
      for (const el of this._tabEls()) {
        const isActive = el.dataset.bwTabKey === activeKey;
        el.setAttribute("aria-selected", isActive ? "true" : "false");
        el.setAttribute("tabindex", isActive ? "0" : "-1");
        if (isActive) el.setAttribute("data-bw-active", "");
        else el.removeAttribute("data-bw-active");
        const panel = document.getElementById(this._panelId(el));
        if (panel) panel.hidden = !isActive;
      }
    },

    _setRoving(focusKey) {
      for (const el of this._tabEls()) {
        el.setAttribute(
          "tabindex",
          el.dataset.bwTabKey === focusKey ? "0" : "-1",
        );
      }
    },

    _focusTabAt(index) {
      const els = this._tabEls();
      if (!els.length) return;
      const wrapped = (index + els.length) % els.length;
      const el = els[wrapped];
      // Roving tabindex follows focus inside the tablist (APG); it parks
      // back on the active tab when focus leaves (see the focusout hook).
      this._setRoving(el.dataset.bwTabKey);
      el.focus();
    },

    _onKeydown(event) {
      const els = this._tabEls();
      const current = els.indexOf(document.activeElement);
      if (current === -1) return;
      const rtl = getComputedStyle(this._tablist).direction === "rtl";
      const forward = rtl ? "ArrowLeft" : "ArrowRight";
      const backward = rtl ? "ArrowRight" : "ArrowLeft";
      switch (event.key) {
        case forward:
          event.preventDefault();
          this._focusTabAt(current + 1);
          break;
        case backward:
          event.preventDefault();
          this._focusTabAt(current - 1);
          break;
        case "Home":
          event.preventDefault();
          this._focusTabAt(0);
          break;
        case "End":
          event.preventDefault();
          this._focusTabAt(-1);
          break;
        case "Enter":
        case " ":
          // MANUAL activation: only Enter/Space (or click) selects.
          event.preventDefault();
          this.select(els[current].dataset.bwTabKey);
          break;
        default:
          break;
      }
    },

    _syncUrl(key) {
      if (!this.urlSync) return;
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("tab", key);
        window.history.replaceState(window.history.state, "", url);
      } catch {
        // Environments without a mutable history (e.g. file:// fixtures in
        // some browsers) keep working; url_sync is an enhancement only.
      }
    },
  };
}
