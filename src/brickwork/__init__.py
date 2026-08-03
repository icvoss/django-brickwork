"""brickwork: a brand-agnostic, app-facing professional UI substrate for Django.

Provides the application shell, navigation and active-route resolution, an
accessible form-field renderer, and interaction primitives (modal, toast,
dropdown, combobox, tabs, disclosure) wrapped behind stable Django components,
on the ecosystem stack (Tailwind 4 CSS-first, Alpine 3, HTMX 2, Django 6.0).

This is NOT a Django-admin skin. Its value is the professional baseline:
WCAG 2.2 AA as a tested guarantee, RTL via logical properties, a real themeable
dark-mode system, and four composable theme axes (brand x theme x density x
direction). See docs/specs/django-brickwork/ in the icvoss/oss umbrella for the five
versioned public-API contracts (token, template, navigation, interaction,
JavaScript).

The design-token layer lives in the framework-neutral ``brickwork.tokens``
sub-module; a separate ``brickwork_tokens`` package is deferred until a
non-Django consumer earns the split.
"""

__version__ = "1.2.0"
