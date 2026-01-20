"""Standardized loading components for the Board Game Data Explorer."""

from typing import Any

from dash import html
import dash_bootstrap_components as dbc

from ..theme import SPINNER_CONFIG


def create_spinner(
    children: Any,
    spinner_id: str | None = None,
    fullscreen: bool = False,
) -> dbc.Spinner:
    """Create a standardized loading spinner.

    Args:
        children: Content to wrap with spinner.
        spinner_id: Optional ID for the spinner.
        fullscreen: Whether to show fullscreen spinner.

    Returns:
        Standardized spinner component.
    """
    kwargs = {
        "color": SPINNER_CONFIG["color"],
        "type": SPINNER_CONFIG["type"],
        "fullscreen": fullscreen,
    }
    if spinner_id is not None:
        kwargs["id"] = spinner_id
    return dbc.Spinner(children, **kwargs)


def create_loading_placeholder(message: str = "Loading...") -> html.Div:
    """Create a loading placeholder with spinner and message.

    Args:
        message: Loading message to display.

    Returns:
        Loading placeholder component.
    """
    return html.Div(
        [
            dbc.Spinner(
                color=SPINNER_CONFIG["color"],
                type=SPINNER_CONFIG["type"],
            ),
            html.P(message, className="text-muted mt-2"),
        ],
        className="text-center py-5",
    )
