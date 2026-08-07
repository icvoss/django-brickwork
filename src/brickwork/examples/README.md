# brickwork example pages

**Copy these. Do not import them.**

Every file here is a complete, working page built from brickwork's tokens,
components, and shells, with real content typed directly into the template.
They are examples you own, not a contract you extend (ADR-056).

## You cannot extend them, by construction

This directory is package **data**, not an app `templates/` directory. Django's
`APP_DIRS` loader only walks `<app>/templates/`, so
`{% extends "brickwork/examples/app/list.html" %}` raises `TemplateDoesNotExist`
no matter how a project is configured. That is deliberate: a whole page is the
most project-specific thing you own, and a package that ships one you extend can
reshape your own page on a pin bump.

## How to use one

1. Open the file (in this directory, on GitHub, or in the gallery).
2. Copy it into your own `templates/` tree.
3. Change the `{% extends %}` line at the top to your own base if you want one.
4. Edit everything else. It is yours.

Read `base.html` first if you want to own your document skeleton too; it is
annotated line by line. If you would rather keep receiving skeleton
improvements automatically, extend `brickwork/shell/base.html` (or
`shell/app.html`, `shell/auth.html`, `shell/centred.html`,
`brickwork_marketing/shell/marketing.html`) instead: the shells remain a
supported, importable part of the package.

## Two units: sections and pages

A **section** is a single band (a hero, a pricing table, a call to action). It
is the unit you actually reuse, because a real page is a stack of them. Copy a
section into a page you already own.

A **page** is a whole document. Copy one when you are starting a page from
nothing.

Sections came first in 3.1.0 for a reason: before them, wanting a pricing band
meant copying a pricing page and deleting most of it.

## The sections

Under `sections/<type>/<variant>.html`. Each file's header comment says what it
is for, when to reach for it over its siblings, and whether it needs anything
from your view.

| Type | Variants |
|---|---|
| `hero` | `centred`, `split-media`, `media-behind`, `minimal` |
| `features` | `icon-grid`, `alternating-rows`, `simple-list` |
| `cta` | `centred-band`, `split`, `full-bleed` |
| `content` | `prose-block`, `media-and-text`, `callout` |
| `pricing` | `three-tier`, `single-plan`, `comparison-table` |
| `testimonial` | `single-quote`, `quote-grid`, `logo-and-quote` |
| `faq` | `single-column`, `two-column` |
| `stats` | `inline-band`, `card-row` |
| `listing` | `card-grid`, `media-list`, `compact-table` |

Most sections render from an EMPTY context, because the copy is typed into the
file. That is what makes them genuinely copy-paste. The exceptions are the ones
whose content is a list of dicts, which a Django template cannot build inline:

| Section | Needs from your view |
|---|---|
| `features/icon-grid` | `features` |
| `pricing/three-tier` | `tiers` |
| `stats/inline-band` | `stats` |
| `listing/*` (all three) | `entries` |

Each of those files documents the exact shape to pass in its header comment.
Where a zero-context alternative exists, the file says so: `pricing/single-plan`
and `faq/*` deliberately include their component once per item with flat
strings rather than looping a list, so the whole section stays editable in the
template.

Some variants are a one-line `{% include %}` of a shipped component, because
the component already does the job and the honest example is the include. The
rest own their markup, and each says why in its header comment: usually that
the arrangement is one the component cannot yet express.

### Long-form text: `bw-prose`

Blog posts and documentation are mostly unclassed markup, whether they came
from a Markdown renderer, a CMS, or a rich-text field. Wrap that content in one
class:

```html
<div class="bw-prose">{{ post.body|safe }}</div>
```

`bw-prose` styles bare headings, paragraphs, lists, blockquotes, inline code,
code blocks, tables, figures and rules from the same tokens as everything else,
at a 65ch reading measure. You put no classes on the content itself. Every rule
is written at zero specificity, so your own class on any element beats the floor
without `!important`.

(`|safe` only if you trust the source. brickwork styles markup; it does not
sanitise it.)

## The pages

| File | Shape |
|---|---|
| `base.html` | The document skeleton, annotated line by line |
| `app/list.html` | Index page: filters, table, pagination |
| `app/detail.html` | One record: facts, related sections, danger zone |
| `app/dashboard.html` | Stat row, content grid, recent activity |
| `app/form.html` | Single create/edit form |
| `app/wizard.html` | One step of a multi-step flow |
| `app/settings.html` | Tabbed settings area |
| `app/console.html` | Blank slate for a section with no data yet |
| `app/confirm.html` | Destructive-action confirmation |
| `auth/signin.html` | Sign in |
| `auth/signup.html` | Create an account |
| `auth/reset.html` | Request a password reset |
| `marketing/landing.html` | Product landing page |
| `marketing/pricing.html` | Pricing with tiers and FAQ |
| `marketing/about.html` | About page |

## The content is fake, and that is the point

Every example carries real, specific, plausible copy ("Invite teammates", "£29
/month", "Acme Corp"), never `Lorem ipsum` and never `{{ heading }}`. You can
see what the page looks like before you own it, and you replace the words
rather than working out what to put where.

Views are not shipped. Where an example needs data that only your project has
(a queryset, a form, a URL name), the template says so in a comment at the
point of use and uses an obvious placeholder you replace.

## They are tested

Each example is rendered in this package's CI through a standalone template
engine pointed at this directory, so an example that breaks against a component
change fails the build. That is the only supported way to render one; pointing
your project's own loaders here would rebuild the extendable-page contract
ADR-056 retires.
