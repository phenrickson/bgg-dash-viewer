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
                        html.H4("Search Filters", className="card-title"),
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
                                html.Div(id="year-range-output", className="mt-2 text-muted small"),
                            ],
                            className="filter-section",
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
                                html.Div(id="complexity-range-output", className="mt-2 text-muted small"),
                            ],
                            className="filter-section",
                        ),
                        # Player Count Filter
                        html.Div(
                            [
                                html.Label("Player Count"),
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
                                    className="mb-2 d-flex",
                                ),
                                dcc.Dropdown(
                                    id="player-count-dropdown",
                                    options=[
                                        {"label": "1 Player", "value": 1},
                                        {"label": "2 Players", "value": 2},
                                        {"label": "3 Players", "value": 3},
                                        {"label": "4 Players", "value": 4},
                                        {"label": "5 Players", "value": 5},
                                        {"label": "6 Players", "value": 6},
                                        {"label": "7 Players", "value": 7},
                                        {"label": "8+ Players", "value": 8},
                                    ],
                                    placeholder="All player counts",
                                    clearable=True,
                                ),
                                html.Div(id="player-count-output", className="mt-2 text-muted small"),
                                html.Div(
                                    id="player-count-type-store",
                                    style={"display": "none"},
                                    children="best",
                                ),
                            ],
                            className="filter-section",
                        ),
                        # Collapsible Advanced Filters
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(
                                    [
                                        html.Div(
                                            [
                                                html.Label("Publishers"),
                                                dcc.Dropdown(
                                                    id="publisher-dropdown",
                                                    options=[],
                                                    multi=True,
                                                    placeholder="Search publishers...",
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                html.Label("Designers"),
                                                dcc.Dropdown(
                                                    id="designer-dropdown",
                                                    options=[],
                                                    multi=True,
                                                    placeholder="Search designers...",
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                html.Label("Categories"),
                                                dcc.Dropdown(
                                                    id="category-dropdown",
                                                    options=[],
                                                    multi=True,
                                                    placeholder="Search categories...",
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                html.Label("Mechanics"),
                                                dcc.Dropdown(
                                                    id="mechanic-dropdown",
                                                    options=[],
                                                    multi=True,
                                                    placeholder="Search mechanics...",
                                                ),
                                            ],
                                        ),
                                    ],
                                    title="More Filters",
                                    item_id="advanced-filters",
                                ),
                            ],
                            id="advanced-filters-accordion",
                            start_collapsed=True,
                            flush=True,
                            className="mb-4",
                        ),
                        # Search Results
                        html.Div(
                            [
                                html.Label("Results Limit"),
                                dcc.Dropdown(
                                    id="results-per-page",
                                    options=[
                                        {"label": "100 games", "value": 100},
                                        {"label": "500 games", "value": 500},
                                        {"label": "1,000 games", "value": 1000},
                                        {"label": "10,000 games", "value": 10000},
                                        {"label": "25,000 games", "value": 25000},
                                    ],
                                    value=100,
                                    clearable=False,
                                ),
                            ],
                            className="filter-section",
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
                        # Reset Filters Button
                        html.Div(
                            [
                                dbc.Button(
                                    "Reset Filters",
                                    id="reset-filters-button",
                                    color="secondary",
                                    outline=True,
                                    className="w-100",
                                    size="sm",
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
