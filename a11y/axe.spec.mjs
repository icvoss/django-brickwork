// axe-core accessibility gate (WCAG 2.2 AA) + the no-JS floor assertion.
//
// Runs against the pre-rendered fixtures (a11y/generate_fixtures.py renders the
// REAL testapp pages through the full shell in light + dark). This is the
// load-bearing differentiator: 0/22 competitor admin templates ship a tested
// a11y guarantee. axe finds ~57% of issues, so this pairs with the keyboard +
// no-JS checks below; manual AT review remains a release-gate step on top.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const pages = readdirSync(FIXTURES).filter((f) => f.endsWith(".html"));

// WCAG 2.2 AA tag set. axe maps these to the rule subset that gates the build.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

for (const page of pages) {
  test(`axe WCAG 2.2 AA: ${page}`, async ({ page: pw }) => {
    await pw.goto(pathToFileURL(join(FIXTURES, page)).href);
    // Settle CSS entrance animations (e.g. the account-menu panel's
    // bw-fade-in-up, 200ms, which plays on load whenever a fixture renders
    // the disclosure already open) before analyzing. Evaluating mid-animation
    // samples transient opacity/position, which axe correctly, but
    // misleadingly, reports as a steady-state contrast/target-size defect;
    // the real, settled state is what WCAG governs. Only FINITE animations are
    // awaited: an infinitely-iterating Animation's .finished promise never
    // settles by spec, so waiting on it would hang forever. The skeleton
    // shimmer, the spinner, and the indeterminate progress sweep (all
    // `infinite`) are steady-state loops, not entrance transitions, so
    // analyzing while they run is correct: that IS their settled state.
    await pw.evaluate(() =>
      Promise.all(
        document
          .getAnimations()
          .filter((a) => a.effect?.getTiming().iterations !== Infinity)
          .map((a) => a.finished),
      ),
    );
    const results = await new AxeBuilder({ page: pw }).withTags(WCAG_TAGS).analyze();
    // Fail with the concrete violations so a regression is actionable.
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

// Both theme variants get the behavioural floor, not just light: a dark-only
// regression (a hidden control, a broken disclosure) must fail the gate too.
const THEMES = ["light", "dark"];

// The no-JS floor (BR-BW-HTMX-001): with JavaScript disabled, the shell must
// still render a complete, navigable document, the skip link and nav links must
// be real anchors, and the native <details> disclosures must work.
test.describe("no-JS floor", () => {
  test.use({ javaScriptEnabled: false });

  for (const theme of THEMES) {
    test(`shell renders and is navigable with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `list-${theme}.html`)).href);
      // skip link is a real anchor to the main region
      const skip = page.locator("a.bw-skip-link");
      await expect(skip).toHaveAttribute("href", "#bw-main");
      await expect(page.locator("#bw-main")).toBeVisible();
      // nav links are real anchors (not JS-only widgets)
      await expect(page.locator("a.bw-nav__link").first()).toBeVisible();
      // the mobile drawer is a native <details> (works with no JS)
      await expect(page.locator("details.bw-drawer")).toHaveCount(1);
      // the records data table rendered rows server-side (scoped to its wrap:
      // the page also carries the definition-variant facts table)
      await expect(page.locator("#widgets-table table.bw-data-table tbody tr")).toHaveCount(2);
      // breadcrumbs render server-side with the current page marked
      await expect(page.locator("ol.bw-breadcrumbs__list li").first()).toBeVisible();
      await expect(page.locator('.bw-breadcrumbs__current[aria-current="page"]')).toBeVisible();
      // the account menu is a native <details>: clicking the summary opens it
      // with JS disabled (disclosure behaviour is HTML, not scripting)
      const menu = page.locator("details.bw-account-menu");
      await expect(menu).toHaveCount(1);
      await expect(page.locator("nav.bw-account-menu__panel")).toBeHidden();
      await page.locator("summary.bw-account-menu__trigger").click();
      await expect(menu).toHaveAttribute("open");
      await expect(page.locator("nav.bw-account-menu__panel")).toBeVisible();
      // the consumer's own property switcher in the nav slot (#21, AC-BW-078)
      // is a native <details> too: it opens with JS disabled
      const switcher = page.locator("aside.bw-sidebar details.bw-sidebar__switcher-trigger");
      await expect(switcher).toHaveCount(1);
      await switcher.locator("summary").click();
      await expect(switcher).toHaveAttribute("open");
      // the filter bar is a plain GET form (TBL-003 no-JS floor)
      await expect(page.locator("form.bw-filter-bar")).toHaveAttribute("method", "get");
    });

    test(`dashboard pattern renders server-side with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `dashboard-${theme}.html`)).href);
      // three stat tiles, rendered entirely server-side
      await expect(page.locator(".bw-stat")).toHaveCount(3);
      // a delta's directional meaning is glyph + text, never colour alone
      // (BR-BW-TPL-007): the trend text labels are present in the DOM
      await expect(page.getByText("One more than last week")).toHaveCount(1);
      // the recent-activity table rendered its rows server-side
      await expect(page.locator("#activity-table table.bw-data-table tbody tr")).toHaveCount(2);
    });

    test(`form errors are present and wired with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `form-errors-${theme}.html`)).href);
      const input = page.locator('input[aria-invalid="true"]').first();
      await expect(input).toHaveCount(1);
      const describedBy = await input.getAttribute("aria-describedby");
      expect(describedBy).toBeTruthy();
      // the referenced error container exists and carries the message
      const errorId = describedBy.split(" ").find((id) => id.endsWith("_errors"));
      await expect(page.locator(`#${errorId}`)).toContainText("not allowed");
      // the drawn checkbox (bw-checkbox) is present and natively toggleable:
      // a real <input type="checkbox"> changes state without any scripting
      const checkbox = page.locator('input[type="checkbox"].bw-checkbox');
      await expect(checkbox).toHaveCount(1);
      await expect(checkbox).not.toBeChecked();
      await checkbox.check();
      await expect(checkbox).toBeChecked();
    });

    // BR-BW-MKT-002's no-JS render floor: every marketing page renders and
    // functions with neither Alpine nor htmx loaded. The marketing shell
    // needs no JS at all (BR-BW-HTMX-001), so this is mostly a structural
    // check: the shell chrome, the FAQ's native <details> accordion, and the
    // hero's single <h1> are all present with JavaScript disabled.
    test(`landing page renders the marketing shell with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `landing-${theme}.html`)).href);
      await expect(page.locator("#bw-main")).toBeVisible();
      await expect(page.locator("header.bw-marketing-header")).toBeVisible();
      await expect(page.locator("footer.bw-marketing-footer")).toBeVisible();
      // exactly one h1, in the hero
      await expect(page.locator("h1")).toHaveCount(1);
      // the nav and header actions are real anchors
      await expect(page.locator(".bw-marketing-header__nav a").first()).toBeVisible();
      await expect(page.locator(".bw-marketing-header__actions a").first()).toBeVisible();
    });

    // The nav renderers (#102/#82): both sibling renderers are real-anchor
    // renders over the same NavItem tree (no JS-only triggers), the compact
    // renderers light the active AREA, and the exact aria-current lives in
    // the contextual tier's ordinary bw_nav render.
    test(`nav renderers are real anchors with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `nav-renderers-${theme}.html`)).href);
      await expect(page.locator("a.bw-nav-header__link").first()).toBeVisible();
      await expect(page.locator("a.bw-nav-rail__link").first()).toBeVisible();
      // ancestor-active treatments on the compact renderers (child route active)
      await expect(page.locator(".bw-nav-header__link--active-ancestor")).toHaveCount(1);
      await expect(page.locator(".bw-nav-rail__link--active-ancestor")).toHaveCount(1);
      // exactly one exact-active marker, in the contextual tier
      await expect(page.locator('[aria-current="page"]')).toHaveCount(1);
      await expect(page.locator('.bw-nav-two-tier .bw-nav__link[aria-current="page"]')).toHaveCount(1);
      // the rail badge chip and the external affordance render server-side
      await expect(page.locator(".bw-nav-rail__badge")).toHaveText("2");
      await expect(page.locator(".bw-nav-header__external")).toHaveCount(1);
    });

    test(`pricing page's FAQ accordion works with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `pricing-${theme}.html`)).href);
      // the pricing table rendered its tiers server-side
      await expect(page.locator(".bw-pricing-tier")).toHaveCount(3);
      // the FAQ is native <details>/<summary> (BR-BW-MKT-004): clicking the
      // summary opens it with JS disabled, no scripting required
      const firstItem = page.locator("details.bw-disclosure").first();
      await expect(page.locator("details.bw-disclosure")).toHaveCount(3);
      await expect(firstItem).not.toHaveAttribute("open");
      await firstItem.locator("summary").click();
      await expect(firstItem).toHaveAttribute("open");
    });

    test(`about page renders its prose body with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `about-${theme}.html`)).href);
      await expect(page.locator("h1")).toHaveCount(1);
      await expect(page.locator(".bw-section-stack")).toContainText("Our story");
    });

    // The date-range picker's floor (examples/app/date-range-picker.html):
    // with JS disabled the calendar trigger buttons do nothing (they carry no
    // href and no default type="submit" behaviour), but the two native
    // <input type="date"> fields ARE the form, so typing a value and
    // submitting must produce a real, correct navigation: proof by an actual
    // browser submit rather than by asserting the markup shape alone.
    test(`date-range picker submits real dates with JS disabled (${theme})`, async ({ page }) => {
      // The fixture's <form action="{{ request.path }}"> bakes in a real
      // Django path (generate_fixtures.py renders it against "/invoices/"),
      // which does not exist as a file:// target once the page is a static
      // snapshot. Routing the navigation lets the browser build the real GET
      // query string from the native <input type="date"> values (the thing
      // under test) without following it into a nonexistent file.
      let requestedUrl = null;
      await page.route("**/invoices/**", async (route) => {
        requestedUrl = new URL(route.request().url());
        await route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>stub</title>" });
      });

      await page.goto(pathToFileURL(join(FIXTURES, `date-range-picker-${theme}.html`)).href);
      const start = page.locator("#id_start_date");
      const end = page.locator("#id_end_date");
      await expect(start).toHaveAttribute("type", "date");
      await expect(end).toHaveAttribute("type", "date");
      await start.fill("2026-08-01");
      await end.fill("2026-08-21");
      await Promise.all([
        page.waitForNavigation(),
        page.locator('form:has(#id_start_date) button[type="submit"]').click(),
      ]);
      expect(requestedUrl.searchParams.get("start_date")).toBe("2026-08-01");
      expect(requestedUrl.searchParams.get("end_date")).toBe("2026-08-21");

      // The calendar trigger is inert without JS: clicking it must not throw,
      // navigate, or reveal the popover (it stays HTML-hidden).
      await page.goto(pathToFileURL(join(FIXTURES, `date-range-picker-${theme}.html`)).href);
      await page.locator('button[aria-label="Choose start date"]').click();
      await expect(page.locator(".bw-drp-popover").first()).toBeHidden();

      // The single-date mode floor submits too.
      requestedUrl = null;
      const due = page.locator("#id_single_date");
      await expect(due).toHaveAttribute("type", "date");
      await due.fill("2026-09-01");
      await Promise.all([
        page.waitForNavigation(),
        page.locator('form:has(#id_single_date) button[type="submit"]').click(),
      ]);
      expect(requestedUrl.searchParams.get("due_date")).toBe("2026-09-01");
    });
  }
});

// Keyboard: the skip link is the first focusable element and targets main.
for (const theme of THEMES) {
  test(`skip link is the first tab stop (${theme})`, async ({ page }) => {
    await page.goto(pathToFileURL(join(FIXTURES, `list-${theme}.html`)).href);
    await page.keyboard.press("Tab");
    const focusedHref = await page.evaluate(() => document.activeElement?.getAttribute("href"));
    expect(focusedHref).toBe("#bw-main");
  });
}

// The mobile-first floor, swept over EVERY fixture (icvoss/django-brickwork#209).
//
// ADR-057 section 1: "a section that only works at desktop width is not a
// shipped section". axe does not measure this, and neither does a render test,
// so a page that scrolls sideways on a phone passes every other gate in this
// repo. This used to run over sections-*.html and hero-placement-*.html only
// (both marketing fixtures), which is exactly why the app shell's topbar
// account cluster and the auth shell's panel shipped a 320px overflow (#209):
// neither fixture family is a marketing page, so the sweep never touched
// them. Iterating `pages` (the same list the axe loop above already builds
// from the fixture directory) closes the class rather than patching the two
// named instances, the load-bearing half of that issue's fix.
//
// It has already caught real defects on the way in, all of which passed axe
// and the full pytest suite:
//   - .bw-hero__copy sized to its content instead of its container, because
//     .bw-hero sets align-items other than stretch.
//   - a <pre>'s <code> child painted outside its own scroll container.
//   - a one-word hero heading ("Documentation") at the fixed 60px display size
//     measured 406px and had no wrap opportunity.
//   - .bw-marketing-header__actions/.bw-marketing-header__nav overflowing at
//     320px (#125).
//   - .bw-topbar__account (a long account label with nowhere to shrink to)
//     and .bw-auth__panel (an implicit grid track with no minmax(0, 1fr)
//     floor, so unbreakable panel content grew the track past the viewport
//     and .bw-auth__panel's own `min(28rem, 100%)` inherited the oversized
//     100%) at narrow widths (#209).
//
// 320px is the narrowest width the package supports
// (icvoss/django-brickwork#125's own comment on MOBILE_WIDTHS); 414px is the
// widest common phone.
const MOBILE_WIDTHS = [320, 360, 375, 414];

for (const width of MOBILE_WIDTHS) {
  for (const page of pages) {
    test(`no sideways scroll at ${width}px: ${page}`, async ({ page: pw }) => {
      await pw.setViewportSize({ width, height: 900 });
      await pw.goto(pathToFileURL(join(FIXTURES, page)).href);

      const result = await pw.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        // Name the culprits, so a failure is actionable rather than a bare
        // number. Only elements whose parent is NOT itself overflowing are
        // reported: those are the root causes, not the cascade above them.
        offenders: [...document.querySelectorAll("*")]
          .filter((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.right <= window.innerWidth + 1) return false;
            const parent = el.parentElement?.getBoundingClientRect();
            return !parent || parent.right <= window.innerWidth + 1;
          })
          .slice(0, 5)
          .map((el) => `${el.tagName}.${typeof el.className === "string" ? el.className.split(" ")[0] : ""}`),
      }));

      expect(
        result.documentWidth,
        `page scrolls horizontally at ${width}px; root causes: ${JSON.stringify(result.offenders)}`,
      ).toBeLessThanOrEqual(result.viewportWidth + 1);
    });
  }
}

// WCAG 2.2 AA success criterion 2.5.8, Target Size (Minimum): 24x24 CSS px,
// swept over EVERY fixture at 375px (icvoss/django-brickwork#208).
//
// NOT covered by the axe run above on purpose: axe ships a `target-size`
// rule under wcag22aa, but it reports `incomplete` rather than `violation`
// for most of these shapes and does not fire on the plain-anchor case at
// all, which is why the axe gate stayed green while .bw-data-table__sort
// measured 74x16, .bw-data-table__row-link and .bw-checkbox sat under the
// floor, and a consumer following the package's own documented
// ".bw-marketing-header__actions > a:not(.bw-btn)" composition got a 40x21
// target. The same "incomplete, not violation" gap the CHANGELOG already
// records for the 3.4.0 hero scrim (composited contrast, measured directly
// below in this file rather than trusted to axe). Measured explicitly here
// instead: getBoundingClientRect() over every interactive element.
//
// Zero-size elements are skipped: a control that is display:none or not yet
// laid out has no target to measure, and the no-JS/hidden-drawer fixtures
// legitimately contain those (the mobile drawer's nav links, the closed
// account-menu panel's items).
//
// TAP_TARGET_EXEMPT_SELECTORS excludes elements that are not a defect in
// this measurement's terms, each with its own reason; every entry was swept
// up while widening this check for #208 and triaged individually rather
// than blanket-excluded:
//   - '.bw-dropzone__input': deliberately visually-hidden (clip, not
//     display:none) so it stays focusable/keyboard-activatable; the
//     dropzone BOX is the real target, documented on the rule itself
//     (components.css).
//   - 'button:not([class])', 'input:not([class])': bare, unclassed native
//     controls the a11y testapp fixtures compose directly (wizard/
//     slide-over/table-selection's plain <button>/<input>, never a
//     bw_button or bw-field render), not a brickwork component; there is no
//     bw-* rule to fix.
//   - 'a:not([class])': the same shape for links, which also covers the
//     testapp's own property-switcher slot content (brickwork#21,
//     AC-BW-078: "Acme Ltd"/"Globex plc") and, until #242, the marketing
//     footer's link-group default. Before #242 this exemption WAS brickwork
//     disclaiming the sizing floor there for #208, on the stated rationale
//     that "brickwork does not own the group's layout, so a sizing floor is
//     not this package's call to make" (this file's own comment on
//     TAP_TARGET_EXEMPT_SELECTORS, added for #212). #242 reverses that
//     position:
//     .bw-marketing-footer__inner :where(a) already matches on tag, not
//     class, so it always reached these links for colour/decoration
//     (BR-BW-MKT-002) regardless of the consumer's own markup, which is the
//     same claim of ownership a sizing floor makes; #242 sizes them too
//     (min-block-size, both tiers, the same as the header nav/actions
//     links) rather than leaving the inconsistency in place. The entry
//     stays in this list only because the sweep is class-based and the
//     footer's own markup carries no class: the coarse-pointer tier is
//     measured separately, below, by selector rather than by class
//     presence, so this element-level exemption no longer means "unsized".
//   - '.bw-toggle': a fixed-shape switch (a deliberate design proportion,
//     not incidental line-height), always rendered inside a real clickable
//     <label class="bw-toggle-field"> when used as the standalone {%
//     bw_toggle %} tag; when opted into via CheckboxInput(attrs={"class":
//     "bw-toggle"}) it instead renders bare through bw_field_widget (the
//     same unwrapped shape .bw-checkbox had), so a track-only fix cannot
//     honour both contexts without either inflating the switch's visible
//     proportions or leaving the form-field usage unfixed. Tracked as its
//     own follow-up rather than folded into #208's fix.
//   - '.bw-listing-list__link': a text-run title link inside prose-style
//     listing content ("Only the title is the link here, not the whole
//     row", marketing.css's own comment), the WCAG 2.5.8 inline/text-run
//     exception this codebase already invokes for .bw-badge__close.
const TAP_TARGET_EXEMPT_SELECTORS = [
  ".bw-dropzone__input",
  "button:not([class])",
  "input:not([class])",
  "a:not([class])",
  ".bw-toggle",
  ".bw-listing-list__link",
].join(", ");

test.describe("tap targets", () => {
  for (const page of pages) {
    test(`interactive controls are at least 24x24: ${page}`, async ({ page: pw }) => {
      await pw.setViewportSize({ width: 375, height: 900 });
      await pw.goto(pathToFileURL(join(FIXTURES, page)).href);

      const undersized = await pw.evaluate((exemptSelector) =>
        [...document.querySelectorAll('a, button, input:not([type="hidden"]), select, [role="button"]')]
          .filter((el) => !el.matches(exemptSelector))
          .map((el) => {
            const rect = el.getBoundingClientRect();
            return {
              tag: el.tagName,
              cls: typeof el.className === "string" ? el.className.split(" ")[0] : "",
              text: (el.textContent || "").trim().slice(0, 30),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
          })
          .filter((m) => m.width > 0 && m.height > 0 && (m.width < 24 || m.height < 24)),
        TAP_TARGET_EXEMPT_SELECTORS,
      );

      expect(undersized, `controls below the 24x24 floor: ${JSON.stringify(undersized, null, 2)}`).toEqual([]);
    });
  }
});

// Coarse-pointer 44px tier (icvoss/django-brickwork#242, on top of #208's
// unconditional 24px AA floor above): the marketing header nav, the
// marketing header actions slot, the marketing footer link groups, and the
// breadcrumb trail all take a `@media (pointer: coarse)` min-block-size
// bump to --bw-size-touch-target-min (2.75rem/44px), the WCAG 2.5.5/
// platform-HIG bar, above what the sweep at 375px above asserts (a
// fine-pointer default context, which is why that sweep cannot see this
// tier at all).
//
// A new browser context with hasTouch: true is required: page.emulateMedia
// cannot emulate `pointer`, only `prefers-color-scheme` and similar, and
// Chromium's `pointer`/`any-pointer` media features are driven by the
// context's touch capability, not the viewport. Each test confirms
// window.matchMedia("(pointer: coarse)").matches is genuinely true (or
// false, for the fine-pointer regression pin) before trusting the size
// assertion below it: an emulation that silently fails to flip the media
// feature would otherwise make this a vacuous test that passes regardless
// of whether the CSS rule fires.
// expectedFinePx pins the exact fine-pointer rendered block-size measured
// against the current fixtures (all four surfaces render at exactly 24px,
// the #208 AA floor, with no extra padding or line-height inflation): a
// >=24/<44 band alone cannot tell a genuine 24px render from a fine-pointer
// creep to, say, 43px, since both pass that band. The 1px tolerance below
// allows for sub-pixel layout rounding, not for a real size change.
const COARSE_TARGETS = [
  {
    fixture: "landing-light.html",
    selector: ".bw-marketing-header__nav a:not(.bw-btn)",
    label: "marketing header nav link",
    expectedFinePx: 24,
  },
  {
    fixture: "landing-light.html",
    selector: ".bw-marketing-header__actions > a:not(.bw-btn)",
    label: "marketing header actions link",
    expectedFinePx: 24,
  },
  {
    fixture: "landing-light.html",
    selector: ".bw-marketing-footer__inner a:not(.bw-btn)",
    label: "marketing footer link",
    expectedFinePx: 24,
  },
  {
    fixture: "list-light.html",
    selector: ".bw-breadcrumbs__link",
    label: "breadcrumb link",
    expectedFinePx: 24,
  },
];

test.describe("coarse-pointer touch targets (#242)", () => {
  for (const { fixture, selector, label, expectedFinePx } of COARSE_TARGETS) {
    test(`${label} reaches 44px block-size under a coarse pointer`, async ({ browser }) => {
      const context = await browser.newContext({ hasTouch: true, viewport: { width: 375, height: 900 } });
      const page = await context.newPage();
      await page.goto(pathToFileURL(join(FIXTURES, fixture)).href);

      const matchesCoarse = await page.evaluate(() => window.matchMedia("(pointer: coarse)").matches);
      expect(
        matchesCoarse,
        "hasTouch: true did not flip (pointer: coarse); this Chromium build's touch emulation is not " +
          "genuine here, so the size assertion below cannot be trusted",
      ).toBe(true);

      const height = await page.evaluate(
        (sel) => document.querySelector(sel)?.getBoundingClientRect().height ?? 0,
        selector,
      );
      expect(height, `${label} (${selector}) measured ${height}px under a coarse pointer, want >= 44px`).toBeGreaterThanOrEqual(
        44,
      );

      await context.close();
    });

    test(`${label} stays at its fine-pointer size (regression pin) under a mouse pointer`, async ({ browser }) => {
      const context = await browser.newContext({ hasTouch: false, viewport: { width: 375, height: 900 } });
      const page = await context.newPage();
      await page.goto(pathToFileURL(join(FIXTURES, fixture)).href);

      const matchesFine = await page.evaluate(() => window.matchMedia("(pointer: fine)").matches);
      expect(
        matchesFine,
        "the default (no hasTouch) context did not report (pointer: fine); this Chromium build's pointer " +
          "media feature default is not what this regression pin assumes",
      ).toBe(true);

      const height = await page.evaluate(
        (sel) => document.querySelector(sel)?.getBoundingClientRect().height ?? 0,
        selector,
      );
      // Pinned to the exact measured value (expectedFinePx), not just a
      // >=24/<44 band: that band alone cannot distinguish a genuine 24px
      // render from a fine-pointer creep to, say, 43px, since both pass a
      // band check. +/-1px tolerance only, for sub-pixel layout rounding.
      expect(
        height,
        `${label} (${selector}) measured ${height}px under a fine pointer, want ` +
          `${expectedFinePx}px (+/-1px); the coarse-pointer tier must not apply here, and any drift from ` +
          `${expectedFinePx}px is a real size change, not rounding`,
      ).toBeGreaterThanOrEqual(expectedFinePx - 1);
      expect(height).toBeLessThanOrEqual(expectedFinePx + 1);

      await context.close();
    });
  }
});

// icvoss/django-brickwork#118: media_placement="beside" is a true side-by-side
// row from 48rem, the classic mobile overflow shape, and it had no dedicated
// mobile check before this fixture existed (hero-placement-*.html, added
// alongside media_placement itself). Covered by the generic sweep above now
// that it runs over every fixture; kept as its own named test too, since it
// asserts something the generic sweep does not: this exact composition mode
// specifically, so a regression here is diagnosed without hunting through
// the generic sweep's fixture list.
for (const theme of THEMES) {
  for (const width of MOBILE_WIDTHS) {
    test(`hero media_placement="beside" does not scroll the page sideways at ${width}px (${theme})`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(pathToFileURL(join(FIXTURES, `hero-placement-${theme}.html`)).href);

      const result = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        offenders: [...document.querySelectorAll("*")]
          .filter((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.right <= window.innerWidth + 1) return false;
            const parent = el.parentElement?.getBoundingClientRect();
            return !parent || parent.right <= window.innerWidth + 1;
          })
          .slice(0, 5)
          .map((el) => `${el.tagName}.${typeof el.className === "string" ? el.className.split(" ")[0] : ""}`),
      }));

      expect(
        result.documentWidth,
        `page scrolls horizontally at ${width}px; root causes: ${JSON.stringify(result.offenders)}`,
      ).toBeLessThanOrEqual(result.viewportWidth + 1);
    });
  }
}

// icvoss/django-brickwork#125 regression: the marketing header specifically,
// on the landing-*.html fixtures the issue itself reproduced against (326px
// scrollWidth at a 320px viewport, from .bw-marketing-header__actions and its
// bw_button both sitting at right edge 326). Asserted directly against the
// header element, not just the document, so a future regression here fails
// on this test rather than only on the broader sweep above.
for (const theme of THEMES) {
  test(`marketing header does not overflow a 320px viewport (${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto(pathToFileURL(join(FIXTURES, `landing-${theme}.html`)).href);

    const result = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      headerRight: document.querySelector(".bw-marketing-header")?.getBoundingClientRect().right ?? 0,
      actionsRight: document.querySelector(".bw-marketing-header__actions")?.getBoundingClientRect().right ?? 0,
    }));

    expect(result.documentWidth, "marketing header scrolls the page sideways at 320px").toBeLessThanOrEqual(
      result.viewportWidth + 1,
    );
    expect(result.headerRight, ".bw-marketing-header overflows the 320px viewport").toBeLessThanOrEqual(
      result.viewportWidth + 1,
    );
    expect(
      result.actionsRight,
      ".bw-marketing-header__actions overflows the 320px viewport",
    ).toBeLessThanOrEqual(result.viewportWidth + 1);
  });
}

// icvoss/django-brickwork#118 regression: WCAG 1.4.3 composited contrast for
// media_placement="behind" over the pale illustration fixture.
//
// axe cannot catch this. It reports "incomplete", never a violation, for text
// painted over a background image (its colour-contrast check does not
// rasterise the page), so the axe gate above ran green over a real defect:
// the original scrim was a linear-gradient from 45% to 75% opacity, which
// made the composited ratio depend on where a line of text happened to fall.
// Measured directly, the lede sat at 4.25:1, under the 4.5:1 floor, while the
// heading higher up passed at the same time. Only a pixel-level measurement
// of the actual rendered page catches that class of defect, which is what
// this test does: it screenshots the composited page (real glyphs over the
// real scrim over the real media, exactly what a reader sees) and computes
// the WCAG relative-luminance contrast ratio from the rendered pixels.
//
// Scoped to the pale-media "behind" hero specifically: that is the harder
// case the CSS comment on the scrim itself names (frontend/src/marketing.css,
// .bw-hero--media-behind .bw-hero__media::after) as the one a lighter
// rebrand most threatens, since --bw-color-surface-inverse resolves to
// --bw-color-fg, which a tenant can retune lighter.
function relativeLuminance([r, g, b]) {
  const channel = (c) => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function wcagContrastRatio(rgbA, rgbB) {
  const lA = relativeLuminance(rgbA);
  const lB = relativeLuminance(rgbB);
  const lighter = Math.max(lA, lB);
  const darker = Math.min(lA, lB);
  return (lighter + 0.05) / (darker + 0.05);
}

// Measures the worst-case composited contrast ratio between an element's own
// text colour and the page pixels actually behind it, across the element's
// full rendered box (its full vertical extent, so a defect that only shows up
// partway down a wrapped line, as the original one did, is still caught).
//
// The element is screenshotted in place (not re-rendered in isolation), so
// what is measured is exactly what a reader sees: real glyphs already
// composited over the real scrim over the real media. Anti-aliased glyph
// edges blend towards the text colour and would otherwise register as a
// falsely dark (or light) "background" pixel a handful of times per row;
// taking the per-row MODE of the non-glyph pixels is robust to that, because
// the true background fills the overwhelming majority of every row that has
// any background at all (line-height leading, inter-word gaps, the insides
// of open letterforms), while the anti-aliasing tail is never the most
// frequent colour in a row.
async function measureComposedContrast(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  const textColourCss = await locator.evaluate((el) => getComputedStyle(el).color);
  const [tr, tg, tb] = await page.evaluate((css) => {
    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
    return [r, g, b];
  }, textColourCss);

  const screenshot = await page.screenshot({
    clip: { x: box.x, y: box.y, width: box.width, height: box.height },
  });

  return page.evaluate(
    async ({ pngBase64, textColour, glyphThreshold }) => {
      const img = new Image();
      img.src = `data:image/png;base64,${pngBase64}`;
      await img.decode();
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;

      const relLum = ([r, g, b]) => {
        const channel = (c) => {
          c /= 255;
          return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        };
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
      };
      const ratio = (a, b) => {
        const lA = relLum(a);
        const lB = relLum(b);
        return (Math.max(lA, lB) + 0.05) / (Math.min(lA, lB) + 0.05);
      };
      const colourDistance = ([r1, g1, b1], [r2, g2, b2]) =>
        Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2);

      let worstRatio = Infinity;
      let worstBackground = null;
      for (let y = 0; y < canvas.height; y++) {
        const rowCounts = new Map();
        for (let x = 0; x < canvas.width; x++) {
          const idx = (y * canvas.width + x) * 4;
          const pixel = [data[idx], data[idx + 1], data[idx + 2]];
          if (colourDistance(pixel, textColour) < glyphThreshold) continue;
          const key = pixel.join(",");
          rowCounts.set(key, (rowCounts.get(key) ?? 0) + 1);
        }
        if (rowCounts.size === 0) continue;
        const [modeKey] = [...rowCounts.entries()].sort((a, b) => b[1] - a[1])[0];
        const modeRgb = modeKey.split(",").map(Number);
        const rowRatio = ratio(textColour, modeRgb);
        if (rowRatio < worstRatio) {
          worstRatio = rowRatio;
          worstBackground = modeRgb;
        }
      }
      return { ratio: worstRatio, background: worstBackground };
    },
    { pngBase64: screenshot.toString("base64"), textColour: [tr, tg, tb], glyphThreshold: 40 },
  );
}

for (const theme of THEMES) {
  test(`hero media_placement="behind" clears WCAG 1.4.3 composited contrast over pale media (${theme})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(pathToFileURL(join(FIXTURES, `hero-placement-${theme}.html`)).href);

    // Document order in the hero-placement fixture (a11y/generate_fixtures.py,
    // render_hero_media_placement): no-media, pale-media, dark-media, then the
    // "beside" hero. The pale-media "behind" hero is the second
    // .bw-hero--media-behind element and the harder of the two contrast cases
    // (the original defect measured 4.25:1 here, under the lede's 4.5:1
    // floor, while the near-black case never approached the floor).
    const paleMediaHero = page.locator(".bw-hero--media-behind").nth(1);
    const heading = paleMediaHero.locator(".bw-hero__heading");
    const lede = paleMediaHero.locator(".bw-hero__lede");

    const headingResult = await measureComposedContrast(page, heading);
    const ledeResult = await measureComposedContrast(page, lede);

    expect(
      headingResult.ratio,
      `hero heading over pale media (${theme} theme) measured ${headingResult.ratio.toFixed(2)}:1 against the composited background ${JSON.stringify(headingResult.background)}, below the WCAG 1.4.3 large-text floor of 3:1`,
    ).toBeGreaterThanOrEqual(3.0);

    expect(
      ledeResult.ratio,
      `hero lede over pale media (${theme} theme) measured ${ledeResult.ratio.toFixed(2)}:1 against the composited background ${JSON.stringify(ledeResult.background)}, below the WCAG 1.4.3 normal-text floor of 4.5:1`,
    ).toBeGreaterThanOrEqual(4.5);
  });
}
