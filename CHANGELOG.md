# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-04-30

### Added

- **Predictions page redesign** as an image-forward grid of cover-tile
  cards alongside the existing AG Grid table. New filter row holds
  Publication Year, a Min P(Hurdle) slider (default 0.25), a
  "Show without cover" switch (default off, hides games without art),
  and the Cards/Table toggle.
- Each prediction tile shows: cover image with rank pill, "NEW" badge
  for `is_new_7d` games, two-line title with ellipsis, year, and a 3+2
  grid of labeled stat badges — Geek, Average, Complexity (top row),
  Users, P(Hurdle) (bottom row). All five values come from the
  prediction columns, not BGG actuals.
- Click a tile → modal with the standardized `render_details_body`
  expansion, with stats relabeled and re-sourced as predictions
  (Predicted Geek / Predicted Average / Predicted Complexity /
  Predicted Users) so the modal stays consistent with the page intent.
- Tier-aware badge coloring per metric:
  - **Geek** (5-tier): secondary → light → warning → success →
    elite-dark-green (≥7.0)
  - **Average** (5-tier): same scale shifted up (success ≥8.0,
    elite-dark-green ≥8.5)
  - **Complexity** (5-tier diverging): blue → cyan → light → warning →
    red, so light gateway games and heavy strategy both pop visually
    while medium-weight stays neutral.
  - **P(Hurdle)** (3-tier): light → warning → success.
- Model Details accordion on the Predictions page now uses the same
  badge-row treatment as the embedding-model display on the Similar
  Games page (one row per model with name, version, experiment badges).
- **Explore Embeddings tab** on the Similar Games page switched from
  UMAP to PCA coordinates. Wired through `bgg_game_coordinates`
  (which now ships PCA columns alongside UMAP). Pre-selected 9
  recognizable games as default highlights — Ticket to Ride, Azul,
  Codenames, Chess, Twilight Struggle, Brass: Birmingham, Blood on
  the Clocktower, Crokinole, Gloomhaven — so users can orient
  themselves without typing a name.
- Hide the shared "Select a Game" search card on the Explore tab
  (it has its own controls). Drop axis ticks/lines/grid on the
  scatter and keep "Component 1" / "Component 2" titles; transparent
  background so the panel-card shows through; Viridis colorscale; cap
  height at 480px so the plot fits in viewport.
- Subtitle above the explorer plot: "Each point is a game. Games closer
  together share similar features — complexity, mechanics, categories,
  and play patterns."
- **Game Neighbors clickable cards**: each neighbor card on the Similar
  Games > Game Neighbors tab now opens an inline expansion on click,
  mirroring the Game Search pattern. The "Selected Game" source card is
  also clickable. Renders the standardized expanded body so designers,
  publishers, description, and full mechanic/family lists appear inline.
- HTML entities in game descriptions (`&mdash;`, `&rsquo;`, etc.) are
  now decoded via `html.unescape` before rendering, so the modal/inline
  expansion shows real characters instead of entity codes.
- `docs/plans/2026-04-30-embeddings-explainer-tab.md` proposing a 5th
  About tab on the Similar Games page — a layperson-targeted manual
  for embeddings (intro / scatter / worked example / under the hood /
  limitations) so a future agent has self-contained context.

### Changed

- `create_game_info_card` accepts `rating_label` / `rating_value` /
  `complexity_label` / `complexity_value` overrides so callers
  (Predictions) can render predicted rating/complexity in the same
  badge slots as actuals.
- `render_details_body` accepts the same family of overrides so modals
  on the Predictions page show predictions instead of actual BGG fields
  (which are pre-release noise for upcoming games).
- `_render_details_body` extracted out of `search_callbacks.py` into
  `src/components/game_details.py` so Game Search, Game Neighbors, and
  Predictions can share one renderer.
- Card thumbnail now vertically centered (align="center" on the Row);
  landscape box art was sitting at the top of its column leaving a
  vertical gap next to the info block.

### Fixed

- Highlight markers in the Explore Embeddings scatter now render on
  top of the base scatter blob (`go.Scattergl` instead of `go.Scatter`,
  so they sit in the same WebGL layer rather than getting occluded).
- Average-rating colorscale floor bumped from 4 to 5 (no real signal
  below 5 in the data).
- KPI strip (Games / Avg Predicted Rating / Median / Avg Complexity)
  removed from the Predictions page — not useful at-a-glance for
  browsing upcoming games.

### Misc

- Add `.claude/` and stray `nul` (Windows-style 2>nul redirect output)
  to `.gitignore`.

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
