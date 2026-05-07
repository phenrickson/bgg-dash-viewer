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

_bq_client: BigQueryClient | None = None


def get_bq_client() -> BigQueryClient:
    """Lazy BigQuery client, mirroring the existing predictions module."""
    global _bq_client
    if _bq_client is None:
        _bq_client = BigQueryClient()
    return _bq_client


def _prob_color(quantile: float | None) -> tuple[str, str | None, str | None]:
    """Color a Predicted Prob badge by per-user quantile (0..1).

    Collection-model probabilities are user-specific — for some users 0.04
    may be a strong pick. Coloring by absolute thresholds is misleading, so
    we color by the row's quantile within that user's full deployed-model
    score distribution. White at the bottom, deepening blue toward the top.

    Returns (bootstrap_color, text_color, bg_override). The ramp is delivered
    via bg_override (a hex string) since Bootstrap doesn't ship a graded blue.
    """
    if quantile is None or pd.isna(quantile):
        return "light", "dark", None
    # Five blue steps from white-ish to deep blue. Top 5% gets the deepest.
    if quantile >= 0.95:
        return "primary", None, "#0b3d91"      # deep blue, white text
    if quantile >= 0.80:
        return "primary", None, "#1d63c8"      # mid-deep blue, white text
    if quantile >= 0.60:
        return "primary", None, "#5a93e0"      # mid blue, white text
    if quantile >= 0.40:
        return "light", "dark", "#a9c8ee"      # light blue, dark text
    return "light", "dark", "#e3eefb"          # near-white blue tint, dark text


def _fmt(value: Any, fmt: str) -> str:
    try:
        return format(value, fmt) if value is not None and not pd.isna(value) else "—"
    except (TypeError, ValueError):
        return "—"


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
        bs_color, text_color, bg_override = _prob_color(row.get("prob_quantile"))
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
                username=username, min_year=PREDICTIONS_MIN_YEAR
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
            df = df.sort_values("predicted_prob", ascending=False).reset_index(drop=True)
            # Per-user quantile of predicted_prob across the loaded set.
            # Coloring on the card uses this rather than absolute prob, since
            # the prob distribution is user-specific (a 0.04 may be elite).
            df["prob_quantile"] = df["predicted_prob"].rank(pct=True, method="average")
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

        # Render the filter bar shell synchronously — no BQ call. The user
        # dropdown gets its options populated by a separate callback so the
        # page paints immediately while users + predictions load in parallel.
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
                                                options=[],
                                                value=None,
                                                clearable=False,
                                                placeholder="Loading users...",
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
                                            html.Label("Top N (per year)", className="mb-2"),
                                            dcc.Dropdown(
                                                id="collection-models-top-n",
                                                options=[
                                                    {"label": str(n), "value": n}
                                                    for n in (100, 200, 300, 400, 500)
                                                ],
                                                value=100,
                                                clearable=False,
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
                            dbc.Spinner(
                                [
                                    html.Div(id="collection-models-summary", className="mb-3"),
                                    html.Div(id="collection-models-content"),
                                ],
                                color="primary",
                                type="border",
                                delay_show=200,
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

    @app.callback(
        [
            Output("collection-models-user-dropdown", "options"),
            Output("collection-models-user-dropdown", "value"),
            Output("collection-models-user-dropdown", "placeholder"),
        ],
        Input("collection-models-user-dropdown", "id"),
    )
    def populate_users(_id):
        """Populate the user dropdown asynchronously after the chrome paints.

        Triggered once when the dropdown mounts. Cached so subsequent loads
        are immediate.
        """
        users = _load_users_cached()
        if not users:
            return [], None, "No deployed users"
        default_user = "phenrickson" if "phenrickson" in users else users[0]
        return (
            [{"label": u, "value": u} for u in users],
            default_user,
            "Select a user...",
        )

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

    @app.callback(
        Output("collection-models-content", "children"),
        [
            Input("collection-models-year-dropdown", "value"),
            Input("collection-models-view-toggle", "data"),
            Input("collection-models-cards-page", "data"),
            Input("collection-models-top-n", "value"),
            Input("collection-models-show-no-cover", "value"),
        ],
        State("collection-models-data-store", "data"),
    )
    def update_content(
        selected_year: str | None,
        view_mode: str,
        page: int | None,
        top_n: int | None,
        show_no_cover: bool | None,
        records: list[dict] | None,
    ):
        if not records or not selected_year:
            raise PreventUpdate

        df = pd.DataFrame(records)
        filtered = df[df["year_bucket"] == selected_year].copy()

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

        if top_n is not None and top_n > 0:
            filtered = filtered.head(top_n)

        if view_mode == "table":
            return _render_table(filtered)
        return _render_cards(filtered.to_dict("records"), page=page or 1)

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
