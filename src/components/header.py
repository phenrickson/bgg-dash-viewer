"""Header component for the Board Game Data Explorer."""

from dash import html
import dash_bootstrap_components as dbc


def create_header() -> html.Div:
    """Create the application header.

    Returns:
        Header component
    """
    return html.Div(
        [
            dbc.Navbar(
                dbc.Container(
                    [
                        html.A(
                            # Use row and col to control vertical alignment of logo / brand
                            dbc.Row(
                                [
                                    dbc.Col(html.I(className="fas fa-dice-d20 fa-2x me-2", style={"color": "#6366f1"})),
                                    dbc.Col(
                                        dbc.NavbarBrand(
                                            "Board Game Data Explorer", className="ms-2 fs-2"
                                        )
                                    ),
                                ],
                                align="center",
                                className="g-0",
                            ),
                            href="/",
                            style={"textDecoration": "none"},
                        ),
                        dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavItem(dbc.NavLink("Game Search", href="/app/game-search")),
                                    dbc.NavItem(dbc.NavLink("Similar Games", href="/app/game-similarity")),
                                    dbc.NavItem(dbc.NavLink("New Games", href="/app/new-games")),
                                    dbc.NavItem(dbc.NavLink("Predictions", href="/app/upcoming-predictions")),
                                    dbc.NavItem(dbc.NavLink("Experiments", href="/app/experiments")),
                                    dbc.NavItem(dbc.NavLink("Game Ratings", href="/app/game-ratings")),
                                ],
                                className="ms-auto",
                                navbar=True,
                            ),
                            id="navbar-collapse",
                            navbar=True,
                        ),
                    ]
                ),
                color="primary",
                dark=True,
                className="mb-4",
            ),
        ]
    )


def create_page_header(
    title: str,
    subtitle: str = None,
    show_border: bool = True,
) -> html.Div:
    """Create a standardized page header with title and optional subtitle.

    Args:
        title: Page title.
        subtitle: Optional page subtitle.
        show_border: Whether to show bottom border (default True).

    Returns:
        Page header component.
    """
    header_content = [html.H1(title, className="display-5 mb-2")]

    if subtitle:
        header_content.append(html.P(subtitle, className="lead text-muted"))

    border_class = " pb-3 border-bottom" if show_border else ""

    return html.Div(
        header_content,
        className=f"mb-4{border_class}",
    )
