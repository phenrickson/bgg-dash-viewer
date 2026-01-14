"""Layout for the upcoming predictions page."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer


def create_upcoming_predictions_layout():
    """Create the layout for the upcoming predictions page.

    Returns:
        Dash component tree for the upcoming predictions page
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    create_page_header(
                        "Game Predictions",
                        "ML predictions for upcoming and recent games",
                    ),
                    # Loading spinner for initial data load
                    dbc.Spinner(
                        html.Div(id="predictions-page-loading"),
                        color="primary",
                        type="border",
                    ),
                    # Main content container (populated after data loads)
                    html.Div(id="predictions-page-content"),
                    # Hidden store
                    dcc.Store(id="predictions-data-store"),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
