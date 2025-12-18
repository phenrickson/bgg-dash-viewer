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
                        "Upcoming Predictions",
                        "View predictions from machine learning model scoring jobs",
                    ),
                    # Job selection card
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Select Prediction Job", className="mb-3"),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Label("Prediction Job:", className="me-2"),
                                                dcc.Dropdown(
                                                    id="prediction-job-dropdown",
                                                    placeholder="Select a job...",
                                                    style={"minWidth": "400px"},
                                                ),
                                            ],
                                            width="auto",
                                            className="d-flex align-items-center",
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
                                                id="refresh-predictions-btn",
                                                color="primary",
                                                size="sm",
                                            ),
                                            width="auto",
                                            className="d-flex align-items-center",
                                        ),
                                    ],
                                ),
                                html.Div(id="selected-job-details", className="mt-2"),
                            ]
                        ),
                        className="mb-4 panel-card",
                    ),
                    # Stats card
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dcc.Loading(
                                    id="predictions-stats-loading",
                                    type="default",
                                    children=html.Div(id="predictions-summary-stats"),
                                ),
                            ]
                        ),
                        className="mb-4 panel-card",
                    ),
                    # Tabs card
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Tabs(
                                    [
                                        dbc.Tab(
                                            label="Predictions",
                                            tab_id="predictions-table",
                                        ),
                                        dbc.Tab(
                                            label="Jobs History",
                                            tab_id="bigquery-jobs",
                                        ),
                                    ],
                                    id="predictions-tabs",
                                    active_tab="predictions-table",
                                    className="mb-3",
                                ),
                                dcc.Loading(
                                    id="predictions-table-loading",
                                    type="default",
                                    children=html.Div(id="predictions-table-content"),
                                ),
                                dcc.Loading(
                                    id="bigquery-jobs-loading",
                                    type="default",
                                    children=html.Div(id="bigquery-jobs-content"),
                                ),
                            ]
                        ),
                        className="panel-card",
                    ),
                    # Hidden stores
                    dcc.Store(id="predictions-jobs-store"),
                    dcc.Store(id="selected-job-predictions-store"),
                    dcc.Store(id="refresh-trigger-store", data=0),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
