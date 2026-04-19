# Next steps after the game-search redesign

Context: we reshaped the **Game Search** tab around a filter-driven
cards/table layout (player count + complexity chips, side-by-side filters,
inline collapse for details, search-summary chips per card, table with
fullscreen toggle). These notes capture what we agreed to build on top.

## 1. Apply the same pattern to the Predictions tab

Goal: bring the Predictions tab in line with Search — same filter chips,
same cards/table toggle, same inline detail expansion.

- Primary filters to consider: release window (e.g. upcoming/new),
  player count (best/rec), complexity bucket, predicted geek rating range.
- Sort dropdown should include the prediction fields (predicted geek
  rating, predicted users rated, predicted complexity, year published).
- Card body should reuse `create_game_info_card`; add a predictions-
  specific block showing predicted geek rating / complexity / users rated
  with uncertainty where available.
- Table view should reuse the AG Grid setup from Search, with a columns
  set tuned for predictions.
- Preserve the search-summary chips in each card header pattern so the
  current filter/sort context is always visible.

## 2. Game explainer module

Port the streamlit prototype (bgg-predictive-models
`src/streamlit/pages/5 Simulations.py`, Game Explorer tab) into the dash
viewer as a dedicated page.

Requirements locked in during prototyping:

- **Single-game selector** (not multi). No "Run" button — auto-fire on
  selection change. Cache results keyed on (game_id, samples).
- **Default game list** = new/upcoming games from the BGG warehouse,
  with a "Search any game" fallback that types ahead over the full
  catalog.
- **Max 500 simulation samples**.
- **Feature contribution plot**:
  - No red default for negative contributions. Sign via bar direction;
    color via hue-family muted version of the outcome color.
  - Sequential blues palette across the four outcomes
    (complexity / rating / users_rated / geek_rating), with geek_rating
    anchoring the dark end to signal it's the composite.
  - Clean feature labels: category prefix preserved, title-cased body,
    trailing noise (`_log`, `_transformed`, `_count`) stripped, feature
    value shown alongside (`Mechanic: Card Play Conflict Resolution = yes`,
    `Predicted Users Rated = 8.97`).
  - Tooltips at 2 decimals.
- **Posterior histogram panel**: same four-subplot layout, same
  sequential blues.

Open questions for the dash port:
- Whether to render inline on the game-detail collapse or as its own
  tab/route.
- Where the scoring service URL is configured and whether the dash
  viewer calls it directly or through an intermediate proxy.

## 3. BigQuery-backed game catalog for the explainer dropdown

The streamlit prototype sources the dropdown from a local simulation run
because the streamlit caller did not have `bigquery.jobs.create` on
`bgg-predictive-models`. In dash that constraint doesn't apply.

- Query `bgg-data-warehouse` for the catalog — the dash viewer already
  has the right credentials via the service account key in
  `credentials/service-account-key.json`.
- New/upcoming list: filter on `year_published >= CURRENT_YEAR` from
  `games_active` (or similar). Sort by predicted geek rating desc.
- Full catalog search: typeahead over `games_active.name`. Probably
  needs a prefix/suffix-tolerant search (server-side endpoint or a
  cached local list, depending on size).

## 4. Reusable card-layout configuration

`create_game_info_card` already takes toggles (`show_categories`,
`show_mechanics`, `show_families`, `show_player_count_rows`, etc.).
Extend this as we port other tabs so each tab can emphasize what's
relevant (e.g. Predictions might want to default-hide families but show
predicted-ratings rows).
