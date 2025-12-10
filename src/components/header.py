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
                                    dbc.Col(html.I(className="fas fa-dice-d20 fa-2x me-2")),
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
                                    dbc.NavItem(dbc.NavLink("Home", href="/")),
                                    dbc.NavItem(dbc.NavLink("Game Search", href="/game-search")),
                                    dbc.NavItem(dbc.NavLink("New Games", href="/new-games")),
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


def create_page_header(title: str, subtitle: str = None) -> html.Div:
    """Create a page header with title and optional subtitle.

    Args:
        title: Page title
        subtitle: Optional page subtitle

    Returns:
        Page header component
    """
    header_content = [html.H1(title, className="display-4")]

    if subtitle:
        header_content.append(html.P(subtitle, className="lead"))

    return html.Div(
        header_content,
        className="mb-4 pb-2 border-bottom",
    )
