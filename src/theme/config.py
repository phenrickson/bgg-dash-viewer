"""Centralized theme configuration for the Board Game Data Explorer."""

from typing import Any

import vizro

# Theme mode: "dark" or "light"
THEME_MODE = "dark"

# Vizro Bootstrap stylesheet
VIZRO_BOOTSTRAP = vizro.bootstrap

# Plotly template based on theme mode
PLOTLY_TEMPLATE = "vizro_dark" if THEME_MODE == "dark" else "vizro_light"

# AG Grid theme class
AG_GRID_CLASS = (
    "ag-theme-quartz-dark ag-theme-vizro"
    if THEME_MODE == "dark"
    else "ag-theme-quartz ag-theme-vizro"
)

# Semantic color tokens using Bootstrap CSS variables
COLORS = {
    "primary": "var(--bs-primary)",
    "secondary": "var(--bs-secondary)",
    "success": "var(--bs-success)",
    "warning": "var(--bs-warning)",
    "danger": "var(--bs-danger)",
    "info": "var(--bs-info)",
    "text": "var(--bs-body-color)",
    "background": "var(--bs-body-bg)",
    "surface": "var(--bs-secondary-bg)",
    "border": "var(--bs-border-color)",
}

# Standard layout configuration
LAYOUT_CONFIG = {
    "container_class": "mb-5",
    "page_wrapper_class": "d-flex flex-column min-vh-100",
    "card_class": "mb-4",
    "row_gutter_class": "g-3",
}

# Standard spinner configuration
SPINNER_CONFIG = {
    "color": "primary",
    "type": "border",
}


def get_plotly_layout_defaults() -> dict[str, Any]:
    """Get default Plotly layout settings for consistent chart styling.

    Returns:
        Dictionary of Plotly layout settings.
    """
    return {
        "template": PLOTLY_TEMPLATE,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "white"} if THEME_MODE == "dark" else {"color": "black"},
        "margin": {"l": 40, "r": 40, "t": 40, "b": 40},
    }
