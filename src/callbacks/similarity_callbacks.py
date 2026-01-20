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
        """Load top 25k games from pre-computed dropdown table - cached for 24 hours."""
        logger.info("Loading top games for dropdown")
        try:
            # Use pre-computed table for fast loading (created by dataform)
            query = """
            SELECT game_id, name, year_published
            FROM `${project_id}.${dataset}.game_dropdown_options`
            ORDER BY COALESCE(bayes_average, 0) DESC
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
        [
            Output("neighbors-game-dropdown", "options"),
            Output("similarity-game-dropdown", "options"),
        ],
        Input("similarity-tabs", "active_tab"),
        prevent_initial_call=False,
    )
    def load_game_options(active_tab):
        """Load top games once on page load."""
        logger.info("Loading game options for dropdowns")
        options = get_top_games()
        return options, options

    # =========================================================================
    # Extended Search Callbacks (for games not in top 25k)
    # =========================================================================

    @app.callback(
        [
            Output("neighbors-extended-search-results", "children"),
            Output("neighbors-extended-search-results", "style"),
        ],
        Input("neighbors-extended-search-btn", "n_clicks"),
        State("neighbors-extended-search-input", "value"),
        prevent_initial_call=True,
    )
    def search_neighbors_extended(n_clicks, search_term):
        """Search all games when user can't find in dropdown."""
        if not n_clicks or not search_term or len(search_term) < 3:
            return [], {"display": "none"}

        results = search_all_games(search_term)
        if not results:
            return [html.Small("No games found.", className="text-muted")], {"display": "block"}

        # Create clickable buttons for each result
        buttons = []
        for opt in results[:10]:  # Limit to 10 results
            buttons.append(
                dbc.Button(
                    opt["label"],
                    id={"type": "neighbors-search-result", "index": opt["value"]},
                    color="link",
                    size="sm",
                    className="text-start p-1 d-block",
                )
            )
        return buttons, {"display": "block"}

    @app.callback(
        Output("neighbors-game-dropdown", "value"),
        Input({"type": "neighbors-search-result", "index": dash.ALL}, "n_clicks"),
        State({"type": "neighbors-search-result", "index": dash.ALL}, "id"),
        prevent_initial_call=True,
    )
    def select_neighbors_search_result(n_clicks, ids):
        """Select a game from extended search results."""
        if not any(n_clicks):
            return no_update
        # Find which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        import json
        game_id = json.loads(triggered_id)["index"]
        return game_id

    @app.callback(
        [
            Output("similarity-extended-search-results", "children"),
            Output("similarity-extended-search-results", "style"),
        ],
        Input("similarity-extended-search-btn", "n_clicks"),
        State("similarity-extended-search-input", "value"),
        prevent_initial_call=True,
    )
    def search_similarity_extended(n_clicks, search_term):
        """Search all games when user can't find in dropdown."""
        if not n_clicks or not search_term or len(search_term) < 3:
            return [], {"display": "none"}

        results = search_all_games(search_term)
        if not results:
            return [html.Small("No games found.", className="text-muted")], {"display": "block"}

        buttons = []
        for opt in results[:10]:
            buttons.append(
                dbc.Button(
                    opt["label"],
                    id={"type": "similarity-search-result", "index": opt["value"]},
                    color="link",
                    size="sm",
                    className="text-start p-1 d-block",
                )
            )
        return buttons, {"display": "block"}

    @app.callback(
        Output("similarity-game-dropdown", "value"),
        Input({"type": "similarity-search-result", "index": dash.ALL}, "n_clicks"),
        State({"type": "similarity-search-result", "index": dash.ALL}, "id"),
        prevent_initial_call=True,
    )
    def select_similarity_search_result(n_clicks, ids):
        """Select a game from extended search results."""
        if not any(n_clicks):
            return no_update
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        import json
        game_id = json.loads(triggered_id)["index"]
        return game_id

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

    # =========================================================================
    # Neighbors Tab Callbacks
    # =========================================================================

    @app.callback(
        [
            Output("neighbors-search-button", "disabled"),
            Output("neighbors-selected-game-store", "data"),
        ],
        Input("neighbors-game-dropdown", "value"),
    )
    def handle_neighbors_game_selection(game_id: int | None) -> tuple[bool, dict | None]:
        """Enable search button and store game data when a game is selected."""
        if game_id is None:
            return True, None
        try:
            game_data = get_game_features(game_id)
            return False, game_data
        except Exception as e:
            logger.warning("Could not fetch game info: %s", str(e))
            return False, None

    @app.callback(
        [
            Output("neighbors-source-card-container", "children"),
            Output("neighbors-source-card-container", "style"),
            Output("neighbors-results-container", "children"),
        ],
        Input("neighbors-search-button", "n_clicks"),
        State("neighbors-game-dropdown", "value"),
        prevent_initial_call=True,
        running=[
            (Output("neighbors-search-button", "disabled"), True, False),
            (Output("neighbors-search-button", "children"), "Searching...", "Find Similar Games"),
        ],
    )
    def display_game_neighbors(n_clicks: int, game_id: int | None) -> tuple[Any, dict, Any]:
        if game_id is None:
            return (
                None,
                {"display": "none"},
                html.Div(
                    [
                        html.I(className="fas fa-users fa-3x text-muted mb-3"),
                        html.H5("Select a Game", className="text-muted"),
                        html.P("Select a game and click 'Find Similar Games' to see results.", className="text-muted"),
                    ],
                    className="text-center py-5",
                ),
            )

        try:
            # Fetch fresh game data directly from dropdown value
            game_data = get_game_features(game_id)
            if game_data is None:
                return (
                    None,
                    {"display": "none"},
                    dbc.Alert("Could not load game data.", color="warning"),
                )

            source_card_content = html.Div([
                html.H4("Selected Game", className="mb-3"),
                dbc.Card(
                    dbc.CardBody(create_game_info_card(game_data)),
                    className="mb-4 panel-card border-primary",
                    style={"borderWidth": "2px"},
                ),
            ])

            # Default filters: 25+ ratings, within complexity band of ±0.5
            filters = SimilarityFilters(
                min_users_rated=DEFAULT_MIN_RATINGS,
                complexity_mode="within_band",
                complexity_band=0.5,
            )

            client = get_similarity_client()
            logger.info(f"Finding neighbors for game_id={game_id}, name={game_data.get('name')}")
            neighbors_df = client.find_similar_games(
                game_id=game_id,
                top_k=10,
                distance_type="cosine",
                filters=filters,
            )
            logger.info(f"Found {len(neighbors_df)} neighbors for game_id={game_id}")

            if neighbors_df.empty:
                return (
                    source_card_content,
                    {"display": "block"},
                    dbc.Alert(
                        [html.Strong("No similar games found. "), f"This game (ID: {game_id}) may not have embeddings generated yet."],
                        color="warning",
                    ),
                )

            # Get full game data for all neighbors from games_features
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

            neighbor_cards = []
            for _, row in neighbors_df.iterrows():
                neighbor_id = int(row["game_id"])
                distance = row["distance"]
                similarity_pct = (1 - distance) * 100  # Cosine: similarity = 1 - distance
                neighbor_data = features_map.get(neighbor_id)
                if neighbor_data:
                    card_content = create_game_info_card(neighbor_data)
                    if card_content:
                        neighbor_card = dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.Div(
                                        [
                                            html.Span(f"#{len(neighbor_cards) + 1}", className="fw-bold"),
                                            dbc.Badge(
                                                f"{similarity_pct:.1f}% similar",
                                                color="success" if similarity_pct >= 90 else "info",
                                                className="ms-2",
                                            ),
                                        ],
                                        className="d-flex align-items-center",
                                    ),
                                    className="py-2",
                                ),
                                dbc.CardBody(card_content),
                            ],
                            className="mb-3 panel-card",
                        )
                        neighbor_cards.append(neighbor_card)

            return (
                source_card_content,
                {"display": "block"},
                html.Div([html.H4(f"Top {len(neighbor_cards)} Similar Games", className="mb-3 mt-2"), html.Div(neighbor_cards)]),
            )

        except Exception as e:
            logger.exception("Error loading neighbors: %s", str(e))
            return (None, {"display": "none"}, dbc.Alert(f"Error loading neighbors: {str(e)}", color="danger"))

    # =========================================================================
    # Similarity Search Tab Callbacks
    # =========================================================================

    @app.callback(
        [
            Output("similarity-search-button", "disabled"),
            Output("similarity-selected-game-store", "data"),
        ],
        Input("similarity-game-dropdown", "value"),
    )
    def handle_game_selection(game_id: int | None) -> tuple[bool, dict | None]:
        if game_id is None:
            return True, None
        try:
            game_data = get_game_features(game_id)
            if game_data:
                return False, game_data
        except Exception as e:
            logger.warning("Could not fetch game info: %s", str(e))
        return False, None

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
            State("similarity-game-dropdown", "value"),
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

            # Build filters based on complexity mode
            if complexity_mode == "absolute":
                # Use absolute complexity range
                filters = SimilarityFilters(
                    min_year=year_range[0] if year_range else None,
                    max_year=year_range[1] if year_range else None,
                    min_complexity=complexity_range[0] if complexity_range else None,
                    max_complexity=complexity_range[1] if complexity_range else None,
                    min_users_rated=effective_min_ratings,
                )
            else:
                # Use relative complexity mode (within_band, less_complex, more_complex)
                filters = SimilarityFilters(
                    min_year=year_range[0] if year_range else None,
                    max_year=year_range[1] if year_range else None,
                    complexity_mode=complexity_mode,
                    complexity_band=complexity_band,
                    min_users_rated=effective_min_ratings,
                )

            client = get_similarity_client()
            results_df = client.find_similar_games(
                game_id=game_id,
                top_k=top_k,
                distance_type=distance_type,
                filters=filters,
                embedding_dims=embedding_dims,
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
