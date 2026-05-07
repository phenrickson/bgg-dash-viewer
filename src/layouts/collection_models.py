"""Layout for the Collection Models page (per-user collection predictions)."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header
from ..components.footer import create_footer
from ..components.loading import create_spinner

REPORTS_BASE_URL = "https://phenrickson.github.io/bgg-predictive-models"


def _page_header() -> html.Div:
    """Page header with title, subtitle, and an inline Model Details link.

    Mirrors the standard `create_page_header` shape but threads a static
    link into the subtitle row so users can jump to the bgg-predictive-models
    GitHub Pages index without leaving the dash.
    """
    return html.Div(
        [
            html.H3("Collection Models", className="mb-1"),
            html.Div(
                [
                    html.Span(
                        "Personalized collection analysis and recommendations.",
                        className="small text-muted me-2",
                    ),
                    html.Span("For details on these models, see ", className="small text-muted"),
                    html.A(
                        "the model reports",
                        href=REPORTS_BASE_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="small",
                    ),
                    html.Span(".", className="small text-muted"),
                ],
                className="d-flex align-items-center flex-wrap",
            ),
        ],
        className="mb-3 pb-2 border-bottom",
    )


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
                    _page_header(),
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
