"""Game similarity search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer


def create_similarity_filters_sidebar() -> dbc.Card:
    """Create the filter sidebar for similarity search.

    Returns:
        Filter sidebar card.
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
                        dcc.Loading(
                            dcc.Dropdown(
                                id="similarity-game-dropdown",
                                options=[],
                                placeholder="Search top 25k games...",
                                searchable=True,
                                clearable=True,
                                optionHeight=35,
                                maxHeight=300,
                            ),
                            type="circle",
                            color="#6366f1",
                        ),
                        # Extended search for obscure games
                        html.Details(
                            [
                                html.Summary(
                                    "Can't find your game?",
                                    className="text-muted small mt-2",
                                    style={"cursor": "pointer"},
                                ),
                                dbc.InputGroup(
                                    [
                                        dbc.Input(
                                            id="similarity-extended-search-input",
                                            placeholder="Search all games...",
                                            size="sm",
                                        ),
                                        dbc.Button(
                                            "Search",
                                            id="similarity-extended-search-btn",
                                            color="secondary",
                                            size="sm",
                                        ),
                                    ],
                                    className="mt-2",
                                    size="sm",
                                ),
                                html.Div(
                                    id="similarity-extended-search-results",
                                    className="mt-2",
                                    style={"display": "none"},
                                ),
                            ],
                            className="mt-2",
                        ),
                    ],
                    className="mb-4",
                    style={"overflow": "visible"},
                ),
                # Number of Results
                html.Div(
                    [
                        html.Label("Number of Results"),
                        dcc.Dropdown(
                            id="similarity-top-k-dropdown",
                            options=[
                                {"label": "10", "value": 10},
                                {"label": "25", "value": 25},
                                {"label": "50", "value": 50},
                                {"label": "100", "value": 100},
                                {"label": "500", "value": 500},
                                {"label": "1,000", "value": 1000},
                                {"label": "5,000", "value": 5000},
                                {"label": "10,000", "value": 10000},
                                {"label": "25,000", "value": 25000},
                            ],
                            value=25,
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
                                    # Embedding Dimensions
                                    html.Div(
                                        [
                                            html.Label("Embedding Dimensions"),
                                            dcc.Dropdown(
                                                id="similarity-embedding-dims-dropdown",
                                                options=[
                                                    {"label": "64 (Full)", "value": 64},
                                                    {"label": "32", "value": 32},
                                                    {"label": "16", "value": 16},
                                                    {"label": "8", "value": 8},
                                                ],
                                                value=64,
                                                clearable=False,
                                            ),
                                            html.Small(
                                                "Lower dimensions = faster but less precise",
                                                className="text-muted",
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
                                                    {"label": "25+", "value": 25},
                                                    {"label": "50+", "value": 50},
                                                    {"label": "100+", "value": 100},
                                                    {"label": "500+", "value": 500},
                                                    {"label": "1,000+", "value": 1000},
                                                    {"label": "5,000+", "value": 5000},
                                                ],
                                                value=25,
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
                            disabled=True,
                        ),
                    ],
                    className="mb-3",
                ),
            ],
            style={"overflow": "visible"},
        ),
        className="mb-4 panel-card",
        style={"overflow": "visible"},
    )


def create_game_similarity_layout() -> html.Div:
    """Create the game similarity search page layout with tabs.

    Returns:
        Game similarity page layout.
    """
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    # Page title
                    html.H2("Similar Games", className="mb-2"),
                    html.P(
                        "Find games similar to your favorites using AI-powered embeddings.",
                        className="text-muted mb-4",
                    ),
                    # Tabs for different views
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="Game Neighbors",
                                tab_id="tab-neighbors",
                                children=[
                                    html.Div(
                                        [
                                            # Game selector for neighbors tab
                                            dbc.Card(
                                                dbc.CardBody(
                                                    [
                                                        html.Label(
                                                            "Select a Game",
                                                            className="fw-bold mb-2",
                                                        ),
                                                        dcc.Loading(
                                                            dcc.Dropdown(
                                                                id="neighbors-game-dropdown",
                                                                options=[],
                                                                placeholder="Search top 25k games...",
                                                                searchable=True,
                                                                clearable=True,
                                                                optionHeight=35,
                                                                maxHeight=300,
                                                            ),
                                                            type="circle",
                                                            color="#6366f1",
                                                        ),
                                                        # Extended search for obscure games
                                                        html.Details(
                                                            [
                                                                html.Summary(
                                                                    "Can't find your game?",
                                                                    className="text-muted small mt-2",
                                                                    style={"cursor": "pointer"},
                                                                ),
                                                                dbc.InputGroup(
                                                                    [
                                                                        dbc.Input(
                                                                            id="neighbors-extended-search-input",
                                                                            placeholder="Search all games...",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Button(
                                                                            "Search",
                                                                            id="neighbors-extended-search-btn",
                                                                            color="secondary",
                                                                            size="sm",
                                                                        ),
                                                                    ],
                                                                    className="mt-2",
                                                                    size="sm",
                                                                ),
                                                                html.Div(
                                                                    id="neighbors-extended-search-results",
                                                                    className="mt-2",
                                                                    style={"display": "none"},
                                                                ),
                                                            ],
                                                            className="mt-2",
                                                        ),
                                                    ],
                                                    style={"overflow": "visible"},
                                                ),
                                                className="mb-4 panel-card",
                                                style={"overflow": "visible"},
                                            ),
                                            # Source game card
                                            dcc.Loading(
                                                html.Div(
                                                    id="neighbors-source-card-container",
                                                    style={"display": "none"},
                                                ),
                                                type="circle",
                                                color="#0d6efd",
                                            ),
                                            # Neighbors cards container
                                            html.Div(
                                                id="neighbors-results-container",
                                                children=[
                                                    html.Div(
                                                        [
                                                            html.I(
                                                                className="fas fa-users fa-3x text-muted mb-3"
                                                            ),
                                                            html.H5(
                                                                "Select a Game",
                                                                className="text-muted",
                                                            ),
                                                            html.P(
                                                                "Choose a game above to see its most similar neighbors.",
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        className="text-center py-5",
                                                    )
                                                ],
                                            ),
                                        ],
                                        className="pt-4",
                                        style={"overflow": "visible"},
                                    ),
                                ],
                                style={"overflow": "visible"},
                            ),
                            dbc.Tab(
                                label="Similarity Search",
                                tab_id="tab-search",
                                children=[
                                    html.Div(
                                        [
                                            # Sidebar + Content layout
                                            dbc.Row(
                                                [
                                                    # Sidebar - Filters
                                                    dbc.Col(
                                                        create_similarity_filters_sidebar(),
                                                        className="filters-sidebar",
                                                    ),
                                                    # Content area
                                                    dbc.Col(
                                                        [
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
                                                                                        "then click 'Search' to find similar titles.",
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
                                        className="pt-4",
                                    ),
                                ],
                            ),
                        ],
                        id="similarity-tabs",
                        active_tab="tab-neighbors",
                        className="mb-3",
                        style={"overflow": "visible"},
                    ),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
            # Store for selected game data
            dcc.Store(id="similarity-selected-game-store"),
            dcc.Store(id="neighbors-selected-game-store"),
        ],
        className="d-flex flex-column min-vh-100",
    )
