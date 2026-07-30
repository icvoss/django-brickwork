"""In-repo test harness app for brickwork.

A minimal CRUD app (a Widget model + list/create/edit views + a form) that
renders through brickwork's shell, nav, page-header, data_table and form-field
components. It exists ONLY to exercise the contracts that need real
views/URLs/templates (the active-route resolver, the 422 HTMX form swap, the
no-JS full-page render) inside brickwork's own CI, without depending on the
pilot apps. It is NOT shipped and is installed only under settings_seams.py.
"""
