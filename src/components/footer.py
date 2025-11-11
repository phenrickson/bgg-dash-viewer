"""Footer component for the BGG Dash Viewer."""

from dash import html
import dash_bootstrap_components as dbc


def create_footer() -> html.Footer:
    """Create the application footer.

    Returns:
        Footer component
    """
    return html.Footer(
        dbc.Container(
            [
                html.Hr(),
                dbc.Row(
                    [
                        dbc.Col(
                            html.P(
                                [
                                    "BGG Dash Viewer - A Dash-based viewer for BoardGameGeek data",
                                    html.Br(),
                                    html.Small(
                                        [
                                            "Data sourced from ",
                                            html.A(
                                                "BoardGameGeek",
                                                href="https://boardgamegeek.com",
                                                target="_blank",
                                            ),
                                            ". This application is not affiliated with or endorsed by BoardGameGeek.",
                                        ]
                                    ),
                                ],
                                className="text-muted",
                            ),
                            md=8,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.P(
                                        [
                                            html.Strong("Links"),
                                            html.Br(),
                                            html.A(
                                                "GitHub",
                                                href="https://github.com/yourusername/bgg-dash-viewer",
                                                target="_blank",
                                                className="me-3",
                                            ),
                                            html.A(
                                                "BoardGameGeek",
                                                href="https://boardgamegeek.com",
                                                target="_blank",
                                                className="me-3",
                                            ),
                                        ],
                                        className="text-muted",
                                    )
                                ],
                                className="text-end",
                            ),
                            md=4,
                        ),
                    ]
                ),
            ],
            fluid=True,
            className="py-3",
        ),
        className="mt-auto bg-light",
    )
