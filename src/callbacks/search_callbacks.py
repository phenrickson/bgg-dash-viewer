"""Search callbacks for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from flask_caching import Cache

from ..components.ag_grid_config import (
    get_default_column_def,
    get_default_grid_options,
    get_grid_class_name,
    get_grid_style,
    get_search_results_rich_column_defs,
)
from ..components.game_card import create_game_info_card
from ..data.bigquery_client import BigQueryClient
from ..layouts.game_search import COMPLEXITY_BUCKETS

logger = logging.getLogger(__name__)

CARDS_PER_PAGE = 15


def _render_modal_body(game: dict[str, Any]) -> html.Div:
    """Build the modal body for a selected game using data from the store."""
    image = game.get("image") or game.get("thumbnail")
    game_id = game.get("game_id")
    description = game.get("description") or ""

    rating = game.get("bayes_average") or 0
    complexity = game.get("average_weight") or 0
    avg_rating = game.get("average_rating") or 0
    users_rated = game.get("users_rated") or 0

    def _fmt_int(x):
        try:
            return int(x) if x is not None else "?"
        except (TypeError, ValueError):
            return "?"

    min_players = _fmt_int(game.get("min_players"))
    max_players = _fmt_int(game.get("max_players"))
    min_playtime = _fmt_int(game.get("min_playtime"))
    max_playtime = _fmt_int(game.get("max_playtime"))
    players_str = (
        f"{min_players}" if min_players == max_players else f"{min_players}–{max_players}"
    )
    playtime_str = (
        f"{min_playtime} min"
        if min_playtime == max_playtime
        else f"{min_playtime}–{max_playtime} min"
    )

    def _badges(items: list | None, color: str) -> list:
        if not items:
            return [html.Small("—", className="text-muted")]
        return [
            dbc.Badge(str(item), color=color, className="me-1 mb-1", pill=True)
            for item in items
        ]

    stats = dbc.Row(
        [
            dbc.Col(
                [
                    html.Small("Geek Rating", className="text-muted d-block"),
                    html.Strong(f"{rating:.2f}" if rating else "—"),
                ],
                xs=6,
                md=3,
            ),
            dbc.Col(
                [
                    html.Small("Avg Rating", className="text-muted d-block"),
                    html.Strong(f"{avg_rating:.2f}" if avg_rating else "—"),
                ],
                xs=6,
                md=3,
            ),
            dbc.Col(
                [
                    html.Small("Complexity", className="text-muted d-block"),
                    html.Strong(f"{complexity:.2f}" if complexity else "—"),
                ],
                xs=6,
                md=3,
            ),
            dbc.Col(
                [
                    html.Small("Ratings", className="text-muted d-block"),
                    html.Strong(f"{users_rated:,}" if users_rated else "—"),
                ],
                xs=6,
                md=3,
            ),
        ],
        className="mb-3 g-2",
    )

    meta = html.Div(
        [
            dbc.Badge(f"{players_str} players", color="light", text_color="dark", className="me-2 mb-1"),
            dbc.Badge(playtime_str, color="light", text_color="dark", className="me-2 mb-1"),
        ],
        className="mb-3",
    )

    sections = []
    for label, key, color in [
        ("Categories", "categories", "secondary"),
        ("Mechanics", "mechanics", "info"),
        ("Designers", "designers", "primary"),
        ("Publishers", "publishers", "dark"),
        ("Families", "families", "secondary"),
    ]:
        items = game.get(key) or []
        if items:
            sections.append(
                html.Div(
                    [
                        html.Small(f"{label}: ", className="text-muted me-1"),
                        *_badges(items, color),
                    ],
                    className="mb-2",
                )
            )

    bgg_link = html.A(
        [html.I(className="fas fa-external-link-alt me-2"), "View on BoardGameGeek"],
        href=f"https://boardgamegeek.com/boardgame/{game_id}",
        target="_blank",
        rel="noopener noreferrer",
        className="btn btn-outline-primary btn-sm mt-3",
    )

    left_col = (
        html.Img(
            src=image,
            style={"maxWidth": "100%", "borderRadius": "6px"},
        )
        if image
        else html.Div()
    )

    right_col = html.Div(
        [stats, meta, *sections, bgg_link],
    )

    body_children = [
        dbc.Row(
            [
                dbc.Col(left_col, md=4),
                dbc.Col(right_col, md=8),
            ],
            className="g-3",
        )
    ]
    if description:
        body_children.append(html.Hr())
        body_children.append(
            html.Div(
                description,
                className="text-muted",
                style={"whiteSpace": "pre-wrap"},
            )
        )

    return html.Div(body_children)


def _render_placeholder() -> html.Div:
    """Placeholder shown before a search has been run."""
    return html.Div(
        [
            html.I(className="fas fa-search fa-3x text-muted mb-3"),
            html.H5("Ready to Search", className="text-muted"),
            html.P(
                "Select your filters and click 'Search Games' to see matching games.",
                className="text-muted",
            ),
        ],
        className="d-flex flex-column align-items-center justify-content-center text-center",
        style={"minHeight": "280px"},
    )


def _render_cards(records: list[dict[str, Any]], start_rank: int = 1) -> html.Div:
    """Render results as a vertical stack of clickable game cards with rank.

    Each card has a header showing its overall rank (`#1`, `#2`, ...) and
    opens a details modal when clicked. The card itself carries a
    pattern-matched id so a single callback handles all clicks.

    Args:
        records: Page of game records to render.
        start_rank: Rank number for the first card (accounts for pagination).
    """
    cards = []
    for i, row in enumerate(records):
        card_body = create_game_info_card(
            row,
            show_categories=True,
            show_mechanics=True,
            show_families=False,
            max_categories=6,
            max_mechanics=6,
            image_size=140,
        )
        if card_body is None:
            continue
        game_id = row.get("game_id")
        rank = start_rank + i
        cards.append(
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.Span(f"#{rank}", className="fw-bold text-muted"),
                        className="py-2",
                    ),
                    dbc.CardBody(card_body),
                ],
                id={"type": "game-card", "game_id": game_id},
                className="mb-3 panel-card search-result-card",
                style={"cursor": "pointer"},
                n_clicks=0,
            )
        )
    if not cards:
        return html.Div(
            dbc.Alert("No games found matching your criteria.", color="warning"),
        )
    return html.Div(cards)


def _render_table(records: list[dict[str, Any]]) -> dag.AgGrid:
    grid_options = get_default_grid_options()
    grid_options["domLayout"] = "normal"
    return dag.AgGrid(
        id="results-table",
        rowData=records,
        columnDefs=get_search_results_rich_column_defs(),
        defaultColDef=get_default_column_def(),
        dashGridOptions=grid_options,
        className=get_grid_class_name(),
        style=get_grid_style("calc(100vh - 400px)"),
    )


def register_search_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register search-related callbacks."""

    def get_bq_client() -> BigQueryClient:
        if not hasattr(get_bq_client, "_client"):
            get_bq_client._client = BigQueryClient()
        return get_bq_client._client

    @cache.memoize(timeout=14400)
    def get_filter_options() -> dict[str, list[dict[str, Any]]]:
        logger.info("Fetching filter options from BigQuery")
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
        opts = get_filter_options()
        return (
            [{"label": p["name"], "value": p["publisher_id"]} for p in opts["publishers"]],
            [{"label": d["name"], "value": d["designer_id"]} for d in opts["designers"]],
            [{"label": c["name"], "value": c["category_id"]} for c in opts["categories"]],
            [{"label": m["name"], "value": m["mechanic_id"]} for m in opts["mechanics"]],
        )

    @app.callback(
        [
            Output("search-view-toggle", "data"),
            Output("view-toggle-cards", "outline"),
            Output("view-toggle-table", "outline"),
        ],
        [
            Input("view-toggle-cards", "n_clicks"),
            Input("view-toggle-table", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def toggle_view(_cards_clicks: int | None, _table_clicks: int | None) -> tuple:
        ctx = dash.callback_context
        if not ctx.triggered:
            return "cards", False, True
        triggered = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered == "view-toggle-table":
            return "table", True, False
        return "cards", False, True

    @app.callback(
        [
            Output("search-results-store", "data"),
            Output("search-page-store", "data", allow_duplicate=True),
        ],
        [Input("search-button", "n_clicks")],
        [
            State("player-count-store", "data"),
            State("player-count-type-store", "children"),
            State("complexity-bucket-store", "data"),
            State("year-range-slider", "value"),
            State("publisher-dropdown", "value"),
            State("designer-dropdown", "value"),
            State("category-dropdown", "value"),
            State("mechanic-dropdown", "value"),
            State("sort-dropdown", "value"),
            State("results-per-page", "value"),
        ],
        prevent_initial_call=True,
    )
    def perform_search(
        n_clicks: int | None,
        player_count: Any,
        player_count_type: str,
        complexity_bucket: str,
        year_range: list[int],
        publishers: list[int] | None,
        designers: list[int] | None,
        categories: list[int] | None,
        mechanics: list[int] | None,
        sort_value: str,
        results_per_page: int,
    ) -> tuple:
        """Fetch games when the user clicks Search. Resets pagination to page 1."""
        if not n_clicks:
            return dash.no_update, dash.no_update

        # Translate chip values into query arguments
        pc_arg = None if player_count in (None, "any") else int(player_count)
        pc_type_arg = player_count_type if pc_arg is not None else None
        cx_range = COMPLEXITY_BUCKETS.get(complexity_bucket or "any", ("Any", [1.0, 5.0]))[1]
        sort_by, _, sort_order = (sort_value or "bayes_average:DESC").partition(":")

        logger.info(
            "search: pc=%s type=%s cx=%s years=%s sort=%s %s",
            pc_arg,
            pc_type_arg,
            complexity_bucket,
            year_range,
            sort_by,
            sort_order,
        )
        try:
            games_df = get_bq_client().get_games(
                limit=results_per_page or 100,
                publishers=publishers,
                designers=designers,
                categories=categories,
                mechanics=mechanics,
                min_year=year_range[0] if year_range and len(year_range) == 2 else None,
                max_year=year_range[1] if year_range and len(year_range) == 2 else None,
                min_complexity=cx_range[0] if complexity_bucket != "any" else None,
                max_complexity=cx_range[1] if complexity_bucket != "any" else None,
                player_count=pc_arg,
                player_count_type=pc_type_arg,
                best_player_count_only=False,
                sort_by=sort_by or "bayes_average",
                sort_order=sort_order or "DESC",
                include_features=True,
            )
        except Exception as e:
            logger.exception("Error searching for games: %s", str(e))
            return {"error": str(e)}, 1

        for col in ("categories", "mechanics", "publishers", "designers", "artists", "families"):
            if col in games_df.columns:
                games_df[col] = games_df[col].apply(
                    lambda v: list(v) if v is not None and len(v) > 0 else []
                )

        return games_df.to_dict("records"), 1

    @app.callback(
        Output("search-page-store", "data"),
        Input("search-pagination", "active_page"),
        prevent_initial_call=True,
    )
    def update_page_store(active_page: int | None) -> int:
        return active_page or 1

    @app.callback(
        [
            Output("search-results-container", "children"),
            Output("search-result-count", "children"),
            Output("search-pagination", "max_value"),
            Output("search-pagination", "active_page"),
            Output("search-pagination-wrapper", "style"),
        ],
        [
            Input("search-results-store", "data"),
            Input("search-view-toggle", "data"),
            Input("search-page-store", "data"),
        ],
    )
    def render_results(
        data: list[dict[str, Any]] | dict[str, Any] | None,
        view: str,
        page: int | None,
    ) -> tuple:
        hidden = {"display": "none"}
        shown = {"display": "flex"}

        if data is None:
            return _render_placeholder(), "", 1, 1, hidden

        if isinstance(data, dict) and "error" in data:
            return (
                html.Div(
                    dbc.Alert(
                        f"An error occurred while searching for games: {data['error']}",
                        color="danger",
                    )
                ),
                "",
                1,
                1,
                hidden,
            )

        if not data:
            return (
                html.Div(
                    dbc.Alert(
                        "No games found matching your criteria.",
                        color="warning",
                    )
                ),
                "0 games",
                1,
                1,
                hidden,
            )

        total = len(data)
        count_text = f"{total:,} game{'s' if total != 1 else ''}"

        # Table view skips pagination (AG Grid has its own)
        if view == "table":
            return _render_table(data), count_text, 1, 1, hidden

        # Cards view: client-side pagination
        max_page = max(1, (total + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE)
        current = min(max(1, page or 1), max_page)
        start = (current - 1) * CARDS_PER_PAGE
        end = start + CARDS_PER_PAGE
        page_records = data[start:end]
        count_text = (
            f"{count_text} · showing {start + 1}–{min(end, total)}"
            if max_page > 1
            else count_text
        )
        pagination_style = shown if max_page > 1 else hidden
        return (
            _render_cards(page_records, start_rank=start + 1),
            count_text,
            max_page,
            current,
            pagination_style,
        )

    @app.callback(
        [
            Output("player-count-store", "data", allow_duplicate=True),
            Output("complexity-bucket-store", "data", allow_duplicate=True),
            Output("year-range-slider", "value"),
            Output("publisher-dropdown", "value"),
            Output("designer-dropdown", "value"),
            Output("category-dropdown", "value"),
            Output("mechanic-dropdown", "value"),
        ],
        Input("reset-filters-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(_n_clicks: int | None) -> tuple:
        return "any", "any", [1950, 2026], None, None, None, None

    @app.callback(
        [
            Output("game-details-modal", "is_open"),
            Output("game-details-modal-title", "children"),
            Output("game-details-modal-body", "children"),
        ],
        Input({"type": "game-card", "game_id": dash.ALL}, "n_clicks"),
        State("search-results-store", "data"),
        prevent_initial_call=True,
    )
    def open_details_modal(
        n_clicks_list: list[int | None],
        data: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> tuple:
        """Open a modal with full details for the clicked card."""
        ctx = dash.callback_context
        if not ctx.triggered_id or not any(n_clicks_list):
            return dash.no_update, dash.no_update, dash.no_update
        if not isinstance(data, list):
            return dash.no_update, dash.no_update, dash.no_update

        clicked_id = ctx.triggered_id["game_id"]
        match = next((row for row in data if row.get("game_id") == clicked_id), None)
        if match is None:
            return dash.no_update, dash.no_update, dash.no_update

        title = match.get("name") or "Game Details"
        year = match.get("year_published")
        if year:
            title = f"{title} ({int(year)})"

        body = _render_modal_body(match)
        return True, title, body
