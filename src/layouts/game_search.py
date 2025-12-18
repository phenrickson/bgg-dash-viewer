"""Game search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.filters import create_filters


def create_game_search_layout() -> html.Div:
    """Create the game search page layout with sidebar + cards.

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
                        "Search and filter board games by various criteria",
                    ),
                    # Tabs for module pages
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="Search",
                                tab_id="search-tab",
                            ),
                        ],
                        id="search-tabs",
                        active_tab="search-tab",
                        className="mb-4",
                    ),
                    # Main layout: sidebar + content
                    dbc.Row(
                        [
                            # Sidebar - Filters card
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(create_filters()),
                                ),
                                lg=2,
                                md=3,
                            ),
                            # Content area
                            dbc.Col(
                                [
                                    # KPIs card
                                    dbc.Card(
                                        dbc.CardBody(
                                            html.Div(id="search-metrics-cards-container")
                                        ),
                                        className="mb-4",
                                    ),
                                    # Loading indicator
                                    dbc.Spinner(
                                        html.Div(id="loading-search-results"),
                                        color="primary",
                                        type="border",
                                    ),
                                    # Table card
                                    dbc.Card(
                                        dbc.CardBody(
                                            html.Div(id="search-results-container")
                                        ),
                                    ),
                                ],
                                lg=10,
                                md=9,
                            ),
                        ],
                    ),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
