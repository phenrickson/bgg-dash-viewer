"""Callbacks package for the Board Game Data Explorer."""

import logging

import dash
from flask_caching import Cache

logger = logging.getLogger(__name__)

__all__ = ["register_callbacks"]


def register_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register all callbacks for the application.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Import callback modules
    from .search_callbacks import register_search_callbacks
    from .filter_callbacks import register_filter_callbacks
    from .game_ratings_callbacks import register_dashboard_callbacks
    from .new_games_callbacks import register_new_games_callbacks
    from .upcoming_predictions_callbacks import register_upcoming_predictions_callbacks
    from .experiments_callbacks import register_experiments_callbacks
    from .similarity_callbacks import register_similarity_callbacks
    from .monitoring_callbacks import register_monitoring_callbacks

    # Register callbacks from each module
    logger.info("Registering search callbacks")
    register_search_callbacks(app, cache)

    logger.info("Registering filter callbacks")
    register_filter_callbacks(app, cache)

    logger.info("Registering dashboard callbacks")
    register_dashboard_callbacks(app, cache)

    logger.info("Registering new games callbacks")
    register_new_games_callbacks(app, cache)

    logger.info("Registering upcoming predictions callbacks")
    register_upcoming_predictions_callbacks(app, cache)

    logger.info("Registering experiments callbacks")
    register_experiments_callbacks(app, cache)

    logger.info("Registering similarity callbacks")
    register_similarity_callbacks(app, cache)

    logger.info("Registering monitoring callbacks")
    register_monitoring_callbacks(app, cache)

    logger.info("All callbacks registered")
