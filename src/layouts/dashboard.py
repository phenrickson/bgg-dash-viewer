"""Dashboard layout for the BGG Dash Viewer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer


def create_dashboard_layout() -> html.Div:
    """Create the dashboard layout with visualizations.

    Returns:
        Dashboard layout
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H1("Board Game Data Dashboard", className="mb-4"),
                                    html.P(
                                        "Interactive visualizations of board game data from BoardGameGeek. "
                                        "All charts show data for rated games only.",
                                        className="lead mb-4",
                                    ),
                                ],
                                width=12,
                            )
                        ]
                    ),
                    # Distribution charts row
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "Average Rating Distribution",
                                                    className="card-title",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="rating-distribution-chart"),
                                                    color="primary",
                                                ),
                                            ]
                                        ),
                                        className="mb-4",
                                    )
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "Complexity Distribution",
                                                    className="card-title",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="weight-distribution-chart"),
                                                    color="primary",
                                                ),
                                            ]
                                        ),
                                        className="mb-4",
                                    )
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "User Ratings Distribution (Log Scale)",
                                                    className="card-title",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="users-rated-distribution-chart"),
                                                    color="primary",
                                                ),
                                            ]
                                        ),
                                        className="mb-4",
                                    )
                                ],
                                md=4,
                            ),
                        ]
                    ),
                    # Scatter plots row
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "Average Rating by Year Published",
                                                    className="card-title",
                                                ),
                                                html.P(
                                                    "Games published from 1975 to present",
                                                    className="text-muted small",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="rating-by-year-chart"),
                                                    color="primary",
                                                ),
                                            ]
                                        ),
                                        className="mb-4",
                                    )
                                ],
                                md=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "Complexity vs Average Rating",
                                                    className="card-title",
                                                ),
                                                html.P(
                                                    "Relationship between game complexity and rating",
                                                    className="text-muted small",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="weight-vs-rating-chart"),
                                                    color="primary",
                                                ),
                                            ]
                                        ),
                                        className="mb-4",
                                    )
                                ],
                                md=6,
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
