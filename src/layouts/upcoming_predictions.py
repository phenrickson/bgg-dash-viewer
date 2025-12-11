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
                    # Job selection at the top
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
                                className="d-flex align-items-center mb-3",
                            ),
                            dbc.Col(
                                dbc.Button(
                                    [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
                                    id="refresh-predictions-btn",
                                    color="primary",
                                    size="sm",
                                ),
                                width="auto",
                                className="d-flex align-items-center mb-3",
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Div(id="selected-job-details", style={"display": "none"}),
                    # Tabs and content
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
                    dbc.Spinner(
                        html.Div(id="predictions-loading"),
                        color="primary",
                        type="border",
                    ),
                    html.Div(id="predictions-table-content"),
                    html.Div(id="bigquery-jobs-content"),
                    # Hidden stores
                    dcc.Store(id="predictions-jobs-store"),
                    dcc.Store(id="selected-job-predictions-store"),
                    dcc.Store(id="refresh-trigger-store", data=0),
                ],
                className="mb-5",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
