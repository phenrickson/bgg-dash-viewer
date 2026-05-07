"""Layout for the Collection Models page (per-user collection predictions)."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


def create_collection_models_layout():
    """Create the layout for the Collection Models page.

    Renders the page chrome (header, page header, footer, modal) and
    delegates the inner content (filter bar, cards/table grid) to
    callbacks via `collection-models-page-content`.
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    create_page_header(
                        "Collection Models",
                        "Personalized collection analysis and recommendations",
                    ),
                    create_spinner(html.Div(id="collection-models-page-loading")),
                    html.Div(id="collection-models-page-content"),
                    dcc.Store(id="collection-models-data-store"),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
