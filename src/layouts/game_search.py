"""Game search page layout for the Board Game Data Explorer."""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header
from ..components.footer import create_footer


# Complexity buckets (label → [min, max])
COMPLEXITY_BUCKETS: dict[str, tuple[str, list[float]]] = {
    "any": ("Any", [1.0, 5.0]),
    "light": ("Light", [1.0, 2.0]),
    "medium_light": ("Medium-Light", [2.0, 2.5]),
    "medium": ("Medium", [2.5, 3.0]),
    "medium_heavy": ("Medium-Heavy", [3.0, 3.5]),
    "heavy": ("Heavy", [3.5, 5.0]),
}

# Player count options for chip row
PLAYER_COUNT_OPTIONS = [
    ("any", "Any"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
    (5, "5"),
    (6, "6"),
    (7, "7"),
    (8, "8+"),
]


def _chip_group(
    chip_type: str,
    options: list[tuple],
    selected_value,
) -> dbc.ButtonGroup:
    """Render a chip-style single-select button group.

    Args:
        chip_type: Identifier used for pattern-matching callbacks
            (e.g. "pc-chip", "cx-chip").
        options: List of (value, label) pairs.
        selected_value: Which chip should start filled (not outlined).
    """
    buttons = []
    for value, label in options:
        buttons.append(
            dbc.Button(
                label,
                id={"type": chip_type, "value": value},
                color="primary",
                outline=value != selected_value,
                size="sm",
                className="chip-btn",
            )
        )
    return dbc.ButtonGroup(buttons, className="flex-wrap")


def _primary_filters() -> html.Div:
    """Two stacked chip rows for the main facets: player count, complexity."""
    return html.Div(
        [
            # Player Count row
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                "Player Count",
                                className="text-uppercase fw-bold small text-muted me-3",
                            ),
                            dbc.ButtonGroup(
                                [
                                    dbc.Button(
                                        "Best",
                                        id="player-count-best-button",
                                        color="primary",
                                        outline=False,
                                        size="sm",
                                    ),
                                    dbc.Button(
                                        "Rec.",
                                        id="player-count-recommended-button",
                                        color="primary",
                                        outline=True,
                                        size="sm",
                                    ),
                                ],
                            ),
                            html.Div(
                                id="player-count-type-store",
                                style={"display": "none"},
                                children="best",
                            ),
                        ],
                        className="d-flex align-items-center mb-2",
                    ),
                    _chip_group("pc-chip", PLAYER_COUNT_OPTIONS, selected_value="any"),
                ],
                className="mb-4",
            ),
            # Complexity row
            html.Div(
                [
                    html.Span(
                        "Complexity",
                        className="text-uppercase fw-bold small text-muted d-block mb-2",
                    ),
                    _chip_group(
                        "cx-chip",
                        [(k, v[0]) for k, v in COMPLEXITY_BUCKETS.items()],
                        selected_value="any",
                    ),
                ],
                className="mb-3",
            ),
            # Stores for selected chip values
            dcc.Store(id="player-count-store", data="any"),
            dcc.Store(id="complexity-bucket-store", data="any"),
        ]
    )


def _search_action_row() -> html.Div:
    """Prominent Search button with Reset + More Filters toggle alongside."""
    return html.Div(
        [
            dbc.Button(
                [html.I(className="fas fa-search me-2"), "Search Games"],
                id="search-button",
                color="primary",
                size="lg",
                className="px-5",
            ),
            dbc.Button(
                "Reset",
                id="reset-filters-button",
                color="secondary",
                outline=True,
                className="ms-2",
            ),
            dbc.Button(
                [html.I(className="fas fa-sliders-h me-2"), "More Filters"],
                id="advanced-filters-toggle",
                color="link",
                className="text-decoration-none ms-auto",
            ),
        ],
        className="d-flex align-items-center mb-3",
    )


def _advanced_filters() -> html.Div:
    """Collapsible advanced filters: year range + tag multi-selects."""
    return html.Div(
        [
            dbc.Collapse(
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Year Published",
                                                className="small fw-bold",
                                            ),
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
                                                tooltip={
                                                    "placement": "bottom",
                                                    "always_visible": True,
                                                },
                                            ),
                                        ],
                                        md=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Results Limit",
                                                className="small fw-bold",
                                            ),
                                            dcc.Dropdown(
                                                id="results-per-page",
                                                options=[
                                                    {"label": "100", "value": 100},
                                                    {"label": "250", "value": 250},
                                                    {"label": "500", "value": 500},
                                                    {"label": "1,000", "value": 1000},
                                                ],
                                                value=100,
                                                clearable=False,
                                            ),
                                        ],
                                        md=3,
                                    ),
                                ],
                                className="g-3 mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Publishers", className="small fw-bold"
                                            ),
                                            dcc.Dropdown(
                                                id="publisher-dropdown",
                                                options=[],
                                                multi=True,
                                                placeholder="Any",
                                            ),
                                        ],
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Designers", className="small fw-bold"
                                            ),
                                            dcc.Dropdown(
                                                id="designer-dropdown",
                                                options=[],
                                                multi=True,
                                                placeholder="Any",
                                            ),
                                        ],
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Categories", className="small fw-bold"
                                            ),
                                            dcc.Dropdown(
                                                id="category-dropdown",
                                                options=[],
                                                multi=True,
                                                placeholder="Any",
                                            ),
                                        ],
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Mechanics", className="small fw-bold"
                                            ),
                                            dcc.Dropdown(
                                                id="mechanic-dropdown",
                                                options=[],
                                                multi=True,
                                                placeholder="Any",
                                            ),
                                        ],
                                        md=3,
                                    ),
                                ],
                                className="g-3",
                            ),
                        ],
                        className="py-3",
                    ),
                    className="panel-card",
                ),
                id="advanced-filters-collapse",
                is_open=False,
            ),
            # Keep the filter-options-container as a hidden trigger for dropdown loading
            html.Div(
                id="filter-options-container",
                children="init",
                style={"display": "none"},
            ),
            html.Div(id="filter-loading-indicator", style={"display": "none"}),
        ],
        className="mb-3",
    )


def _results_toolbar() -> html.Div:
    """Toolbar above the results: result count, sort, view toggle."""
    return html.Div(
        [
            html.Div(
                id="search-result-count",
                className="text-muted small me-auto align-self-center",
            ),
            html.Div(
                [
                    html.Span("Sort by", className="small text-muted me-2"),
                    dcc.Dropdown(
                        id="sort-dropdown",
                        options=[
                            {"label": "Geek Rating", "value": "bayes_average:DESC"},
                            {"label": "Avg Rating", "value": "average_rating:DESC"},
                            {"label": "Users Rated", "value": "users_rated:DESC"},
                            {"label": "Year (newest)", "value": "year_published:DESC"},
                            {"label": "Year (oldest)", "value": "year_published:ASC"},
                            {"label": "Complexity (lightest)", "value": "average_weight:ASC"},
                            {"label": "Complexity (heaviest)", "value": "average_weight:DESC"},
                            {"label": "Name (A–Z)", "value": "name:ASC"},
                        ],
                        value="bayes_average:DESC",
                        clearable=False,
                        style={"minWidth": "200px"},
                    ),
                ],
                className="d-flex align-items-center me-3",
            ),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        [html.I(className="fas fa-th-large me-2"), "Cards"],
                        id="view-toggle-cards",
                        color="primary",
                        outline=False,
                        size="sm",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-table me-2"), "Table"],
                        id="view-toggle-table",
                        color="primary",
                        outline=True,
                        size="sm",
                    ),
                ],
            ),
            dcc.Store(id="search-view-toggle", data="cards"),
        ],
        className="d-flex align-items-center mb-3",
    )


def create_game_search_layout() -> html.Div:
    """Create the game search page layout."""
    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    html.H2("Search Games", className="mb-1"),
                    html.P(
                        "Browse the BGG catalog by player count and complexity.",
                        className="text-muted mb-4",
                    ),
                    _primary_filters(),
                    _search_action_row(),
                    _advanced_filters(),
                    html.Hr(className="my-3"),
                    _results_toolbar(),
                    dcc.Loading(
                        id="search-loading",
                        type="circle",
                        overlay_style={"visibility": "visible", "filter": "blur(2px)"},
                        children=html.Div(id="search-results-container"),
                    ),
                    # Pagination shown when results > page size
                    html.Div(
                        dbc.Pagination(
                            id="search-pagination",
                            max_value=1,
                            active_page=1,
                            size="sm",
                            first_last=True,
                            previous_next=True,
                            fully_expanded=False,
                        ),
                        id="search-pagination-wrapper",
                        className="d-flex justify-content-center mt-3",
                        style={"display": "none"},
                    ),
                    dcc.Store(id="search-results-store"),
                    dcc.Store(id="search-page-store", data=1),
                    # Details modal (populated on card click)
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle(id="game-details-modal-title")),
                            dbc.ModalBody(id="game-details-modal-body"),
                        ],
                        id="game-details-modal",
                        size="lg",
                        is_open=False,
                        scrollable=True,
                    ),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
