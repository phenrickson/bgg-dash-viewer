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
                # Add "Powered by BGG" logo section
                dbc.Row(
                    dbc.Col(
                        html.Div(
                            html.A(
                                html.Img(
                                    src="https://cf.geekdo-images.com/HZy35cmzmmyV9BarSuk6ug__medium/img/Lru_FJkj084_7MInilQO4LiiB_U=/fit-in/500x500/filters:no_upscale():strip_icc()/pic7779581.png",
                                    alt="Powered by BGG",
                                    style={"height": "40px", "width": "auto", "opacity": "0.8"},
                                ),
                                href="https://boardgamegeek.com",
                                target="_blank",
                                title="Powered by BoardGameGeek",
                            ),
                            className="text-center mt-3",
                        ),
                        width=12,
                    ),
                    className="mt-2",
                ),
            ],
            fluid=True,
            className="py-3",
        ),
        className="mt-auto",
        style={"backgroundColor": "var(--bs-secondary-bg)"},
    )
