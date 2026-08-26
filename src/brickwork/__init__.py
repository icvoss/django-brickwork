"""brickwork: a brand-agnostic interface foundation for Django.

Owns reusable design across public sites, product applications, data-heavy
operations, documentation, editorial publishing and transactional journeys,
on the ecosystem stack (Tailwind 4 CSS-first, Alpine 3, HTMX 2, Django 6.0).

This is NOT a Django-admin skin. Consumers provide their domain data,
permissions and business behaviour; Brickwork provides the reusable interface
design on a professional, tested-accessible baseline: RTL via logical
properties, a real themeable dark-mode system, and four composable theme axes
(brand x theme x density x direction). See docs/specs/django-brickwork/ in the
icvoss/oss umbrella for the five versioned public-API contracts (token,
template, navigation, interaction, JavaScript).

The design-token layer lives in the framework-neutral ``brickwork.tokens``
sub-module; a separate ``brickwork_tokens`` package is deferred until a
non-Django consumer earns the split.
"""

__version__ = "3.11.0"
