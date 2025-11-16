"""Filter callbacks for the Board Game Data Explorer."""

import logging
from typing import Dict, List, Any, Optional, Tuple

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from flask_caching import Cache
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from ..data.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


def register_filter_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register filter-related callbacks.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Initialize BigQuery client
    bq_client = BigQueryClient()

    @app.callback(
        Output("year-range-output", "children"),
        [Input("year-range-slider", "value")],
    )
    def update_year_range_output(value: List[int]) -> str:
        """Update the year range output text.

        Args:
            value: Min and max year values

        Returns:
            Text displaying the selected year range
        """
        if not value:
            return "All years"
        return f"Years: {value[0]} to {value[1]}"

    @app.callback(
        Output("complexity-range-output", "children"),
        [Input("complexity-range-slider", "value")],
    )
    def update_complexity_range_output(value: List[float]) -> str:
        """Update the complexity range output text.

        Args:
            value: Min and max complexity values

        Returns:
            Text displaying the selected complexity range
        """
        if not value:
            return "All complexity levels"
        return f"Complexity: {value[0]:.1f} to {value[1]:.1f}"

    @app.callback(
        Output("player-count-output", "children"),
        [Input("filter-options-container", "children")],
    )
    def init_player_count_output(_: Any) -> str:
        """Initialize the player count output text.

        Args:
            _: Dummy input to trigger the callback

        Returns:
            Initial player count output text
        """
        return "All player counts"

    @app.callback(
        [
            Output("player-count-best-button", "outline"),
            Output("player-count-recommended-button", "outline"),
            Output("player-count-type-store", "children"),
        ],
        [
            Input("player-count-best-button", "n_clicks"),
            Input("player-count-recommended-button", "n_clicks"),
        ],
        [State("player-count-type-store", "children")],
    )
    def toggle_player_count_type(
        best_clicks: Optional[int], recommended_clicks: Optional[int], current_type: str
    ) -> Tuple[bool, bool, str]:
        """Toggle between Best and Recommended player count types.

        Args:
            best_clicks: Number of clicks on the Best button
            recommended_clicks: Number of clicks on the Recommended button
            current_type: Current player count type

        Returns:
            Tuple of (best_button_outline, recommended_button_outline, player_count_type)
        """
        ctx = dash.callback_context

        if not ctx.triggered:
            # Default to "best" if no button has been clicked
            return False, True, "best"

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "player-count-best-button":
            return False, True, "best"
        elif button_id == "player-count-recommended-button":
            return True, False, "recommended"

        # Fallback to current state if something unexpected happens
        return current_type == "recommended", current_type == "best", current_type

    @app.callback(
        Output("player-count-output", "children", allow_duplicate=True),
        [
            Input("player-count-dropdown", "value"),
            Input("player-count-type-store", "children"),
        ],
        prevent_initial_call=True,
    )
    def update_player_count_output(player_count: Optional[int], player_count_type: str) -> str:
        """Update the player count output text.

        Args:
            player_count: Selected player count
            player_count_type: Type of player count (best or recommended)

        Returns:
            Text displaying the selected player count
        """
        if not player_count:
            return "All player counts"

        type_display = "Best" if player_count_type == "best" else "Recommended"
        return f"{type_display} for {player_count} players"

    @app.callback(
        Output("reset-filters-container", "style"),
        [
            Input("publisher-dropdown", "value"),
            Input("designer-dropdown", "value"),
            Input("category-dropdown", "value"),
            Input("mechanic-dropdown", "value"),
            Input("year-range-slider", "value"),
            Input("complexity-range-slider", "value"),
            Input("player-count-dropdown", "value"),
        ],
    )
    def show_reset_button(
        publishers: Optional[List[int]],
        designers: Optional[List[int]],
        categories: Optional[List[int]],
        mechanics: Optional[List[int]],
        year_range: List[int],
        complexity_range: List[float],
        player_count: Optional[int],
    ) -> Dict[str, str]:
        """Show the reset button if any filters are applied.

        Args:
            publishers: Selected publisher IDs
            designers: Selected designer IDs
            categories: Selected category IDs
            mechanics: Selected mechanic IDs
            year_range: Min and max year published
            complexity_range: Min and max complexity
            player_count_range: Min and max player count

        Returns:
            Style dictionary for the reset button container
        """
        # Check if any filters are applied
        any_filters = (
            (publishers and len(publishers) > 0)
            or (designers and len(designers) > 0)
            or (categories and len(categories) > 0)
            or (mechanics and len(mechanics) > 0)
            or (year_range is not None and len(year_range) == 2)
            or (complexity_range is not None and len(complexity_range) == 2)
            or (player_count is not None)
        )

        # Show the reset button if any filters are applied
        if any_filters:
            return {"display": "block", "margin-top": "20px"}
        else:
            return {"display": "none"}

    @app.callback(
        [
            Output("publisher-dropdown", "value"),
            Output("designer-dropdown", "value"),
            Output("category-dropdown", "value"),
            Output("mechanic-dropdown", "value"),
            Output("year-range-slider", "value"),
            Output("complexity-range-slider", "value"),
            Output("player-count-dropdown", "value"),
            Output("player-count-best-button", "outline", allow_duplicate=True),
            Output("player-count-recommended-button", "outline", allow_duplicate=True),
            Output("player-count-type-store", "children", allow_duplicate=True),
        ],
        [Input("reset-filters-button", "n_clicks")],
        prevent_initial_call=True,
    )
    def reset_filters(n_clicks: int) -> Tuple:
        """Reset all filters to their default values.

        Args:
            n_clicks: Number of times the reset button has been clicked

        Returns:
            Tuple of default values for all filters
        """
        return None, None, None, None, None, None, None, False, True, "best"

    @cache.memoize()
    def get_summary_stats() -> Dict[str, Any]:
        """Get summary statistics for the dashboard.

        Returns:
            Dictionary with summary statistics
        """
        logger.info("Fetching summary statistics from BigQuery")
        return bq_client.get_summary_stats()

    @app.callback(
        Output("summary-stats-container", "children"),
        [Input("refresh-stats-button", "n_clicks")],
    )
    def update_summary_stats(n_clicks: Optional[int]) -> html.Div:
        """Update the summary statistics.

        Args:
            n_clicks: Number of times the refresh button has been clicked

        Returns:
            Div containing summary statistics
        """
        # Get summary statistics
        stats = get_summary_stats()

        # Create summary cards
        total_games_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H5("Total Games", className="card-title"),
                    html.H2(f"{stats['total_games']:,}", className="card-text"),
                ]
            ),
            className="mb-4",
        )

        rated_games_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H5("Rated Games", className="card-title"),
                    html.H2(f"{stats['rated_games']:,}", className="card-text"),
                ]
            ),
            className="mb-4",
        )

        categories_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H5("Categories", className="card-title"),
                    html.H2(f"{stats['entity_counts']['category_count']:,}", className="card-text"),
                ]
            ),
            className="mb-4",
        )

        mechanics_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H5("Mechanics", className="card-title"),
                    html.H2(f"{stats['entity_counts']['mechanic_count']:,}", className="card-text"),
                ]
            ),
            className="mb-4",
        )

        # Create rating distribution chart
        rating_df = pd.DataFrame(stats["rating_distribution"])
        rating_fig = px.bar(
            rating_df,
            x="rating_bin",
            y="game_count",
            title="Geek Rating Distribution",
            labels={"rating_bin": "Geek Rating", "game_count": "Number of Games"},
            template="plotly_dark",
        )
        rating_fig.update_layout(
            xaxis_title="Rating",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
        )
        rating_fig.update_traces(marker_color="#2FA4E7")  # Cerulean blue

        # Create year distribution chart
        year_df = pd.DataFrame(stats["year_distribution"])
        year_fig = px.bar(
            year_df,
            x="year_published",
            y="game_count",
            title="Games Published by Year",
            labels={"year_published": "Year", "game_count": "Number of Games"},
            template="plotly_dark",
        )
        year_fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
        )
        year_fig.update_traces(marker_color="#2FA4E7")  # Cerulean blue

        # Create summary container
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(total_games_card, width=3),
                        dbc.Col(rated_games_card, width=3),
                        dbc.Col(categories_card, width=3),
                        dbc.Col(mechanics_card, width=3),
                    ],
                    className="mb-4",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        # html.H5("Rating Distribution", className="card-title"),
                                        dcc.Graph(figure=rating_fig),
                                    ]
                                )
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        # html.H5("Games Published by Year", className="card-title"),
                                        dcc.Graph(figure=year_fig),
                                    ]
                                )
                            ),
                            width=6,
                        ),
                    ]
                ),
            ]
        )
