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
                    fluid=True,
                    children=[
                        html.A(
                            dbc.NavbarBrand(
                                "Board Game Data Explorer", className="fs-5"
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
                className="mb-2",
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
    header_content = [html.H3(title, className="mb-1")]

    if subtitle:
        header_content.append(html.P(subtitle, className="small text-muted mb-0"))

    border_class = " pb-2 border-bottom" if show_border else ""

    return html.Div(
        header_content,
        className=f"mb-3{border_class}",
    )
