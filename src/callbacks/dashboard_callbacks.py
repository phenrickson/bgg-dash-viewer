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
          AND year_published >= 1975
          AND year_published <= EXTRACT(YEAR FROM CURRENT_DATE())
        ORDER BY bayes_average DESC
        """

        return bq_client.execute_query(query)

    @app.callback(
        Output("rating-distribution-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_rating_distribution(pathname: str) -> Dict[str, Any]:
        """Update the rating distribution chart.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for rating distribution
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()

        fig = px.histogram(
            df,
            x="average_rating",
            nbins=50,
            title="Distribution of Average Ratings",
            labels={"average_rating": "Average Rating", "count": "Number of Games"},
            template="plotly_dark",
        )

        fig.update_layout(
            xaxis_title="Average Rating",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=False,
        )

        fig.update_traces(marker_color="#3498db", opacity=0.7)

        return fig

    @app.callback(
        Output("weight-distribution-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_weight_distribution(pathname: str) -> Dict[str, Any]:
        """Update the complexity distribution chart.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for complexity distribution
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()

        fig = px.histogram(
            df,
            x="average_weight",
            nbins=40,
            title="Distribution of Game Complexity",
            labels={"average_weight": "Complexity Weight", "count": "Number of Games"},
            template="plotly_dark",
        )

        fig.update_layout(
            xaxis_title="Complexity Weight",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=False,
        )

        fig.update_traces(marker_color="#e74c3c", opacity=0.7)

        return fig

    @app.callback(
        Output("users-rated-distribution-chart", "figure"),
        [Input("url", "pathname")],
    )
    def update_users_rated_distribution(pathname: str) -> Dict[str, Any]:
        """Update the users rated distribution chart.

        Args:
            pathname: URL pathname (used as trigger)

        Returns:
            Plotly figure for users rated distribution
        """
        if pathname != "/dashboard":
            return {}

        df = get_dashboard_data()

        # Create log-transformed data for better visualization
        df_log = df.copy()
        df_log["log_users_rated"] = np.log10(df_log["users_rated"])

        fig = px.histogram(
            df_log,
            x="log_users_rated",
            nbins=40,
            title="Distribution of User Ratings (Log Scale)",
            labels={"log_users_rated": "Log₁₀(Number of User Ratings)", "count": "Number of Games"},
            template="plotly_dark",
        )

        fig.update_layout(
            xaxis_title="Log₁₀(Number of User Ratings)",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=False,
        )

        fig.update_traces(marker_color="#f39c12", opacity=0.7)

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

        # Sample data for better performance if dataset is large
        if len(df) > 5000:
            df_sample = df.sample(n=5000, random_state=42)
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
            color="log_users_rated",
            title="Average Rating by Year Published (1975-Present)",
            labels={
                "year_jittered": "Year Published",
                "average_rating": "Average Rating",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            template="plotly_dark",
            opacity=0.6,
            hover_data=["name", "year_published", "users_rated"],
        )

        fig.update_layout(
            xaxis_title="Year Published",
            yaxis_title="Average Rating",
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            coloraxis_colorbar=dict(title="Log₁₀(User Ratings)"),
        )

        fig.update_traces(marker=dict(size=4))

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

        # Sample data for better performance if dataset is large
        if len(df) > 5000:
            df_sample = df.sample(n=5000, random_state=42)
        else:
            df_sample = df

        # Add jitter to avoid overplotting
        np.random.seed(42)
        df_sample = df_sample.copy()
        df_sample["weight_jittered"] = df_sample["average_weight"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )
        df_sample["rating_jittered"] = df_sample["average_rating"] + np.random.uniform(
            -0.05, 0.05, len(df_sample)
        )

        # Size by number of ratings (log scale)
        df_sample["log_users_rated"] = np.log10(df_sample["users_rated"])

        fig = px.scatter(
            df_sample,
            x="weight_jittered",
            y="rating_jittered",
            size="log_users_rated",
            color="log_users_rated",
            title="Game Complexity vs Average Rating",
            labels={
                "weight_jittered": "Complexity Weight",
                "rating_jittered": "Average Rating",
                "log_users_rated": "Log₁₀(User Ratings)",
            },
            template="plotly_dark",
            opacity=0.6,
            hover_data=["name", "average_weight", "average_rating", "users_rated"],
            size_max=15,
        )

        fig.update_layout(
            xaxis_title="Complexity Weight",
            yaxis_title="Average Rating",
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            coloraxis_colorbar=dict(title="Log₁₀(User Ratings)"),
        )

        return fig
