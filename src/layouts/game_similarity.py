"""Game similarity search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer


def create_similarity_filters() -> html.Div:
    """Create the filter components for similarity search.

    Returns:
        Filter components for the sidebar.
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.H4("Find Similar Games", className="card-title mb-3"),
                html.Hr(),
                # Game Selection
                html.Div(
                    [
                        html.Label("Select a Game"),
                        dcc.Dropdown(
                            id="similarity-game-dropdown",
                            options=[],  # Populated by callback
                            placeholder="Search for a game...",
                            searchable=True,
                            clearable=True,
                        ),
                        html.Small(
                            "Start typing to search by game name",
                            className="text-muted",
                        ),
                    ],
                    className="mb-4",
                ),
                # Number of Results
                html.Div(
                    [
                        html.Label("Number of Results"),
                        dcc.Dropdown(
                            id="similarity-top-k-dropdown",
                            options=[
                                {"label": "10", "value": 10},
                                {"label": "20", "value": 20},
                                {"label": "30", "value": 30},
                                {"label": "50", "value": 50},
                            ],
                            value=20,
                            clearable=False,
                        ),
                    ],
                    className="mb-4",
                ),
                # Collapsible Settings section
                html.Div(
                    [
                        dbc.Button(
                            [
                                html.I(className="fas fa-cog me-2"),
                                "Settings",
                                html.I(
                                    className="fas fa-chevron-down ms-2",
                                    id="similarity-filter-chevron",
                                ),
                            ],
                            id="similarity-filter-toggle",
                            color="link",
                            className="p-0 text-decoration-none text-body",
                        ),
                        dbc.Collapse(
                            html.Div(
                                [
                                    # Distance Metric
                                    html.Div(
                                        [
                                            html.Label("Distance Metric"),
                                            dcc.Dropdown(
                                                id="similarity-distance-dropdown",
                                                options=[
                                                    {"label": "Cosine", "value": "cosine"},
                                                    {"label": "Euclidean", "value": "euclidean"},
                                                    {"label": "Dot Product", "value": "dot_product"},
                                                ],
                                                value="cosine",
                                                clearable=False,
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    # Year Range Filter
                                    html.Div(
                                        [
                                            html.Label("Year Published"),
                                            dcc.RangeSlider(
                                                id="similarity-year-slider",
                                                min=1950,
                                                max=2030,
                                                step=1,
                                                marks={
                                                    1950: "1950",
                                                    1980: "1980",
                                                    2000: "2000",
                                                    2025: "2025",
                                                },
                                                value=[1950, 2030],
                                                allowCross=False,
                                                tooltip={"placement": "bottom", "always_visible": False},
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    # Complexity Range Filter
                                    html.Div(
                                        [
                                            html.Label("Complexity"),
                                            dcc.RangeSlider(
                                                id="similarity-complexity-slider",
                                                min=1.0,
                                                max=5.0,
                                                step=0.1,
                                                marks={1: "1", 2: "2", 3: "3", 4: "4", 5: "5"},
                                                value=[1.0, 5.0],
                                                allowCross=False,
                                                tooltip={"placement": "bottom", "always_visible": False},
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    # Min Ratings Filter
                                    html.Div(
                                        [
                                            html.Label("Minimum User Ratings"),
                                            dcc.Dropdown(
                                                id="similarity-min-ratings-dropdown",
                                                options=[
                                                    {"label": "Any", "value": 0},
                                                    {"label": "10+", "value": 10},
                                                    {"label": "50+", "value": 50},
                                                    {"label": "100+", "value": 100},
                                                    {"label": "500+", "value": 500},
                                                    {"label": "1,000+", "value": 1000},
                                                    {"label": "5,000+", "value": 5000},
                                                ],
                                                value=0,
                                                clearable=False,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                                className="mt-3",
                            ),
                            id="similarity-filter-collapse",
                            is_open=False,
                        ),
                    ],
                    className="mb-4",
                ),
                # Search Button
                html.Div(
                    [
                        dbc.Button(
                            "Search",
                            id="similarity-search-button",
                            color="primary",
                            className="w-100",
                            disabled=True,  # Enabled when a game is selected
                        ),
                    ],
                    className="mb-3",
                ),
            ]
        ),
        className="mb-4 panel-card",
    )


def create_game_similarity_layout() -> html.Div:
    """Create the game similarity search page layout.

    Returns:
        Game similarity page layout.
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    # Page title
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H2("Game Similarity Search", className="mb-2"),
                                    html.P(
                                        "Find games similar to your favorites using AI-powered embeddings. "
                                        "Select a game and discover related titles based on mechanics, "
                                        "themes, and gameplay characteristics.",
                                        className="text-muted mb-4",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Main layout: sidebar + content
                    dbc.Row(
                        [
                            # Sidebar - Filters
                            dbc.Col(
                                create_similarity_filters(),
                                className="filters-sidebar",
                            ),
                            # Content area
                            dbc.Col(
                                [
                                    # Selected game info card with loading spinner
                                    dcc.Loading(
                                        dbc.Card(
                                            dbc.CardBody(
                                                html.Div(id="similarity-source-game-info")
                                            ),
                                            id="similarity-source-game-card",
                                            className="mb-4 panel-card",
                                            style={"display": "none"},
                                        ),
                                        type="circle",
                                        color="#0d6efd",
                                    ),
                                    # Loading indicator
                                    dbc.Spinner(
                                        html.Div(id="similarity-loading"),
                                        color="primary",
                                        type="border",
                                    ),
                                    # Results card
                                    dbc.Card(
                                        dbc.CardBody(
                                            html.Div(
                                                id="similarity-results-container",
                                                children=[
                                                    html.Div(
                                                        [
                                                            html.I(
                                                                className="fas fa-search fa-3x text-muted mb-3"
                                                            ),
                                                            html.H5(
                                                                "Select a Game to Get Started",
                                                                className="text-muted",
                                                            ),
                                                            html.P(
                                                                "Use the search on the left to find a game, "
                                                                "then click 'Find Similar Games' to discover "
                                                                "related titles.",
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        className="text-center py-5",
                                                    )
                                                ],
                                            )
                                        ),
                                        className="panel-card",
                                    ),
                                ],
                            ),
                        ],
                        className="flex-nowrap",
                    ),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
            # Store for selected game data
            dcc.Store(id="similarity-selected-game-store"),
        ],
        className="d-flex flex-column min-vh-100",
    )
