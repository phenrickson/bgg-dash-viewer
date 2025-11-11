"""Filter components for the BGG Dash Viewer."""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_filters() -> html.Div:
    """Create the filter components for the game search page.

    Returns:
        Filter components
    """
    return html.Div(
        [
            html.Div(id="filter-options-container"),  # Hidden div to trigger filter options loading
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4("Search Filters", className="card-title"),
                        html.Hr(),
                        # Year Range Filter
                        html.Div(
                            [
                                html.Label("Year Published"),
                                dcc.RangeSlider(
                                    id="year-range-slider",
                                    min=1900,
                                    max=2025,
                                    step=1,
                                    marks={
                                        1900: "1900",
                                        1950: "1950",
                                        2000: "2000",
                                        2025: "2025",
                                    },
                                    value=None,
                                    allowCross=False,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(id="year-range-output", className="mt-2 text-muted"),
                            ],
                            className="mb-4",
                        ),
                        # Rating Range Filter
                        html.Div(
                            [
                                html.Label("Geek Rating"),
                                dcc.RangeSlider(
                                    id="rating-range-slider",
                                    min=5.0,
                                    max=10.0,
                                    step=0.1,
                                    marks={
                                        5.0: "5.0",
                                        6.0: "6.0",
                                        7.0: "7.0",
                                        8.0: "8.0",
                                        9.0: "9.0",
                                        10.0: "10.0",
                                    },
                                    value=None,
                                    allowCross=False,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(id="rating-range-output", className="mt-2 text-muted"),
                            ],
                            className="mb-4",
                        ),
                        # Complexity Range Filter
                        html.Div(
                            [
                                html.Label("Complexity Weight"),
                                dcc.RangeSlider(
                                    id="complexity-range-slider",
                                    min=1.0,
                                    max=5.0,
                                    step=0.1,
                                    marks={
                                        1.0: "1.0",
                                        2.0: "2.0",
                                        3.0: "3.0",
                                        4.0: "4.0",
                                        5.0: "5.0",
                                    },
                                    value=None,
                                    allowCross=False,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(id="complexity-range-output", className="mt-2 text-muted"),
                            ],
                            className="mb-4",
                        ),
                        # Player Count Range Filter
                        html.Div(
                            [
                                html.Label("Player Count"),
                                dcc.RangeSlider(
                                    id="player-count-range-slider",
                                    min=1,
                                    max=10,
                                    step=1,
                                    marks={i: str(i) for i in range(1, 11)},
                                    value=None,
                                    allowCross=False,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(
                                    id="player-count-range-output", className="mt-2 text-muted"
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
                        # Results Per Page
                        html.Div(
                            [
                                html.Label("Results Per Page"),
                                dcc.Slider(
                                    id="results-per-page",
                                    min=10,
                                    max=100,
                                    step=10,
                                    marks={
                                        10: "10",
                                        50: "50",
                                        100: "100",
                                    },
                                    value=50,
                                    tooltip={"placement": "bottom", "always_visible": False},
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
                className="mb-4",
            ),
        ]
    )
