"""Standardized loading components for the Board Game Data Explorer."""

from typing import Any

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..theme import SPINNER_CONFIG


def create_spinner(
    children: Any,
    spinner_id: str | None = None,
    fullscreen: bool = False,
    blur: bool = True,
) -> dcc.Loading:
    """Create the standardized loading spinner used across the app.

    Wraps `children` in a `dcc.Loading`. When `blur=True` (the default), a
    visible blur overlay keeps existing content in place during loading
    rather than replacing it with an empty container — same pattern as
    Game Search and Similar Games. Pass `blur=False` for inline elements
    like dropdowns where blurring the field itself looks weird.

    Args:
        children: Content to wrap with the loading overlay.
        spinner_id: Optional ID for the loading component.
        fullscreen: Reserved for compatibility; ignored.
        blur: If True (default), blur the wrapped content during loading.
            Set False for inline form controls.

    Returns:
        Standardized loading component.
    """
    del fullscreen  # accepted for backward compatibility; not used
    kwargs: dict[str, Any] = {"type": "circle"}
    if blur:
        kwargs["overlay_style"] = {"visibility": "visible", "filter": "blur(2px)"}
    if spinner_id is not None:
        kwargs["id"] = spinner_id
    return dcc.Loading(children, **kwargs)


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
