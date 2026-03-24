"""Layout for the ML experiments page."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


def create_experiments_layout() -> html.Div:
    """Create the layout for the ML experiments page."""
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
                                            label="Metrics",
                                            tab_id="metrics-tab",
                                        ),
                                        dbc.Tab(
                                            _create_predictions_tab(),
                                            label="Predictions",
                                            tab_id="predictions-tab",
                                        ),
                                        dbc.Tab(
                                            _create_features_tab(),
                                            label="Features",
                                            tab_id="features-tab",
                                        ),
                                        dbc.Tab(
                                            _create_details_tab(),
                                            label="Details",
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
            create_spinner(
                html.Div(id="metrics-table-container"),
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
            # Experiment and version selectors
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
                    dbc.Col(
                        [
                            html.Label("Version", className="mb-2"),
                            dcc.Dropdown(
                                id="details-version-selector",
                                placeholder="Latest",
                                clearable=False,
                            ),
                        ],
                        width=2,
                    ),
                ],
                className="mb-4",
            ),
            # Finalized badge area
            html.Div(id="details-finalized-badge", className="mb-3"),
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


def _create_features_tab() -> html.Div:
    """Create the features tab content (coefficients + feature importance)."""
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
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Version", className="mb-2"),
                            dcc.Dropdown(
                                id="fi-version-selector",
                                placeholder="Latest",
                                clearable=False,
                            ),
                        ],
                        width=2,
                    ),
                    dbc.Col(
                        [
                            html.Label("Category", className="mb-2"),
                            dcc.Dropdown(
                                id="fi-category-selector",
                                options=[
                                    {"label": "All", "value": "all"},
                                    {"label": "Designer", "value": "designer_"},
                                    {"label": "Publisher", "value": "publisher_"},
                                    {"label": "Artist", "value": "artist_"},
                                    {"label": "Mechanic", "value": "mechanic_"},
                                    {"label": "Category", "value": "category_"},
                                    {"label": "Family", "value": "family_"},
                                    {"label": "Embedding", "value": "emb_"},
                                    {"label": "Other", "value": "__other__"},
                                ],
                                value="all",
                                clearable=False,
                            ),
                        ],
                        width=2,
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
            # Main feature chart
            create_spinner(
                html.Div(id="feature-importance-chart-container"),
            ),
            # Coefficients by year chart (for eval experiments)
            html.Div(
                id="coefficients-by-year-container",
                className="mt-4",
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
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Version", className="mb-2"),
                            dcc.Dropdown(
                                id="predictions-version-selector",
                                placeholder="Latest",
                                clearable=False,
                            ),
                        ],
                        width=2,
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
            create_spinner(
                html.Div(id="predictions-loading"),
            ),
            # Results container
            html.Div(id="predictions-results-container"),
        ],
        className="p-3",
    )
