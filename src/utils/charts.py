"""Chart utilities for consistent Plotly styling across the application."""

from typing import Any

import plotly.express as px
import plotly.graph_objects as go

from ..theme import PLOTLY_TEMPLATE, get_plotly_layout_defaults


def apply_standard_layout(fig: go.Figure, **kwargs: Any) -> go.Figure:
    """Apply standard layout settings to a Plotly figure.

    Args:
        fig: Plotly figure to update.
        **kwargs: Additional layout settings to apply.

    Returns:
        Updated figure with standard styling.
    """
    defaults = get_plotly_layout_defaults()
    defaults.update(kwargs)
    fig.update_layout(**defaults)
    return fig


def create_scatter_plot(
    df,
    x: str,
    y: str,
    color: str | None = None,
    hover_data: list | None = None,
    title: str | None = None,
    **kwargs: Any,
) -> go.Figure:
    """Create a standardized scatter plot.

    Args:
        df: DataFrame with data to plot.
        x: Column name for x-axis.
        y: Column name for y-axis.
        color: Optional column name for color encoding.
        hover_data: Optional list of columns for hover tooltip.
        title: Optional chart title.
        **kwargs: Additional arguments for px.scatter.

    Returns:
        Plotly figure with standard styling.
    """
    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color,
        hover_data=hover_data,
        title=title,
        template=PLOTLY_TEMPLATE,
        **kwargs,
    )
    return apply_standard_layout(fig)


def create_bar_chart(
    df,
    x: str,
    y: str,
    color: str | None = None,
    title: str | None = None,
    orientation: str = "v",
    **kwargs: Any,
) -> go.Figure:
    """Create a standardized bar chart.

    Args:
        df: DataFrame with data to plot.
        x: Column name for x-axis.
        y: Column name for y-axis.
        color: Optional column name for color encoding.
        title: Optional chart title.
        orientation: Bar orientation ('v' for vertical, 'h' for horizontal).
        **kwargs: Additional arguments for px.bar.

    Returns:
        Plotly figure with standard styling.
    """
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        orientation=orientation,
        template=PLOTLY_TEMPLATE,
        **kwargs,
    )
    return apply_standard_layout(fig)


def create_histogram(
    df,
    x: str,
    nbins: int | None = None,
    title: str | None = None,
    **kwargs: Any,
) -> go.Figure:
    """Create a standardized histogram.

    Args:
        df: DataFrame with data to plot.
        x: Column name for values.
        nbins: Optional number of bins.
        title: Optional chart title.
        **kwargs: Additional arguments for px.histogram.

    Returns:
        Plotly figure with standard styling.
    """
    fig = px.histogram(
        df,
        x=x,
        nbins=nbins,
        title=title,
        template=PLOTLY_TEMPLATE,
        **kwargs,
    )
    return apply_standard_layout(fig)


def create_line_chart(
    df,
    x: str,
    y: str,
    color: str | None = None,
    title: str | None = None,
    **kwargs: Any,
) -> go.Figure:
    """Create a standardized line chart.

    Args:
        df: DataFrame with data to plot.
        x: Column name for x-axis.
        y: Column name for y-axis.
        color: Optional column name for color encoding.
        title: Optional chart title.
        **kwargs: Additional arguments for px.line.

    Returns:
        Plotly figure with standard styling.
    """
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        template=PLOTLY_TEMPLATE,
        **kwargs,
    )
    return apply_standard_layout(fig)


def get_chart_grid_style() -> dict[str, Any]:
    """Get standard grid line styling for charts.

    Returns:
        Dictionary with grid styling settings.
    """
    return {
        "showgrid": True,
        "gridcolor": "rgba(255,255,255,0.1)",
    }
