"""Game similarity search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


def create_advanced_search_filters() -> html.Div:
    """Create the inline filters for advanced similarity search.

    Returns:
        Filter content div (not wrapped in a card).
    """
    return html.Div(
        [
            html.Hr(className="my-3"),
            html.H6("Filters", className="mb-3"),
            # First row: Number of Results, Distance, Embedding, Min Ratings
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Number of Results", className="small"),
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
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Distance Metric", className="small"),
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
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Embedding Dimensions", className="small"),
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
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Minimum User Ratings", className="small"),
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
                        md=3,
                    ),
                ],
                className="mb-3",
            ),
            # Second row: Complexity filters
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Complexity Filter", className="small"),
                            dcc.Dropdown(
                                id="similarity-complexity-mode-dropdown",
                                options=[
                                    {"label": "Similar Complexity", "value": "within_band"},
                                    {"label": "Less Complex", "value": "less_complex"},
                                    {"label": "More Complex", "value": "more_complex"},
                                    {"label": "Custom Range", "value": "absolute"},
                                ],
                                value="within_band",
                                clearable=False,
                            ),
                            html.Small(
                                "Filter relative to the selected game's complexity",
                                className="text-muted",
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            # Complexity Band (for relative modes)
                            html.Div(
                                [
                                    html.Label("Complexity Range (±)", className="small"),
                                    dcc.Slider(
                                        id="similarity-complexity-band-slider",
                                        min=0.25,
                                        max=1.5,
                                        step=0.25,
                                        marks={
                                            0.25: "±0.25",
                                            0.5: "±0.5",
                                            1.0: "±1.0",
                                            1.5: "±1.5",
                                        },
                                        value=0.5,
                                        tooltip={
                                            "placement": "bottom",
                                            "always_visible": False,
                                        },
                                    ),
                                ],
                                id="similarity-complexity-band-container",
                            ),
                            # Absolute Complexity Range (for custom mode)
                            html.Div(
                                [
                                    html.Label("Complexity Range", className="small"),
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
                                style={"display": "none"},
                            ),
                        ],
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
        ],
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
                    # Tabs (navigation only, content managed separately)
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Game Neighbors", tab_id="tab-neighbors"),
                            dbc.Tab(label="Compare Games", tab_id="tab-compare"),
                            dbc.Tab(label="Advanced Search", tab_id="tab-search"),
                        ],
                        id="similarity-tabs",
                        active_tab="tab-neighbors",
                        className="mb-0",
                    ),
                    # Shared game selector (appears under tabs for all views)
                    dbc.Card(
                        dbc.CardBody(
                            [
                                # Game dropdown - full width
                                html.Label(
                                    "Select a Game",
                                    className="fw-bold mb-2",
                                ),
                                create_spinner(
                                    dcc.Dropdown(
                                        id="shared-game-dropdown",
                                        options=[],
                                        placeholder="Search top 1000 games...",
                                        searchable=True,
                                        clearable=True,
                                        optionHeight=50,
                                        maxHeight=400,
                                    ),
                                ),
                                html.Small(
                                    [
                                        "Can't find your game? ",
                                        html.A(
                                            "Search all games",
                                            id="shared-search-all-link",
                                            href="#",
                                            className="text-primary",
                                        ),
                                    ],
                                    className="text-muted mt-1 d-block",
                                ),
                                # Collapsible search for games not in top 1000
                                dbc.Collapse(
                                    html.Div(
                                        [
                                            html.Hr(className="my-3"),
                                            html.Label("Search All Games", className="fw-bold mb-2"),
                                            dbc.Input(
                                                id="shared-game-search-input",
                                                type="text",
                                                placeholder="Type at least 3 characters to search...",
                                                debounce=True,
                                            ),
                                            html.Div(
                                                id="shared-game-search-results",
                                                className="mt-2",
                                            ),
                                        ],
                                    ),
                                    id="shared-search-collapse",
                                    is_open=False,
                                ),
                                # Advanced search filters (shown only on Advanced Search tab)
                                html.Div(
                                    create_advanced_search_filters(),
                                    id="advanced-filters-container",
                                    style={"display": "none"},
                                ),
                                # Search button - full width below dropdown
                                dbc.Button(
                                    [
                                        html.I(className="fas fa-search me-2"),
                                        "Find Similar Games",
                                    ],
                                    id="shared-search-button",
                                    color="primary",
                                    size="lg",
                                    className="w-100 mt-3",
                                    disabled=True,
                                ),
                            ],
                            style={"overflow": "visible"},
                        ),
                        className="mt-3 mb-4 panel-card",
                        style={"overflow": "visible"},
                    ),
                    # Tab content container
                    html.Div(
                        [
                            # Game Neighbors content
                            html.Div(
                                dcc.Loading(
                                    id="neighbors-loading",
                                    type="circle",
                                    overlay_style={"visibility": "visible", "filter": "blur(2px)"},
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
                                                            "Find Similar Games",
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
                                id="tab-neighbors-content",
                            ),
                            # Why Similar? content
                            html.Div(
                                dcc.Loading(
                                    id="compare-loading",
                                    type="circle",
                                    overlay_style={"visibility": "visible", "filter": "blur(2px)"},
                                    children=[
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    html.Div(
                                                        id="compare-neighbors-list",
                                                        children=[
                                                            html.Div(
                                                                [
                                                                    html.I(className="fas fa-list fa-3x text-muted mb-3"),
                                                                    html.H5("Find Similar Games", className="text-muted"),
                                                                    html.P(
                                                                        "Select a game and click 'Find Similar Games' first.",
                                                                        className="text-muted",
                                                                    ),
                                                                ],
                                                                className="text-center py-5",
                                                            )
                                                        ],
                                                    ),
                                                    md=4,
                                                    className="pe-2",
                                                ),
                                                dbc.Col(
                                                    html.Div(
                                                        id="compare-panel",
                                                        children=[
                                                            html.Div(
                                                                [
                                                                    html.I(className="fas fa-balance-scale fa-3x text-muted mb-3"),
                                                                    html.H5("Compare Games", className="text-muted"),
                                                                    html.P(
                                                                        "Click a neighbor to see why it's similar.",
                                                                        className="text-muted",
                                                                    ),
                                                                ],
                                                                className="text-center py-5",
                                                            )
                                                        ],
                                                    ),
                                                    md=8,
                                                    className="ps-2",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                id="tab-compare-content",
                                style={"display": "none"},
                            ),
                            # Advanced Search content
                            html.Div(
                                [
                                    # Results area
                                    create_spinner(
                                        html.Div(id="similarity-loading"),
                                    ),
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
                                                                "Advanced Search",
                                                                className="text-muted",
                                                            ),
                                                            html.P(
                                                                "Configure the filters above and click "
                                                                "'Find Similar Games' to search.",
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
                                id="tab-search-content",
                                style={"display": "none"},
                            ),
                        ],
                        id="tab-content-container",
                    ),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
            # Stores for shared game data
            dcc.Store(id="shared-source-game-store"),
            dcc.Store(id="shared-neighbors-store"),
            # Legacy stores (for backward compatibility)
            dcc.Store(id="similarity-selected-game-store"),
        ],
        className="d-flex flex-column min-vh-100",
    )
