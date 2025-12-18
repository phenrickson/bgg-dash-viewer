"""Game ratings callbacks for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from flask_caching import Cache
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from ..data.bigquery_client import BigQueryClient
from ..components.metrics_cards import create_metrics_cards
from ..utils.sampling import prepare_visualization_data
from ..theme import PLOTLY_TEMPLATE

logger = logging.getLogger(__name__)


def register_dashboard_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register dashboard-related callbacks.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Lazy-load BigQuery client to reduce startup time
    def get_bq_client() -> BigQueryClient:
        """Get or create BigQuery client instance."""
        if not hasattr(get_bq_client, '_client'):
            get_bq_client._client = BigQueryClient()
        return get_bq_client._client

    @cache.memoize(timeout=3600)  # Cache for 1 hour
    def get_dashboard_data() -> pd.DataFrame:
        """Get data for dashboard visualizations.

        Returns:
            DataFrame with game data for visualizations
        """
        logger.info("Fetching dashboard data from BigQuery")

        query = """
        SELECT 
            game_id,
            name,
            year_published,
            average_rating,
            bayes_average,
            average_weight,
            users_rated
        FROM `${project_id}.${dataset}.games_active_table`
        WHERE bayes_average IS NOT NULL 
          AND bayes_average > 0
          AND average_rating IS NOT NULL
          AND average_weight IS NOT NULL
          AND users_rated IS NOT NULL
          AND users_rated > 0
          AND average_weight > 0
          AND year_published >= 1975
          AND year_published <= EXTRACT(YEAR FROM CURRENT_DATE())
        ORDER BY bayes_average DESC
        """

        return get_bq_client().execute_query(query)

    @cache.memoize(timeout=3600)  # Cache for 1 hour
    def get_prepared_dashboard_data() -> pd.DataFrame:
        """Get prepared data for dashboard visualizations with sampling and jitter applied.

        Returns:
            DataFrame with game data prepared for visualizations
        """
        df = get_dashboard_data()

        # Apply standardized sampling and jitter for all visualizations
        sampling_config = {"max_rows": 30000, "threshold": 30000, "strategy": "stratified"}
        jitter_config = {"year_published": 0.3, "average_rating": 0.05, "average_weight": 0.05}

        df_sample, was_sampled = prepare_visualization_data(df, sampling_config, jitter_config)

        if was_sampled:
            logger.info(f"Sampled data for dashboard charts: {len(df_sample)} from {len(df)} rows")

        # Add commonly used derived columns
        df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])
        df_sample["log_users_jittered"] = df_sample["log_users_rated"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )

        return df_sample

    def create_rating_by_year_chart(
        df_sample: pd.DataFrame, is_modal: bool = False, selected_games: list[int] | None = None
    ) -> dict[str, Any]:
        """Create the rating by year scatter plot.

        Args:
            df_sample: Pre-processed DataFrame with sampling and jitter applied
            is_modal: Whether this is for the modal (larger) version
            selected_games: List of selected game IDs to highlight

        Returns:
            Plotly figure for rating by year
        """
        if selected_games is None:
            selected_games = []

        fig = px.scatter(
            df_sample,
            x="year_published_jittered",
            y="average_rating",
            color="average_rating",
            title=" Published (1975-Present)" if is_modal else None,
            labels={
                "year_published_jittered": "Year Published",
                "average_rating": "Average Rating",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            template=PLOTLY_TEMPLATE,
            opacity=0.6,
            range_color=[5, 9],
            hover_data=["name", "year_published", "users_rated"],
        )

        # Customize hover template for better readability
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Year Published: %{customdata[1]}<br>"
            + "Average Rating: %{y:.2f}<br>"
            + "User Ratings: %{customdata[2]:,}<br>"
            + "<extra></extra>"
        )

        # Configure layout based on modal vs regular view
        if is_modal:
            margin = dict(l=60, r=60, t=80, b=60)
            font_size = 14
            marker_size = 6
            height = 600
        else:
            margin = dict(l=40, r=40, t=60, b=40)
            font_size = None
            marker_size = 4
            height = None

        fig.update_layout(
            xaxis_title="Year Published",
            yaxis_title="Average Rating",
            margin=margin,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=font_size) if font_size else dict(color="white"),
            coloraxis_colorbar=dict(title="Average Rating"),
            # coloraxis_colorbar=dict(title="Log₁₀(User Ratings)"),
            height=height,
        )

        # Add highlighting for selected games
        if selected_games:
            # Create a mask for selected games
            selected_mask = df_sample["game_id"].isin(selected_games)

            if selected_mask.any():
                # Dim non-selected points
                fig.update_traces(
                    marker=dict(size=marker_size, opacity=0.3), selector=dict(type="scatter")
                )

                # Add highlighted points for selected games
                selected_data = df_sample[selected_mask]

                fig.add_trace(
                    go.Scatter(
                        x=selected_data["year_published_jittered"],
                        y=selected_data["average_rating"],
                        mode="markers",
                        marker=dict(
                            size=marker_size * 2,
                            color="gold",
                            line=dict(color="white", width=2),
                            opacity=1.0,
                        ),
                        customdata=selected_data[["name", "year_published", "users_rated"]].values,
                        hovertemplate="<b>%{customdata[0]} (SELECTED)</b><br>"
                        + "Year Published: %{customdata[1]}<br>"
                        + "Average Rating: %{y:.2f}<br>"
                        + "User Ratings: %{customdata[2]:,}<br>"
                        + "<extra></extra>",
                        showlegend=False,
                        name="Selected Games",
                    )
                )
        else:
            fig.update_traces(marker=dict(size=marker_size))

        return fig

    @app.callback(
        Output("metrics-cards-container", "children"),
        [Input("url", "pathname")],
    )
    def update_metrics_cards(pathname: str) -> dbc.Row:
        """Update the metrics cards with current data.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Row containing metrics cards
        """
        if pathname != "/app/game-ratings":
            return dbc.Row([])

        df = get_dashboard_data()
        return create_metrics_cards(df)

    @app.callback(
        Output("rating-by-year-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_rating_by_year_chart(pathname: str) -> dict[str, Any]:
        """Update the rating by year jitter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for rating by year
        """
        if pathname != "/app/game-ratings":
            return {}

        df_sample = get_prepared_dashboard_data()
        return create_rating_by_year_chart(df_sample, is_modal=False)

    @app.callback(
        [
            Output("chart-modal", "is_open"),
            Output("modal-chart", "figure"),
            Output("modal-chart-title", "children"),
        ],
        [
            Input("expand-rating-by-year-btn", "n_clicks"),
            Input("expand-weight-vs-rating-btn", "n_clicks"),
            Input("expand-users-by-year-btn", "n_clicks"),
            Input("expand-rating-vs-users-btn", "n_clicks"),
            Input("close-modal-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def toggle_modal(
        rating_year_clicks: int,
        weight_rating_clicks: int,
        complexity_year_clicks: int,
        rating_users_clicks: int,
        close_clicks: int,
    ) -> tuple[bool, dict[str, Any], str]:
        """Toggle the chart modal and update its content.

        Args:
            rating_year_clicks: Number of clicks on rating by year expand button
            weight_rating_clicks: Number of clicks on weight vs rating expand button
            complexity_year_clicks: Number of clicks on complexity by year expand button
            rating_users_clicks: Number of clicks on rating vs users expand button
            close_clicks: Number of clicks on close button

        Returns:
            Tuple of (is_open, figure, title)
        """
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, {}, ""

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "close-modal-btn":
            return False, {}, ""

        # Get the prepared data for creating full-size charts (same as regular charts)
        df_sample = get_prepared_dashboard_data()

        if button_id == "expand-rating-by-year-btn":
            fig = create_rating_by_year_chart(df_sample, is_modal=True)
            return True, fig, "Average Rating by Year Published"

        elif button_id == "expand-weight-vs-rating-btn":
            fig = create_weight_vs_rating_chart(df_sample, is_modal=True)
            return True, fig, "Complexity vs Average Rating"

        elif button_id == "expand-users-by-year-btn":
            fig = create_users_by_year_chart(df_sample, is_modal=True)
            return True, fig, "User Ratings by Year Published"

        elif button_id == "expand-rating-vs-users-btn":
            fig = create_rating_vs_users_chart(df_sample, is_modal=True)
            return True, fig, "Rating vs User Engagement"

        return False, {}, ""

    def create_weight_vs_rating_chart(
        df_sample: pd.DataFrame, is_modal: bool = False, selected_games: list[int] | None = None
    ) -> dict[str, Any]:
        """Create the complexity vs rating scatter plot.

        Args:
            df_sample: Pre-processed DataFrame with sampling and jitter applied
            is_modal: Whether this is for the modal (larger) version
            selected_games: List of selected game IDs to highlight

        Returns:
            Plotly figure for complexity vs rating
        """
        if selected_games is None:
            selected_games = []

        # Use the pre-processed data that already has sampling and jitter applied
        # Add log_users_rated if not already present
        if "log_users_rated" not in df_sample.columns:
            df_sample = df_sample.copy()
            df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])

        # Configure size based on modal vs regular view
        size_max = 20 if is_modal else 15
        size_column = "log_users_rated" if is_modal else None

        fig = px.scatter(
            df_sample,
            x="average_weight_jittered",
            y="average_rating_jittered",
            color="average_rating",
            labels={
                "average_weight_jittered": "Complexity Weight",
                "average_rating_jittered": "Average Rating",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            template=PLOTLY_TEMPLATE,
            opacity=0.45,
            hover_data=["name", "average_weight", "average_rating", "users_rated"],
            range_color=[5, 9],
        )

        # Customize hover template for better readability
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Complexity: %{customdata[1]:.2f}/5<br>"
            + "Average Rating: %{customdata[2]:.2f}<br>"
            + "User Ratings: %{customdata[3]:,}<br>"
            + "<extra></extra>"
        )

        # Configure layout based on modal vs regular view
        # Configure layout based on modal vs regular view
        if is_modal:
            margin = dict(l=60, r=60, t=80, b=60)
            font_size = 14
            marker_size = 6
            height = 600
        else:
            margin = dict(l=40, r=40, t=60, b=40)
            font_size = None
            marker_size = 4
            height = None

        fig.update_layout(
            xaxis_title="Complexity Weight",
            yaxis_title="Average Rating",
            margin=margin,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=font_size) if font_size else dict(color="white"),
            coloraxis_colorbar=dict(title="Average Rating"),
            height=height,
        )

        # Add highlighting for selected games
        if selected_games:
            # Create a mask for selected games
            selected_mask = df_sample["game_id"].isin(selected_games)

            if selected_mask.any():
                # Dim non-selected points
                fig.update_traces(
                    marker=dict(size=marker_size, opacity=0.2), selector=dict(type="scatter")
                )

                # Add highlighted points for selected games
                selected_data = df_sample[selected_mask]

                fig.add_trace(
                    go.Scatter(
                        x=selected_data["average_weight_jittered"],
                        y=selected_data["average_rating_jittered"],
                        mode="markers",
                        marker=dict(
                            size=marker_size * 2,
                            color="gold",
                            line=dict(color="white", width=2),
                            opacity=1.0,
                        ),
                        customdata=selected_data[
                            ["name", "average_weight", "average_rating", "users_rated"]
                        ].values,
                        hovertemplate="<b>%{customdata[0]} (SELECTED)</b><br>"
                        + "Complexity: %{customdata[1]:.2f}/5<br>"
                        + "Average Rating: %{customdata[2]:.2f}<br>"
                        + "User Ratings: %{customdata[3]:,}<br>"
                        + "<extra></extra>",
                        showlegend=False,
                        name="Selected Games",
                    )
                )
        else:
            fig.update_traces(marker=dict(size=marker_size))

        return fig

    def create_users_by_year_chart(
        df_sample: pd.DataFrame, is_modal: bool = False, selected_games: list[int] | None = None
    ) -> dict[str, Any]:
        """Create the users by year scatter plot.

        Args:
            df_sample: Pre-processed DataFrame with sampling and jitter applied
            is_modal: Whether this is for the modal (larger) version
            selected_games: List of selected game IDs to highlight

        Returns:
            Plotly figure for users by year
        """
        if selected_games is None:
            selected_games = []

        # Use the pre-processed data that already has sampling and jitter applied
        # Add log_users_rated if not already present
        if "log_users_rated" not in df_sample.columns:
            df_sample = df_sample.copy()
            df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])

        fig = px.scatter(
            df_sample,
            x="year_published_jittered",
            y="log_users_rated",
            color="bayes_average",
            title="User Rating Trends" if is_modal else None,
            labels={
                "year_published_jittered": "Year Published",
                "average_weight": "Average Complexity",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            range_color=[5, 8],
            template=PLOTLY_TEMPLATE,
            opacity=0.6,
            hover_data=["name", "year_published", "users_rated"],
        )

        # Customize hover template for better readability
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Year Published: %{customdata[1]}<br>"
            + "User Ratings: %{customdata[2]:,}<br>"
            + "Geek Rating: %{marker.color:.2f}<br>"
            + "<extra></extra>"
        )

        # Configure layout based on modal vs regular view
        if is_modal:
            margin = dict(l=60, r=60, t=80, b=60)
            font_size = 14
            marker_size = 6
            height = 600
        else:
            margin = dict(l=40, r=40, t=60, b=40)
            font_size = None
            marker_size = 4
            height = None

        fig.update_layout(
            xaxis_title="Year Published",
            yaxis_title="Users Rated (logged)",
            margin=margin,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=font_size) if font_size else dict(color="white"),
            coloraxis_colorbar=dict(title="Geek Rating"),
            height=height,
        )

        # Add highlighting for selected games
        if selected_games:
            # Create a mask for selected games
            selected_mask = df_sample["game_id"].isin(selected_games)

            if selected_mask.any():
                # Dim non-selected points
                fig.update_traces(
                    marker=dict(size=marker_size, opacity=0.3), selector=dict(type="scatter")
                )

                # Add highlighted points for selected games
                selected_data = df_sample[selected_mask]

                fig.add_trace(
                    go.Scatter(
                        x=selected_data["year_published_jittered"],
                        y=selected_data["log_users_rated"],
                        mode="markers",
                        marker=dict(
                            size=marker_size * 2,
                            color="gold",
                            line=dict(color="white", width=2),
                            opacity=1.0,
                        ),
                        customdata=selected_data[["name", "year_published", "users_rated"]].values,
                        hovertemplate="<b>%{customdata[0]} (SELECTED)</b><br>"
                        + "Year Published: %{customdata[1]}<br>"
                        + "User Ratings: %{customdata[2]:,}<br>"
                        + "Geek Rating: %{marker.color:.2f}<br>"
                        + "<extra></extra>",
                        showlegend=False,
                        name="Selected Games",
                    )
                )
        else:
            fig.update_traces(marker=dict(size=marker_size))

        return fig

    def create_rating_vs_users_chart(
        df_sample: pd.DataFrame, is_modal: bool = False, selected_games: list[int] | None = None
    ) -> dict[str, Any]:
        """Create the rating vs users scatter plot.

        Args:
            df_sample: Pre-processed DataFrame with sampling and jitter applied
            is_modal: Whether this is for the modal (larger) version
            selected_games: List of selected game IDs to highlight

        Returns:
            Plotly figure for rating vs users
        """
        if selected_games is None:
            selected_games = []

        # Use the pre-processed data that already has sampling and jitter applied
        # Add log_users_rated and log_users_jittered if not already present
        if "log_users_jittered" not in df_sample.columns:
            df_sample = df_sample.copy()
            if "log_users_rated" not in df_sample.columns:
                df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])
            df_sample["log_users_jittered"] = df_sample["log_users_rated"] + np.random.uniform(
                -0.05, 0.05, len(df_sample)
            )

        fig = px.scatter(
            df_sample,
            x="average_rating_jittered",
            y="log_users_jittered",
            color="bayes_average",
            title="Average Rating vs User Ratings" if is_modal else None,
            labels={
                "average_rating_jittered": "Average Rating",
                "log_users_jittered": "Log₁₀(User Ratings)",
                "bayes_average": "Geek Rating",
            },
            template=PLOTLY_TEMPLATE,
            opacity=0.6,
            range_color=[5, 8],
            hover_data=["name", "average_rating", "users_rated", "bayes_average"],
        )

        # Customize hover template for better readability
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Average Rating: %{customdata[1]:.2f}<br>"
            + "User Ratings: %{customdata[2]:,}<br>"
            + "Geek Rating: %{customdata[3]:.2f}<br>"
            + "<extra></extra>"
        )

        # Configure layout based on modal vs regular view
        if is_modal:
            margin = dict(l=60, r=60, t=80, b=60)
            font_size = 14
            marker_size = 6
            height = 600
        else:
            margin = dict(l=40, r=40, t=60, b=40)
            font_size = None
            marker_size = 4
            height = None

        fig.update_layout(
            xaxis_title="Average Rating",
            yaxis_title="Log₁₀(User Ratings)",
            margin=margin,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=font_size) if font_size else dict(color="white"),
            coloraxis_colorbar=dict(title="Geek Rating"),
            height=height,
        )

        # Add highlighting for selected games
        if selected_games:
            # Create a mask for selected games
            selected_mask = df_sample["game_id"].isin(selected_games)

            if selected_mask.any():
                # Dim non-selected points
                fig.update_traces(
                    marker=dict(size=marker_size, opacity=0.3), selector=dict(type="scatter")
                )

                # Add highlighted points for selected games
                selected_data = df_sample[selected_mask]

                fig.add_trace(
                    go.Scatter(
                        x=selected_data["average_rating_jittered"],
                        y=selected_data["log_users_jittered"],
                        mode="markers",
                        marker=dict(
                            size=marker_size * 2,
                            color="gold",
                            line=dict(color="white", width=2),
                            opacity=1.0,
                        ),
                        customdata=selected_data[
                            ["name", "average_rating", "users_rated", "bayes_average"]
                        ].values,
                        hovertemplate="<b>%{customdata[0]} (SELECTED)</b><br>"
                        + "Average Rating: %{customdata[1]:.2f}<br>"
                        + "User Ratings: %{customdata[2]:,}<br>"
                        + "Geek Rating: %{customdata[3]:.2f}<br>"
                        + "<extra></extra>",
                        showlegend=False,
                        name="Selected Games",
                    )
                )
        else:
            fig.update_traces(marker=dict(size=marker_size))

        return fig

    @app.callback(
        Output("weight-vs-rating-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_weight_vs_rating_chart(pathname: str) -> dict[str, Any]:
        """Update the complexity vs rating scatter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for complexity vs rating
        """
        if pathname != "/app/game-ratings":
            return {}

        df_sample = get_prepared_dashboard_data()
        return create_weight_vs_rating_chart(df_sample, is_modal=False)

    @app.callback(
        Output("complexity-by-year-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_complexity_by_year_chart(pathname: str) -> dict[str, Any]:
        """Update the users by year scatter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for users by year
        """
        if pathname != "/app/game-ratings":
            return {}

        df_sample = get_prepared_dashboard_data()
        return create_users_by_year_chart(df_sample, is_modal=False)

    @app.callback(
        Output("rating-vs-users-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_rating_vs_users_chart(pathname: str) -> dict[str, Any]:
        """Update the rating vs users scatter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for rating vs users
        """
        if pathname != "/app/game-ratings":
            return {}

        df_sample = get_prepared_dashboard_data()
        return create_rating_vs_users_chart(df_sample, is_modal=False)
