"""Game search page layout for the BGG Dash Viewer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.filters import create_filters


def create_game_search_layout() -> html.Div:
    """Create the game search page layout.

    Returns:
        Game search page layout
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    create_page_header(
                        "Game Search",
                        "Search and filter board games from the BoardGameGeek database",
                    ),
                    dbc.Row(
                        [
                            # Filters Column
                            dbc.Col(
                                [create_filters()],
                                md=3,
                                className="mb-4",
                            ),
                            # Results Column
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.H4("Search Results"),
                                            html.Div(
                                                id="search-results-count",
                                                className="text-muted mb-3",
                                            ),
                                            dbc.Spinner(
                                                html.Div(id="loading-search-results"),
                                                color="primary",
                                                type="border",
                                            ),
                                            html.Div(id="search-results-container"),
                                        ],
                                        className="mb-4",
                                    ),
                                ],
                                md=9,
                                className="mb-4",
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
