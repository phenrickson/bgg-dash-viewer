"""Callbacks package for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from flask_caching import Cache

logger = logging.getLogger(__name__)


def register_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register all callbacks for the application.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Import callback modules
    from .search_callbacks import register_search_callbacks
    from .filter_callbacks import register_filter_callbacks
    from .dashboard_callbacks import register_dashboard_callbacks
    from .new_games_callbacks import register_new_games_callbacks

    # Register callbacks from each module
    logger.info("Registering search callbacks")
    register_search_callbacks(app, cache)

    logger.info("Registering filter callbacks")
    register_filter_callbacks(app, cache)

    logger.info("Registering dashboard callbacks")
    register_dashboard_callbacks(app, cache)

    logger.info("Registering new games callbacks")
    register_new_games_callbacks(app, cache)

    logger.info("All callbacks registered")
