"""Metrics cards component for displaying key dashboard statistics."""

from typing import Dict, Any
import dash_bootstrap_components as dbc
from dash import html
import pandas as pd


def create_metrics_cards(df: pd.DataFrame) -> dbc.Row:
    """Create metrics cards showing key statistics.

    Args:
        df: DataFrame with game data

    Returns:
        Row containing metrics cards
    """
    if df.empty:
        return dbc.Row([])

    # Calculate metrics
    total_games = len(df)
    median_geek_rating = df["bayes_average"].median()
    median_average_rating = df["average_rating"].median()
    median_complexity = df["average_weight"].median()
    median_user_ratings = df["users_rated"].median()

    # Create individual metric cards
    cards = [
        create_metric_card(title="Total Games", value=f"{total_games:,}", color="primary"),
        create_metric_card(
            title="Median Geek Rating",
            value=f"{median_geek_rating:.2f}",
            color="success",
        ),
        create_metric_card(
            title="Median Rating",
            value=f"{median_average_rating:.2f}",
            color="info",
        ),
        create_metric_card(
            title="Median Complexity",
            value=f"{median_complexity:.2f}",
            color="warning",
        ),
        create_metric_card(
            title="Median User Ratings",
            value=f"{median_user_ratings:,.0f}",
            color="danger",
        ),
    ]

    return dbc.Row(
        [dbc.Col(card, width=12, md=6, lg=2, xl=2) for card in cards], className="mb-2 g-3"
    )


def create_metric_card(title: str, value: str, color: str) -> dbc.Card:
    """Create an individual metric card.

    Args:
        title: Card title
        value: Metric value to display
        color: Bootstrap color theme

    Returns:
        Metric card component
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.H5(value, className="mb-0 fw-bold text-center"),
                        html.P(title, className="text-muted mb-0 small text-center"),
                    ],
                    className="text-center",
                ),
            ],
            className="py-2 px-3",  # Reduced padding
        ),
        className="h-100 metric-card",
        style={
            "background": "linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)",
            "border": "1px solid rgba(255,255,255,0.1)",
            "backdrop-filter": "blur(10px)",
        },
    )
