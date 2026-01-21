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
from ..components.game_card import create_game_info_card
from ..components.game_comparison import (
    create_feature_comparison,
    create_neighbor_card,
)

logger = logging.getLogger(__name__)

# Default minimum ratings for similarity search results
DEFAULT_MIN_RATINGS = 100


def get_similarity_results_column_defs(distance_type: str = "cosine") -> list[dict[str, Any]]:
    """Get column definitions for similarity search results."""
    if distance_type == "cosine":
        distance_col = {
            "field": "distance",
            "headerName": "Similarity",
            "width": 100,
            "valueFormatter": {"function": "d3.format('.1%')(1 - params.value)"},
            "filter": "agNumberColumnFilter",
            "sort": "asc",
            "cellStyle": {
                "function": "(1 - params.value) >= 0.9 ? {'color': 'var(--bs-success)', 'fontWeight': 'bold'} : (1 - params.value) < 0.7 ? {'color': 'var(--bs-warning)'} : {}"
            },
        }
    elif distance_type == "euclidean":
        distance_col = {
            "field": "distance",
            "headerName": "Distance",
            "width": 100,
            "valueFormatter": {"function": "d3.format('.3f')(params.value)"},
            "filter": "agNumberColumnFilter",
            "sort": "asc",
            "cellStyle": {
                "function": "params.value <= 1.0 ? {'color': 'var(--bs-success)', 'fontWeight': 'bold'} : params.value > 3.0 ? {'color': 'var(--bs-warning)'} : {}"
            },
        }
    else:
        distance_col = {
            "field": "distance",
            "headerName": "Similarity",
            "width": 100,
            "valueFormatter": {"function": "d3.format('.3f')(-params.value)"},
            "filter": "agNumberColumnFilter",
            "sort": "asc",
            "cellStyle": {
                "function": "-params.value >= 0.9 ? {'color': 'var(--bs-success)', 'fontWeight': 'bold'} : -params.value < 0.5 ? {'color': 'var(--bs-warning)'} : {}"
            },
        }

    return [
        {"field": "year_published", "headerName": "Year", "width": 80, "filter": "agNumberColumnFilter"},
        {"field": "name", "headerName": "Name", "flex": 2, "minWidth": 200, "filter": "agTextColumnFilter", "cellRenderer": "ExternalLink"},
        distance_col,
        {"field": "geek_rating", "headerName": "Geek Rating", "width": 110, "valueFormatter": {"function": "params.value ? d3.format('.2f')(params.value) : '-'"}, "filter": "agNumberColumnFilter", "cellStyle": {"function": "params.value >= 8.0 ? {'color': 'var(--bs-success)', 'fontWeight': 'bold'} : params.value < 6.0 ? {'color': 'var(--bs-danger)'} : {}"}},
        {"field": "average_rating", "headerName": "Avg Rating", "width": 100, "valueFormatter": {"function": "params.value ? d3.format('.2f')(params.value) : '-'"}, "filter": "agNumberColumnFilter"},
        {"field": "complexity", "headerName": "Complexity", "width": 100, "valueFormatter": {"function": "params.value ? d3.format('.2f')(params.value) : '-'"}, "filter": "agNumberColumnFilter"},
        {"field": "users_rated", "headerName": "Ratings", "width": 100, "valueFormatter": {"function": "params.value ? d3.format(',')(params.value) : '-'"}, "filter": "agNumberColumnFilter"},
    ]


def register_similarity_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register similarity search callbacks."""

    def get_bq_client() -> BigQueryClient:
        if not hasattr(get_bq_client, "_client"):
            get_bq_client._client = BigQueryClient()
        return get_bq_client._client

    def get_similarity_client():
        if not hasattr(get_similarity_client, "_client"):
            get_similarity_client._client = create_similarity_client()
        return get_similarity_client._client

    @cache.memoize(timeout=86400)
    def get_top_games() -> list[dict[str, Any]]:
        """Load top 1000 games from pre-computed dropdown table - cached for 24 hours."""
        logger.info("Loading top games for dropdown")
        try:
            # Use pre-computed table for fast loading (created by dataform)
            query = """
            SELECT game_id, name, year_published
            FROM `${project_id}.${dataset}.game_dropdown_options`
            ORDER BY COALESCE(bayes_average, 0) DESC
            LIMIT 1000
            """
            df = get_bq_client().execute_query(query)
            logger.info(f"Loaded {len(df)} top games for dropdown")
            options = []
            for _, row in df.iterrows():
                year = f" ({int(row['year_published'])})" if pd.notna(row["year_published"]) else ""
                label = f"{row['name']}{year}"
                options.append({"label": label, "value": int(row["game_id"])})
            return options
        except Exception as e:
            logger.exception(f"Error loading games: {e}")
            return []

    @cache.memoize(timeout=3600)
    def search_all_games(search_term: str) -> list[dict[str, Any]]:
        """Search all games by name - for finding obscure games not in top 25k."""
        if not search_term or len(search_term) < 3:
            return []
        logger.info(f"Searching all games for: {search_term}")
        try:
            safe_term = search_term.replace("'", "''")
            query = f"""
            SELECT game_id, name, year_published
            FROM `${{project_id}}.${{dataset}}.games_features`
            WHERE LOWER(name) LIKE LOWER('%{safe_term}%')
            ORDER BY COALESCE(bayes_average, 0) DESC
            LIMIT 50
            """
            df = get_bq_client().execute_query(query)
            logger.info(f"Found {len(df)} games matching '{search_term}'")
            options = []
            for _, row in df.iterrows():
                year = f" ({int(row['year_published'])})" if pd.notna(row["year_published"]) else ""
                label = f"{row['name']}{year}"
                options.append({"label": label, "value": int(row["game_id"])})
            return options
        except Exception as e:
            logger.exception(f"Error searching games: {e}")
            return []

    # =========================================================================
    # Load Games Once on Page Load
    # =========================================================================

    @app.callback(
        Output("shared-game-dropdown", "options"),
        Input("similarity-tabs", "active_tab"),
        prevent_initial_call=False,
    )
    def load_game_options(active_tab):
        """Load top games once on page load."""
        logger.info("Loading game options for dropdown")
        return get_top_games()

    # =========================================================================
    # Tab Content Switching
    # =========================================================================

    @app.callback(
        [
            Output("tab-neighbors-content", "style"),
            Output("tab-compare-content", "style"),
            Output("tab-search-content", "style"),
        ],
        Input("similarity-tabs", "active_tab"),
    )
    def switch_tab_content(active_tab: str):
        """Show/hide tab content based on active tab."""
        neighbors_style = {"display": "block"} if active_tab == "tab-neighbors" else {"display": "none"}
        compare_style = {"display": "block"} if active_tab == "tab-compare" else {"display": "none"}
        search_style = {"display": "block"} if active_tab == "tab-search" else {"display": "none"}
        return neighbors_style, compare_style, search_style

    # =========================================================================
    # Shared Game Selector (for all tabs)
    # =========================================================================

    @app.callback(
        [
            Output("shared-search-button", "disabled"),
            Output("similarity-search-button", "disabled"),
        ],
        Input("shared-game-dropdown", "value"),
    )
    def handle_shared_game_selection(game_id: int | None):
        """Enable search buttons when a game is selected."""
        disabled = game_id is None
        return disabled, disabled

    @app.callback(
        Output("shared-search-collapse", "is_open"),
        Input("shared-search-all-link", "n_clicks"),
        State("shared-search-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_search_collapse(n_clicks: int, is_open: bool) -> bool:
        """Toggle the search all games collapse."""
        return not is_open

    @app.callback(
        Output("shared-game-search-results", "children"),
        Input("shared-game-search-input", "value"),
        prevent_initial_call=True,
    )
    def search_all_games_callback(search_term: str):
        """Search all games and display clickable results."""
        if not search_term or len(search_term) < 3:
            return html.Small("Type at least 3 characters to search", className="text-muted")

        results = search_all_games(search_term)
        if not results:
            return html.Small("No games found", className="text-muted")

        # Create clickable list items
        items = []
        for game in results[:10]:  # Limit to 10 results
            items.append(
                dbc.ListGroupItem(
                    game["label"],
                    id={"type": "search-result-item", "index": game["value"]},
                    action=True,
                    className="py-2",
                    style={"cursor": "pointer"},
                )
            )

        return dbc.ListGroup(items, flush=True)

    @app.callback(
        [
            Output("shared-game-dropdown", "value"),
            Output("shared-game-dropdown", "options", allow_duplicate=True),
            Output("shared-search-collapse", "is_open", allow_duplicate=True),
            Output("shared-game-search-input", "value"),
        ],
        Input({"type": "search-result-item", "index": dash.ALL}, "n_clicks"),
        State("shared-game-dropdown", "options"),
        prevent_initial_call=True,
    )
    def select_search_result(n_clicks_list, current_options):
        """Select a game from search results."""
        if not any(n_clicks_list):
            return no_update, no_update, no_update, no_update

        # Find which result was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update

        triggered_id = ctx.triggered[0]["prop_id"]
        if "search-result-item" not in triggered_id:
            return no_update, no_update, no_update, no_update

        import json
        try:
            id_dict = json.loads(triggered_id.split(".")[0])
            game_id = id_dict["index"]
        except (json.JSONDecodeError, KeyError):
            return no_update, no_update, no_update, no_update

        # Get the game info to add to dropdown options
        game_data = get_game_features(game_id)
        if game_data:
            year = f" ({int(game_data['year_published'])})" if game_data.get("year_published") else ""
            new_option = {"label": f"{game_data['name']}{year}", "value": game_id}

            # Add to options if not already present
            if not any(opt["value"] == game_id for opt in current_options):
                current_options = [new_option] + current_options

        return game_id, current_options, False, ""

    @cache.memoize(timeout=3600)
    def get_game_features(game_id: int) -> dict[str, Any] | None:
        query = f"""
        SELECT game_id, name, year_published, bayes_average, average_weight, thumbnail,
               min_players, max_players, min_playtime, max_playtime,
               categories, mechanics, families
        FROM `${{project_id}}.${{dataset}}.games_features`
        WHERE game_id = {game_id}
        """
        df = get_bq_client().execute_query(query)
        if not df.empty:
            return df.iloc[0].to_dict()
        return None

    def get_source_game_for_similarity(game_id: int) -> pd.DataFrame:
        """Get source game data from similarity search table for prepending to results."""
        query = f"""
        SELECT game_id, name, year_published, users_rated, average_rating,
               geek_rating, complexity, thumbnail
        FROM `${{project_id}}.${{dataset}}.game_similarity_search`
        WHERE game_id = {game_id}
        """
        return get_bq_client().execute_query(query)

    @cache.memoize(timeout=3600)
    def cached_find_similar_games(
        game_id: int,
        top_k: int,
        distance_type: str,
        embedding_dims: int | None,
        min_year: int | None,
        max_year: int | None,
        min_users_rated: int | None,
        complexity_mode: str | None,
        complexity_band: float | None,
        min_complexity: float | None,
        max_complexity: float | None,
    ) -> pd.DataFrame:
        """Cached wrapper for similarity search - avoids re-querying for same parameters."""
        filters = SimilarityFilters(
            min_year=min_year,
            max_year=max_year,
            min_users_rated=min_users_rated,
            complexity_mode=complexity_mode,
            complexity_band=complexity_band,
            min_complexity=min_complexity,
            max_complexity=max_complexity,
        )
        client = get_similarity_client()
        return client.find_similar_games(
            game_id=game_id,
            top_k=top_k,
            distance_type=distance_type,
            filters=filters,
            embedding_dims=embedding_dims,
        )

    # =========================================================================
    # Shared Search Callback (populates both Neighbors and Compare tabs)
    # =========================================================================

    @app.callback(
        [
            Output("neighbors-source-card-container", "children"),
            Output("neighbors-source-card-container", "style"),
            Output("neighbors-results-container", "children"),
            Output("compare-neighbors-list", "children"),
            Output("compare-panel", "children"),
            Output("shared-source-game-store", "data"),
            Output("shared-neighbors-store", "data"),
        ],
        Input("shared-search-button", "n_clicks"),
        State("shared-game-dropdown", "value"),
        prevent_initial_call=True,
        running=[
            (Output("shared-search-button", "disabled"), True, False),
            (Output("shared-search-button", "children"), "Searching...", "Find Similar Games"),
        ],
    )
    def shared_search_games(n_clicks: int, game_id: int | None):
        """Search for similar games and populate both Neighbors and Compare tabs."""
        # Default empty state for Compare tab
        compare_empty = html.Div([
            html.I(className="fas fa-list fa-3x text-muted mb-3"),
            html.H5("Select a Game", className="text-muted"),
            html.P("Select a game above to see its neighbors.", className="text-muted"),
        ], className="text-center py-5")
        compare_panel_empty = html.Div([
            html.I(className="fas fa-balance-scale fa-3x text-muted mb-3"),
            html.H5("Compare Games", className="text-muted"),
            html.P("Click a neighbor to see why it's similar.", className="text-muted"),
        ], className="text-center py-5")

        if game_id is None:
            neighbors_empty = html.Div([
                html.I(className="fas fa-users fa-3x text-muted mb-3"),
                html.H5("Select a Game", className="text-muted"),
                html.P("Select a game and click 'Find Similar Games' to see results.", className="text-muted"),
            ], className="text-center py-5")
            return (None, {"display": "none"}, neighbors_empty, compare_empty, compare_panel_empty, None, None)

        # Helper for safe array conversion (defined early so it can be used for source game)
        def safe_list(arr):
            if arr is None:
                return []
            try:
                return list(arr) if len(arr) > 0 else []
            except (TypeError, ValueError):
                return []

        try:
            # Fetch game data
            raw_game_data = get_game_features(game_id)
            if raw_game_data is None:
                return (None, {"display": "none"}, dbc.Alert("Could not load game data.", color="warning"),
                        compare_empty, compare_panel_empty, None, None)

            # Convert arrays for safe JSON serialization in store
            game_data = {
                **raw_game_data,
                "categories": safe_list(raw_game_data.get("categories")),
                "mechanics": safe_list(raw_game_data.get("mechanics")),
                "families": safe_list(raw_game_data.get("families")),
            }

            # Source card for Neighbors tab
            source_card_content = html.Div([
                html.H4("Selected Game", className="mb-3"),
                dbc.Card(
                    dbc.CardBody(create_game_info_card(game_data)),
                    className="mb-4 panel-card border-primary",
                    style={"borderWidth": "2px"},
                ),
            ])

            # Find neighbors
            logger.info(f"Finding neighbors for game_id={game_id}, name={game_data.get('name')}")
            neighbors_df = cached_find_similar_games(
                game_id=game_id,
                top_k=10,
                distance_type="cosine",
                embedding_dims=None,
                min_year=None,
                max_year=None,
                min_users_rated=DEFAULT_MIN_RATINGS,
                complexity_mode="within_band",
                complexity_band=0.75,
                min_complexity=None,
                max_complexity=None,
            )
            logger.info(f"Found {len(neighbors_df)} neighbors for game_id={game_id}")

            if neighbors_df.empty:
                no_results = dbc.Alert(
                    [html.Strong("No similar games found. "), f"This game (ID: {game_id}) may not have embeddings yet."],
                    color="warning",
                )
                return (source_card_content, {"display": "block"}, no_results,
                        compare_empty, compare_panel_empty, game_data, None)

            # Get full game data for all neighbors
            neighbor_ids = neighbors_df["game_id"].tolist()
            neighbor_ids_str = ",".join(str(int(g)) for g in neighbor_ids)
            query = f"""
            SELECT game_id, name, year_published, bayes_average, average_weight, thumbnail,
                   min_players, max_players, min_playtime, max_playtime,
                   categories, mechanics, families
            FROM `${{project_id}}.${{dataset}}.games_features`
            WHERE game_id IN ({neighbor_ids_str})
            """
            features_df = get_bq_client().execute_query(query)
            features_map = {int(row["game_id"]): row.to_dict() for _, row in features_df.iterrows()}

            # Build data for both tabs
            neighbors_data = []
            neighbor_cards = []
            for _, row in neighbors_df.iterrows():
                neighbor_id = int(row["game_id"])
                distance = row["distance"]
                similarity_pct = (1 - distance) * 100
                features = features_map.get(neighbor_id, {})

                # Store data for Compare tab
                neighbors_data.append({
                    "game_id": neighbor_id,
                    "name": features.get("name", row.get("name", "Unknown")),
                    "year_published": features.get("year_published"),
                    "thumbnail": features.get("thumbnail"),
                    "average_weight": features.get("average_weight"),
                    "min_players": features.get("min_players"),
                    "max_players": features.get("max_players"),
                    "min_playtime": features.get("min_playtime"),
                    "max_playtime": features.get("max_playtime"),
                    "categories": safe_list(features.get("categories")),
                    "mechanics": safe_list(features.get("mechanics")),
                    "families": safe_list(features.get("families")),
                    "distance": distance,
                    "similarity_pct": similarity_pct,
                })

                # Build card for Neighbors tab
                if features:
                    card_content = create_game_info_card(features)
                    if card_content:
                        neighbor_card = dbc.Card([
                            dbc.CardHeader(
                                html.Div([
                                    html.Span(f"#{len(neighbor_cards) + 1}", className="fw-bold"),
                                    dbc.Badge(
                                        f"{similarity_pct:.1f}% similar",
                                        color="success" if similarity_pct >= 90 else "info",
                                        className="ms-2",
                                    ),
                                ], className="d-flex align-items-center"),
                                className="py-2",
                            ),
                            dbc.CardBody(card_content),
                        ], className="mb-3 panel-card")
                        neighbor_cards.append(neighbor_card)

            # Build Neighbors tab content
            neighbors_content = html.Div([
                html.H4(f"Top {len(neighbor_cards)} Similar Games", className="mb-3 mt-2"),
                html.Div(neighbor_cards),
            ])

            # Build Compare tab neighbor list
            compare_list_content = []
            compare_list_content.append(html.Div([
                html.H6("Source Game", className="mb-2"),
                dbc.Card(
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(
                                html.Img(
                                    src=game_data.get("thumbnail", ""),
                                    style={"height": "50px", "width": "50px", "objectFit": "contain"},
                                    className="rounded",
                                ) if game_data.get("thumbnail") else None,
                                width="auto",
                            ),
                            dbc.Col([
                                html.Div(game_data.get("name", "Unknown"), className="fw-bold text-truncate"),
                                html.Small("Selected", className="text-primary"),
                            ]),
                        ], align="center"),
                    ], className="py-2"),
                    className="mb-3 border-primary border-2",
                ),
            ]))
            compare_list_content.append(html.H6("Similar Games", className="mb-2 mt-3"))
            compare_list_content.append(html.Small("Click a game to compare", className="text-muted d-block mb-2"))

            for neighbor in neighbors_data:
                compare_list_content.append(
                    html.Div(
                        create_neighbor_card(neighbor, neighbor["similarity_pct"], is_selected=False),
                        id={"type": "compare-neighbor-card", "index": neighbor["game_id"]},
                        n_clicks=0,
                    )
                )

            return (
                source_card_content,
                {"display": "block"},
                neighbors_content,
                html.Div(compare_list_content),
                compare_panel_empty,  # Reset comparison panel
                game_data,
                neighbors_data,
            )

        except Exception as e:
            logger.exception("Error loading neighbors: %s", str(e))
            error_alert = dbc.Alert(f"Error: {str(e)}", color="danger")
            return (None, {"display": "none"}, error_alert, compare_empty, compare_panel_empty, None, None)

    # =========================================================================
    # Similarity Search Tab Callbacks
    # =========================================================================

    @app.callback(
        Output("similarity-selected-game-store", "data"),
        Input("shared-game-dropdown", "value"),
    )
    def store_selected_game(game_id: int | None) -> dict | None:
        """Store selected game data for use by other callbacks."""
        if game_id is None:
            return None
        try:
            game_data = get_game_features(game_id)
            if game_data:
                return game_data
        except Exception as e:
            logger.warning("Could not fetch game info: %s", str(e))
        return None

    @app.callback(
        [
            Output("similarity-filter-collapse", "is_open"),
            Output("similarity-filter-chevron", "className"),
        ],
        Input("similarity-filter-toggle", "n_clicks"),
        State("similarity-filter-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_filter_collapse(n_clicks: int, is_open: bool) -> tuple[bool, str]:
        new_is_open = not is_open
        chevron_class = "fas fa-chevron-up ms-2" if new_is_open else "fas fa-chevron-down ms-2"
        return new_is_open, chevron_class

    @app.callback(
        [
            Output("similarity-complexity-band-container", "style"),
            Output("similarity-complexity-absolute-container", "style"),
        ],
        Input("similarity-complexity-mode-dropdown", "value"),
    )
    def toggle_complexity_ui(complexity_mode: str) -> tuple[dict, dict]:
        """Show/hide complexity controls based on selected mode."""
        if complexity_mode == "absolute":
            # Show absolute range slider, hide band slider
            return {"display": "none"}, {"display": "block"}
        else:
            # Show band slider, hide absolute range slider
            return {"display": "block"}, {"display": "none"}

    @app.callback(
        [
            Output("similarity-results-container", "children"),
            Output("similarity-loading", "children"),
        ],
        Input("similarity-search-button", "n_clicks"),
        [
            State("shared-game-dropdown", "value"),
            State("similarity-top-k-dropdown", "value"),
            State("similarity-distance-dropdown", "value"),
            State("similarity-embedding-dims-dropdown", "value"),
            State("similarity-year-slider", "value"),
            State("similarity-complexity-mode-dropdown", "value"),
            State("similarity-complexity-band-slider", "value"),
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
        embedding_dims: int,
        year_range: list[int],
        complexity_mode: str,
        complexity_band: float,
        complexity_range: list[float],
        min_ratings: int,
    ) -> tuple[Any, str]:
        if not n_clicks or game_id is None:
            return no_update, ""

        logger.info(f"Searching for games similar to game_id={game_id}, complexity_mode={complexity_mode}")

        try:
            # Use default min ratings if not specified
            effective_min_ratings = min_ratings if min_ratings > 0 else DEFAULT_MIN_RATINGS

            # Build filter parameters based on complexity mode
            if complexity_mode == "absolute":
                # Use absolute complexity range
                results_df = cached_find_similar_games(
                    game_id=game_id,
                    top_k=top_k,
                    distance_type=distance_type,
                    embedding_dims=embedding_dims,
                    min_year=year_range[0] if year_range else None,
                    max_year=year_range[1] if year_range else None,
                    min_users_rated=effective_min_ratings,
                    complexity_mode=None,
                    complexity_band=None,
                    min_complexity=complexity_range[0] if complexity_range else None,
                    max_complexity=complexity_range[1] if complexity_range else None,
                )
            else:
                # Use relative complexity mode (within_band, less_complex, more_complex)
                results_df = cached_find_similar_games(
                    game_id=game_id,
                    top_k=top_k,
                    distance_type=distance_type,
                    embedding_dims=embedding_dims,
                    min_year=year_range[0] if year_range else None,
                    max_year=year_range[1] if year_range else None,
                    min_users_rated=effective_min_ratings,
                    complexity_mode=complexity_mode,
                    complexity_band=complexity_band,
                    min_complexity=None,
                    max_complexity=None,
                )

            # Prepend source game with distance=0 (100% similarity)
            source_game_df = get_source_game_for_similarity(game_id)
            if not source_game_df.empty:
                source_game_df["distance"] = 0.0
                results_df = pd.concat([source_game_df, results_df], ignore_index=True)

            if results_df.empty:
                return (html.Div(dbc.Alert("No similar games found. Try adjusting your filters.", color="warning"), className="py-4"), "")

            grid_options = get_default_grid_options()
            grid_options["domLayout"] = "normal"
            grid_options["rowHeight"] = 50

            grid = dag.AgGrid(
                id="similarity-results-table",
                rowData=results_df.to_dict("records"),
                columnDefs=get_similarity_results_column_defs(distance_type),
                defaultColDef=get_default_column_def(),
                dashGridOptions=grid_options,
                className=get_grid_class_name(),
                style=get_grid_style("calc(100vh - 400px)"),
            )

            if distance_type == "cosine":
                metric_explanation = "Higher percentages indicate more similar games."
            elif distance_type == "euclidean":
                metric_explanation = "Lower distance values indicate more similar games."
            else:
                metric_explanation = "Higher values indicate more similar games."

            header = html.Div([html.H5(f"Found {len(results_df)} Similar Games", className="mb-3"), html.P(metric_explanation, className="text-muted small mb-3")])

            return html.Div([header, grid]), ""

        except Exception as e:
            logger.exception("Error searching for similar games: %s", str(e))
            error_msg = str(e)
            if "Connection" in error_msg or "refused" in error_msg.lower():
                error_detail = "Could not connect to the similarity search service."
            else:
                error_detail = f"An error occurred: {error_msg}"
            return (html.Div(dbc.Alert(error_detail, color="danger"), className="py-4"), "")

    # =========================================================================
    # Compare Tab Callbacks (Why Similar?)
    # =========================================================================

    @app.callback(
        Output("compare-panel", "children", allow_duplicate=True),
        Input({"type": "compare-neighbor-card", "index": dash.ALL}, "n_clicks"),
        State("shared-source-game-store", "data"),
        State("shared-neighbors-store", "data"),
        prevent_initial_call=True,
    )
    def display_comparison(n_clicks_list, source_game, neighbors_data):
        """Display comparison when a neighbor is clicked."""
        if not any(n_clicks_list) or source_game is None or neighbors_data is None:
            return no_update

        # Find which neighbor was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update

        triggered_id = ctx.triggered[0]["prop_id"]
        if "compare-neighbor-card" not in triggered_id:
            return no_update

        # Extract game_id from the triggered ID
        import json
        try:
            id_dict = json.loads(triggered_id.split(".")[0])
            clicked_game_id = id_dict["index"]
        except (json.JSONDecodeError, KeyError):
            return no_update

        # Find the clicked neighbor data
        neighbor_data = None
        for neighbor in neighbors_data:
            if neighbor["game_id"] == clicked_game_id:
                neighbor_data = neighbor
                break

        if neighbor_data is None:
            return dbc.Alert("Could not find neighbor data.", color="warning")

        # Feature comparison only (no embedding queries to save cost)
        return dbc.Card(
            dbc.CardBody(
                create_feature_comparison(
                    source_game,
                    neighbor_data,
                    neighbor_data["similarity_pct"],
                )
            ),
            className="panel-card",
        )
