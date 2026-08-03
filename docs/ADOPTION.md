# Adopting brickwork into an existing app (the strangle pattern)

[INTEGRATION.md](INTEGRATION.md) covers a greenfield install. This guide covers
the harder, more common case: strangling an existing UI kit (a hand-built shell
plus a `c-`/`x-` component library) onto brickwork **cluster by cluster**,
keeping the old kit alive until the last screen moves. It is a checklist distilled
from a real console cutover, not a theory; the structure below is reusable for the
next brownfield adopter.

## Principle: strangle, do not big-bang

brickwork is pre-1.0 and releasing rapidly. A whole-app commit before 1.0 carries
real churn risk: every rapid minor could touch a contract you depend on across
every screen at once. Migrate incrementally so that at any moment most of the app
still runs on the proven old kit and only the migrated cluster carries brickwork
risk. Keep rollback trivial at every step.

## The sequence

### 1. Pilot one screen cluster first

Pick one coherent cluster (a settings area, one resource's list+detail+form) and
move only that. The pilot's job is to prove the four load-bearing seams end to
end on real screens:

- the **shell** (does your layout survive inside `brickwork/shell/app.html`?),
- the **nav** (does your route tree map onto `NavItem`, including any
  parameterised / multi-view sections?),
- the **forms** (does your validation flow map onto the 422 loop, or the no-JS
  full-page redisplay floor?),
- the **JS-bearing body** (does your chart / editor mount cleanly inside
  `{% block content %}` with your own asset pipeline coexisting?).

Wire each per [INTEGRATION.md](INTEGRATION.md). If all four hold on the pilot
cluster, the rest is repetition; if one fights you, you have found the real
adoption cost before committing the whole app.

### 2. Migrate cluster by cluster, each its own PR

One cluster per PR keeps every step reviewable and independently revertable. Do
not let a half-migrated cluster straddle a release. The old kit and the brickwork
shell **coexist for the duration**: two base templates live side by side, screens
extend whichever kit they currently belong to, and you move screens across one
cluster at a time. This is expected and fine; plan for months of coexistence, not
a weekend.

### 3. Draw the boundary explicitly

Decide, up front and in writing, what migrates and what does not:

- **Migrates:** your own chrome (shell, nav, topbar), your forms, your list and
  detail screens, your dashboards.
- **Does NOT migrate:** data-viz bodies (charts stay app-owned inside
  `{% block content %}`, a declared brickwork non-goal); anything an engine or
  third party owns; a separately-branded, separately-hosted marketing / public
  site is not pulled into an *application-shell* cutover (that boundary stops
  "while we are in here" scope creep mid-migration). The core `brickwork` app is
  the *application* substrate. Note (ADR-055, from v1.2.0): brickwork now also
  ships an **opt-in `brickwork.marketing` sub-app** (add `"brickwork.marketing"`
  to `INSTALLED_APPS`) with marketing page templates (landing / pricing / about),
  a marketing shell, and eight marketing components (hero, feature grid,
  pricing tier/table, CTA, testimonial, logo cloud, stat band, FAQ) on the
  same `--bw-*` token / brand / accessibility contract.
  If a consumer *wants* its marketing pages on brickwork too (the "one package
  covers all templating" case), that is now a supported opt-in, migrated on its
  own schedule, not forced into the console cutover. What brickwork still does not
  ship is a general-purpose public-website *theme engine* (no page builder, no
  tenant-arbitrary content or CSS/JS); the marketing kit is a fixed, curated set
  of templates, not a CMS. The marketing kit is the first slice of a wider
  templates-catalogue trajectory (layout variants, then themed starter kits,
  each demand-gated); see `oss/docs/plans/brickwork-templates-catalogue-direction.md`
  in the umbrella.

Writing the boundary down stops scope creep mid-migration, where "while we are in
here" quietly pulls non-goals into the cutover.

### 4. Gate the final "delete the old kit" step on a stability signal

The last step, removing the old kit entirely, is the one with no rollback. Gate
it on a stability signal rather than doing it the moment the last screen moves:
a brickwork release you have pinned and validated across the migrated app, ideally
1.0 or a release-candidate you trust. Until then, keeping the old kit's code in
the tree (even with no screens using it) costs nothing and preserves the escape
hatch.

## Two wrinkles a real brownfield cutover hits (brickwork#49)

### Multi-host projects (the shell branches per host)

A project served on several hosts (django-hosts: a merchant host, an agency host,
an account host, each branching the shell) must decide per host whether that
host's screens are in the migration. The clean pattern: each host resolves its own
base template, and you migrate host by host as well as cluster by cluster. A host
still on the old shell and a host on the brickwork shell coexist with no shared
state beyond your own context; the per-request brand / theme resolver
(`BRICKWORK_THEME_RESOLVER`, see INTEGRATION.md section 3) is where a multi-host
app branches brand per host. Do not try to run one shared base template across
hosts mid-migration; let each host cross the line on its own schedule.

### Legacy-shell / brickwork-shell asset coexistence

While both shells are live, both asset pipelines are live. The classic pairing is
**django-vite hashed bundles** (the legacy kit) alongside **brickwork's plain
`{% static %}` artefacts**. These coexist cleanly: brickwork never enters your
bundler, and your bundler never needs to touch brickwork's static. Points to hold:

- Load brickwork's stylesheet through the shell (it does this for you) and your
  brand override through `head_extra`; load your Vite bundles the way you already
  do. Two independent `<link>` / `<script>` sets on the page is correct, not a
  smell.
- Do not route brickwork's `brickwork.css` through Vite to "unify" the pipeline;
  that couples you to brickwork's internal asset layout, which is not a contract.
- If you run Alpine yourself (host-owned `Alpine.start()`), brickwork registers
  its interaction components against your instance; keep a single Alpine start,
  not one per kit.

## The htmx floor, if you are brownfield on htmx 1.9 (brickwork#48)

brickwork's interaction contracts are built and CI-gated on **htmx >= 2.0**
only (BR-BW-HTMX-010); htmx 1.9 is out of contract. If your app is on htmx 1.9,
treat the htmx 1 -> 2 upgrade as a **prerequisite workstream** that lands before
the brickwork cutover, not something to reconcile screen by screen mid-migration.
htmx 2 changed default response handling in ways the 422 swap loop relies on;
running the cutover on 1.9 means wiring `htmx:beforeSwap` by hand on a path
brickwork does not test. Sequence the htmx upgrade first, then strangle onto
brickwork on a supported floor.

## What a worked instance looks like

The console cutover this guide is distilled from ran as an ADR plus a staged
plan: one ADR recording the decision and boundary, then a plan enumerating the
clusters in migration order with the "delete the old kit" step gated last. That
shape (decision + boundary in an ADR, ordered clusters in a plan) is worth
copying: it makes the migration auditable and the boundary durable against
scope creep.
