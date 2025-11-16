"""Dashboard callbacks for the BGG Dash Viewer."""

import logging
from typing import Dict, List, Any, Optional

import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from flask_caching import Cache
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from ..data.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


def register_dashboard_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register dashboard-related callbacks.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Initialize BigQuery client
    bq_client = BigQueryClient()

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

        return bq_client.execute_query(query)

    def create_rating_by_year_chart(df: pd.DataFrame, is_modal: bool = False) -> Dict[str, Any]:
        """Create the rating by year scatter plot.

        Args:
            df: DataFrame with game data
            is_modal: Whether this is for the modal (larger) version

        Returns:
            Plotly figure for rating by year
        """
        # Sample data for better performance if dataset is large
        if len(df) > 25000:
            df_sample = df.sample(n=10000, random_state=42)
        else:
            df_sample = df

        # Add jitter to avoid overplotting
        np.random.seed(42)
        df_sample = df_sample.copy()
        df_sample["year_jittered"] = df_sample["year_published"] + np.random.uniform(
            -0.3, 0.3, len(df_sample)
        )

        # Color by number of ratings (log scale)
        df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])

        fig = px.scatter(
            df_sample,
            x="year_jittered",
            y="average_rating",
            color="average_rating",
            title=" Published (1975-Present)" if is_modal else None,
            labels={
                "year_jittered": "Year Published",
                "average_rating": "Average Rating",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            template="plotly_dark",
            opacity=0.6,
            range_color=[5, 9],
            hover_data=["name", "year_published", "users_rated"],
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

        fig.update_traces(marker=dict(size=marker_size))

        return fig

    @app.callback(
        Output("rating-by-year-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_rating_by_year_chart(pathname: str) -> Dict[str, Any]:
        """Update the rating by year jitter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for rating by year
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()
        return create_rating_by_year_chart(df, is_modal=False)

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
    ) -> tuple[bool, Dict[str, Any], str]:
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

        # Get the data for creating full-size charts
        df = get_dashboard_data()

        if button_id == "expand-rating-by-year-btn":
            fig = create_rating_by_year_chart(df, is_modal=True)
            return True, fig, "Average Rating by Year Published"

        elif button_id == "expand-weight-vs-rating-btn":
            fig = create_weight_vs_rating_chart(df, is_modal=True)
            return True, fig, "Complexity vs Average Rating"

        elif button_id == "expand-complexity-by-year-btn":
            fig = create_users_by_year_chart(df, is_modal=True)
            return True, fig, "User Ratings by Year Published"

        elif button_id == "expand-rating-vs-users-btn":
            fig = create_rating_vs_users_chart(df, is_modal=True)
            return True, fig, "Rating vs User Engagement"

        return False, {}, ""

    def create_weight_vs_rating_chart(df: pd.DataFrame, is_modal: bool = False) -> Dict[str, Any]:
        """Create the complexity vs rating scatter plot.

        Args:
            df: DataFrame with game data
            is_modal: Whether this is for the modal (larger) version

        Returns:
            Plotly figure for complexity vs rating
        """
        # Use all data (no sampling based on your adjustments)
        df_sample = df.copy()

        # Add jitter to avoid overplotting
        np.random.seed(42)
        df_sample["weight_jittered"] = df_sample["average_weight"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )
        df_sample["rating_jittered"] = df_sample["average_rating"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )

        # Size by number of ratings (log scale)
        df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])

        # Configure size based on modal vs regular view
        size_max = 20 if is_modal else 15
        size_column = "log_users_rated" if is_modal else None

        fig = px.scatter(
            df_sample,
            x="weight_jittered",
            y="rating_jittered",
            color="average_rating",
            labels={
                "weight_jittered": "Complexity Weight",
                "rating_jittered": "Average Rating",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            template="plotly_dark",
            opacity=0.45,
            hover_data=["name", "average_weight", "average_rating", "users_rated"],
            range_color=[5, 9],
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

        return fig

    def create_users_by_year_chart(df: pd.DataFrame, is_modal: bool = False) -> Dict[str, Any]:
        """Create the complexity by year scatter plot.

        Args:
            df: DataFrame with game data
            is_modal: Whether this is for the modal (larger) version

        Returns:
            Plotly figure for complexity by year
        """
        # Sample data for better performance if dataset is large
        if len(df) > 25000:
            df_sample = df.sample(n=10000, random_state=42)
        else:
            df_sample = df

        # Add jitter to avoid overplotting
        np.random.seed(42)
        df_sample = df_sample.copy()
        df_sample["year_jittered"] = df_sample["year_published"] + np.random.uniform(
            -0.3, 0.3, len(df_sample)
        )
        df_sample["weight_jittered"] = df_sample["average_weight"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )

        # Color by number of ratings (log scale)
        df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])

        fig = px.scatter(
            df_sample,
            x="year_jittered",
            y="log_users_rated",
            color="bayes_average",
            title="Complexity Trends Over Time" if is_modal else None,
            labels={
                "year_jittered": "Year Published",
                "average_weight": "Average Complexity",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            range_color=[5, 8],
            template="plotly_dark",
            opacity=0.6,
            hover_data=["name", "year_published", "users_rated"],
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

        fig.update_traces(marker=dict(size=marker_size))

        return fig

    def create_rating_vs_users_chart(df: pd.DataFrame, is_modal: bool = False) -> Dict[str, Any]:
        """Create the rating vs users scatter plot.

        Args:
            df: DataFrame with game data
            is_modal: Whether this is for the modal (larger) version

        Returns:
            Plotly figure for rating vs users
        """
        # Use all data (no sampling based on your preference)
        df_sample = df.copy()

        # Add jitter to avoid overplotting
        np.random.seed(42)
        df_sample["rating_jittered"] = df_sample["average_rating"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )

        # Log transform users_rated and add jitter
        df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])
        df_sample["log_users_jittered"] = df_sample["log_users_rated"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )

        fig = px.scatter(
            df_sample,
            x="rating_jittered",
            y="log_users_jittered",
            color="bayes_average",
            title="Average Rating vs User Ratings" if is_modal else None,
            labels={
                "rating_jittered": "Average Rating",
                "log_users_jittered": "Log₁₀(User Ratings)",
                "bayes_average": "Geek Rating",
            },
            template="plotly_dark",
            opacity=0.6,
            range_color=[5, 8],
            hover_data=["name", "average_rating", "users_rated", "bayes_average"],
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

        fig.update_traces(marker=dict(size=marker_size))

        return fig

    @app.callback(
        Output("weight-vs-rating-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_weight_vs_rating_chart(pathname: str) -> Dict[str, Any]:
        """Update the complexity vs rating scatter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for complexity vs rating
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()
        return create_weight_vs_rating_chart(df, is_modal=False)

    @app.callback(
        Output("complexity-by-year-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_complexity_by_year_chart(pathname: str) -> Dict[str, Any]:
        """Update the complexity by year scatter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for complexity by year
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()
        return create_users_by_year_chart(df, is_modal=False)

    @app.callback(
        Output("rating-vs-users-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_rating_vs_users_chart(pathname: str) -> Dict[str, Any]:
        """Update the rating vs users scatter plot.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for rating vs users
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()
        return create_rating_vs_users_chart(df, is_modal=False)
