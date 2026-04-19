# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-04-19

### Added

- Inline details collapse on game cards (replaces the details modal);
  one card expanded at a time
- Best/Recommended player-count rows on cards using the same green pill
  scheme as the AG Grid table
- Search-summary chips in each card header showing the active filters
  (player count, complexity bucket, year range) and sort
- Full Screen toggle on the table view that covers the viewport
- Search spinner/blur overlay now fires while the BigQuery query runs
- `docs/plans/2026-04-19-search-pattern-rollout.md` capturing next steps:
  Predictions tab rebuild, game explainer module, BigQuery-backed
  catalog dropdown, reusable card config

### Changed

- Primary filters (Player Count / Complexity) laid out side-by-side with
  Best/Rec stacked above the player-count chips
- Cover image in the expanded details capped at 240px so the text fills
  more of the row
- Designers/publishers/families in the expanded details capped with
  "+N more" overflow; designers/publishers got their own accent colors
- Table default height raised to `100vh - 180px`, default page size 50
- AG Grid `PlayerCountPills` renderer: tighter row gap so wrapped pills
  don't leave a big vertical gap, light-green for recommended-only
  instead of gray, top-aligned with sibling cells

### Fixed

- `dbc.Card` `n_clicks` incompatibility on dash-bootstrap-components 2.x
  by moving the clickable/id onto a wrapping `html.Div`

## [0.3.0] - 2025-01-23

### Added

- User authentication system with Flask-Login
- User registration and login pages
- Password hashing with bcrypt
- User storage in BigQuery (`core.users` table)
- Session management with signed cookies
- Auth tests with mocked BigQuery
- SECRET_KEY configuration for production deployment

### Changed

- Updated Cloud Run deployment to include SECRET_KEY environment variable

## [0.2.0] - Previous Release

- Initial dashboard viewer functionality
- BigQuery integration for game data
- Similarity search features
