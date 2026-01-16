"""Similarity search callbacks for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from dash import html, dcc, no_update
from dash.dependencies import Input, Output, State
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from flask_caching import Cache
import pandas as pd

from ..data.bigquery_client import BigQueryClient
from ..data.similarity_client import get_similarity_client as create_similarity_client, SimilarityFilters
from ..components.ag_grid_config import (
    get_default_grid_options,
    get_default_column_def,
    get_grid_style,
    get_grid_class_name,
)

logger = logging.getLogger(__name__)


def get_similarity_results_column_defs() -> list[dict[str, Any]]:
    """Get column definitions for similarity search results.

    Returns:
        List of column definitions.
    """
    return [
        {
            "field": "thumbnail",
            "headerName": "",
            "width": 60,
            "cellRenderer": "ThumbnailImage",
            "sortable": False,
            "filter": False,
        },
        {
            "field": "year_published",
            "headerName": "Year",
            "width": 80,
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "name",
            "headerName": "Name",
            "flex": 2,
            "minWidth": 200,
            "filter": "agTextColumnFilter",
            "cellRenderer": "ExternalLink",
        },
        {
            "field": "distance",
            "headerName": "Similarity",
            "width": 100,
            "valueFormatter": {"function": "d3.format('.1%')(1 - params.value)"},
            "filter": "agNumberColumnFilter",
            "sort": "asc",
            "cellStyle": {
                "function": "(1 - params.value) >= 0.9 ? {'color': 'var(--bs-success)', 'fontWeight': 'bold'} : (1 - params.value) < 0.7 ? {'color': 'var(--bs-warning)'} : {}"
            },
        },
        {
            "field": "geek_rating",
            "headerName": "Geek Rating",
            "width": 110,
            "valueFormatter": {"function": "params.value ? d3.format('.2f')(params.value) : '-'"},
            "filter": "agNumberColumnFilter",
            "cellStyle": {
                "function": "params.value >= 8.0 ? {'color': 'var(--bs-success)', 'fontWeight': 'bold'} : params.value < 6.0 ? {'color': 'var(--bs-danger)'} : {}"
            },
        },
        {
            "field": "average_rating",
            "headerName": "Avg Rating",
            "width": 100,
            "valueFormatter": {"function": "params.value ? d3.format('.2f')(params.value) : '-'"},
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "complexity",
            "headerName": "Complexity",
            "width": 100,
            "valueFormatter": {"function": "params.value ? d3.format('.2f')(params.value) : '-'"},
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "users_rated",
            "headerName": "Ratings",
            "width": 100,
            "valueFormatter": {"function": "params.value ? d3.format(',')(params.value) : '-'"},
            "filter": "agNumberColumnFilter",
        },
    ]


def register_similarity_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register similarity search callbacks.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Lazy-load clients
    def get_bq_client() -> BigQueryClient:
        """Get or create BigQuery client instance."""
        if not hasattr(get_bq_client, "_client"):
            get_bq_client._client = BigQueryClient()
        return get_bq_client._client

    def get_similarity_client():
        """Get or create Similarity Search client instance."""
        if not hasattr(get_similarity_client, "_client"):
            get_similarity_client._client = create_similarity_client()
        return get_similarity_client._client

    @cache.memoize(timeout=3600)  # Cache for 1 hour
    def get_game_options() -> list[dict[str, Any]]:
        """Get game options for the dropdown.

        Returns:
            List of game options with label and value.
        """
        logger.info("Fetching game options for similarity dropdown")
        query = """
        SELECT game_id, name, year_published, bayes_average
        FROM `${project_id}.${dataset}.games_active`
        WHERE bayes_average IS NOT NULL AND bayes_average > 0
        ORDER BY bayes_average DESC
        LIMIT 10000
        """
        df = get_bq_client().execute_query(query)

        options = []
        for _, row in df.iterrows():
            year = f" ({int(row['year_published'])})" if pd.notna(row["year_published"]) else ""
            label = f"{row['name']}{year}"
            options.append({"label": label, "value": int(row["game_id"])})

        return options

    @app.callback(
        [
            Output("similarity-game-dropdown", "options"),
            Output("similarity-game-dropdown", "value"),
        ],
        Input("url", "pathname"),
    )
    def populate_game_dropdown(pathname: str) -> tuple[list[dict[str, Any]], int | None]:
        """Populate the game dropdown when the page loads.

        Args:
            pathname: Current URL path.

        Returns:
            Tuple of (list of game options, default selected value).
        """
        if pathname != "/app/game-similarity":
            return [], None

        try:
            options = get_game_options()
            # Default to first game in the list
            default_value = options[0]["value"] if options else None
            return options, default_value
        except Exception as e:
            logger.exception("Error fetching game options: %s", str(e))
            return [], None

    @app.callback(
        [
            Output("similarity-filter-collapse", "is_open"),
            Output("similarity-filter-chevron", "className"),
        ],
        Input("similarity-filter-toggle", "n_clicks"),
        State("similarity-filter-collapse", "is_open"),
    )
    def toggle_filter_collapse(n_clicks: int | None, is_open: bool) -> tuple[bool, str]:
        """Toggle the filter collapse section.

        Args:
            n_clicks: Number of clicks on toggle button.
            is_open: Current collapse state.

        Returns:
            Tuple of (new collapse state, chevron icon class).
        """
        if n_clicks is None:
            return False, "fas fa-chevron-down ms-2"

        new_state = not is_open
        chevron_class = "fas fa-chevron-up ms-2" if new_state else "fas fa-chevron-down ms-2"
        return new_state, chevron_class

    @app.callback(
        [
            Output("similarity-search-button", "disabled"),
            Output("similarity-selected-game-store", "data"),
        ],
        Input("similarity-game-dropdown", "value"),
    )
    def handle_game_selection(game_id: int | None) -> tuple[bool, dict | None]:
        """Handle game selection to enable/disable search button.

        Args:
            game_id: Selected game ID.

        Returns:
            Tuple of (button disabled state, selected game data).
        """
        if game_id is None:
            return True, None

        # Fetch game info from games_features for preview card (includes categories, mechanics, etc.)
        try:
            query = f"""
            SELECT game_id, name, year_published, bayes_average, average_weight, thumbnail,
                   min_players, max_players, min_playtime, max_playtime,
                   categories, mechanics, families
            FROM `${{project_id}}.${{dataset}}.games_features`
            WHERE game_id = {game_id}
            """
            df = get_bq_client().execute_query(query)
            if not df.empty:
                game_data = df.iloc[0].to_dict()
                return False, game_data
        except Exception as e:
            logger.warning("Could not fetch game info for preview: %s", str(e))

        # Enable button even if preview fails
        return False, None

    @app.callback(
        [
            Output("similarity-source-game-card", "style"),
            Output("similarity-source-game-info", "children"),
        ],
        Input("similarity-selected-game-store", "data"),
    )
    def display_selected_game(game_data: dict | None) -> tuple[dict, Any]:
        """Display information about the selected source game.

        Args:
            game_data: Selected game data from store.

        Returns:
            Tuple of (card style, card content).
        """
        if game_data is None or game_data.get("name") is None:
            return {"display": "none"}, None

        # Build game info display
        game_id = game_data.get("game_id", "")
        thumbnail = game_data.get("thumbnail", "")
        name = game_data.get("name", "")
        year = game_data.get("year_published", "")
        rating = game_data.get("bayes_average", 0)
        complexity = game_data.get("average_weight", 0)
        min_players = game_data.get("min_players")
        max_players = game_data.get("max_players")
        min_playtime = game_data.get("min_playtime")
        max_playtime = game_data.get("max_playtime")
        categories = game_data.get("categories", []) or []
        mechanics = game_data.get("mechanics", []) or []
        families = game_data.get("families", []) or []

        # Format player count string
        if min_players and max_players:
            if min_players == max_players:
                players_str = f"{int(min_players)} players"
            elif max_players >= 8:
                players_str = f"{int(min_players)}-8+ players"
            else:
                players_str = f"{int(min_players)}-{int(max_players)} players"
        elif min_players:
            players_str = f"{int(min_players)}+ players"
        elif max_players:
            players_str = f"Up to {int(max_players)} players"
        else:
            players_str = None

        # Format playtime string
        if min_playtime and max_playtime:
            if min_playtime == max_playtime:
                playtime_str = f"{int(min_playtime)} min"
            else:
                playtime_str = f"{int(min_playtime)}-{int(max_playtime)} min"
        elif min_playtime:
            playtime_str = f"{int(min_playtime)}+ min"
        elif max_playtime:
            playtime_str = f"Up to {int(max_playtime)} min"
        else:
            playtime_str = None

        # Build BGG link
        bgg_url = f"https://boardgamegeek.com/boardgame/{game_id}"
        title_text = f"{name} ({int(year)})" if year else name

        # Helper to create badge list with limit
        def create_badges(items: list, color: str, max_items: int = 5) -> list:
            badges = []
            for item in items[:max_items]:
                badges.append(
                    dbc.Badge(item, color=color, className="me-1 mb-1", pill=True)
                )
            if len(items) > max_items:
                badges.append(
                    dbc.Badge(f"+{len(items) - max_items} more", color="secondary", className="me-1 mb-1", pill=True)
                )
            return badges

        content = dbc.Row(
            [
                dbc.Col(
                    html.Img(
                        src=thumbnail,
                        style={"height": "140px", "width": "140px", "objectFit": "cover"},
                        className="rounded shadow",
                    )
                    if thumbnail
                    else html.Div(),
                    width="auto",
                ),
                dbc.Col(
                    [
                        # Clickable title
                        html.H4(
                            html.A(
                                title_text,
                                href=bgg_url,
                                target="_blank",
                                rel="noopener noreferrer",
                                style={"textDecoration": "none"},
                            ),
                            className="mb-2",
                        ),
                        # Rating, complexity, players, and playtime badges
                        html.Div(
                            [
                                dbc.Badge(
                                    f"Rating: {rating:.1f}" if rating else "Unrated",
                                    color="success" if rating and rating >= 7 else "secondary",
                                    className="me-2 mb-2",
                                ),
                                dbc.Badge(
                                    f"Complexity: {complexity:.1f}" if complexity else "N/A",
                                    color="info",
                                    className="me-2 mb-2",
                                ),
                                dbc.Badge(
                                    players_str if players_str else "N/A",
                                    color="primary",
                                    className="me-2 mb-2",
                                ),
                                dbc.Badge(
                                    playtime_str if playtime_str else "N/A",
                                    color="secondary",
                                    className="me-2 mb-2",
                                ),
                            ],
                            className="mb-2",
                        ),
                        # Categories
                        html.Div(
                            [
                                html.Small("Categories: ", className="text-muted me-1"),
                                *create_badges(categories, "primary", max_items=4),
                            ],
                            className="mb-1",
                        ) if categories else None,
                        # Mechanics
                        html.Div(
                            [
                                html.Small("Mechanics: ", className="text-muted me-1"),
                                *create_badges(mechanics, "warning", max_items=4),
                            ],
                            className="mb-1",
                        ) if mechanics else None,
                        # Families
                        html.Div(
                            [
                                html.Small("Families: ", className="text-muted me-1"),
                                *create_badges(families, "dark", max_items=3),
                            ],
                        ) if families else None,
                    ],
                ),
            ],
            align="start",
        )

        return {"display": "block"}, content

    @app.callback(
        [
            Output("similarity-results-container", "children"),
            Output("similarity-loading", "children"),
        ],
        Input("similarity-search-button", "n_clicks"),
        [
            State("similarity-game-dropdown", "value"),
            State("similarity-top-k-dropdown", "value"),
            State("similarity-distance-dropdown", "value"),
            State("similarity-year-slider", "value"),
            State("similarity-complexity-slider", "value"),
            State("similarity-min-ratings-dropdown", "value"),
        ],
        prevent_initial_call=True,
    )
    def search_similar_games(
        n_clicks: int,
        game_id: int | None,
        top_k: int,
        distance_type: str,
        year_range: list[int],
        complexity_range: list[float],
        min_ratings: int,
    ) -> tuple[Any, str]:
        """Search for similar games.

        Args:
            n_clicks: Button click count.
            game_id: Selected game ID.
            top_k: Number of results to return.
            year_range: Min/max year filter.
            complexity_range: Min/max complexity filter.
            min_ratings: Minimum user ratings filter.

        Returns:
            Tuple of (results container, loading indicator).
        """
        if not n_clicks or game_id is None:
            return no_update, ""

        logger.info(f"Searching for games similar to game_id={game_id}")

        try:
            # Build filters
            filters = SimilarityFilters(
                min_year=year_range[0] if year_range else None,
                max_year=year_range[1] if year_range else None,
                min_complexity=complexity_range[0] if complexity_range else None,
                max_complexity=complexity_range[1] if complexity_range else None,
                min_users_rated=min_ratings if min_ratings > 0 else None,
            )

            # Call similarity service
            client = get_similarity_client()
            results_df = client.find_similar_games(
                game_id=game_id,
                top_k=top_k,
                distance_type=distance_type,
                filters=filters,
            )

            if results_df.empty:
                return (
                    html.Div(
                        dbc.Alert(
                            "No similar games found. Try adjusting your filters.",
                            color="warning",
                        ),
                        className="py-4",
                    ),
                    "",
                )

            # Thumbnail and Name are rendered by custom cell renderers

            # Create results grid
            grid_options = get_default_grid_options()
            grid_options["domLayout"] = "normal"
            grid_options["rowHeight"] = 50

            grid = dag.AgGrid(
                id="similarity-results-table",
                rowData=results_df.to_dict("records"),
                columnDefs=get_similarity_results_column_defs(),
                defaultColDef=get_default_column_def(),
                dashGridOptions=grid_options,
                className=get_grid_class_name(),
                style=get_grid_style("calc(100vh - 400px)"),
            )

            # Results header
            header = html.Div(
                [
                    html.H5(f"Found {len(results_df)} Similar Games", className="mb-3"),
                    html.P(
                        "Similarity is based on game mechanics, themes, and characteristics. "
                        "Higher percentages indicate more similar games.",
                        className="text-muted small mb-3",
                    ),
                ],
            )

            return html.Div([header, grid]), ""

        except Exception as e:
            logger.exception("Error searching for similar games: %s", str(e))

            # Check if it's a connection error
            error_msg = str(e)
            if "Connection" in error_msg or "refused" in error_msg.lower():
                error_detail = (
                    "Could not connect to the similarity search service. "
                    "Please ensure the service is running."
                )
            else:
                error_detail = f"An error occurred: {error_msg}"

            return (
                html.Div(
                    dbc.Alert(error_detail, color="danger"),
                    className="py-4",
                ),
                "",
            )
