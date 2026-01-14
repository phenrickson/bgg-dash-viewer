"""Callbacks for the upcoming predictions page."""

from datetime import datetime

import dash_ag_grid as dag
import pandas as pd
from dash import Input, Output, State, html
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

            # Load predictions
            predictions_df = client.get_latest_predictions(limit=15000)

            if predictions_df.empty:
                return [], {}

            # Add year bucket for filtering
            predictions_df["year_bucket"] = predictions_df["year_published"].apply(
                lambda x: "Other" if pd.isna(x) or x < 2020 else str(int(x))
            )

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
            Output("predictions-summary-stats", "children"),
            Output("predictions-model-details", "children"),
            Output("year-filter-dropdown", "options"),
            Output("year-filter-dropdown", "value"),
        ],
        [Input("url", "pathname")],
    )
    def load_predictions(pathname: str):
        """Load predictions data on page load.

        Args:
            pathname: URL pathname

        Returns:
            Tuple of (predictions data, summary stats, model details, year options, default year)
        """
        if pathname != "/app/upcoming-predictions":
            raise PreventUpdate

        predictions_data, summary_stats = _load_predictions_cached()

        if not predictions_data:
            return (
                [],
                html.Span("No predictions available."),
                html.Span("No model information available."),
                [],
                None,
            )

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

        # Build model details content - helper function for formatting
        # Format: model_name/experiment/version (e.g., rating-v2026/catboost-rating/v1)
        def format_model_info(prefix: str) -> str:
            name = summary_stats.get(f"{prefix}_model_name", "N/A")
            version = summary_stats.get(f"{prefix}_model_version", "")
            experiment = summary_stats.get(f"{prefix}_experiment", "")
            exp_str = f"/{experiment}" if experiment else ""
            version_str = f"/v{version}" if version else ""
            return f"{name}{exp_str}{version_str}"

        model_details = html.Div(
            [
                html.Div(
                    [
                        html.Strong("Hurdle: ", className="me-1"),
                        html.Span(format_model_info("hurdle")),
                    ],
                    className="mb-1",
                ),
                html.Div(
                    [
                        html.Strong("Complexity: ", className="me-1"),
                        html.Span(format_model_info("complexity")),
                    ],
                    className="mb-1",
                ),
                html.Div(
                    [
                        html.Strong("Rating: ", className="me-1"),
                        html.Span(format_model_info("rating")),
                    ],
                    className="mb-1",
                ),
                html.Div(
                    [
                        html.Strong("Users Rated: ", className="me-1"),
                        html.Span(format_model_info("users_rated")),
                    ],
                ),
            ],
            className="small",
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
            # Find closest future year
            numeric_years = [int(y) for y in unique_years if y != "Other"]
            if numeric_years:
                default_year = str(max(numeric_years))
            else:
                default_year = unique_years[0] if unique_years else None

        return predictions_data, summary_content, model_details, year_options, default_year

    @app.callback(
        [
            Output("predictions-year-stats", "children"),
            Output("predictions-table-content", "children"),
        ],
        [Input("year-filter-dropdown", "value")],
        [State("predictions-data-store", "data")],
    )
    def update_predictions_display(
        selected_year: str | None, predictions_data: list[dict]
    ):
        """Update predictions display based on selected year.

        Args:
            selected_year: Selected publication year
            predictions_data: All predictions data

        Returns:
            Tuple of (year stats, data table)
        """
        if not predictions_data or not selected_year:
            raise PreventUpdate

        df = pd.DataFrame(predictions_data)
        filtered_df = df[df["year_bucket"] == selected_year].copy()

        if filtered_df.empty:
            return (
                html.Div(),
                html.Div("No predictions for selected year.", className="text-muted text-center"),
            )

        # Sort by predicted rating
        filtered_df = filtered_df.sort_values(
            "predicted_geek_rating", ascending=False
        ).reset_index(drop=True)

        # Statistics cards
        stats_cards = dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Games", className="text-muted mb-1"),
                                html.H4(f"{len(filtered_df):,}", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Avg Predicted Rating", className="text-muted mb-1"),
                                html.H4(
                                    f"{filtered_df['predicted_geek_rating'].mean():.2f}",
                                    className="mb-0",
                                ),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Median Rating", className="text-muted mb-1"),
                                html.H4(
                                    f"{filtered_df['predicted_geek_rating'].median():.2f}",
                                    className="mb-0",
                                ),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Avg Complexity", className="text-muted mb-1"),
                                html.H4(
                                    f"{filtered_df['predicted_complexity'].mean():.2f}",
                                    className="mb-0",
                                ),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
            ],
            className="mb-4",
        )

        # Create BGG links for game names
        filtered_df["name_link"] = filtered_df.apply(
            lambda row: f"[{row['name']}](https://boardgamegeek.com/boardgame/{row['game_id']})",
            axis=1,
        )

        # Prepare display columns
        display_columns = [
            "year_published",
            "game_id",
            "name_link",
            "predicted_geek_rating",
            "predicted_hurdle_prob",
            "predicted_complexity",
            "predicted_rating",
            "predicted_users_rated",
        ]

        # Create AG Grid
        grid_options = get_default_grid_options()
        grid_options["paginationPageSize"] = 100

        data_grid = dag.AgGrid(
            id="predictions-table",
            rowData=filtered_df[display_columns].to_dict("records"),
            columnDefs=get_predictions_column_defs(),
            defaultColDef=get_default_column_def(),
            dashGridOptions=grid_options,
            className=get_grid_class_name(),
            style=get_grid_style("600px"),
        )

        return stats_cards, data_grid
