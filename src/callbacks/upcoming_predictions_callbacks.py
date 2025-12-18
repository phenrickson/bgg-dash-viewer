"""Callbacks for the upcoming predictions page."""

from datetime import datetime
from typing import Any

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
    get_jobs_column_defs,
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
    def _load_prediction_jobs_cached() -> tuple[list[dict], list[dict], str]:
        """Cached helper to load available prediction jobs from BigQuery.

        Returns:
            Tuple of (jobs data, dropdown options, default selected job_id)
        """
        try:
            client = get_bq_client()
            jobs_df = client.get_prediction_summary()

            if jobs_df.empty:
                return [], [], None

            # Convert to list of dicts for storage
            jobs_data = jobs_df.to_dict("records")

            # Create dropdown options
            options = []
            for job in jobs_data:
                latest_pred = pd.to_datetime(job["latest_prediction"]).strftime(
                    "%Y-%m-%d %H:%M"
                )
                label = f"{latest_pred} ({job['num_predictions']:,} predictions)"
                options.append({"label": label, "value": job["job_id"]})

            # Default to first job
            default_job_id = jobs_data[0]["job_id"] if jobs_data else None

            return jobs_data, options, default_job_id

        except Exception as e:
            print(f"Error loading prediction jobs: {e}")
            return [], [], None

    @app.callback(
        [
            Output("predictions-jobs-store", "data"),
            Output("prediction-job-dropdown", "options"),
            Output("prediction-job-dropdown", "value"),
        ],
        [Input("url", "pathname"), Input("refresh-trigger-store", "data")],
    )
    def load_prediction_jobs(pathname: str, refresh_trigger: int) -> tuple[list[dict], list[dict], str]:
        """Load available prediction jobs from BigQuery.

        Args:
            pathname: URL pathname (triggers on page load)
            refresh_trigger: Dummy trigger to force refresh

        Returns:
            Tuple of (jobs data, dropdown options, default selected job_id)
        """
        # Only load data if we're on the predictions page
        if pathname != "/app/upcoming-predictions":
            raise PreventUpdate

        return _load_prediction_jobs_cached()

    @app.callback(
        Output("selected-job-details", "children"),
        [Input("prediction-job-dropdown", "value")],
        [State("predictions-jobs-store", "data")],
    )
    def update_job_details(
        selected_job_id: str | None, jobs_data: list[dict]
    ) -> html.Div:
        """Update the selected job details display.

        Args:
            selected_job_id: ID of selected job
            jobs_data: List of all jobs data

        Returns:
            Div containing job details
        """
        if not selected_job_id or not jobs_data:
            return html.Div()

        # Find selected job
        selected_job = next(
            (job for job in jobs_data if job["job_id"] == selected_job_id), None
        )

        if not selected_job:
            return html.Div()

        # Format the details
        latest_pred = pd.to_datetime(selected_job["latest_prediction"]).strftime(
            "%Y-%m-%d %H:%M"
        )

        return html.Span(
            [
                html.Small(
                    [
                        f"{selected_job['num_predictions']:,} predictions",
                        html.Span(" • ", className="text-muted mx-1"),
                        latest_pred,
                    ],
                    className="text-muted",
                )
            ]
        )

    @cache.memoize(timeout=600)  # Cache for 10 minutes
    def _load_predictions_for_job_cached(selected_job_id: str) -> list[dict]:
        """Cached helper function to load predictions."""
        try:
            client = get_bq_client()
            df = client.query_predictions(selected_job_id)

            if df.empty:
                return []

            # Add year bucket
            df["year_bucket"] = df["year_published"].apply(
                lambda x: "Other" if x < 2010 else str(int(x))
            )

            return df.to_dict("records")

        except Exception as e:
            print(f"Error loading predictions for job {selected_job_id}: {e}")
            return []

    @app.callback(
        Output("selected-job-predictions-store", "data"),
        [Input("prediction-job-dropdown", "value")],
    )
    def load_predictions_for_job(selected_job_id: str | None) -> list[dict]:
        """Load predictions for the selected job.

        Args:
            selected_job_id: ID of selected job

        Returns:
            List of predictions as dicts
        """
        if not selected_job_id:
            raise PreventUpdate

        return _load_predictions_for_job_cached(selected_job_id)

    @app.callback(
        Output("predictions-table-content", "children"),
        [Input("selected-job-predictions-store", "data")],
    )
    def render_predictions_table_tab(predictions_data: list[dict]) -> html.Div:
        """Render the predictions table tab.

        Args:
            predictions_data: List of predictions

        Returns:
            Div containing the predictions table tab content
        """
        if not predictions_data:
            return html.Div("No predictions data available.", className="text-center")

        df = pd.DataFrame(predictions_data)

        # Get unique years for dropdown
        unique_years = sorted(
            df["year_bucket"].unique(), key=lambda x: (x == "Other", x)
        )

        # Find default year (closest to current year)
        current_year = datetime.now().year
        numeric_years = [int(year) for year in unique_years if year != "Other"]
        if numeric_years:
            closest_year = min(numeric_years, key=lambda x: abs(x - current_year))
            default_year = str(closest_year)
        else:
            default_year = unique_years[0] if unique_years else None

        return html.Div(
            [
                # Year selection
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Select Publication Year"),
                                dcc.Dropdown(
                                    id="year-filter-dropdown",
                                    options=[
                                        {"label": year, "value": year}
                                        for year in unique_years
                                    ],
                                    value=default_year,
                                    clearable=False,
                                ),
                            ],
                            width=3,
                        )
                    ],
                    className="mb-3",
                ),
                # Statistics cards
                html.Div(id="predictions-stats-cards"),
                # Data table
                html.Div(id="predictions-data-table"),
            ]
        )

    @app.callback(
        [
            Output("predictions-stats-cards", "children"),
            Output("predictions-data-table", "children"),
        ],
        [Input("year-filter-dropdown", "value")],
        [State("selected-job-predictions-store", "data")],
    )
    def update_predictions_table(
        selected_year: str | None, predictions_data: list[dict]
    ) -> tuple[html.Div, html.Div]:
        """Update predictions table and stats based on selected year.

        Args:
            selected_year: Selected publication year
            predictions_data: List of all predictions

        Returns:
            Tuple of (stats cards, data table)
        """
        if not predictions_data or not selected_year:
            raise PreventUpdate

        df = pd.DataFrame(predictions_data)
        filtered_df = df[df["year_bucket"] == selected_year].copy()

        if filtered_df.empty:
            return html.Div("No data for selected year."), html.Div()

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
                                html.H6("Total Games", className="text-muted"),
                                html.H3(f"{len(filtered_df):,}"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Average Geek Rating", className="text-muted"),
                                html.H3(
                                    f"{filtered_df['predicted_geek_rating'].mean():.2f}"
                                ),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Median Geek Rating", className="text-muted"),
                                html.H3(
                                    f"{filtered_df['predicted_geek_rating'].median():.2f}"
                                ),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=4,
                ),
            ],
            className="mb-4",
        )

        # Create BGG links for game names
        filtered_df["name_link"] = filtered_df.apply(
            lambda row: f"[{row['name']}](https://boardgamegeek.com/boardgame/{row['game_id']})",
            axis=1
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

        # Create AG Grid with Vizro theming
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


    @app.callback(
        [
            Output("predictions-table-content", "style"),
            Output("bigquery-jobs-content", "style"),
        ],
        [Input("predictions-tabs", "active_tab")],
    )
    def toggle_tab_content(active_tab: str) -> tuple[dict, dict]:
        """Show/hide content based on active tab.

        Args:
            active_tab: ID of the active tab

        Returns:
            Tuple of (predictions style, jobs style)
        """
        if active_tab == "predictions-table":
            return {"display": "block"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block"}

    @app.callback(
        Output("bigquery-jobs-content", "children"),
        [Input("predictions-jobs-store", "data")],
    )
    def render_bigquery_jobs_tab(jobs_data: list[dict]) -> html.Div:
        """Render the BigQuery jobs tab.

        Args:
            jobs_data: List of all jobs

        Returns:
            Div containing jobs table and statistics
        """
        if not jobs_data:
            return html.Div("No jobs data available.", className="text-center")

        df = pd.DataFrame(jobs_data)

        # Format timestamps
        df["latest_prediction"] = pd.to_datetime(df["latest_prediction"]).dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        df["earliest_prediction"] = pd.to_datetime(
            df["earliest_prediction"]
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        # Round numeric columns
        if "avg_predicted_rating" in df.columns:
            df["avg_predicted_rating"] = df["avg_predicted_rating"].round(3)

        # Statistics cards
        total_jobs = len(df)
        total_predictions = df["num_predictions"].sum()
        latest_job_time = pd.to_datetime(
            jobs_data[0]["latest_prediction"]
        ).strftime("%Y-%m-%d")
        overall_avg = df["avg_predicted_rating"].mean()

        stats_cards = dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Total Jobs", className="text-muted"),
                                html.H3(f"{total_jobs:,}"),
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
                                html.H6("Total Predictions", className="text-muted"),
                                html.H3(f"{total_predictions:,}"),
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
                                html.H6("Latest Job", className="text-muted"),
                                html.H3(latest_job_time),
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
                                html.H6("Overall Avg Rating", className="text-muted"),
                                html.H3(f"{overall_avg:.3f}"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
            ],
            className="mb-4",
        )

        # Jobs table
        display_columns = [
            "job_id",
            "num_predictions",
            "latest_prediction",
            "earliest_prediction",
            "min_year",
            "max_year",
            "avg_predicted_rating",
            "hurdle_experiment",
            "complexity_experiment",
            "rating_experiment",
            "users_rated_experiment",
        ]

        # Create AG Grid for jobs with Vizro theming
        grid_options = get_default_grid_options()
        grid_options["paginationPageSize"] = 20

        jobs_grid = dag.AgGrid(
            id="jobs-table",
            rowData=df[display_columns].to_dict("records"),
            columnDefs=get_jobs_column_defs(),
            defaultColDef=get_default_column_def(),
            dashGridOptions=grid_options,
            className=get_grid_class_name(),
            style=get_grid_style("400px"),
        )

        return html.Div(
            [
                html.H4("Summary Statistics", className="mb-3"),
                stats_cards,
                html.H4("All Prediction Jobs", className="mt-5 mb-3"),
                jobs_grid,
            ]
        )

    @app.callback(
        Output("refresh-trigger-store", "data"),
        [Input("refresh-predictions-btn", "n_clicks")],
        [State("refresh-trigger-store", "data")],
    )
    def refresh_data(n_clicks: int | None, current_trigger: int) -> int:
        """Handle refresh button click.

        Args:
            n_clicks: Number of times button was clicked
            current_trigger: Current trigger value

        Returns:
            Incremented trigger value
        """
        if n_clicks is None:
            raise PreventUpdate

        # Clear cache
        cache.clear()

        # Increment trigger to force reload
        return current_trigger + 1
