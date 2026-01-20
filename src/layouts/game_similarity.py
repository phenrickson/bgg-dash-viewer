"""Game similarity search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


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
                        create_spinner(
                            dcc.Dropdown(
                                id="similarity-game-dropdown",
                                options=[],
                                placeholder="Search top 25k games...",
                                searchable=True,
                                clearable=True,
                                optionHeight=50,
                                maxHeight=400,
                            ),
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
                                                    {
                                                        "label": "Dot Product",
                                                        "value": "dot_product",
                                                    },
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
                                                tooltip={
                                                    "placement": "bottom",
                                                    "always_visible": False,
                                                },
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    # Complexity Filter Mode
                                    html.Div(
                                        [
                                            html.Label("Complexity Filter"),
                                            dcc.Dropdown(
                                                id="similarity-complexity-mode-dropdown",
                                                options=[
                                                    {
                                                        "label": "Similar Complexity",
                                                        "value": "within_band",
                                                    },
                                                    {
                                                        "label": "Less Complex",
                                                        "value": "less_complex",
                                                    },
                                                    {
                                                        "label": "More Complex",
                                                        "value": "more_complex",
                                                    },
                                                    {
                                                        "label": "Custom Range",
                                                        "value": "absolute",
                                                    },
                                                ],
                                                value="within_band",
                                                clearable=False,
                                            ),
                                            html.Small(
                                                "Filter relative to the selected game's complexity",
                                                className="text-muted",
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    # Complexity Band (for relative modes)
                                    html.Div(
                                        [
                                            html.Label("Complexity Range (±)"),
                                            dcc.Slider(
                                                id="similarity-complexity-band-slider",
                                                min=0.25,
                                                max=2.0,
                                                step=0.25,
                                                marks={
                                                    0.25: "±0.25",
                                                    0.5: "±0.5",
                                                    1.0: "±1.0",
                                                    1.5: "±1.5",
                                                    2.0: "±2.0",
                                                },
                                                value=0.5,
                                                tooltip={
                                                    "placement": "bottom",
                                                    "always_visible": False,
                                                },
                                            ),
                                        ],
                                        id="similarity-complexity-band-container",
                                        className="mb-4",
                                    ),
                                    # Absolute Complexity Range (for custom mode)
                                    html.Div(
                                        [
                                            html.Label("Complexity Range"),
                                            dcc.RangeSlider(
                                                id="similarity-complexity-slider",
                                                min=1.0,
                                                max=5.0,
                                                step=0.1,
                                                marks={1: "1", 2: "2", 3: "3", 4: "4", 5: "5"},
                                                value=[1.0, 5.0],
                                                allowCross=False,
                                                tooltip={
                                                    "placement": "bottom",
                                                    "always_visible": False,
                                                },
                                            ),
                                        ],
                                        id="similarity-complexity-absolute-container",
                                        className="mb-4",
                                        style={"display": "none"},
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
                        "Find games similar to your favorites based on game features such as complexity, mechanics, categories and more.",
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
                                                        create_spinner(
                                                            dcc.Dropdown(
                                                                id="neighbors-game-dropdown",
                                                                options=[],
                                                                placeholder="Search top 25k games...",
                                                                searchable=True,
                                                                clearable=True,
                                                                optionHeight=50,
                                                                maxHeight=400,
                                                            ),
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
                                                        # Search button inside the card
                                                        dbc.Button(
                                                            "Find Similar Games",
                                                            id="neighbors-search-button",
                                                            color="primary",
                                                            className="w-100 mt-3",
                                                            disabled=True,
                                                        ),
                                                    ],
                                                    style={"overflow": "visible"},
                                                ),
                                                className="mb-4 panel-card",
                                                style={"overflow": "visible"},
                                            ),
                                            # Source card + results wrapped in Loading
                                            dcc.Loading(
                                                id="neighbors-loading",
                                                type="circle",
                                                overlay_style={"visibility": "visible", "filter": "blur(2px)"},
                                                custom_spinner=html.Div(
                                                    [
                                                        dbc.Spinner(color="primary", size="lg"),
                                                        html.P("Finding similar games...", className="text-muted mt-2"),
                                                    ],
                                                    className="text-center py-4",
                                                    style={
                                                        "position": "absolute",
                                                        "top": "20px",
                                                        "left": "50%",
                                                        "transform": "translateX(-50%)",
                                                        "zIndex": "1000",
                                                    },
                                                ),
                                                children=[
                                                    html.Div(
                                                        id="neighbors-source-card-container",
                                                        style={"display": "none"},
                                                    ),
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
                                                                        "Select a game and click 'Find Similar Games' to see results.",
                                                                        className="text-muted",
                                                                    ),
                                                                ],
                                                                className="text-center py-5",
                                                            )
                                                        ],
                                                    ),
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
                                                            create_spinner(
                                                                html.Div(id="similarity-loading"),
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
