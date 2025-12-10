"""New games monitoring page layout for the Board Game Data Explorer."""

from datetime import datetime, timedelta
from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components.header import create_header, create_page_header
from ..components.footer import create_footer


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
                    html.H1("New Games Added", className="mb-2"),
                    html.P("Monitoring new games added to the warehouse", className="text-muted mb-1"),
                    html.P(
                        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                        className="text-muted mb-4",
                        style={"fontSize": "0.9rem"}
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
                    dbc.Spinner(
                        html.Div(id="new-games-loading"),
                        color="primary",
                        type="border",
                    ),

                    # Results container
                    html.Div(id="new-games-results-container"),
                ],
                fluid=True,
                className="mb-5",
            ),
            create_footer(),
        ],
        className="d-flex flex-column min-vh-100",
    )
