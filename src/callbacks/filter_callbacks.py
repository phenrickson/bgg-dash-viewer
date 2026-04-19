"""Filter callbacks for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from dash import html, dcc, ALL
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from flask_caching import Cache
import plotly.express as px
import pandas as pd

from ..data.bigquery_client import BigQueryClient
from ..theme import PLOTLY_TEMPLATE

logger = logging.getLogger(__name__)


def register_filter_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register filter-related callbacks."""

    def get_bq_client() -> BigQueryClient:
        if not hasattr(get_bq_client, "_client"):
            get_bq_client._client = BigQueryClient()
        return get_bq_client._client

    # Best / Recommended toggle for player-count type
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
        _best_clicks: int | None,
        _rec_clicks: int | None,
        current_type: str,
    ) -> tuple[bool, bool, str]:
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, True, "best"
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "player-count-best-button":
            return False, True, "best"
        if button_id == "player-count-recommended-button":
            return True, False, "recommended"
        return current_type == "recommended", current_type == "best", current_type

    # Player-count chip selection
    @app.callback(
        Output("player-count-store", "data"),
        Input({"type": "pc-chip", "value": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def select_player_count_chip(_clicks: list[int | None]) -> Any:
        ctx = dash.callback_context
        if not ctx.triggered_id:
            return dash.no_update
        return ctx.triggered_id["value"]

    @app.callback(
        Output({"type": "pc-chip", "value": ALL}, "outline"),
        Input("player-count-store", "data"),
        State({"type": "pc-chip", "value": ALL}, "id"),
    )
    def style_pc_chips(selected: Any, ids: list[dict]) -> list[bool]:
        return [item["value"] != selected for item in ids]

    # Complexity chip selection
    @app.callback(
        Output("complexity-bucket-store", "data"),
        Input({"type": "cx-chip", "value": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def select_complexity_chip(_clicks: list[int | None]) -> Any:
        ctx = dash.callback_context
        if not ctx.triggered_id:
            return dash.no_update
        return ctx.triggered_id["value"]

    @app.callback(
        Output({"type": "cx-chip", "value": ALL}, "outline"),
        Input("complexity-bucket-store", "data"),
        State({"type": "cx-chip", "value": ALL}, "id"),
    )
    def style_cx_chips(selected: str, ids: list[dict]) -> list[bool]:
        return [item["value"] != selected for item in ids]

    # Advanced filters collapse toggle
    @app.callback(
        Output("advanced-filters-collapse", "is_open"),
        Input("advanced-filters-toggle", "n_clicks"),
        State("advanced-filters-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_advanced_filters(_n_clicks: int | None, is_open: bool) -> bool:
        return not is_open

    # Summary stats (used by other pages — kept as-is)
    @cache.memoize()
    def get_summary_stats() -> dict[str, Any]:
        logger.info("Fetching summary statistics from BigQuery")
        return get_bq_client().get_summary_stats()

    @app.callback(
        Output("summary-stats-container", "children"),
        [Input("refresh-stats-button", "n_clicks")],
    )
    def update_summary_stats(_n_clicks: int | None) -> html.Div:
        stats = get_summary_stats()

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
                    html.H2(
                        f"{stats['entity_counts']['category_count']:,}",
                        className="card-text",
                    ),
                ]
            ),
            className="mb-4",
        )
        mechanics_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H5("Mechanics", className="card-title"),
                    html.H2(
                        f"{stats['entity_counts']['mechanic_count']:,}",
                        className="card-text",
                    ),
                ]
            ),
            className="mb-4",
        )

        rating_df = pd.DataFrame(stats["rating_distribution"])
        rating_fig = px.bar(
            rating_df,
            x="rating_bin",
            y="game_count",
            title="Geek Rating Distribution",
            labels={"rating_bin": "Geek Rating", "game_count": "Number of Games"},
            template=PLOTLY_TEMPLATE,
        )
        rating_fig.update_layout(
            xaxis_title="Rating",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
        )
        rating_fig.update_traces(marker_color="#2FA4E7")

        year_df = pd.DataFrame(stats["year_distribution"])
        year_fig = px.bar(
            year_df,
            x="year_published",
            y="game_count",
            title="Games Published by Year",
            labels={"year_published": "Year", "game_count": "Number of Games"},
            template=PLOTLY_TEMPLATE,
        )
        year_fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Number of Games",
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
        )
        year_fig.update_traces(marker_color="#2FA4E7")

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
                                dbc.CardBody([dcc.Graph(figure=rating_fig)])
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody([dcc.Graph(figure=year_fig)])
                            ),
                            width=6,
                        ),
                    ]
                ),
            ]
        )
