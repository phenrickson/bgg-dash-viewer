"""Layout for the ML experiments page."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer


def create_experiments_layout() -> html.Div:
    """Create the layout for the ML experiments page.

    Returns:
        Dash component tree for the experiments page
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    create_page_header(
                        "Model Experiments",
                        "ML experiment tracking and model comparison",
                    ),
                    # Model type selector and summary
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Label(
                                        "Model Type",
                                        className="fw-bold mb-2",
                                    ),
                                    dcc.Dropdown(
                                        id="model-type-dropdown",
                                        placeholder="Select model type...",
                                        clearable=False,
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                html.Div(
                                    id="experiments-summary-stats",
                                    className="text-muted pt-4",
                                ),
                                width=9,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Main content tabs
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Tabs(
                                    [
                                        dbc.Tab(
                                            _create_metrics_tab(),
                                            label="Metrics Overview",
                                            tab_id="metrics-tab",
                                        ),
                                        dbc.Tab(
                                            _create_predictions_tab(),
                                            label="Predictions",
                                            tab_id="predictions-tab",
                                        ),
                                        dbc.Tab(
                                            _create_feature_importance_tab(),
                                            label="Feature Importance",
                                            tab_id="feature-importance-tab",
                                        ),
                                        dbc.Tab(
                                            _create_details_tab(),
                                            label="Experiment Details",
                                            tab_id="details-tab",
                                        ),
                                    ],
                                    id="experiments-tabs",
                                    active_tab="metrics-tab",
                                ),
                            ]
                        ),
                        className="panel-card",
                    ),
                    # Hidden stores for data
                    dcc.Store(id="experiments-data-store"),
                    dcc.Store(id="feature-importance-store"),
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
            # Dataset selector
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Dataset", className="mb-2"),
                            dbc.RadioItems(
                                id="metrics-dataset-selector",
                                options=[
                                    {"label": "Train", "value": "train"},
                                    {"label": "Tune", "value": "tune"},
                                    {"label": "Test", "value": "test"},
                                ],
                                value="test",
                                inline=True,
                            ),
                        ],
                        width="auto",
                    ),
                ],
                className="mb-3",
            ),
            # Metrics table
            dbc.Spinner(
                html.Div(id="metrics-table-container"),
                color="primary",
                type="border",
            ),
            # Performance chart
            html.Div(
                id="metrics-chart-container",
                className="mt-4",
            ),
        ],
        className="p-3",
    )


def _create_details_tab() -> html.Div:
    """Create the experiment details tab content."""
    return html.Div(
        [
            # Experiment selector
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Experiment", className="mb-2"),
                            dcc.Dropdown(
                                id="details-experiment-selector",
                                placeholder="Select experiment...",
                                clearable=False,
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            # Parameters and model info
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H5("Parameters", className="mb-3"),
                            html.Div(id="parameters-table-container"),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.H5("Model Info", className="mb-3"),
                            html.Div(id="model-info-container"),
                        ],
                        width=6,
                    ),
                ],
            ),
            # Metrics comparison
            html.Div(
                [
                    html.H5("Metrics", className="mb-3 mt-4"),
                    html.Div(id="experiment-metrics-container"),
                ],
            ),
        ],
        className="p-3",
    )


def _create_feature_importance_tab() -> html.Div:
    """Create the feature importance tab content."""
    return html.Div(
        [
            # Controls row
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Experiment", className="mb-2"),
                            dcc.Dropdown(
                                id="fi-experiment-selector",
                                placeholder="Select experiment...",
                                clearable=False,
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("Top N Features", className="mb-2"),
                            dcc.Slider(
                                id="feature-importance-top-n",
                                min=10,
                                max=100,
                                step=10,
                                value=30,
                                marks={i: str(i) for i in range(10, 101, 20)},
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            # Overall feature importance chart
            dbc.Spinner(
                html.Div(id="feature-importance-chart-container"),
                color="primary",
                type="border",
            ),
            # Category breakdown
            html.Div(
                [
                    html.H5("Feature Importance by Category", className="mb-3 mt-4"),
                    dbc.Tabs(
                        id="feature-category-tabs",
                        children=[],
                    ),
                ],
                id="feature-category-container",
                style={"display": "none"},
            ),
        ],
        className="p-3",
    )


def _create_predictions_tab() -> html.Div:
    """Create the predictions analysis tab content."""
    return html.Div(
        [
            # Controls row
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Experiment", className="mb-2"),
                            dcc.Dropdown(
                                id="predictions-experiment-selector",
                                placeholder="Select experiment...",
                                clearable=False,
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("Dataset", className="mb-2"),
                            dbc.RadioItems(
                                id="predictions-dataset-selector",
                                options=[
                                    {"label": "Tune", "value": "tune"},
                                    {"label": "Test", "value": "test"},
                                ],
                                value="test",
                                inline=True,
                            ),
                        ],
                        width="auto",
                        className="pt-2",
                    ),
                ],
                className="mb-4",
            ),
            # Loading spinner
            dbc.Spinner(
                html.Div(id="predictions-loading"),
                color="primary",
                type="border",
            ),
            # Results container
            html.Div(id="predictions-results-container"),
        ],
        className="p-3",
    )
