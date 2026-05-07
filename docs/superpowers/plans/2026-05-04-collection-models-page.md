# Collection Models Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the greyed-out "Collection Models" tile on the bgg-dash-viewer landing page by landing per-user collection predictions in the data warehouse via Dataform and adding a new page that mirrors the existing Predictions module (cards + table dual view) with a username dropdown.

**Architecture:** New incremental Dataform model `predictions.user_collection_predictions` in `bgg-data-warehouse` that joins `bgg-predictive-models.raw.collection_predictions_landing` to the `collection_models_registry` (active rows only) and dedupes on latest `score_ts`. New `bgg-dash-viewer` page at `/app/collection-models` with a username dropdown that lazy-fetches per-user predictions joined to `games_features`, with the existing cards/table renderer reused with collection-specific stat fields.

**Tech Stack:** Dataform (SQLX) for warehouse; Python 3.12 + Dash + dash-bootstrap-components + dash-ag-grid + Polars/pandas + google-cloud-bigquery for the dashboard; pytest + unittest.mock for tests; `uv run pytest` for execution.

**Spec:** `docs/superpowers/specs/2026-05-04-collection-models-page-design.md`

**Repos involved:**
- `/Users/phenrickson/Documents/projects/bgg-data-warehouse` — Dataform changes
- `/Users/phenrickson/Documents/projects/bgg-dash-viewer` — page + client + nav

**Ordering constraint:** Task 1–3 (warehouse) must merge first. Task 4+ (dash viewer) depends on `predictions.user_collection_predictions` existing in BigQuery. The Dataform CI workflow runs on push to `main` and creates the table.

---

## Task 1: Declare cross-project sources in Dataform

**Files:**
- Modify: `/Users/phenrickson/Documents/projects/bgg-data-warehouse/definitions/sources.js`

The existing file already declares `bgg-predictive-models.raw.ml_predictions_landing` and friends; we follow the same pattern.

- [ ] **Step 1: Add two declare() calls**

Append at the bottom of [definitions/sources.js](/Users/phenrickson/Documents/projects/bgg-data-warehouse/definitions/sources.js), after the existing `game_coordinates` declaration:

```javascript
declare({
  database: "bgg-predictive-models",
  schema: "raw",
  name: "collection_predictions_landing"
});

declare({
  database: "bgg-predictive-models",
  schema: "raw",
  name: "collection_models_registry"
});
```

- [ ] **Step 2: Commit**

```bash
cd /Users/phenrickson/Documents/projects/bgg-data-warehouse
git add definitions/sources.js
git commit -m "Declare collection predictions/registry sources from bgg-predictive-models"
```

---

## Task 2: Create the user_collection_predictions Dataform model

**Files:**
- Create: `/Users/phenrickson/Documents/projects/bgg-data-warehouse/definitions/user_collection_predictions.sqlx`

This mirrors the structure of [definitions/bgg_predictions.sqlx](/Users/phenrickson/Documents/projects/bgg-data-warehouse/definitions/bgg_predictions.sqlx): incremental, deduped via `ROW_NUMBER`, with `${when(incremental(), ...)}` keyed on `MAX(score_ts)`. Adds an inner-join to the registry filtered to `status = 'active'` so only currently-deployed `(username, outcome, model_version)` predictions land.

- [ ] **Step 1: Write the SQLX file**

Create [definitions/user_collection_predictions.sqlx](/Users/phenrickson/Documents/projects/bgg-data-warehouse/definitions/user_collection_predictions.sqlx) with:

```sqlx
config {
  type: "incremental",
  schema: "predictions",
  name: "user_collection_predictions",
  uniqueKey: ["username", "game_id", "outcome"]
}

WITH active_models AS (
  SELECT
    username,
    outcome,
    model_version,
    finalize_through_year,
    registered_at
  FROM ${ref("bgg-predictive-models", "raw", "collection_models_registry")}
  WHERE status = 'active'
),
landing_for_active AS (
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
FROM landing_for_active l
INNER JOIN active_models a USING (username, outcome, model_version)
WHERE l.rn = 1
```

- [ ] **Step 2: Commit**

```bash
cd /Users/phenrickson/Documents/projects/bgg-data-warehouse
git add definitions/user_collection_predictions.sqlx
git commit -m "Add user_collection_predictions: per-(user, game, outcome) latest-active predictions"
```

---

## Task 3: Verify Dataform output in BigQuery

This task is run **after** Tasks 1–2 are pushed to `main` and the GitHub Actions Dataform workflow has completed.

- [ ] **Step 1: Push the warehouse branch and wait for CI**

```bash
cd /Users/phenrickson/Documents/projects/bgg-data-warehouse
git push
```

Then watch the run via `gh run watch` (or in the Actions tab) until the "Run Dataform" workflow finishes for the merged commit.

- [ ] **Step 2: Run `use-personal` and verify the table exists**

```bash
use-personal
bq show --schema --format=prettyjson bgg-data-warehouse:predictions.user_collection_predictions | head -60
```

Expected: schema lists `username`, `game_id`, `outcome`, `predicted_prob`, `predicted_label`, `threshold`, `model_name`, `model_version`, `score_ts`, `finalize_through_year`, `registered_at`.

- [ ] **Step 3: Spot-check row counts vs the source landing table**

```bash
bq query --use_legacy_sql=false --format=prettyjson --max_rows=20 'SELECT username, outcome, model_version, COUNT(*) AS n FROM `bgg-data-warehouse.predictions.user_collection_predictions` GROUP BY 1,2,3 ORDER BY 1,2,3'
```

Expected: row counts roughly match the active-status entries from `collection_models_registry` × games scored. Inactive registry rows should not appear.

- [ ] **Step 4: Confirm dedup**

```bash
bq query --use_legacy_sql=false --format=prettyjson 'SELECT COUNT(*) AS total, COUNT(DISTINCT FORMAT("%s|%d|%s", username, game_id, outcome)) AS distinct_keys FROM `bgg-data-warehouse.predictions.user_collection_predictions`'
```

Expected: `total == distinct_keys`. If not, the dedup `ROW_NUMBER` filter is broken.

If any check fails, return to Task 2 to fix the SQLX before proceeding.

---

## Task 4: Add `get_users_with_collection_models()` to BigQueryClient (TDD)

**Files:**
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/data/bigquery_client.py`
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/tests/test_bigquery_client.py`

This method returns the list of usernames that have at least one row in `predictions.user_collection_predictions`. It powers the username dropdown.

- [ ] **Step 1: Write the failing test**

Append to [tests/test_bigquery_client.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/tests/test_bigquery_client.py), inside `class TestBigQueryClient`:

```python
def test_get_users_with_collection_models_returns_sorted_usernames(self):
    """Returns DISTINCT usernames from user_collection_predictions, alphabetically."""
    mock_query_job = MagicMock()
    mock_dataframe = pd.DataFrame({"username": ["GOBBluth89", "TomBrewstErr", "phenrickson"]})
    mock_query_job.to_dataframe.return_value = mock_dataframe
    self.mock_client_instance.query.return_value = mock_query_job

    result = self.bq_client.get_users_with_collection_models()

    self.assertEqual(result, ["GOBBluth89", "TomBrewstErr", "phenrickson"])
    # Verify the query targets the right table.
    call_args = self.mock_client_instance.query.call_args
    query_text = call_args[0][0]
    self.assertIn("predictions.user_collection_predictions", query_text)
    self.assertIn("DISTINCT", query_text.upper())
    self.assertIn("ORDER BY", query_text.upper())

def test_get_users_with_collection_models_empty(self):
    """Returns empty list when there are no rows."""
    mock_query_job = MagicMock()
    mock_query_job.to_dataframe.return_value = pd.DataFrame({"username": []})
    self.mock_client_instance.query.return_value = mock_query_job

    result = self.bq_client.get_users_with_collection_models()

    self.assertEqual(result, [])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/phenrickson/Documents/projects/bgg-dash-viewer
uv run pytest tests/test_bigquery_client.py::TestBigQueryClient::test_get_users_with_collection_models_returns_sorted_usernames tests/test_bigquery_client.py::TestBigQueryClient::test_get_users_with_collection_models_empty -v
```

Expected: FAIL with `AttributeError: 'BigQueryClient' object has no attribute 'get_users_with_collection_models'`.

- [ ] **Step 3: Implement the method**

Append to the `BigQueryClient` class in [src/data/bigquery_client.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/data/bigquery_client.py), after `get_predictions_summary_stats`:

```python
def get_users_with_collection_models(self) -> List[str]:
    """List usernames with at least one row in user_collection_predictions.

    Powers the username dropdown on the Collection Models page. Sorted
    alphabetically for stable UI.
    """
    query = """
    SELECT DISTINCT username
    FROM `${project_id}.predictions.user_collection_predictions`
    ORDER BY username
    """
    df = self.execute_query(query)
    if df.empty:
        return []
    return df["username"].tolist()
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_bigquery_client.py::TestBigQueryClient::test_get_users_with_collection_models_returns_sorted_usernames tests/test_bigquery_client.py::TestBigQueryClient::test_get_users_with_collection_models_empty -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/data/bigquery_client.py tests/test_bigquery_client.py
git commit -m "Add BigQueryClient.get_users_with_collection_models for dropdown"
```

---

## Task 5: Add `get_user_collection_predictions()` to BigQueryClient (TDD)

**Files:**
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/data/bigquery_client.py`
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/tests/test_bigquery_client.py`

Returns predictions for one user joined to `games_features`. Mirrors the column set used by `get_latest_predictions_with_features` so the existing card renderer code can be reused with minimal field swaps.

- [ ] **Step 1: Write the failing test**

Append to `class TestBigQueryClient` in [tests/test_bigquery_client.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/tests/test_bigquery_client.py):

```python
def test_get_user_collection_predictions_filters_and_joins(self):
    """Returns user-filtered predictions joined to games_features."""
    mock_query_job = MagicMock()
    mock_df = pd.DataFrame({
        "game_id": [1, 2],
        "name": ["A", "B"],
        "year_published": [2025, 2026],
        "predicted_prob": [0.9, 0.7],
        "predicted_label": [True, False],
        "threshold": [0.5, 0.5],
        "model_name": ["m", "m"],
        "model_version": [1, 1],
        "score_ts": pd.to_datetime(["2026-05-01", "2026-05-01"]),
        "thumbnail": ["t1", "t2"],
        "image": ["i1", "i2"],
        "categories": [[], []],
        "mechanics": [[], []],
        "families": [[], []],
        "designers": [[], []],
        "publishers": [[], []],
    })
    mock_query_job.to_dataframe.return_value = mock_df
    self.mock_client_instance.query.return_value = mock_query_job

    result = self.bq_client.get_user_collection_predictions(
        username="phenrickson", min_year=2025, limit=20000
    )

    self.assertEqual(len(result), 2)
    call_args = self.mock_client_instance.query.call_args
    query_text = call_args[0][0]
    self.assertIn("predictions.user_collection_predictions", query_text)
    self.assertIn("games_features", query_text)
    self.assertIn("@username", query_text)
    self.assertIn("gf.year_published >= 2025", query_text)
    self.assertIn("LIMIT 20000", query_text)
    # Ensure the username goes through as a query parameter.
    job_config = call_args.kwargs.get("job_config") or call_args[1]["job_config"]
    params = {p.name: p.value for p in job_config.query_parameters}
    self.assertEqual(params.get("username"), "phenrickson")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_bigquery_client.py::TestBigQueryClient::test_get_user_collection_predictions_filters_and_joins -v
```

Expected: FAIL with `AttributeError: 'BigQueryClient' object has no attribute 'get_user_collection_predictions'`.

- [ ] **Step 3: Implement the method**

Append to `BigQueryClient` in [src/data/bigquery_client.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/data/bigquery_client.py), after `get_users_with_collection_models`:

```python
def get_user_collection_predictions(
    self,
    username: str,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    limit: int = 20000,
) -> pd.DataFrame:
    """Per-user collection predictions joined to games_features.

    Inner-join (since we only want games we have features for) on
    `game_id`. The returned columns include the prediction fields
    (predicted_prob/predicted_label/threshold/model_name/model_version/
    score_ts) plus the same games_features payload returned by
    get_latest_predictions_with_features so the existing card renderer
    can be reused with minimal swaps.

    Args:
        username: BGG username — the row filter for predictions.
        min_year: Optional inclusive lower bound on year_published.
        max_year: Optional inclusive upper bound on year_published.
        limit: Maximum rows to return (defaults to 20_000).
    """
    year_filters = []
    if min_year is not None:
        year_filters.append(f"p.year_published >= {min_year}")
    if max_year is not None:
        year_filters.append(f"p.year_published <= {max_year}")

    extra_filters = ""
    if year_filters:
        extra_filters = " AND " + " AND ".join(year_filters)

    query = f"""
    SELECT
        p.game_id,
        p.username,
        p.outcome,
        p.predicted_prob,
        p.predicted_label,
        p.threshold,
        p.model_name,
        p.model_version,
        p.score_ts,
        p.finalize_through_year,
        gf.name,
        gf.year_published,
        gf.thumbnail,
        gf.image,
        gf.description,
        gf.bayes_average,
        gf.average_rating,
        gf.average_weight,
        gf.users_rated,
        gf.min_players,
        gf.max_players,
        gf.min_playtime,
        gf.max_playtime,
        gf.categories,
        gf.mechanics,
        gf.families,
        gf.designers,
        gf.publishers
    FROM `${{project_id}}.predictions.user_collection_predictions` p
    INNER JOIN `${{project_id}}.${{dataset}}.games_features` gf
        ON p.game_id = gf.game_id
    WHERE p.username = @username{extra_filters}
    ORDER BY p.predicted_prob DESC
    LIMIT {limit}
    """
    return self.execute_query(query, params={"username": username})
```

Note: the assertion in Step 1 references `p.year_published >= 2025`. Since `year_published` actually lives on `games_features`, the column qualifier here is `gf.year_published`. Update the test assertion accordingly:

Replace `"p.year_published >= 2025"` in Step 1 with `"gf.year_published >= 2025"`. (If you reach this step before fixing the test, fix it now and rerun.)

Also append to the existing `_get_param_type` helper coverage if needed — string params are already supported.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/test_bigquery_client.py::TestBigQueryClient::test_get_user_collection_predictions_filters_and_joins -v
```

Expected: 1 passed. If the test still fails on the year filter assertion, ensure both the test and the implementation use the `gf.year_published` qualifier.

- [ ] **Step 5: Commit**

```bash
git add src/data/bigquery_client.py tests/test_bigquery_client.py
git commit -m "Add BigQueryClient.get_user_collection_predictions for per-user predictions"
```

---

## Task 6: Build the Collection Models page layout

**Files:**
- Create: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/layouts/collection_models.py`

This is a static skeleton mirroring [src/layouts/upcoming_predictions.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/layouts/upcoming_predictions.py). The callbacks fill in everything inside `collection-models-page-content`.

- [ ] **Step 1: Create the layout file**

```python
"""Layout for the Collection Models page (per-user collection predictions)."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


def create_collection_models_layout():
    """Create the layout for the Collection Models page.

    Renders the page chrome (header, page header, footer, modal) and
    delegates the inner content (filter bar, cards/table grid) to
    callbacks via `collection-models-page-content`.
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    create_page_header(
                        "Collection Models",
                        "Personalized collection analysis and recommendations",
                    ),
                    create_spinner(html.Div(id="collection-models-page-loading")),
                    html.Div(id="collection-models-page-content"),
                    dcc.Store(id="collection-models-data-store"),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/layouts/collection_models.py
git commit -m "Add Collection Models page layout skeleton"
```

---

## Task 7: Wire up the route in `dash_app.py` and the nav header

**Files:**
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/dash_app.py`
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/components/header.py`

- [ ] **Step 1: Add the route in `display_page`**

In [dash_app.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/dash_app.py), inside `display_page` around line 175–202, add the import and the route branch. Insert the import next to the existing layout imports (after `create_game_similarity_layout`):

```python
    from src.layouts.collection_models import create_collection_models_layout
```

Then, in the `if/elif` chain (just before the `pathname.startswith("/app/game/")` branch around line 203), add:

```python
    elif pathname == "/app/collection-models":
        return create_collection_models_layout()
```

- [ ] **Step 2: Add the nav link in the header**

In [src/components/header.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/components/header.py:33), add a NavItem for Collection Models. Insert it after the "Predictions" nav item (currently `dbc.NavItem(dbc.NavLink("Predictions", href="/app/upcoming-predictions"))`):

```python
                                    dbc.NavItem(dbc.NavLink("Collection Models", href="/app/collection-models")),
```

- [ ] **Step 3: Smoke-check the import wiring**

```bash
cd /Users/phenrickson/Documents/projects/bgg-dash-viewer
uv run python -c "from src.layouts.collection_models import create_collection_models_layout; print(create_collection_models_layout() is not None)"
```

Expected: `True`.

- [ ] **Step 4: Commit**

```bash
git add dash_app.py src/components/header.py
git commit -m "Route /app/collection-models and add navbar link"
```

---

## Task 8: Build the Collection Models callbacks

**Files:**
- Create: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/callbacks/collection_models_callbacks.py`

This is the largest task. Layout follows [src/callbacks/upcoming_predictions_callbacks.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/callbacks/upcoming_predictions_callbacks.py) closely; we adapt the renderers to show `predicted_prob` + `predicted_label` instead of geek/complexity/hurdle stats, and we add a username dropdown that drives a per-user data fetch.

- [ ] **Step 1: Create the callbacks file with module-level helpers**

```python
"""Callbacks for the Collection Models page."""

from datetime import datetime
from typing import Any

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from ..components.ag_grid_config import (
    get_default_column_def,
    get_default_grid_options,
    get_grid_class_name,
    get_grid_style,
)
from ..components.game_details import render_details_body
from ..data.bigquery_client import BigQueryClient

CARDS_PER_PAGE = 24
PREDICTIONS_MIN_YEAR = 2025
PREDICTIONS_PER_YEAR = 1000

_bq_client: BigQueryClient | None = None


def get_bq_client() -> BigQueryClient:
    """Lazy BigQuery client, mirroring the existing predictions module."""
    global _bq_client
    if _bq_client is None:
        _bq_client = BigQueryClient()
    return _bq_client


def _prob_color(value: float | None) -> tuple[str, str | None, str | None]:
    """Color a Predicted Prob badge by tier.

    Returns (bootstrap_color, text_color, bg_override). Tiers chosen to
    visually separate "almost certainly add" (>=0.9), "likely" (>=0.75),
    "borderline" (>=0.5), and "unlikely" (<0.5). Tune against the actual
    distribution if needed.
    """
    if value is None or pd.isna(value):
        return "light", "dark", None
    if value >= 0.9:
        return "success", None, "#1e7e34"
    if value >= 0.75:
        return "success", None, None
    if value >= 0.5:
        return "warning", "dark", None
    return "secondary", None, None


def _fmt(value: Any, fmt: str) -> str:
    try:
        return format(value, fmt) if value is not None and not pd.isna(value) else "—"
    except (TypeError, ValueError):
        return "—"
```

- [ ] **Step 2: Add the cards renderer**

Append to the same file:

```python
def _render_cards(records: list[dict[str, Any]], page: int) -> html.Div:
    """Render a paginated grid of cover-image tiles for collection predictions."""
    total = len(records)
    if total == 0:
        return html.Div(
            "No predictions match the current filters.",
            className="text-muted text-center py-4",
        )

    page_size = CARDS_PER_PAGE
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    page_records = records[start:start + page_size]

    title_clamp_style = {
        "display": "-webkit-box",
        "WebkitLineClamp": "2",
        "WebkitBoxOrient": "vertical",
        "overflow": "hidden",
        "fontSize": "0.95rem",
        "lineHeight": "1.2",
        "minHeight": "2.4em",
    }

    tiles = []
    for i, row in enumerate(page_records):
        game_id = row.get("game_id")
        rank = start + i + 1
        thumbnail = row.get("thumbnail") or row.get("image") or ""
        name = row.get("name", "Unknown")
        year = row.get("year_published")
        year_str = f"({int(year)})" if year and not pd.isna(year) else ""

        prob_value = row.get("predicted_prob")
        prob_str = _fmt(prob_value, ".0%")
        bs_color, text_color, bg_override = _prob_color(prob_value)
        prob_badge_style = {
            "fontSize": "0.85rem",
            "padding": "0.35em 0.55em",
            "fontWeight": "bold",
        }
        if bg_override:
            prob_badge_style["backgroundColor"] = bg_override
            prob_badge_style["color"] = "white"

        label_value = bool(row.get("predicted_label"))
        label_text = "YES" if label_value else "NO"
        label_color = "success" if label_value else "secondary"

        rank_badge = dbc.Badge(
            f"#{rank}",
            color="dark",
            className="position-absolute",
            style={
                "top": "8px",
                "left": "8px",
                "fontSize": "0.85rem",
                "padding": "0.4em 0.6em",
                "opacity": "0.9",
            },
        )

        image_block = html.Div(
            [
                html.Img(
                    src=thumbnail,
                    style={
                        "width": "100%",
                        "aspectRatio": "1 / 1",
                        "objectFit": "cover",
                        "borderRadius": "6px 6px 0 0",
                    },
                ) if thumbnail else html.Div(
                    style={
                        "width": "100%",
                        "aspectRatio": "1 / 1",
                        "background": "rgba(255,255,255,0.05)",
                        "borderRadius": "6px 6px 0 0",
                    },
                ),
                rank_badge,
            ],
            className="position-relative",
        )

        body = html.Div(
            [
                html.Div(name, className="fw-bold", title=name, style=title_clamp_style),
                html.Small(year_str, className="text-muted d-block mb-2"),
                html.Hr(className="my-2"),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Small(
                                        "Predicted Prob",
                                        className="text-muted d-block",
                                        style={"fontSize": "0.7rem", "lineHeight": "1"},
                                    ),
                                    dbc.Badge(
                                        prob_str,
                                        color=bs_color if not bg_override else None,
                                        text_color=text_color if not bg_override else None,
                                        className="mt-1",
                                        style=prob_badge_style,
                                    ),
                                ],
                                className="text-center",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Small(
                                        "Label",
                                        className="text-muted d-block",
                                        style={"fontSize": "0.7rem", "lineHeight": "1"},
                                    ),
                                    dbc.Badge(
                                        label_text,
                                        color=label_color,
                                        className="mt-1",
                                        style={
                                            "fontSize": "0.85rem",
                                            "padding": "0.35em 0.55em",
                                            "fontWeight": "bold",
                                        },
                                    ),
                                ],
                                className="text-center",
                            ),
                            width=6,
                        ),
                    ],
                    className="g-1",
                ),
            ],
            className="p-2",
        )

        tile = html.Div(
            dbc.Card([image_block, body], className="panel-card h-100"),
            id={"type": "collection-prediction-card", "game_id": game_id},
            style={"cursor": "pointer"},
            n_clicks=0,
            className="h-100",
        )
        tiles.append(dbc.Col(tile, xs=12, sm=6, md=4, lg=3, xl=2, className="mb-3"))

    grid = dbc.Row(tiles, className="g-3")
    pagination = dbc.Pagination(
        id="collection-models-cards-pagination",
        max_value=total_pages,
        active_page=page,
        first_last=True,
        previous_next=True,
        fully_expanded=False,
        size="sm",
        className="mt-3",
    ) if total_pages > 1 else html.Div()

    return html.Div([grid, pagination])
```

- [ ] **Step 3: Add the table renderer**

Append:

```python
def _render_table(df: pd.DataFrame) -> html.Div:
    """AG Grid table view for the same data."""
    display_columns = [
        "game_id",
        "name",
        "year_published",
        "predicted_prob",
        "predicted_label",
        "threshold",
        "model_name",
        "model_version",
        "score_ts",
    ]
    display_columns = [c for c in display_columns if c in df.columns]

    column_defs = [
        {"field": "game_id", "headerName": "ID", "width": 90, "filter": "agNumberColumnFilter"},
        {"field": "name", "headerName": "Name", "flex": 2, "filter": "agTextColumnFilter"},
        {"field": "year_published", "headerName": "Year", "width": 90, "filter": "agNumberColumnFilter"},
        {
            "field": "predicted_prob",
            "headerName": "Predicted Prob",
            "width": 140,
            "filter": "agNumberColumnFilter",
            "valueFormatter": {"function": "params.value == null ? '' : (params.value * 100).toFixed(1) + '%'"},
        },
        {"field": "predicted_label", "headerName": "Label", "width": 100, "filter": "agSetColumnFilter"},
        {
            "field": "threshold",
            "headerName": "Threshold",
            "width": 110,
            "filter": "agNumberColumnFilter",
            "valueFormatter": {"function": "params.value == null ? '' : params.value.toFixed(2)"},
        },
        {"field": "model_name", "headerName": "Model", "flex": 1, "filter": "agTextColumnFilter"},
        {"field": "model_version", "headerName": "v", "width": 70, "filter": "agNumberColumnFilter"},
        {"field": "score_ts", "headerName": "Scored At", "width": 170},
    ]

    grid_options = get_default_grid_options()
    grid_options["paginationPageSize"] = 100

    return dag.AgGrid(
        id="collection-models-table",
        rowData=df[display_columns].to_dict("records"),
        columnDefs=column_defs,
        defaultColDef=get_default_column_def(),
        dashGridOptions=grid_options,
        className=get_grid_class_name(),
        style=get_grid_style("600px"),
    )
```

- [ ] **Step 4: Add the registration function (page-load + dropdown population)**

Append:

```python
def register_collection_models_callbacks(app, cache):
    """Register all callbacks for the Collection Models page."""

    @cache.memoize(timeout=300)
    def _load_users_cached() -> list[str]:
        try:
            return get_bq_client().get_users_with_collection_models()
        except Exception as exc:  # noqa: BLE001 — BQ failure surfaced as empty UI
            print(f"Error loading collection-models users: {exc}")
            return []

    @cache.memoize(timeout=300)
    def _load_user_predictions_cached(username: str) -> list[dict]:
        try:
            df = get_bq_client().get_user_collection_predictions(
                username=username, min_year=PREDICTIONS_MIN_YEAR, limit=20000
            )
            if df.empty:
                return []
            df["year_bucket"] = df["year_published"].apply(
                lambda x: "Other" if pd.isna(x) or x < 2020 else str(int(x))
            )
            for col in ("categories", "mechanics", "families", "designers", "publishers"):
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda v: list(v) if v is not None and len(v) > 0 else []
                    )
            df = (
                df.sort_values("predicted_prob", ascending=False)
                .groupby("year_bucket", group_keys=False)
                .head(PREDICTIONS_PER_YEAR)
                .reset_index(drop=True)
            )
            for col in ("description", "image"):
                if col in df.columns:
                    df = df.drop(columns=[col])
            return df.to_dict("records")
        except Exception as exc:  # noqa: BLE001
            print(f"Error loading predictions for '{username}': {exc}")
            return []

    @app.callback(
        [
            Output("collection-models-page-content", "children"),
            Output("collection-models-page-loading", "children"),
        ],
        Input("url", "pathname"),
    )
    def render_page_shell(pathname: str):
        if pathname != "/app/collection-models":
            raise PreventUpdate

        users = _load_users_cached()
        if not users:
            return (
                html.Div(
                    "No collection models are deployed yet.",
                    className="text-muted text-center py-4",
                ),
                "",
            )

        default_user = "phenrickson" if "phenrickson" in users else users[0]
        user_options = [{"label": u, "value": u} for u in users]

        page_content = html.Div(
            [
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("User", className="mb-2"),
                                            dcc.Dropdown(
                                                id="collection-models-user-dropdown",
                                                options=user_options,
                                                value=default_user,
                                                clearable=False,
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Publication Year", className="mb-2"),
                                            dcc.Dropdown(
                                                id="collection-models-year-dropdown",
                                                options=[],
                                                clearable=False,
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Min Predicted Prob", className="mb-2"),
                                            dcc.Slider(
                                                id="collection-models-prob-slider",
                                                min=0.0,
                                                max=1.0,
                                                step=0.05,
                                                value=0.25,
                                                marks={0: "0", 0.5: "0.5", 1: "1"},
                                                tooltip={"placement": "bottom", "always_visible": False},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Cover art", className="mb-2 d-block"),
                                            dbc.Switch(
                                                id="collection-models-show-no-cover",
                                                label="Show without cover",
                                                value=False,
                                                className="mt-1",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Div(
                                                dbc.ButtonGroup(
                                                    [
                                                        dbc.Button(
                                                            [html.I(className="fas fa-th-large me-2"), "Cards"],
                                                            id="collection-models-view-toggle-cards",
                                                            color="primary",
                                                            outline=False,
                                                            size="sm",
                                                        ),
                                                        dbc.Button(
                                                            [html.I(className="fas fa-table me-2"), "Table"],
                                                            id="collection-models-view-toggle-table",
                                                            color="primary",
                                                            outline=True,
                                                            size="sm",
                                                        ),
                                                    ],
                                                ),
                                                className="d-flex justify-content-end align-items-end h-100",
                                            ),
                                            dcc.Store(id="collection-models-view-toggle", data="cards"),
                                        ],
                                        width=2,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(id="collection-models-summary", className="mb-3"),
                            dbc.Spinner(
                                html.Div(id="collection-models-content"),
                                color="primary",
                                type="border",
                            ),
                            dcc.Store(id="collection-models-cards-page", data=1),
                        ]
                    ),
                    className="panel-card",
                ),
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle(id="collection-models-modal-title")),
                        dbc.ModalBody(id="collection-models-modal-body"),
                    ],
                    id="collection-models-modal",
                    size="lg",
                    is_open=False,
                    scrollable=True,
                ),
            ]
        )

        return page_content, ""
```

- [ ] **Step 5: Add the per-user data callback**

Append (still inside `register_collection_models_callbacks`):

```python
    @app.callback(
        [
            Output("collection-models-data-store", "data"),
            Output("collection-models-year-dropdown", "options"),
            Output("collection-models-year-dropdown", "value"),
            Output("collection-models-summary", "children"),
        ],
        Input("collection-models-user-dropdown", "value"),
    )
    def load_user_data(username: str | None):
        if not username:
            raise PreventUpdate

        records = _load_user_predictions_cached(username)
        if not records:
            return [], [], None, html.Div(
                f"No predictions for user '{username}'.",
                className="text-muted",
            )

        df = pd.DataFrame(records)
        years = sorted(
            df["year_bucket"].unique(),
            key=lambda x: (x == "Other", x),
            reverse=True,
        )
        year_options = [{"label": y, "value": y} for y in years]
        current_year = str(datetime.now().year)
        if current_year in years:
            default_year = current_year
        else:
            numeric = [int(y) for y in years if y != "Other"]
            default_year = str(max(numeric)) if numeric else (years[0] if years else None)

        # Compact summary line.
        latest_ts = df["score_ts"].max() if "score_ts" in df.columns else None
        latest_str = pd.to_datetime(latest_ts).strftime("%Y-%m-%d") if latest_ts is not None else "—"
        model_name = df["model_name"].iloc[0] if "model_name" in df.columns and len(df) else "—"
        model_version = df["model_version"].iloc[0] if "model_version" in df.columns and len(df) else "—"
        threshold = df["threshold"].iloc[0] if "threshold" in df.columns and len(df) else None
        threshold_str = _fmt(threshold, ".2f")

        summary = html.Div(
            [
                html.Span(f"{len(df):,} games", className="me-3"),
                html.Span(f"Model: {model_name} v{model_version}", className="me-3"),
                html.Span(f"Threshold: {threshold_str}", className="me-3"),
                html.Span(f"Last scored: {latest_str}"),
            ],
            className="text-muted small",
        )

        return records, year_options, default_year, summary
```

- [ ] **Step 6: Add the year/view/page filter + content callback**

Append:

```python
    @app.callback(
        Output("collection-models-content", "children"),
        [
            Input("collection-models-year-dropdown", "value"),
            Input("collection-models-view-toggle", "data"),
            Input("collection-models-cards-page", "data"),
            Input("collection-models-prob-slider", "value"),
            Input("collection-models-show-no-cover", "value"),
        ],
        State("collection-models-data-store", "data"),
    )
    def update_content(
        selected_year: str | None,
        view_mode: str,
        page: int | None,
        min_prob: float | None,
        show_no_cover: bool | None,
        records: list[dict] | None,
    ):
        if not records or not selected_year:
            raise PreventUpdate

        df = pd.DataFrame(records)
        filtered = df[df["year_bucket"] == selected_year].copy()

        if min_prob is not None and min_prob > 0:
            filtered = filtered[filtered["predicted_prob"].fillna(0) >= min_prob]

        if not show_no_cover and "thumbnail" in filtered.columns:
            filtered = filtered[
                filtered["thumbnail"].notna() & (filtered["thumbnail"] != "")
            ]

        if filtered.empty:
            return html.Div(
                "No predictions match the current filters.",
                className="text-muted text-center",
            )

        filtered = filtered.sort_values("predicted_prob", ascending=False).reset_index(drop=True)

        if view_mode == "table":
            return _render_table(filtered)
        return _render_cards(filtered.to_dict("records"), page=page or 1)
```

- [ ] **Step 7: Add the view-toggle, pagination, and modal callbacks**

Append (still inside the registration function):

```python
    @app.callback(
        [
            Output("collection-models-view-toggle", "data"),
            Output("collection-models-view-toggle-cards", "outline"),
            Output("collection-models-view-toggle-table", "outline"),
        ],
        [
            Input("collection-models-view-toggle-cards", "n_clicks"),
            Input("collection-models-view-toggle-table", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def toggle_view(_cards_clicks, _table_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return "cards", False, True
        triggered = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered == "collection-models-view-toggle-table":
            return "table", True, False
        return "cards", False, True

    @app.callback(
        Output("collection-models-cards-page", "data"),
        Input("collection-models-cards-pagination", "active_page"),
        prevent_initial_call=True,
    )
    def update_page(active_page):
        return active_page or 1

    @app.callback(
        Output("collection-models-cards-page", "data", allow_duplicate=True),
        [
            Input("collection-models-year-dropdown", "value"),
            Input("collection-models-user-dropdown", "value"),
        ],
        prevent_initial_call=True,
    )
    def reset_page_on_change(_year, _user):
        return 1

    @app.callback(
        [
            Output("collection-models-modal", "is_open"),
            Output("collection-models-modal-title", "children"),
            Output("collection-models-modal-body", "children"),
        ],
        Input({"type": "collection-prediction-card", "game_id": dash.ALL}, "n_clicks"),
        State("collection-models-data-store", "data"),
        prevent_initial_call=True,
    )
    def open_modal(n_clicks_list, records):
        ctx = dash.callback_context
        if not ctx.triggered_id or not any(n_clicks_list):
            return dash.no_update, dash.no_update, dash.no_update

        clicked_id = ctx.triggered_id["game_id"]
        if not records:
            return dash.no_update, dash.no_update, dash.no_update

        row = next((r for r in records if r.get("game_id") == clicked_id), None)
        if row is None:
            return dash.no_update, dash.no_update, dash.no_update

        name = row.get("name", "Unknown")
        year = row.get("year_published")
        year_str = f" ({int(year)})" if year and not pd.isna(year) else ""
        title = f"{name}{year_str}"

        return True, title, render_details_body(
            row,
            rating_label="Predicted Prob",
            rating_value=row.get("predicted_prob"),
        )
```

- [ ] **Step 8: Smoke-check the import**

```bash
cd /Users/phenrickson/Documents/projects/bgg-dash-viewer
uv run python -c "from src.callbacks.collection_models_callbacks import register_collection_models_callbacks; print(register_collection_models_callbacks is not None)"
```

Expected: `True`. If `render_details_body`'s signature does not accept the kwargs we pass, fix the call to match the actual signature in [src/components/game_details.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/components/game_details.py) (it accepts `rating_label`, `rating_value`, etc., per usage in `upcoming_predictions_callbacks.py:870`; pass only the kwargs that exist).

- [ ] **Step 9: Commit**

```bash
git add src/callbacks/collection_models_callbacks.py
git commit -m "Add Collection Models page callbacks (cards/table dual view, per-user fetch)"
```

---

## Task 9: Register the callbacks in the package init

**Files:**
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/callbacks/__init__.py`

- [ ] **Step 1: Add the import and registration call**

In [src/callbacks/__init__.py](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/callbacks/__init__.py), inside `register_callbacks` after the `register_upcoming_predictions_callbacks` import block:

```python
    from .collection_models_callbacks import register_collection_models_callbacks
```

Then, after `register_upcoming_predictions_callbacks(app, cache)`:

```python
    logger.info("Registering collection models callbacks")
    register_collection_models_callbacks(app, cache)
```

- [ ] **Step 2: Smoke-check the app boots**

```bash
cd /Users/phenrickson/Documents/projects/bgg-dash-viewer
uv run python -c "import dash_app; print('booted')"
```

Expected: `booted` (Dash logging may print routing/setup messages first).

- [ ] **Step 3: Commit**

```bash
git add src/callbacks/__init__.py
git commit -m "Register Collection Models callbacks at app start"
```

---

## Task 10: Activate the landing-page tile

**Files:**
- Modify: `/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/landing.py`

- [ ] **Step 1: Flip the route**

In [src/landing.py:39-45](/Users/phenrickson/Documents/projects/bgg-dash-viewer/src/landing.py#L39-L45), change:

```python
    {
        "title": "Collection Models",
        "description": "Personalized collection analysis and recommendations",
        "icon": "fas fa-chart-pie",
        "color": "#3b82f6",  # blue
        "route": None,  # Coming soon
    },
```

to:

```python
    {
        "title": "Collection Models",
        "description": "Personalized collection analysis and recommendations",
        "icon": "fas fa-chart-pie",
        "color": "#3b82f6",  # blue
        "route": "/app/collection-models",
    },
```

- [ ] **Step 2: Commit**

```bash
git add src/landing.py
git commit -m "Activate Collection Models tile on landing page"
```

---

## Task 11: End-to-end manual verification in a browser

**Files:** none (verification only).

This step replaces the usual "run the test suite" beat for UI features — the main risks are integration shape (BQ schema, dash callback wiring, modal rendering) which mocks don't catch.

- [ ] **Step 1: Run the full test suite**

```bash
cd /Users/phenrickson/Documents/projects/bgg-dash-viewer
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Boot the app locally**

```bash
use-personal
uv run python dash_app.py
```

Expected: server starts on port 8050 (or whatever the config sets) without import errors or callback errors in the log.

- [ ] **Step 3: Visit the landing page and click the Collection Models tile**

In a browser, open `http://localhost:8050/`. Confirm:

- The Collection Models tile is no longer greyed out.
- Clicking it navigates to `/app/collection-models`.

- [ ] **Step 4: Exercise the page**

On `/app/collection-models`:

- Username dropdown lists at least the 3 users with predictions today (`GOBBluth89`, `TomBrewstErr`, `phenrickson`); `rahdo` is **not** present (registry-only).
- Year dropdown defaults to the current year (or closest); changing it filters cards.
- Min Predicted Prob slider trims the grid as expected at `0.5` and `0.9`.
- Show without cover toggle works.
- Cards/Table toggle switches the view; the table view shows `predicted_prob`, `predicted_label`, `threshold`, `model_name`, `model_version`.
- Clicking a card opens the modal with the game's full details.
- Switching the username re-renders the grid with that user's predictions.
- Browser console shows no Dash callback errors.

- [ ] **Step 5: Commit any verification fixes**

If you discovered a small bug during verification (e.g. typoed callback id, missed import), fix it and commit a separate `Fix:` commit. Do not amend earlier commits.

---

## Self-review checklist

Before declaring done, walk the spec sections:

- [ ] **Spec §1.a (sources.js)** — Task 1.
- [ ] **Spec §1.b (incremental sqlx)** — Task 2.
- [ ] **Spec §1.c (no backfill)** — covered by relying on Dataform's standard run; Task 3 verifies the table after CI.
- [ ] **Spec §2.a (route + landing tile)** — Tasks 7 (route), 10 (tile).
- [ ] **Spec §2.b (layout)** — Task 6.
- [ ] **Spec §2.c (callbacks: dropdown, lazy fetch, filter bar)** — Task 8.
- [ ] **Spec §2.d (card body: predicted_prob + label, no threshold per card)** — Task 8 step 2.
- [ ] **Spec §2.e (model-details summary)** — Task 8 step 5 renders a compact summary line. (The spec calls for an accordion; the implementation is a compact inline summary because the model card has fewer fields than the existing predictions module. If you prefer the accordion shape used on the existing page for parity, swap the `summary` html.Div for a `dbc.Accordion` with the same content.)
- [ ] **Spec §2.f (modal)** — Task 8 step 7.
- [ ] **Spec §2.g (BQ client)** — Tasks 4, 5.
- [ ] **Spec §3 edge cases** — registry-without-landing handled by inner-join in Task 2; empty year/cache TTL/year floor handled in Task 8 helpers.
