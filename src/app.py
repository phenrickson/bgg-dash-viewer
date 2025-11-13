"""Main application module for the BGG Dash Viewer."""

import os
import logging
from typing import Dict, Any

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from flask_caching import Cache

from .config import get_app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get application configuration
app_config = get_app_config()

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CERULEAN, dbc.icons.FONT_AWESOME],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
    suppress_callback_exceptions=True,
)

# Add clientside callback to set dark mode by default
app.clientside_callback(
    """
    function(trigger) {
        document.documentElement.setAttribute("data-bs-theme", "dark");
        return window.dash_clientside.no_update;
    }
    """,
    dash.Output("_", "children"),
    dash.Input("_", "children"),
)

# Add clientside callback to trigger filter options loading on page load
app.clientside_callback(
    """
    function(pathname) {
        if (pathname === "/game-search") {
            return "load";
        }
        return "init";
    }
    """,
    dash.Output("filter-options-container", "children"),
    dash.Input("url", "pathname"),
)

# Set app title
app.title = "BGG Dash Viewer"

# Initialize cache
cache = Cache(
    app.server,
    config={
        "CACHE_TYPE": "filesystem",
        "CACHE_DIR": ".cache-data",
        "CACHE_DEFAULT_TIMEOUT": app_config["cache_timeout"],
    },
)

# Define app layout with URL routing
app.layout = html.Div(
    [
        html.Div(id="_", style={"display": "none"}),  # Hidden div for clientside callback
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ]
)


# URL routing callback
@app.callback(
    dash.dependencies.Output("page-content", "children"),
    [dash.dependencies.Input("url", "pathname")],
)
def display_page(pathname: str) -> Any:
    """Route to the appropriate page based on URL pathname.

    Args:
        pathname: URL path

    Returns:
        Page layout
    """
    # Import layouts here to avoid circular imports
    from .layouts.home import create_home_layout
    from .layouts.game_search import create_game_search_layout
    from .layouts.game_details import create_game_details_layout
    from .layouts.dashboard import create_dashboard_layout

    logger.info(f"Routing to: {pathname}")

    if pathname == "/game-search":
        return create_game_search_layout()
    elif pathname == "/dashboard":
        return create_dashboard_layout()
    elif pathname and pathname.startswith("/game/"):
        try:
            game_id = int(pathname.split("/")[-1])
            return create_game_details_layout(game_id)
        except (ValueError, IndexError):
            return html.Div(
                [
                    html.H1("404 - Game Not Found"),
                    html.P("The requested game could not be found."),
                    dcc.Link("Go back to home", href="/"),
                ]
            )
    else:
        return create_home_layout()


def main() -> None:
    """Run the application."""
    # Import callbacks to register them
    from .callbacks import register_callbacks

    # Register all callbacks
    register_callbacks(app, cache)

    # Run the app
    app.run(
        host=app_config["host"],
        port=app_config["port"],
        debug=app_config["debug"],
    )


if __name__ == "__main__":
    main()
