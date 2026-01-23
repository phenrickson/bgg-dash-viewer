"""Game search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer
from ..components.filters import create_filters
from ..components.loading import create_spinner


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
                            # Sidebar - Filters (already wrapped in a card)
                            dbc.Col(
                                create_filters(),
                                className="filters-sidebar",
                            ),
                            # Content area
                            dbc.Col(
                                [
                                    # Loading indicator
                                    create_spinner(
                                        html.Div(id="loading-search-results"),
                                    ),
                                    # Table card
                                    dbc.Card(
                                        dbc.CardBody(
                                            html.Div(id="search-results-container")
                                        ),
                                        className="panel-card",
                                    ),
                                ],
                            ),
                        ],
                        className="flex-nowrap",
                    ),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
