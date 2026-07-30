# Changelog

All notable changes to saas_ui are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning. Template block names, HTMX target IDs, Alpine component
names, event names and token names are treated as public API (see the spec's
versioning contract).

## [Unreleased]

### Added
- Repository scaffold: importable Django app skeleton (`src/saas_ui`),
  framework-neutral token sub-module stub (`saas_ui/tokens`), frontend build
  stub (Vite + `@tailwindcss/vite` + Style Dictionary, stable-filename output),
  smoke tests, and CI (Python green; frontend + accessibility/no-JS jobs
  stubbed for Phase 0). No components yet.
