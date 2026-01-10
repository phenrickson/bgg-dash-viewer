"""Search callbacks for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from dash import html
from dash.dependencies import Input, Output, State
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from flask_caching import Cache
import pandas as pd

from ..data.bigquery_client import BigQueryClient
from ..components.metrics_cards import create_metrics_cards
from ..components.ag_grid_config import (
    get_default_grid_options,
    get_default_column_def,
    get_grid_style,
    get_grid_class_name,
    get_search_results_column_defs,
)

logger = logging.getLogger(__name__)


def register_search_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register search-related callbacks.

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

    # Cache filter options to improve performance
    @cache.memoize(timeout=14400)  # Cache for 4 hours (data changes infrequently)
    def get_filter_options() -> dict[str, list[dict[str, Any]]]:
        """Get options for filter dropdowns.

        Returns:
            Dictionary with filter options
        """
        logger.info("Fetching filter options from BigQuery using optimized combined table")

        # Use the new optimized method that queries the pre-computed combined table
        return get_bq_client().get_all_filter_options()

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
            {"label": p['name'], "value": p["publisher_id"]}
            for p in filter_options["publishers"]
        ]

        designer_options = [
            {"label": d['name'], "value": d["designer_id"]}
            for d in filter_options["designers"]
        ]

        category_options = [
            {"label": c['name'], "value": c["category_id"]}
            for c in filter_options["categories"]
        ]

        mechanic_options = [
            {"label": m['name'], "value": m["mechanic_id"]}
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
            Output("loading-search-results", "children"),
            Output("search-metrics-cards-container", "children"),
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
        publishers: list[int] | None,
        designers: list[int] | None,
        categories: list[int] | None,
        mechanics: list[int] | None,
        year_range: list[int],
        complexity_range: list[float],
        player_count: int | None,
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
            Tuple of (search results container, loading indicator, metrics cards)
        """
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Skip search if this is just the initial page load with "init" value
        if trigger_id == "filter-options-container" and filter_options_trigger == "init":
            return html.Div(), "", html.Div()

        logger.info("Searching for games with filters")
        try:
            # Get games from BigQuery
            games_df = get_bq_client().get_games(
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

            # Create metrics cards
            metrics_cards = create_metrics_cards(games_df)

            if games_df.empty:
                return (
                    html.Div(
                        dbc.Alert(
                            "No games found matching your criteria. Try adjusting your filters.",
                            color="warning",
                        )
                    ),
                    "",
                    html.Div(),  # Empty metrics cards for no results
                )

            # Make the game name a clickable link to BGG
            games_df["name"] = games_df.apply(
                lambda row: f"[{row['name']}](https://boardgamegeek.com/boardgame/{row['game_id']})",
                axis=1,
            )

            # Create AG Grid with Vizro theming (fixed height to match filters)
            grid_options = get_default_grid_options()
            grid_options["domLayout"] = "normal"  # Use fixed height, not autoHeight

            grid = dag.AgGrid(
                id="results-table",
                rowData=games_df.to_dict("records"),
                columnDefs=get_search_results_column_defs(),
                defaultColDef=get_default_column_def(),
                dashGridOptions=grid_options,
                className=get_grid_class_name(),
                style=get_grid_style("calc(100vh - 350px)"),
            )

            return grid, "", metrics_cards

        except Exception as e:
            logger.exception("Error searching for games: %s", str(e))
            return (
                html.Div(
                    dbc.Alert(
                        f"An error occurred while searching for games: {str(e)}",
                        color="danger",
                    )
                ),
                "",
                html.Div(),  # Empty metrics cards for error case
            )
