"""Home page layout for the BGG Dash Viewer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer


def create_home_layout() -> html.Div:
    """Create the home page layout.

    Returns:
        Home page layout
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    # create_page_header(
                    #     "BoardGameGeek Data Explorer",
                    #     "Explore and analyze board game data from BoardGameGeek",
                    # ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            # html.H2("Welcome to BGG Dash Viewer"),
                                            html.P(
                                                "This application provides an interactive interface for exploring and analyzing board game data from BoardGameGeek.",
                                                className="lead",
                                            ),
                                            # html.P(
                                            #     "Use the navigation menu to access different features of the application."
                                            # ),
                                        ],
                                        className="mb-4",
                                    ),
                                    html.Div(
                                        [
                                            html.H3("Features"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Card(
                                                            dbc.CardBody(
                                                                [
                                                                    html.H4(
                                                                        "Game Search",
                                                                        className="card-title",
                                                                    ),
                                                                    html.P(
                                                                        "Search for games with advanced filtering options including publishers, designers, categories, mechanics, ratings, and more.",
                                                                        className="card-text",
                                                                    ),
                                                                    dbc.Button(
                                                                        "Search Games",
                                                                        color="primary",
                                                                        href="/game-search",
                                                                    ),
                                                                ]
                                                            ),
                                                            className="h-100",
                                                        ),
                                                        md=6,
                                                        className="mb-4",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Card(
                                                            dbc.CardBody(
                                                                [
                                                                    html.H4(
                                                                        "Data Visualizations",
                                                                        className="card-title",
                                                                    ),
                                                                    html.P(
                                                                        "Explore interactive visualizations of board game data, including ratings, complexity, publication years, and more.",
                                                                        className="card-text",
                                                                    ),
                                                                    dbc.Button(
                                                                        "View Dashboard",
                                                                        color="primary",
                                                                        href="/dashboard",
                                                                        id="refresh-stats-button",
                                                                    ),
                                                                ]
                                                            ),
                                                            className="h-100",
                                                        ),
                                                        md=6,
                                                        className="mb-4",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    html.Div(
                                        [
                                            html.H3("Overview"),
                                            dbc.Spinner(
                                                html.Div(id="summary-stats-container"),
                                                color="primary",
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                ]
                            )
                        ]
                    ),
                ],
                className="mb-5",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
