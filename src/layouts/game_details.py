"""Game details page layout for the BGG Dash Viewer."""

import logging
from typing import Dict, List, Any, Optional

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..data.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


def create_game_details_layout(game_id: int) -> html.Div:
    """Create the game details page layout.

    Args:
        game_id: ID of the game to display

    Returns:
        Game details page layout
    """
    # Initialize BigQuery client
    bq_client = BigQueryClient()

    try:
        # Get game details
        game_data = bq_client.get_game_details(game_id)

        if not game_data:
            return html.Div(
                [
                    create_header(),
                    dbc.Container(
                        [
                            html.H1("Game Not Found", className="text-danger"),
                            html.P(f"No game found with ID {game_id}"),
                            dcc.Link(
                                "Back to Search", href="/game-search", className="btn btn-primary"
                            ),
                        ],
                        className="py-5",
                    ),
                    create_footer(),
                ],
                className="d-flex flex-column min-vh-100",
            )

        # Create player count chart
        player_counts = pd.DataFrame(game_data.get("player_counts", []))
        player_count_fig = None

        if not player_counts.empty:
            player_count_fig = go.Figure()
            player_count_fig.add_trace(
                go.Bar(
                    x=player_counts["player_count"],
                    y=player_counts["best_percentage"],
                    name="Best",
                    marker_color="green",
                )
            )
            player_count_fig.add_trace(
                go.Bar(
                    x=player_counts["player_count"],
                    y=player_counts["recommended_percentage"],
                    name="Recommended",
                    marker_color="blue",
                )
            )
            player_count_fig.update_layout(
                title="Player Count Recommendations",
                xaxis_title="Player Count",
                yaxis_title="Percentage of Votes",
                barmode="group",
                margin=dict(l=40, r=40, t=40, b=40),
            )

        # Create game details layout
        return html.Div(
            [
                create_header(),
                dbc.Container(
                    [
                        # Back button
                        html.Div(
                            [
                                dbc.Button(
                                    [html.I(className="fas fa-arrow-left me-2"), "Back to Search"],
                                    href="/game-search",
                                    color="secondary",
                                    outline=True,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        # Game header
                        dbc.Row(
                            [
                                # Game image
                                dbc.Col(
                                    [
                                        (
                                            html.Img(
                                                src=game_data.get("image")
                                                or game_data.get("thumbnail"),
                                                alt=game_data.get("name"),
                                                className="img-fluid rounded",
                                                style={"max-height": "300px"},
                                            )
                                            if game_data.get("image") or game_data.get("thumbnail")
                                            else html.Div(
                                                "No image available",
                                                className="text-center p-5 bg-light rounded",
                                            )
                                        ),
                                        html.Div(
                                            [
                                                html.A(
                                                    "View on BoardGameGeek",
                                                    href=f"https://boardgamegeek.com/boardgame/{game_id}",
                                                    target="_blank",
                                                    className="btn btn-sm btn-outline-secondary mt-2 w-100",
                                                ),
                                            ]
                                        ),
                                    ],
                                    md=3,
                                    className="mb-4",
                                ),
                                # Game info
                                dbc.Col(
                                    [
                                        html.H1(game_data.get("name"), className="mb-2"),
                                        html.P(
                                            f"Published in {game_data.get('year_published')}",
                                            className="text-muted",
                                        ),
                                        html.Hr(),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.H5("Geek Rating"),
                                                                html.H2(
                                                                    f"{game_data.get('bayes_average', 0):.1f}",
                                                                    className="text-primary",
                                                                ),
                                                                html.Small(
                                                                    f"Based on {game_data.get('users_rated', 0):,} ratings",
                                                                    className="text-muted",
                                                                ),
                                                            ],
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.H5("Complexity"),
                                                                html.H2(
                                                                    f"{game_data.get('average_weight', 0):.1f}",
                                                                    className="text-primary",
                                                                ),
                                                                html.Small(
                                                                    f"Out of 5",
                                                                    className="text-muted",
                                                                ),
                                                            ],
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.H5("Players"),
                                                                html.H2(
                                                                    f"{game_data.get('min_players', 0)}-{game_data.get('max_players', 0)}",
                                                                    className="text-primary",
                                                                ),
                                                                html.Small(
                                                                    f"Playing time: {game_data.get('playing_time', 0)} min",
                                                                    className="text-muted",
                                                                ),
                                                            ],
                                                            className="mb-3",
                                                        ),
                                                    ],
                                                    md=4,
                                                ),
                                            ]
                                        ),
                                    ],
                                    md=9,
                                    className="mb-4",
                                ),
                            ]
                        ),
                        # Game details
                        dbc.Row(
                            [
                                # Left column
                                dbc.Col(
                                    [
                                        # Description
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H4("Description", className="card-title"),
                                                    html.Div(
                                                        game_data.get(
                                                            "description",
                                                            "No description available.",
                                                        ),
                                                        style={
                                                            "maxHeight": "400px",
                                                            "overflow": "auto",
                                                        },
                                                    ),
                                                ]
                                            ),
                                            className="mb-4",
                                        ),
                                        # Player count recommendations
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H4(
                                                        "Player Count Recommendations",
                                                        className="card-title",
                                                    ),
                                                    (
                                                        dcc.Graph(figure=player_count_fig)
                                                        if player_count_fig
                                                        else html.P(
                                                            "No player count data available."
                                                        )
                                                    ),
                                                ]
                                            ),
                                            className="mb-4",
                                        ),
                                    ],
                                    md=8,
                                ),
                                # Right column
                                dbc.Col(
                                    [
                                        # Game details
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H4("Game Details", className="card-title"),
                                                    html.Div(
                                                        [
                                                            html.H5("Categories"),
                                                            html.Div(
                                                                [
                                                                    dbc.Badge(
                                                                        category["name"],
                                                                        color="primary",
                                                                        className="me-1 mb-1",
                                                                    )
                                                                    for category in game_data.get(
                                                                        "categories", []
                                                                    )
                                                                ]
                                                                if game_data.get("categories")
                                                                else "No categories available."
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.H5("Mechanics"),
                                                            html.Div(
                                                                [
                                                                    dbc.Badge(
                                                                        mechanic["name"],
                                                                        color="secondary",
                                                                        className="me-1 mb-1",
                                                                    )
                                                                    for mechanic in game_data.get(
                                                                        "mechanics", []
                                                                    )
                                                                ]
                                                                if game_data.get("mechanics")
                                                                else "No mechanics available."
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.H5("Designers"),
                                                            html.Div(
                                                                [
                                                                    html.Span(
                                                                        designer["name"] + ", "
                                                                    )
                                                                    for designer in game_data.get(
                                                                        "designers", []
                                                                    )[:-1]
                                                                ]
                                                                + [
                                                                    html.Span(
                                                                        game_data.get(
                                                                            "designers", []
                                                                        )[-1]["name"]
                                                                    )
                                                                ]
                                                                if game_data.get("designers")
                                                                else "No designers available."
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.H5("Publishers"),
                                                            html.Div(
                                                                [
                                                                    html.Span(
                                                                        publisher["name"] + ", "
                                                                    )
                                                                    for publisher in game_data.get(
                                                                        "publishers", []
                                                                    )[:-1]
                                                                ]
                                                                + [
                                                                    html.Span(
                                                                        game_data.get(
                                                                            "publishers", []
                                                                        )[-1]["name"]
                                                                    )
                                                                ]
                                                                if game_data.get("publishers")
                                                                else "No publishers available."
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                ]
                                            ),
                                            className="mb-4",
                                        ),
                                    ],
                                    md=4,
                                ),
                            ]
                        ),
                    ],
                    className="mb-5",
                ),
                create_footer(),
            ],
            className="d-flex flex-column min-vh-100",
        )
    except Exception as e:
        logger.exception("Error creating game details layout: %s", str(e))
        return html.Div(
            [
                create_header(),
                dbc.Container(
                    [
                        html.H1("Error", className="text-danger"),
                        html.P(f"An error occurred while loading game details: {str(e)}"),
                        dcc.Link(
                            "Back to Search", href="/game-search", className="btn btn-primary"
                        ),
                    ],
                    className="py-5",
                ),
                create_footer(),
            ],
            className="d-flex flex-column min-vh-100",
        )
