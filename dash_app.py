"""Main Dash application module for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from flask_caching import Cache

from src.config import get_app_config
from src.theme import VIZRO_BOOTSTRAP
from src.landing import landing_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get application configuration
app_config = get_app_config()

# Initialize Dash app with Vizro Bootstrap theme
# Mount Dash at /app/ so Flask can serve the landing page at /
app = dash.Dash(
    __name__,
    external_stylesheets=[VIZRO_BOOTSTRAP, dbc.icons.FONT_AWESOME],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
    suppress_callback_exceptions=True,
    url_base_pathname="/app/",
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
        if (pathname === "/app/game-search") {
            return "load";
        }
        return "init";
    }
    """,
    dash.Output("filter-options-container", "children"),
    dash.Input("url", "pathname"),
)

# Set app title
app.title = "Board Game Data Explorer"

# Initialize cache
cache = Cache(
    app.server,
    config={
        "CACHE_TYPE": "filesystem",
        "CACHE_DIR": ".cache-data",
        "CACHE_DEFAULT_TIMEOUT": app_config["cache_timeout"],
    },
)


# Register Flask landing page blueprint
app.server.register_blueprint(landing_bp)


# Serve Flask landing page at root instead of Dash
@app.server.route("/")
def index():
    """Serve the landing page."""
    from flask import render_template
    from src.landing import FEATURES, REPORTS, MONITORING

    return render_template(
        "landing.html",
        features=FEATURES,
        reports=REPORTS,
        monitoring=MONITORING,
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
    from src.layouts.home import create_home_layout
    from src.layouts.game_search import create_game_search_layout
    from src.layouts.game_details import create_game_details_layout
    from src.layouts.game_ratings import create_dashboard_layout
    from src.layouts.new_games import create_new_games_layout
    from src.layouts.upcoming_predictions import create_upcoming_predictions_layout
    from src.layouts.experiments import create_experiments_layout
    from src.layouts.game_similarity import create_game_similarity_layout

    logger.info(f"Routing to: {pathname}")

    # Routes are now under /app/ prefix
    if pathname == "/app/game-search":
        return create_game_search_layout()
    elif pathname == "/app/game-ratings":
        return create_dashboard_layout()
    elif pathname == "/app/new-games":
        return create_new_games_layout()
    elif pathname == "/app/upcoming-predictions":
        return create_upcoming_predictions_layout()
    elif pathname == "/app/experiments":
        return create_experiments_layout()
    elif pathname == "/app/game-similarity":
        return create_game_similarity_layout()
    elif pathname and pathname.startswith("/app/game/"):
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
        # Default to game search as the main Dash page
        return create_game_search_layout()


# Import and register callbacks when module is loaded
from src.callbacks import register_callbacks

register_callbacks(app, cache)

# Expose server for gunicorn
server = app.server


def main() -> None:
    """Run the application."""
    # Run the app
    app.run(
        host=app_config["host"],
        port=app_config["port"],
        debug=app_config["debug"],
    )


if __name__ == "__main__":
    main()
