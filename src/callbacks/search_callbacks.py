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

    @cache.memoize()
    def get_filter_options() -> Dict[str, List[Dict[str, Any]]]:
        """Get options for filter dropdowns.

        Returns:
            Dictionary with filter options
        """
        logger.info("Fetching filter options from BigQuery")

        # Get player counts separately
        player_counts = bq_client.get_player_counts()

        return {
            "publishers": bq_client.get_publishers(),
            "designers": bq_client.get_designers(),
            "categories": bq_client.get_categories(),
            "mechanics": bq_client.get_mechanics(),
            "player_counts": player_counts,
        }

    @app.callback(
        [
            Output("publisher-dropdown", "options"),
            Output("designer-dropdown", "options"),
            Output("category-dropdown", "options"),
            Output("mechanic-dropdown", "options"),
            Output("player-count-dropdown", "options"),
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

        player_count_options = [
            {"label": str(pc["player_count"]), "value": pc["player_count"]}
            for pc in filter_options["player_counts"]
        ]

        return (
            publisher_options,
            designer_options,
            category_options,
            mechanic_options,
            player_count_options,
        )

    @app.callback(
        [
            Output("search-results-container", "children"),
            Output("search-results-count", "children"),
            Output("loading-search-results", "children"),
        ],
        [Input("search-button", "n_clicks")],
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
            publishers: Selected publisher IDs
            designers: Selected designer IDs
            categories: Selected category IDs
            mechanics: Selected mechanic IDs
            year_range: Min and max year published
            complexity_range: Min and max complexity
            player_count_range: Min and max player count
            results_per_page: Number of results to display per page

        Returns:
            Tuple of (search results container, results count text, loading indicator)
        """
        if n_clicks is None:
            # Initial load, return empty results
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

            # Add BGG link column
            games_df["bgg_link"] = games_df["game_id"].apply(
                lambda x: f"https://boardgamegeek.com/boardgame/{x}"
            )

            # Add local link column
            games_df["view_details"] = games_df["game_id"].apply(lambda x: f"/game/{x}")

            # Create data table
            table = dash_table.DataTable(
                id="results-table",
                columns=[
                    {"name": "Name", "id": "name"},
                    {"name": "Year", "id": "year_published"},
                    {
                        "name": "Rating",
                        "id": "bayes_average",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "name": "Weight",
                        "id": "average_weight",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "name": "BGG",
                        "id": "bgg_link",
                        "presentation": "markdown",
                    },
                    {
                        "name": "Details",
                        "id": "view_details",
                        "presentation": "markdown",
                    },
                ],
                data=games_df.to_dict("records"),
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "10px",
                    "whiteSpace": "normal",
                    "height": "auto",
                },
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)",
                    }
                ],
                page_size=10,
                sort_action="native",
                filter_action="native",
                markdown_options={"link_target": "_blank"},
            )

            # Create results container
            results_container = html.Div(
                [
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Search Results", className="card-title"),
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
