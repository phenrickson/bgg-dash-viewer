"""New games monitoring page layout for the Board Game Data Explorer."""

from datetime import datetime, timedelta
from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer
from ..components.loading import create_spinner


def create_new_games_layout() -> html.Div:
    """Create the new games monitoring page layout.

    Returns:
        New games page layout
    """
    # Calculate default date range (last 7 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    return html.Div(
        [
            create_header(),
            dbc.Container(
                [
                    # Page header
                    create_page_header(
                        "New Games Added",
                        subtitle="Monitoring new games added to the warehouse",
                    ),

                    # Time range filter buttons
                    html.Div([
                        html.Label("Time Range:", className="me-2 mb-2"),
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    "Last 7 Days",
                                    id="btn-filter-7days",
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                    active=True,
                                    className="me-2",
                                ),
                                dbc.Button(
                                    "Last 30 Days",
                                    id="btn-filter-30days",
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                    className="me-2",
                                ),
                                dbc.Button(
                                    "Last Year",
                                    id="btn-filter-365days",
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                ),
                            ],
                        ),
                        # Hidden stores for selected time range
                        dcc.Store(id="new-games-days-back", data=7),
                    ], className="mb-4"),

                    # Loading spinner
                    create_spinner(
                        html.Div(id="new-games-loading"),
                    ),

                    # Results container
                    html.Div(id="new-games-results-container"),
                ],
                fluid=True,
                className="py-4 px-4",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
