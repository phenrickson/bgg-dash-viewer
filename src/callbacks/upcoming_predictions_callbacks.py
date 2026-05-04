"""Callbacks for the upcoming predictions page."""

from datetime import datetime
from typing import Any

import dash
import dash_ag_grid as dag
import pandas as pd
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from ..data.bigquery_client import BigQueryClient
from ..components.ag_grid_config import (
    get_default_grid_options,
    get_default_column_def,
    get_grid_style,
    get_grid_class_name,
    get_predictions_column_defs,
)
from ..components.game_card import create_game_info_card
from ..components.game_details import render_details_body

CARDS_PER_PAGE = 15

# Lower bound on year_published for the predictions page. Older releases
# aren't relevant to a "browse upcoming games" view.
PREDICTIONS_MIN_YEAR = 2025

# Top-N games per year to keep in the dcc.Store payload, ordered by predicted
# geek rating. Bounds the initial response size on Cloud Run.
PREDICTIONS_PER_YEAR = 1000

# Lazy-loaded BigQuery client
_bq_client: BigQueryClient | None = None


def get_bq_client() -> BigQueryClient:
    """Get or create BigQuery client instance.

    Returns:
        BigQueryClient instance
    """
    global _bq_client
    if _bq_client is None:
        _bq_client = BigQueryClient()
    return _bq_client


def _predictions_stats_block(row: dict[str, Any]) -> html.Div:
    """Compact strip of predicted stats shown on each card body."""
    def _fmt(value, fmt: str) -> str:
        try:
            return format(value, fmt) if value is not None and not pd.isna(value) else "—"
        except (TypeError, ValueError):
            return "—"

    geek = _fmt(row.get("predicted_geek_rating"), ".2f")
    complexity = _fmt(row.get("predicted_complexity"), ".2f")
    users = row.get("predicted_users_rated")
    users_str = f"{int(users):,}" if users is not None and not pd.isna(users) else "—"
    hurdle = _fmt(row.get("predicted_hurdle_prob"), ".0%")

    return html.Div(
        [
            html.Hr(className="my-2"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Small("Predicted Geek", className="text-muted d-block"),
                            html.Strong(geek),
                        ],
                        xs=6,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Small("Predicted Complexity", className="text-muted d-block"),
                            html.Strong(complexity),
                        ],
                        xs=6,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Small("Predicted Users Rated", className="text-muted d-block"),
                            html.Strong(users_str),
                        ],
                        xs=6,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Small("Hurdle Prob", className="text-muted d-block"),
                            html.Strong(hurdle),
                        ],
                        xs=6,
                        md=3,
                    ),
                ],
                className="g-2",
            ),
        ]
    )


def _render_predictions_cards(records: list[dict[str, Any]], page: int) -> html.Div:
    """Render predictions as a paginated grid of cover-image tiles.

    Image-forward layout for "browse upcoming games by recognition". Each
    tile is mostly cover art with a rank corner badge and a predicted-rating
    overlay; title + year sit below. Click opens a modal with full details
    so the grid layout doesn't reflow on expand.
    """
    total = len(records)
    if total == 0:
        return html.Div(
            "No predictions for selected year.",
            className="text-muted text-center py-4",
        )

    # Larger page size for the grid view — many tiles fit per screen.
    page_size = 24
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    page_records = records[start:end]

    def _stat_badge(
        label: str,
        value: str,
        color: str = "light",
        text_color: str | None = "dark",
        bg_override: str | None = None,
    ) -> html.Div:
        """Labeled badge for a single prediction stat in the tile footer.

        ``bg_override`` lets a tier specify a hex color outside the standard
        Bootstrap palette (e.g., a darker green for "elite" predictions).
        When set, it replaces the Bootstrap ``color`` background via inline
        style; ``text_color`` is forced white.
        """
        badge_style = {
            "fontSize": "0.85rem",
            "padding": "0.35em 0.55em",
            "fontWeight": "bold",
        }
        if bg_override:
            badge_style["backgroundColor"] = bg_override
            badge_style["color"] = "white"

        return html.Div(
            [
                html.Small(label, className="text-muted d-block", style={"fontSize": "0.7rem", "lineHeight": "1"}),
                dbc.Badge(
                    value,
                    color=color if not bg_override else None,
                    text_color=text_color if not bg_override else None,
                    className="mt-1",
                    style=badge_style,
                ),
            ],
            className="text-center",
        )

    # Darker "elite" green for the top rating tier, since Bootstrap doesn't
    # ship a second green out of the box.
    ELITE_GREEN = "#1e7e34"

    def _geek_color(value: float | None) -> tuple[str, str | None, str | None]:
        """Color a Predicted Geek badge.

        Returns (bootstrap_color, text_color, bg_override). bg_override is
        non-None for the elite tier (≥7) which uses a custom darker green.
        Predicted Geek ratings tend to live in the 5.0–7.0 band.
        """
        if value is None or pd.isna(value):
            return "light", "dark", None
        if value >= 7.0:
            return "success", None, ELITE_GREEN
        if value >= 6.5:
            return "success", None, None
        if value >= 6.0:
            return "warning", "dark", None
        if value >= 5.5:
            return "light", "dark", None
        return "secondary", None, None

    def _average_color(value: float | None) -> tuple[str, str | None, str | None]:
        """Color a Predicted Average badge.

        Predicted Average ratings tend to live in the 6.5–9.5 band, so the
        thresholds are shifted up relative to the Geek scale.
        """
        if value is None or pd.isna(value):
            return "light", "dark", None
        if value >= 8.5:
            return "success", None, ELITE_GREEN
        if value >= 8.0:
            return "success", None, None
        if value >= 7.5:
            return "warning", "dark", None
        if value >= 7.0:
            return "light", "dark", None
        return "secondary", None, None

    def _hurdle_color(value: float | None) -> tuple[str, str | None, str | None]:
        """Color the hurdle-probability badge by confidence tier."""
        if value is None or pd.isna(value):
            return "light", "dark", None
        if value >= 0.9:
            return "success", None, None
        if value >= 0.7:
            return "warning", "dark", None
        return "light", "dark", None

    def _complexity_color(value: float | None) -> tuple[str, str | None, str | None]:
        """Color the complexity badge as a diverging blue→white→red scale.

        Light gateway games and heavy strategy both have meaning, so the
        midpoint sits neutral and either extreme pops visually.
        """
        if value is None or pd.isna(value):
            return "light", "dark", None
        if value > 3.5:
            return "danger", None, None  # heavy
        if value > 3.0:
            return "warning", "dark", None  # medium-heavy
        if value > 2.0:
            return "light", "dark", None  # medium (neutral midpoint)
        if value > 1.5:
            return "info", None, None  # medium-light
        return "primary", None, None  # light

    def _fmt(value, fmt: str) -> str:
        try:
            return format(value, fmt) if value is not None and not pd.isna(value) else "—"
        except (TypeError, ValueError):
            return "—"

    tiles = []
    for i, row in enumerate(page_records):
        game_id = row.get("game_id")
        rank = start + i + 1
        thumbnail = row.get("thumbnail") or row.get("image") or ""
        name = row.get("name", "Unknown")
        year = row.get("year_published")
        year_str = f"({int(year)})" if year and not pd.isna(year) else ""

        pred_geek = _fmt(row.get("predicted_geek_rating"), ".2f")
        pred_average = _fmt(row.get("predicted_rating"), ".2f")
        pred_complexity = _fmt(row.get("predicted_complexity"), ".2f")
        users_value = row.get("predicted_users_rated")
        if users_value is not None and not pd.isna(users_value):
            users_str = f"{int(users_value):,}" if users_value < 10000 else f"{users_value/1000:.1f}k"
        else:
            users_str = "—"
        hurdle_value = row.get("predicted_hurdle_prob")
        hurdle_str = (
            f"{hurdle_value:.0%}"
            if hurdle_value is not None and not pd.isna(hurdle_value)
            else "—"
        )

        # Two lines title with ellipsis on overflow — show as much of the
        # name as fits before truncating.
        title_clamp_style = {
            "display": "-webkit-box",
            "WebkitLineClamp": "2",
            "WebkitBoxOrient": "vertical",
            "overflow": "hidden",
            "fontSize": "0.95rem",
            "lineHeight": "1.2",
            "minHeight": "2.4em",
        }

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

        # NEW pill for games that have only recently entered the predictions
        # table (is_new_7d). Top-right corner, only rendered when set.
        is_new = bool(row.get("is_new_7d"))
        new_badge = (
            dbc.Badge(
                "NEW",
                color="danger",
                className="position-absolute",
                style={
                    "top": "8px",
                    "right": "8px",
                    "fontSize": "0.7rem",
                    "padding": "0.35em 0.55em",
                    "letterSpacing": "0.05em",
                    "fontWeight": "bold",
                },
            )
            if is_new
            else None
        )

        image_children = [
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
        ]
        if new_badge is not None:
            image_children.append(new_badge)

        image_block = html.Div(image_children, className="position-relative")

        body = html.Div(
            [
                html.Div(name, className="fw-bold", title=name, style=title_clamp_style),
                html.Small(year_str, className="text-muted d-block mb-2"),
                html.Hr(className="my-2"),
                # 5 stats in a 3+2 grid (3 per row, 2 in the second row).
                dbc.Row(
                    [
                        dbc.Col(_stat_badge("Geek", pred_geek, *_geek_color(row.get("predicted_geek_rating"))), width=4),
                        dbc.Col(_stat_badge("Average", pred_average, *_average_color(row.get("predicted_rating"))), width=4),
                        dbc.Col(_stat_badge("Complexity", pred_complexity, *_complexity_color(row.get("predicted_complexity"))), width=4),
                    ],
                    className="g-1 mb-1",
                ),
                dbc.Row(
                    [
                        dbc.Col(_stat_badge("Users", users_str), width=4),
                        dbc.Col(_stat_badge("P(Hurdle)", hurdle_str, *_hurdle_color(row.get("predicted_hurdle_prob"))), width=4),
                    ],
                    className="g-1",
                ),
            ],
            className="p-2",
        )

        tile = html.Div(
            dbc.Card(
                [image_block, body],
                className="panel-card h-100",
            ),
            id={"type": "prediction-card", "game_id": game_id},
            style={"cursor": "pointer"},
            n_clicks=0,
            className="h-100",
        )

        tiles.append(
            dbc.Col(tile, xs=12, sm=6, md=4, lg=3, xl=2, className="mb-3"),
        )

    grid = dbc.Row(tiles, className="g-3")

    pagination = dbc.Pagination(
        id="predictions-cards-pagination",
        max_value=total_pages,
        active_page=page,
        first_last=True,
        previous_next=True,
        fully_expanded=False,
        size="sm",
        className="mt-3",
    ) if total_pages > 1 else html.Div()

    return html.Div([grid, pagination])


def _render_predictions_table(df: pd.DataFrame) -> html.Div:
    """Render predictions as the existing AG Grid table."""
    display_columns = [
        "game_id",
        "name",
        "year_published",
        "is_new_7d",
        "predicted_geek_rating",
        "predicted_hurdle_prob",
        "predicted_complexity",
        "predicted_rating",
        "predicted_users_rated",
    ]
    display_columns = [c for c in display_columns if c in df.columns]

    grid_options = get_default_grid_options()
    grid_options["paginationPageSize"] = 100

    return dag.AgGrid(
        id="predictions-table",
        rowData=df[display_columns].to_dict("records"),
        columnDefs=get_predictions_column_defs(),
        defaultColDef=get_default_column_def(),
        dashGridOptions=grid_options,
        className=get_grid_class_name(),
        style=get_grid_style("600px"),
    )


def register_upcoming_predictions_callbacks(app, cache):
    """Register all callbacks for the upcoming predictions page.

    Args:
        app: Dash app instance
        cache: Flask-Caching instance
    """

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def _load_predictions_cached() -> tuple[list[dict], dict]:
        """Cached helper to load predictions from BigQuery.

        Returns:
            Tuple of (predictions data, summary stats)
        """
        try:
            client = get_bq_client()

            # Load predictions joined with games_features so cards/expansions
            # have everything they need (thumbnail, image, description,
            # categories/mechanics/families, designers, publishers, etc.)
            # Restrict to upcoming/current years; older years aren't relevant
            # to a "browse upcoming games" view.
            predictions_df = client.get_latest_predictions_with_features(
                min_year=PREDICTIONS_MIN_YEAR, limit=20000
            )

            if predictions_df.empty:
                return [], {}

            # Add year bucket for filtering
            predictions_df["year_bucket"] = predictions_df["year_published"].apply(
                lambda x: "Other" if pd.isna(x) or x < 2020 else str(int(x))
            )

            # Coerce ARRAY columns to plain Python lists so render_details_body
            # and create_game_info_card don't trip on numpy truthiness checks
            # after the dcc.Store roundtrip.
            for col in ("categories", "mechanics", "families", "designers", "publishers"):
                if col in predictions_df.columns:
                    predictions_df[col] = predictions_df[col].apply(
                        lambda v: list(v) if v is not None and len(v) > 0 else []
                    )

            # Cap to top-N games per year (by predicted geek rating) so the
            # initial dcc.Store payload stays well under Cloud Run's 32 MB
            # response cap regardless of how many low-ranked games exist for
            # any given year.
            predictions_df = (
                predictions_df.sort_values("predicted_geek_rating", ascending=False)
                .groupby("year_bucket", group_keys=False)
                .head(PREDICTIONS_PER_YEAR)
                .reset_index(drop=True)
            )

            # Drop heavy fields before serializing into dcc.Store. `description`
            # isn't shown on the card grid (modal falls back gracefully when
            # missing); `image` is the full-res cover and cards use `thumbnail`.
            for col in ("description", "image"):
                if col in predictions_df.columns:
                    predictions_df = predictions_df.drop(columns=[col])

            predictions_data = predictions_df.to_dict("records")

            # Get summary stats
            summary_stats = client.get_predictions_summary_stats()

            return predictions_data, summary_stats

        except Exception as e:
            print(f"Error loading predictions: {e}")
            return [], {}

    @app.callback(
        [
            Output("predictions-data-store", "data"),
            Output("predictions-page-content", "children"),
            Output("predictions-page-loading", "children"),
        ],
        [Input("url", "pathname")],
    )
    def load_predictions(pathname: str):
        """Load predictions data on page load.

        Args:
            pathname: URL pathname

        Returns:
            Tuple of (predictions data, page content, loading indicator)
        """
        if pathname != "/app/upcoming-predictions":
            raise PreventUpdate

        predictions_data, summary_stats = _load_predictions_cached()

        if not predictions_data:
            content = html.Div(
                "No predictions available.",
                className="text-muted text-center py-4",
            )
            return [], content, ""

        # Build simple summary display
        total = summary_stats.get("total_predictions", 0)
        min_year = summary_stats.get("min_year", "N/A")
        max_year = summary_stats.get("max_year", "N/A")
        latest_ts = summary_stats.get("latest_score_ts")

        if latest_ts:
            latest_str = pd.to_datetime(latest_ts).strftime("%Y-%m-%d")
        else:
            latest_str = "N/A"

        summary_content = html.Span(
            [
                f"{total:,} games",
                html.Span(" | ", className="mx-2"),
                f"Years {int(min_year)}-{int(max_year)}",
                html.Span(" | ", className="mx-2"),
                f"Last updated: {latest_str}",
            ]
        )

        # Build model details content as labeled badge rows, mirroring the
        # embedding-model-info pattern on the Similar Games page.
        def model_badge_row(label: str, prefix: str) -> html.Div:
            name = summary_stats.get(f"{prefix}_model_name", "N/A")
            version = summary_stats.get(f"{prefix}_model_version")
            experiment = summary_stats.get(f"{prefix}_experiment")

            badges = [
                dbc.Badge(
                    [html.I(className="fas fa-brain me-1"), name],
                    color="secondary",
                    className="me-2",
                )
            ]
            if version is not None and version != "":
                badges.append(
                    dbc.Badge(
                        [html.I(className="fas fa-code-branch me-1"), f"v{version}"],
                        color="info",
                        className="me-2",
                    )
                )
            if experiment:
                badges.append(
                    dbc.Badge(
                        [html.I(className="fas fa-cog me-1"), experiment],
                        color="light",
                        text_color="dark",
                        className="me-2",
                    )
                )

            return html.Div(
                [
                    html.Strong(f"{label}:", className="me-2", style={"minWidth": "100px", "display": "inline-block"}),
                    *badges,
                ],
                className="mb-2 d-flex align-items-center flex-wrap",
            )

        model_details = html.Div(
            [
                model_badge_row("Hurdle", "hurdle"),
                model_badge_row("Complexity", "complexity"),
                model_badge_row("Rating", "rating"),
                model_badge_row("Users Rated", "users_rated"),
            ]
        )

        # Get unique years for dropdown
        df = pd.DataFrame(predictions_data)
        unique_years = sorted(
            df["year_bucket"].unique(),
            key=lambda x: (x == "Other", x),
            reverse=True,
        )
        year_options = [{"label": year, "value": year} for year in unique_years]

        # Default to current year or closest
        current_year = str(datetime.now().year)
        if current_year in unique_years:
            default_year = current_year
        else:
            numeric_years = [int(y) for y in unique_years if y != "Other"]
            if numeric_years:
                default_year = str(max(numeric_years))
            else:
                default_year = unique_years[0] if unique_years else None

        # Build the full page content
        page_content = html.Div(
            [
                # Summary stats with collapsible model details
                html.Div(
                    [
                        html.Div(summary_content, className="text-muted"),
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(
                                    model_details,
                                    title="Model Details",
                                ),
                            ],
                            start_collapsed=True,
                            className="mt-2",
                            style={"maxWidth": "600px"},
                        ),
                    ],
                    className="mb-4",
                ),
                # Year filter, view toggle, and predictions content
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Publication Year", className="mb-2"),
                                            dcc.Dropdown(
                                                id="year-filter-dropdown",
                                                options=year_options,
                                                value=default_year,
                                                placeholder="Select year...",
                                                clearable=False,
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Min P(Hurdle)", className="mb-2"),
                                            dcc.Slider(
                                                id="predictions-hurdle-slider",
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
                                                id="predictions-show-no-cover",
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
                                                            id="predictions-view-toggle-cards",
                                                            color="primary",
                                                            outline=False,
                                                            size="sm",
                                                        ),
                                                        dbc.Button(
                                                            [html.I(className="fas fa-table me-2"), "Table"],
                                                            id="predictions-view-toggle-table",
                                                            color="primary",
                                                            outline=True,
                                                            size="sm",
                                                        ),
                                                    ],
                                                ),
                                                className="d-flex justify-content-end align-items-end h-100",
                                            ),
                                            dcc.Store(id="predictions-view-toggle", data="cards"),
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Statistics cards for filtered year
                            html.Div(id="predictions-year-stats", className="mb-3"),
                            # Cards or table view (toggled by predictions-view-toggle)
                            dbc.Spinner(
                                html.Div(id="predictions-content"),
                                color="primary",
                                type="border",
                            ),
                            # Pagination state for cards view
                            dcc.Store(id="predictions-cards-page", data=1),
                        ]
                    ),
                    className="panel-card",
                ),
                # Modal shown when a tile is clicked.
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle(id="predictions-modal-title")),
                        dbc.ModalBody(id="predictions-modal-body"),
                    ],
                    id="predictions-modal",
                    size="lg",
                    is_open=False,
                    scrollable=True,
                ),
            ]
        )

        return predictions_data, page_content, ""

    @app.callback(
        [
            Output("predictions-year-stats", "children"),
            Output("predictions-content", "children"),
        ],
        [
            Input("year-filter-dropdown", "value"),
            Input("predictions-view-toggle", "data"),
            Input("predictions-cards-page", "data"),
            Input("predictions-hurdle-slider", "value"),
            Input("predictions-show-no-cover", "value"),
        ],
        [State("predictions-data-store", "data")],
    )
    def update_predictions_display(
        selected_year: str | None,
        view_mode: str,
        page: int | None,
        min_hurdle: float | None,
        show_no_cover: bool | None,
        predictions_data: list[dict],
    ):
        """Update predictions display based on year + view + page + filters."""
        if not predictions_data or not selected_year:
            raise PreventUpdate

        df = pd.DataFrame(predictions_data)
        filtered_df = df[df["year_bucket"] == selected_year].copy()

        # Hurdle probability minimum filter
        if min_hurdle is not None and min_hurdle > 0:
            filtered_df = filtered_df[
                filtered_df["predicted_hurdle_prob"].fillna(0) >= min_hurdle
            ]

        # Hide games without cover art unless toggled on
        if not show_no_cover and "thumbnail" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["thumbnail"].notna() & (filtered_df["thumbnail"] != "")
            ]

        if filtered_df.empty:
            return (
                html.Div(),
                html.Div("No predictions match the current filters.", className="text-muted text-center"),
            )

        filtered_df = filtered_df.sort_values(
            "predicted_geek_rating", ascending=False
        ).reset_index(drop=True)

        # KPI strip removed — not useful at-a-glance for browsing upcoming games.
        stats_cards = html.Div()

        if view_mode == "table":
            content = _render_predictions_table(filtered_df)
        else:
            content = _render_predictions_cards(
                filtered_df.to_dict("records"), page=page or 1
            )

        return stats_cards, content

    @app.callback(
        [
            Output("predictions-view-toggle", "data"),
            Output("predictions-view-toggle-cards", "outline"),
            Output("predictions-view-toggle-table", "outline"),
        ],
        [
            Input("predictions-view-toggle-cards", "n_clicks"),
            Input("predictions-view-toggle-table", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def toggle_predictions_view(_cards_clicks, _table_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return "cards", False, True
        triggered = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered == "predictions-view-toggle-table":
            return "table", True, False
        return "cards", False, True

    @app.callback(
        Output("predictions-cards-page", "data"),
        Input("predictions-cards-pagination", "active_page"),
        prevent_initial_call=True,
    )
    def update_predictions_page(active_page):
        return active_page or 1

    @app.callback(
        Output("predictions-cards-page", "data", allow_duplicate=True),
        Input("year-filter-dropdown", "value"),
        prevent_initial_call=True,
    )
    def reset_page_on_year_change(_year):
        return 1

    @app.callback(
        [
            Output("predictions-modal", "is_open"),
            Output("predictions-modal-title", "children"),
            Output("predictions-modal-body", "children"),
        ],
        Input({"type": "prediction-card", "game_id": dash.ALL}, "n_clicks"),
        State("predictions-data-store", "data"),
        prevent_initial_call=True,
    )
    def open_prediction_modal(n_clicks_list, predictions_data):
        """Open the modal with the clicked tile's full details."""
        ctx = dash.callback_context
        if not ctx.triggered_id or not any(n_clicks_list):
            return dash.no_update, dash.no_update, dash.no_update

        clicked_id = ctx.triggered_id["game_id"]
        if not predictions_data:
            return dash.no_update, dash.no_update, dash.no_update

        row = next((r for r in predictions_data if r.get("game_id") == clicked_id), None)
        if row is None:
            return dash.no_update, dash.no_update, dash.no_update

        name = row.get("name", "Unknown")
        year = row.get("year_published")
        year_str = f" ({int(year)})" if year and not pd.isna(year) else ""
        title = f"{name}{year_str}"

        return True, title, render_details_body(
            row,
            rating_label="Predicted Geek",
            rating_value=row.get("predicted_geek_rating"),
            avg_rating_label="Predicted Average",
            avg_rating_value=row.get("predicted_rating"),
            complexity_label="Predicted Complexity",
            complexity_value=row.get("predicted_complexity"),
            users_label="Predicted Users",
            users_value=row.get("predicted_users_rated"),
        )
