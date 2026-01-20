"""Layout for the BigQuery monitoring page."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


def create_bigquery_monitoring_layout() -> html.Div:
    """Create the layout for the BigQuery monitoring page.

    Returns:
        Dash component tree for the BigQuery monitoring page
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    create_page_header(
                        "BigQuery Monitoring",
                        "Database statistics and data catalog",
                    ),
                    # Tabs for different views
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                _create_metrics_tab(),
                                label="Overview",
                                tab_id="metrics-tab",
                            ),
                            dbc.Tab(
                                _create_catalog_tab(),
                                label="Data Catalog",
                                tab_id="catalog-tab",
                            ),
                        ],
                        id="bigquery-tabs",
                        active_tab="metrics-tab",
                        className="mb-4",
                    ),
                    # Hidden stores for data
                    dcc.Store(id="bigquery-data-store"),
                    dcc.Store(id="bigquery-tables-store"),
                    dcc.Store(id="bigquery-schema-store"),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )


def _create_metrics_tab() -> html.Div:
    """Create the metrics overview tab content."""
    return html.Div(
        [
            # Refresh button row
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            [
                                html.I(className="fas fa-sync-alt me-2"),
                                "Refresh",
                            ],
                            id="bigquery-refresh-btn",
                            color="primary",
                            size="sm",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.Div(
                            id="bigquery-last-updated",
                            className="text-muted pt-1",
                        ),
                        width="auto",
                    ),
                ],
                className="mb-4",
            ),
            # Main metrics cards
            create_spinner(
                html.Div(id="bigquery-metrics-container"),
            ),
        ],
        className="p-3",
    )


def _create_catalog_tab() -> html.Div:
    """Create the data catalog tab content."""
    return html.Div(
        [
            # Dataset selector row
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Dataset", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id="catalog-dataset-dropdown",
                                placeholder="Select a dataset...",
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        dbc.Button(
                            [
                                html.I(className="fas fa-sync-alt me-2"),
                                "Refresh Catalog",
                            ],
                            id="catalog-refresh-btn",
                            color="secondary",
                            size="sm",
                            className="mt-4",
                        ),
                        width="auto",
                    ),
                ],
                className="mb-4",
            ),
            # Two-column layout: table list and schema
            dbc.Row(
                [
                    # Table list column
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H6("Tables", className="mb-0"),
                                ),
                                dbc.CardBody(
                                    create_spinner(
                                        html.Div(
                                            id="catalog-table-list",
                                            style={
                                                "maxHeight": "500px",
                                                "overflowY": "auto",
                                            },
                                        ),
                                    ),
                                    className="p-0",
                                ),
                            ],
                            className="panel-card",
                        ),
                        md=4,
                    ),
                    # Schema display column
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.Div(id="catalog-schema-header"),
                                ),
                                dbc.CardBody(
                                    create_spinner(
                                        html.Div(id="catalog-schema-display"),
                                    ),
                                ),
                            ],
                            className="panel-card",
                        ),
                        md=8,
                    ),
                ],
            ),
        ],
        className="p-3",
    )


def create_metric_card(
    title: str,
    value: str,
    subtitle: str = "",
) -> dbc.Card:
    """Create a simple metric card component.

    Args:
        title: Card title
        value: Main metric value to display
        subtitle: Optional subtitle text

    Returns:
        A Bootstrap card component
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(title, className="text-muted mb-1"),
                html.H3(value, className="mb-0"),
                html.Small(subtitle, className="text-muted") if subtitle else None,
            ]
        ),
        className="panel-card h-100",
    )
