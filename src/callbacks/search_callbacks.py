"""Search callbacks for the BGG Dash Viewer."""

import logging
from typing import Dict, List, Any, Optional

import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from flask_caching import Cache
import pandas as pd

from ..data.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


def register_search_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register search-related callbacks.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Initialize BigQuery client
    bq_client = BigQueryClient()

    # Cache filter options to improve performance
    @cache.memoize(timeout=14400)  # Cache for 4 hours (data changes infrequently)
    def get_filter_options() -> Dict[str, List[Dict[str, Any]]]:
        """Get options for filter dropdowns.

        Returns:
            Dictionary with filter options
        """
        logger.info("Fetching filter options from BigQuery using optimized combined table")

        # Use the new optimized method that queries the pre-computed combined table
        return bq_client.get_all_filter_options()

    @app.callback(
        [
            Output("publisher-dropdown", "options"),
            Output("designer-dropdown", "options"),
            Output("category-dropdown", "options"),
            Output("mechanic-dropdown", "options"),
        ],
        [Input("filter-options-container", "children")],
    )
    def populate_filter_dropdowns(_: Any) -> tuple:
        """Populate filter dropdowns with options.

        Args:
            _: Dummy input to trigger the callback

        Returns:
            Tuple of dropdown options
        """
        filter_options = get_filter_options()

        publisher_options = [
            {"label": f"{p['name']} ({p['game_count']})", "value": p["publisher_id"]}
            for p in filter_options["publishers"]
        ]

        designer_options = [
            {"label": f"{d['name']} ({d['game_count']})", "value": d["designer_id"]}
            for d in filter_options["designers"]
        ]

        category_options = [
            {"label": f"{c['name']} ({c['game_count']})", "value": c["category_id"]}
            for c in filter_options["categories"]
        ]

        mechanic_options = [
            {"label": f"{m['name']} ({m['game_count']})", "value": m["mechanic_id"]}
            for m in filter_options["mechanics"]
        ]

        return (
            publisher_options,
            designer_options,
            category_options,
            mechanic_options,
        )

    @app.callback(
        [
            Output("search-results-container", "children"),
            Output("search-results-count", "children"),
            Output("loading-search-results", "children"),
        ],
        [Input("search-button", "n_clicks"), Input("filter-options-container", "children")],
        [
            State("publisher-dropdown", "value"),
            State("designer-dropdown", "value"),
            State("category-dropdown", "value"),
            State("mechanic-dropdown", "value"),
            State("year-range-slider", "value"),
            State("complexity-range-slider", "value"),
            State("player-count-dropdown", "value"),
            State("player-count-type-store", "children"),
            State("results-per-page", "value"),
        ],
    )
    def search_games(
        n_clicks: int,
        filter_options_trigger: str,
        publishers: Optional[List[int]],
        designers: Optional[List[int]],
        categories: Optional[List[int]],
        mechanics: Optional[List[int]],
        year_range: List[int],
        complexity_range: List[float],
        player_count: Optional[int],
        player_count_type: str,
        results_per_page: int,
    ) -> tuple:
        """Search for games based on filter criteria.

        Args:
            n_clicks: Number of times the search button has been clicked
            filter_options_trigger: Trigger for filter options loading
            publishers: Selected publisher IDs
            designers: Selected designer IDs
            categories: Selected category IDs
            mechanics: Selected mechanic IDs
            year_range: Min and max year published
            complexity_range: Min and max complexity
            player_count: Selected player count
            player_count_type: Type of player count (best or recommended)
            results_per_page: Number of results to display per page

        Returns:
            Tuple of (search results container, results count text, loading indicator)
        """
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Skip search if this is just the initial page load with "init" value
        if trigger_id == "filter-options-container" and filter_options_trigger == "init":
            return html.Div(), "", ""

        logger.info("Searching for games with filters")
        try:
            # Get games from BigQuery
            games_df = bq_client.get_games(
                limit=results_per_page,
                publishers=publishers,
                designers=designers,
                categories=categories,
                mechanics=mechanics,
                min_year=year_range[0] if year_range and len(year_range) == 2 else None,
                max_year=year_range[1] if year_range and len(year_range) == 2 else None,
                min_rating=None,
                max_rating=None,
                min_complexity=(
                    complexity_range[0] if complexity_range and len(complexity_range) == 2 else None
                ),
                max_complexity=(
                    complexity_range[1] if complexity_range and len(complexity_range) == 2 else None
                ),
                player_count=player_count,
                player_count_type=player_count_type if player_count is not None else None,
                best_player_count_only=False,  # We're using the new player_count_type parameter instead
            )

            # Create results count text
            results_count = f"Found {len(games_df)} games"

            if games_df.empty:
                return (
                    html.Div(
                        dbc.Alert(
                            "No games found matching your criteria. Try adjusting your filters.",
                            color="warning",
                        )
                    ),
                    results_count,
                    "",
                )

            # Format player counts as badges
            def format_player_counts(counts):
                if not counts or pd.isna(counts):
                    return ""
                return " ".join(
                    [
                        f"<span class='player-count-badge'>{c}</span>"
                        for c in str(counts).split(", ")
                    ]
                )

            # Apply formatting to player counts
            games_df["best_player_counts_formatted"] = games_df["best_player_counts"].apply(
                format_player_counts
            )
            games_df["recommended_player_counts_formatted"] = games_df[
                "recommended_player_counts"
            ].apply(format_player_counts)

            # Make the game name a clickable link to BGG
            games_df["name"] = games_df.apply(
                lambda row: f"[{row['name']}](https://boardgamegeek.com/boardgame/{row['game_id']})",
                axis=1,
            )

            # Create data table with improved styling
            table = dash_table.DataTable(
                id="results-table",
                columns=[
                    {"name": "Name", "id": "name", "presentation": "markdown"},
                    {"name": "Year", "id": "year_published"},
                    {
                        "name": "Geek Rating",
                        "id": "bayes_average",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "name": "Average Rating",
                        "id": "average_rating",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "name": "Complexity",
                        "id": "average_weight",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "name": "User Ratings",
                        "id": "users_rated",
                        "type": "numeric",
                        "format": {"specifier": ",d"},
                    },
                    {
                        "name": "Best Player Counts",
                        "id": "best_player_counts_formatted",
                        "type": "text",
                        "presentation": "markdown",
                    },
                    {
                        "name": "Recommended Player Counts",
                        "id": "recommended_player_counts_formatted",
                        "type": "text",
                        "presentation": "markdown",
                    },
                ],
                data=games_df.to_dict("records"),
                style_table={
                    "overflowX": "auto",
                    "borderRadius": "8px",  # Increased border radius
                    "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.2)",  # Enhanced shadow
                },
                style_cell={
                    "textAlign": "center",  # Default to center alignment for all columns
                    "padding": "12px 8px",  # Adjusted padding
                    "whiteSpace": "normal",
                    "height": "auto",
                    "fontSize": "14px",
                    "fontFamily": "'Roboto', 'Helvetica Neue', Arial, sans-serif",  # Match site font
                    "verticalAlign": "middle",  # Vertically center all cell content
                },
                # More consistent column widths
                style_cell_conditional=[
                    {
                        "if": {"column_id": "name"},
                        "textAlign": "left",  # Keep name column left-aligned
                        "width": "25%",  # Name column gets more space
                        "minWidth": "200px",
                    },
                    {
                        "if": {"column_id": "year_published"},
                        "width": "8%",
                        "minWidth": "80px",
                    },
                    {
                        "if": {"column_id": "bayes_average"},
                        "width": "10%",
                        "minWidth": "100px",
                    },
                    {
                        "if": {"column_id": "average_rating"},
                        "width": "10%",
                        "minWidth": "100px",
                    },
                    {
                        "if": {"column_id": "average_weight"},
                        "width": "10%",
                        "minWidth": "100px",
                    },
                    {
                        "if": {"column_id": "users_rated"},
                        "width": "10%",
                        "minWidth": "100px",
                    },
                    {
                        "if": {"column_id": "best_player_counts_formatted"},
                        "width": "13%",
                        "minWidth": "120px",
                    },
                    {
                        "if": {"column_id": "recommended_player_counts_formatted"},
                        "width": "14%",
                        "minWidth": "130px",
                    },
                ],
                # Enhanced header styling - removed uppercase transform
                style_header={
                    "backgroundColor": "#2c3e50",  # Darker header for better contrast
                    "color": "white",
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "padding": "15px 10px",
                    "borderBottom": "2px solid #34495e",
                },
                # Enhanced conditional styling
                style_data_conditional=[
                    # Removed alternating row colors (row banding) as per user feedback
                    # Highlight selected rows
                    {
                        "if": {"state": "selected"},
                        "backgroundColor": "#34495e",
                        "border": "1px solid #3498db",
                    },
                    # Bold game names
                    {
                        "if": {"column_id": "name"},
                        "fontWeight": "bold",
                    },
                    # Color-code ratings based on value
                    {
                        "if": {
                            "column_id": "bayes_average",
                            "filter_query": "{bayes_average} >= 8.0",
                        },
                        "color": "#2ecc71",  # Green for high ratings
                        "fontWeight": "bold",
                    },
                    {
                        "if": {
                            "column_id": "bayes_average",
                            "filter_query": "{bayes_average} < 6.0",
                        },
                        "color": "#e74c3c",  # Red for low ratings
                    },
                    {
                        "if": {
                            "column_id": "average_rating",
                            "filter_query": "{average_rating} >= 8.0",
                        },
                        "color": "#2ecc71",  # Green for high ratings
                        "fontWeight": "bold",
                    },
                    {
                        "if": {
                            "column_id": "average_rating",
                            "filter_query": "{average_rating} < 6.0",
                        },
                        "color": "#e74c3c",  # Red for low ratings
                    },
                ],
                page_size=10,
                page_action="native",
                sort_action="native",
                sort_mode="multi",  # Allow sorting by multiple columns
                filter_action="native",
                tooltip_delay=0,
                tooltip_duration=None,
                markdown_options={"link_target": "_blank", "html": True},  # Enable HTML in markdown
            )

            # Create results container
            results_container = html.Div(
                [
                    dbc.Card(
                        dbc.CardBody(
                            [
                                # html.H4("Search Results", className="card-title"),
                                html.Div(table),
                            ]
                        )
                    )
                ]
            )

            return results_container, results_count, ""

        except Exception as e:
            logger.exception("Error searching for games: %s", str(e))
            return (
                html.Div(
                    dbc.Alert(
                        f"An error occurred while searching for games: {str(e)}",
                        color="danger",
                    )
                ),
                "Error",
                "",
            )
