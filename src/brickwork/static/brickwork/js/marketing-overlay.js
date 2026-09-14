/**
 * Marketing header overlay progressive enhancement (ADR-105,
 * icvoss/django-brickwork#565).
 *
 * Vanilla IIFE: no Alpine, no htmx. The marketing shell loads this on every
 * marketing page; it no-ops unless a .bw-marketing-header--overlay is present.
 *
 * Public attributes stamped on the overlay header:
 *   data-bw-overlay-ready   present once enhancement has run
 *   data-bw-scrolled        "true" | "false"
 *   data-bw-nav-context     "light" | "dark" (from marked bands, or author
 *                           initial value on the header)
 *
 * Consumer marks bands: data-bw-nav-context="light"|"dark" on elements that
 * should drive chrome ink when they sit under the nav.
 */
(function () {
  "use strict";

  var SCROLL_THRESHOLD_PX = 24;
  var HEADER_PROBE_PX = 56;

  function enhance(header) {
    if (header.hasAttribute("data-bw-overlay-ready")) return;

    var root = header.closest(".bw-marketing");
    var scope = root || document;

    function panels() {
      return Array.prototype.slice.call(
        scope.querySelectorAll("[data-bw-nav-context]"),
      ).filter(function (el) {
        return el !== header && !header.contains(el);
      });
    }

    function update() {
      var scrollY = window.scrollY || window.pageYOffset || 0;
      header.setAttribute(
        "data-bw-scrolled",
        scrollY > SCROLL_THRESHOLD_PX ? "true" : "false",
      );

      var ctx = header.getAttribute("data-bw-nav-context") || "light";
      var list = panels();
      // Last band whose top has crossed under the nav probe wins (Vendably
      // precedent). Do not require bottom > 0: a tall first band can still
      // intersect the viewport after scroll while a later band already owns
      // the under-nav strip.
      for (var i = list.length - 1; i >= 0; i--) {
        var rect = list[i].getBoundingClientRect();
        if (rect.top <= HEADER_PROBE_PX) {
          var marked = list[i].getAttribute("data-bw-nav-context");
          if (marked === "light" || marked === "dark") {
            ctx = marked;
          }
          break;
        }
      }
      header.setAttribute("data-bw-nav-context", ctx);
    }

    header.setAttribute("data-bw-overlay-ready", "");
    if (!header.getAttribute("data-bw-nav-context")) {
      header.setAttribute("data-bw-nav-context", "light");
    }
    header.setAttribute("data-bw-scrolled", "false");
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
  }

  function boot() {
    var headers = document.querySelectorAll(".bw-marketing-header--overlay");
    for (var i = 0; i < headers.length; i++) {
      enhance(headers[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
