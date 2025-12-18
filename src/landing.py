"""Flask blueprint for the landing page."""

from flask import Blueprint, render_template
import os

# Create blueprint with custom template and static folders
# Paths are relative to root since templates/ and static/ are at project root
landing_bp = Blueprint(
    "landing",
    __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/landing/static",
)

# Module configurations
FEATURES = [
    {
        "title": "Game Search",
        "description": "Search and explore board games with advanced filtering options",
        "icon": "fas fa-search",
        "color": "#f97316",  # orange
        "route": "/app/game-search",
    },
    {
        "title": "Game Predictions",
        "description": "ML-powered predictions for upcoming and new games",
        "icon": "fas fa-bullseye",
        "color": "#a855f7",  # purple
        "route": "/app/upcoming-predictions",
    },
    {
        "title": "Game Similarity",
        "description": "Find similar games based on mechanics and themes",
        "icon": "fas fa-dice",
        "color": "#22c55e",  # green
        "route": None,  # Coming soon
    },
    {
        "title": "Collection Models",
        "description": "Personalized collection analysis and recommendations",
        "icon": "fas fa-chart-pie",
        "color": "#3b82f6",  # blue
        "route": None,  # Coming soon
    },
]

REPORTS = [
    {
        "title": "New Games",
        "description": "Track newly added games to BoardGameGeek",
        "icon": "fas fa-plus-circle",
        "color": "#ef4444",  # red
        "route": "/app/new-games",
    },
    {
        "title": "Game Ratings",
        "description": "Interactive rating analytics and trends over time",
        "icon": "fas fa-chart-line",
        "color": "#06b6d4",  # cyan
        "route": "/app/game-ratings",
    },
    {
        "title": "Publishers",
        "description": "Publisher statistics and game catalogs",
        "icon": "fas fa-building",
        "color": "#ec4899",  # pink
        "route": None,  # Coming soon
    },
    {
        "title": "Designers",
        "description": "Designer profiles and game portfolios",
        "icon": "fas fa-pencil-ruler",
        "color": "#eab308",  # yellow
        "route": None,  # Coming soon
    },
]

MONITORING = [
    {
        "title": "BigQuery",
        "description": "Database statistics and table information",
        "icon": "fas fa-database",
        "color": "#14b8a6",  # teal
        "route": None,  # Coming soon
    },
    {
        "title": "ETL",
        "description": "Data pipeline monitoring and job status",
        "icon": "fas fa-cogs",
        "color": "#6366f1",  # indigo
        "route": None,  # Coming soon
    },
    {
        "title": "Deployments",
        "description": "Application deployment status and logs",
        "icon": "fas fa-rocket",
        "color": "#f59e0b",  # amber
        "route": None,  # Coming soon
    },
]


@landing_bp.route("/")
def index():
    """Render the landing page."""
    return render_template(
        "landing.html",
        features=FEATURES,
        reports=REPORTS,
        monitoring=MONITORING,
    )
