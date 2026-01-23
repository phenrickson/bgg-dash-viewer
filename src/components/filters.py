"""Filter components for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_filters() -> html.Div:
    """Create the filter components for the game search page.

    Returns:
        Filter components
    """
    return html.Div(
        [
            html.Div(
                id="filter-options-container", children="init", style={"display": "none"}
            ),  # Hidden div to trigger filter options loading
            html.Div(id="filter-loading-indicator", style={"display": "none"}),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Search Filters", className="card-title mb-3"),
                        html.Hr(),
                        # Year Range Filter
                        html.Div(
                            [
                                html.Label("Year Published"),
                                dcc.RangeSlider(
                                    id="year-range-slider",
                                    min=1950,
                                    max=2030,
                                    step=1,
                                    marks={
                                        1950: "1950",
                                        1980: "1980",
                                        2000: "2000",
                                        2026: "2026",
                                    },
                                    value=[1950, 2026],
                                    allowCross=False,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(id="year-range-output", className="mt-2 text-muted"),
                            ],
                            className="mb-4",
                        ),
                        # Complexity Range Filter
                        html.Div(
                            [
                                html.Label("Complexity"),
                                dcc.RangeSlider(
                                    id="complexity-range-slider",
                                    min=1.0,
                                    max=5.0,
                                    step=0.1,
                                    marks={
                                        1: "1.0",
                                        2: "2.0",
                                        3: "3.0",
                                        4: "4.0",
                                        5: "5.0",
                                    },
                                    value=[1.0, 5.0],
                                    allowCross=False,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(id="complexity-range-output", className="mt-2 text-muted"),
                            ],
                            className="mb-4",
                        ),
                        # Player Count Filter
                        html.Div(
                            [
                                html.Label("Player Count"),
                                # Player count toggle moved above the dropdown
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            "Best",
                                            id="player-count-best-button",
                                            color="primary",
                                            outline=False,
                                            size="sm",
                                            className="me-1",
                                        ),
                                        dbc.Button(
                                            "Recommended",
                                            id="player-count-recommended-button",
                                            color="primary",
                                            outline=True,
                                            size="sm",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                dcc.Dropdown(
                                    id="player-count-dropdown",
                                    options=[
                                        {"label": "1", "value": 1},
                                        {"label": "2", "value": 2},
                                        {"label": "3", "value": 3},
                                        {"label": "4", "value": 4},
                                        {"label": "5", "value": 5},
                                        {"label": "6", "value": 6},
                                        {"label": "7", "value": 7},
                                        {"label": "8", "value": 8},
                                    ],  # Hard-coded player count options
                                    placeholder="Select player count...",
                                    clearable=True,
                                ),
                                html.Div(id="player-count-output", className="mt-2 text-muted"),
                                # Hidden div to store the current player count type
                                html.Div(
                                    id="player-count-type-store",
                                    style={"display": "none"},
                                    children="best",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Publisher Dropdown
                        html.Div(
                            [
                                html.Label("Publishers"),
                                dcc.Dropdown(
                                    id="publisher-dropdown",
                                    options=[],  # Will be populated by callback
                                    multi=True,
                                    placeholder="Select publishers...",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Designer Dropdown
                        html.Div(
                            [
                                html.Label("Designers"),
                                dcc.Dropdown(
                                    id="designer-dropdown",
                                    options=[],  # Will be populated by callback
                                    multi=True,
                                    placeholder="Select designers...",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Category Dropdown
                        html.Div(
                            [
                                html.Label("Categories"),
                                dcc.Dropdown(
                                    id="category-dropdown",
                                    options=[],  # Will be populated by callback
                                    multi=True,
                                    placeholder="Select categories...",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Mechanic Dropdown
                        html.Div(
                            [
                                html.Label("Mechanics"),
                                dcc.Dropdown(
                                    id="mechanic-dropdown",
                                    options=[],  # Will be populated by callback
                                    multi=True,
                                    placeholder="Select mechanics...",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Search Results
                        html.Div(
                            [
                                html.Label("Search Results"),
                                dcc.Dropdown(
                                    id="results-per-page",
                                    options=[
                                        {"label": "100", "value": 100},
                                        {"label": "500", "value": 500},
                                        {"label": "1,000", "value": 1000},
                                        {"label": "10,000", "value": 10000},
                                        {"label": "25,000", "value": 25000},
                                    ],
                                    value=100,
                                    clearable=False,
                                    placeholder="Select number of results...",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Search Button
                        html.Div(
                            [
                                dbc.Button(
                                    "Search Games",
                                    id="search-button",
                                    color="primary",
                                    className="w-100",
                                ),
                            ],
                            className="mb-3",
                        ),
                        # Reset Filters Button (hidden by default, shown by callback)
                        html.Div(
                            [
                                dbc.Button(
                                    "Reset Filters",
                                    id="reset-filters-button",
                                    color="secondary",
                                    outline=True,
                                    className="w-100",
                                ),
                            ],
                            id="reset-filters-container",
                            style={"display": "none"},
                        ),
                    ]
                ),
                className="mb-4 panel-card",
            ),
        ]
    )
