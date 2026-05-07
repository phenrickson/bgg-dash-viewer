# Collection Models Page — Design

## Goal

Wire up the "Collection Models" tile on the bgg-dash-viewer landing page (currently greyed out, `route: None`). The new page lets you pick a username and browse top upcoming games for that user's deployed collection model, mirroring the existing `/app/upcoming-predictions` page (cards + table dual view) but driven by user-specific predictions.

## Context

`bgg-predictive-models` already populates two tables in its `raw` dataset:

- `bgg-predictive-models.raw.collection_predictions_landing` — long-format predictions, one row per `(username, game_id, outcome, model_version, score_ts)`. Columns: `job_id, username, game_id, outcome, predicted_prob, predicted_label, threshold, model_name, model_version, score_ts`. Partitioned by `score_ts`, clustered by `(username, game_id)`.
- `bgg-predictive-models.raw.collection_models_registry` — registry, one row per `(username, outcome, model_version)`. Columns: `username, outcome, model_version, finalize_through_year, gcs_path, registered_at, status` (`status` is `active` / `inactive`).

The dash already consumes the global predictions via the warehouse table `predictions.bgg_predictions`, populated by `bgg-data-warehouse/definitions/bgg_predictions.sqlx`. This design follows that exact pattern for the per-user case: cross-project source declaration → incremental warehouse table → BigQuery client method → Dash page.

A registry row may exist with no landing rows yet (e.g. user enrolled, scoring job hasn't run). The dropdown shows only users that actually have predictions in the warehouse.

## Section 1 — Dataform (`bgg-data-warehouse`)

### 1a. Source declarations (`definitions/sources.js`)

Append two declarations alongside the existing `ml_predictions_landing` etc.:

```js
declare({ database: "bgg-predictive-models", schema: "raw", name: "collection_predictions_landing" });
declare({ database: "bgg-predictive-models", schema: "raw", name: "collection_models_registry" });
```

### 1b. New incremental table (`definitions/user_collection_predictions.sqlx`)

```sqlx
config {
  type: "incremental",
  schema: "predictions",
  name: "user_collection_predictions",
  uniqueKey: ["username", "game_id", "outcome"]
}

WITH active_models AS (
  SELECT username, outcome, model_version, finalize_through_year, registered_at
  FROM ${ref("bgg-predictive-models", "raw", "collection_models_registry")}
  WHERE status = 'active'
),
latest_per_user_outcome_game AS (
  SELECT
    p.username,
    p.game_id,
    p.outcome,
    p.predicted_prob,
    p.predicted_label,
    p.threshold,
    p.model_name,
    p.model_version,
    p.score_ts,
    p.job_id,
    ROW_NUMBER() OVER (
      PARTITION BY p.username, p.game_id, p.outcome
      ORDER BY p.score_ts DESC, p.job_id DESC
    ) AS rn
  FROM ${ref("bgg-predictive-models", "raw", "collection_predictions_landing")} p
  INNER JOIN active_models a
    ON  a.username      = p.username
    AND a.outcome       = p.outcome
    AND a.model_version = p.model_version
  WHERE TRUE
    ${when(incremental(), `AND p.score_ts > (SELECT MAX(score_ts) FROM ${self()})`)}
)
SELECT
  l.username,
  l.game_id,
  l.outcome,
  l.predicted_prob,
  l.predicted_label,
  l.threshold,
  l.model_name,
  l.model_version,
  l.score_ts,
  a.finalize_through_year,
  a.registered_at
FROM latest_per_user_outcome_game l
INNER JOIN active_models a USING (username, outcome, model_version)
WHERE l.rn = 1
```

Key choices:

- `uniqueKey: ["username", "game_id", "outcome"]` — incremental MERGE replaces stale rows when re-scores arrive.
- Inner-join on `active_models` filters out rows for inactive (superseded) model versions, so the warehouse only carries currently-deployed predictions.
- Dedup by `(username, game_id, outcome)` keeps only the latest `score_ts` per game.
- The incremental clause keys on `MAX(score_ts)` like `bgg_predictions.sqlx`.

### 1c. No backfill action required

Dataform's standard run will populate the table on first execution.

## Section 2 — Dash module (`bgg-dash-viewer`)

Separate page, mirroring the structure of the existing predictions module file-for-file. Naming aligns with the landing tile already in place ("Collection Models").

### 2a. Route + landing tile

- New route: `/app/collection-models`.
- `src/landing.py:44` — change the Collection Models tile from `"route": None` to `"route": "/app/collection-models"`. The "coming soon" greyed-out styling falls away automatically because it is driven by `route is None`.
- Register the route in `dash_app.py`.
- Add a nav-bar entry in `src/components/header.py` with label "Collection Models".

### 2b. Layout (`src/layouts/collection_models.py`)

Skeleton parallel to `src/layouts/upcoming_predictions.py`:

- Header + page header (title: "Collection Models", subtitle: "Personalized collection analysis and recommendations").
- Loading spinner during initial fetch.
- Content container populated by callback.
- `dcc.Store(id="collection-predictions-data-store")` for cached per-user data.

### 2c. Callbacks (`src/callbacks/collection_models_callbacks.py`)

Closely follow `upcoming_predictions_callbacks.py`. Three key differences:

1. **First page-load callback** populates the user dropdown from the warehouse and renders the filter bar shell. No predictions are fetched yet.
2. **Username dropdown callback** fetches predictions for the selected user (cached, 5-min TTL keyed on username) and renders the cards/table content.
3. Cards/table renderers reuse the existing patterns but show collection-model fields rather than universe-model fields.

Filter bar elements (left to right):

- **Username dropdown** — populated from `SELECT DISTINCT username FROM predictions.user_collection_predictions ORDER BY username`. Default value: `phenrickson` if present, else first alphabetically.
- **Publication Year** dropdown — same as existing page (`year_bucket`).
- **Min Predicted Prob** slider — analogous to the existing hurdle slider, default `0.25`, range `[0, 1]`.
- **Show without cover** toggle — preserved as-is.
- **Cards / Table** view toggle — preserved as-is.

Outcome dropdown is intentionally excluded for now (only `own` exists today). The Dataform table is long-format so adding outcomes later is purely a UI change — no warehouse migration required.

### 2d. Card body

Mirrors the existing tile but swaps the prediction stats:

- **Predicted Prob** badge — color-tiered like `_geek_color` (e.g. `>=0.9` elite, `>=0.75` success, `>=0.5` warning, lower neutral; final thresholds tuned during implementation against the actual distribution).
- **Predicted Label** badge — small yes/no badge derived from `predicted_label`.
- Cover art, title, year, click-to-open modal — all preserved.

The threshold value is **not** shown on individual cards; it surfaces only in the model-details accordion at the top of the page.

### 2e. Model-details accordion

Same shape as the existing page's "Model Details" accordion, populated for the active user:

- Model: `{model_name} v{model_version}`
- Threshold: `{threshold:.2f}`
- Finalize through year: `{finalize_through_year}`
- Registered at: `{registered_at}`
- Last scored: `MAX(score_ts)` for the user

### 2f. Modal

Reuses `render_details_body` with collection-specific labels:

- `rating_label="Predicted Prob"`, `rating_value=row.predicted_prob`
- Other slots set to `None` so the helper degrades gracefully.

### 2g. BigQuery client (`src/data/bigquery_client.py`)

Two new methods:

```python
def get_users_with_collection_models(self) -> list[str]:
    """SELECT DISTINCT username FROM predictions.user_collection_predictions ORDER BY username."""

def get_user_collection_predictions(
    self,
    username: str,
    min_year: int = 2025,
    limit: int = 20000,
) -> pd.DataFrame:
    """Inner-join user_collection_predictions to games_features on game_id,
    filter by username and year, return prediction columns plus the same
    games_features payload (thumbnail/name/year/categories/mechanics/etc.)
    that the existing predictions page consumes."""
```

`get_user_collection_predictions` returns the same game-feature columns as `get_latest_predictions_with_features` so the existing card renderer code can be reused with minimal changes. Heavy fields (`description`, `image`) are dropped before serializing into `dcc.Store`, matching the existing 32 MB Cloud Run cap protection.

## Section 3 — Edge cases & operational notes

- **Registry without landing rows** (e.g. `rahdo` today): users only appear in the dropdown when they have rows in `predictions.user_collection_predictions`. Effectively gates the UI on "deployed *and* has predictions." No special handling required.
- **Empty year filter result**: existing "No predictions match the current filters" empty state applies unchanged.
- **Cache key**: `cache.memoize` on the per-user fetch keyed on `username` (5-min TTL, matching existing predictions page). Initial dropdown population is a separate cached call.
- **Auth / authorization**: page sits behind the existing registration gate (`3aca4e9`). No per-user access control — anyone logged in can browse any user's predictions. Deferred until there is a reason to restrict.
- **Year floor**: `PREDICTIONS_MIN_YEAR = 2025` reused; older predictions stay in the warehouse but aren't fetched into the page.
- **Top-N per year cap**: same `PREDICTIONS_PER_YEAR = 1000` cap on the in-memory store payload, applied per `(year_bucket)` after sorting by `predicted_prob DESC`.

## Out of scope

- Outcome dropdown (only `own` ships today; design accommodates additions without warehouse change).
- Per-user authorization (everyone with viewer access sees every user).
- Backfill / migration scripts (Dataform incremental handles cold start).
- Surfacing model performance metrics (val/test) on the page — registry doesn't carry them today.
