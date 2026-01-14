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
                    # Summary stats with collapsible model details
                    html.Div(
                        [
                            html.Div(
                                id="predictions-summary-stats",
                                className="text-muted",
                            ),
                            dbc.Accordion(
                                [
                                    dbc.AccordionItem(
                                        html.Div(id="predictions-model-details"),
                                        title="Model Details",
                                    ),
                                ],
                                start_collapsed=True,
                                className="mt-2",
                                style={"maxWidth": "600px"},
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Year filter and predictions table
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Label("Publication Year", className="mb-2"),
                                                dcc.Dropdown(
                                                    id="year-filter-dropdown",
                                                    placeholder="Select year...",
                                                    clearable=False,
                                                ),
                                            ],
                                            width=3,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                # Statistics cards for filtered year
                                html.Div(id="predictions-year-stats", className="mb-3"),
                                # Data table
                                dbc.Spinner(
                                    html.Div(id="predictions-table-content"),
                                    color="primary",
                                    type="border",
                                ),
                            ]
                        ),
                        className="panel-card",
                    ),
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
