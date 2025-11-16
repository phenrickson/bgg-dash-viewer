"""Dashboard layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer
from ..components.metrics_cards import create_metrics_cards


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
                                    html.H1("BoardGameGeek Ratings", className="mb-4"),
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
                    # Metrics cards row
                    html.Div(id="metrics-cards-container"),
                    # First row of scatter plots
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            "Average Rating by Year Published",
                                                            className="card-title d-inline",
                                                        ),
                                                        dbc.Button(
                                                            html.I(className="fas fa-expand"),
                                                            id="expand-rating-by-year-btn",
                                                            color="link",
                                                            size="sm",
                                                            className="float-end p-1",
                                                            title="Expand to full screen",
                                                        ),
                                                    ],
                                                    className="d-flex justify-content-between align-items-center",
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
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            "Complexity vs Average Rating",
                                                            className="card-title d-inline",
                                                        ),
                                                        dbc.Button(
                                                            html.I(className="fas fa-expand"),
                                                            id="expand-weight-vs-rating-btn",
                                                            color="link",
                                                            size="sm",
                                                            className="float-end p-1",
                                                            title="Expand to full screen",
                                                        ),
                                                    ],
                                                    className="d-flex justify-content-between align-items-center",
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
                    # Second row of scatter plots
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            "User Ratings by Year Published",
                                                            className="card-title d-inline",
                                                        ),
                                                        dbc.Button(
                                                            html.I(className="fas fa-expand"),
                                                            id="expand-users-by-year-btn",
                                                            color="link",
                                                            size="sm",
                                                            className="float-end p-1",
                                                            title="Expand to full screen",
                                                        ),
                                                    ],
                                                    className="d-flex justify-content-between align-items-center",
                                                ),
                                                html.P(
                                                    "User rating trends over time",
                                                    className="text-muted small",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="complexity-by-year-chart"),
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
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            "Average Rating and User Ratings",
                                                            className="card-title d-inline",
                                                        ),
                                                        dbc.Button(
                                                            html.I(className="fas fa-expand"),
                                                            id="expand-rating-vs-users-btn",
                                                            color="link",
                                                            size="sm",
                                                            className="float-end p-1",
                                                            title="Expand to full screen",
                                                        ),
                                                    ],
                                                    className="d-flex justify-content-between align-items-center",
                                                ),
                                                html.P(
                                                    "Relationship between average rating and number of user ratings",
                                                    className="text-muted small",
                                                ),
                                                dbc.Spinner(
                                                    dcc.Graph(id="rating-vs-users-chart"),
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
                    # Modal for expanded chart view
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                [
                                    dbc.ModalTitle(id="modal-chart-title"),
                                    dbc.Button(
                                        "×",
                                        id="close-modal-btn",
                                        className="btn-close",
                                        n_clicks=0,
                                        style={
                                            "background": "none",
                                            "border": "none",
                                            "font-size": "1.5rem",
                                        },
                                    ),
                                ],
                                className="d-flex justify-content-between align-items-center",
                            ),
                            dbc.ModalBody(
                                dcc.Graph(id="modal-chart", style={"height": "70vh"}),
                                className="p-0",
                            ),
                        ],
                        id="chart-modal",
                        size="xl",
                        is_open=False,
                        backdrop=True,
                        scrollable=True,
                    ),
                ],
                className="mb-5",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
