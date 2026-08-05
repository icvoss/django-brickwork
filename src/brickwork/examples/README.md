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

## What is here

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
