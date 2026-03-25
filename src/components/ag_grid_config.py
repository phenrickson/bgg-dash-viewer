"""AG Grid configuration for consistent table styling across the application."""

from typing import Any

from ..theme import AG_GRID_CLASS


def get_default_grid_options() -> dict[str, Any]:
    """Get default AG Grid options for consistent behavior.

    Returns:
        Dictionary of AG Grid options.
    """
    return {
        "pagination": True,
        "paginationPageSize": 25,
        "paginationPageSizeSelector": [25, 50, 100, 200],
        "animateRows": True,
        "rowSelection": "single",
        "suppressCellFocus": True,
    }


def get_default_column_def() -> dict[str, Any]:
    """Get base column definition settings.

    Returns:
        Dictionary of default column settings.
    """
    return {
        "sortable": True,
        "filter": True,
        "resizable": True,
        "minWidth": 80,
    }


def get_grid_style(height: str | None = None) -> dict[str, str]:
    """Get standard grid container style.

    Args:
        height: Height of the grid container. None for autoHeight mode.

    Returns:
        Style dictionary for the grid.
    """
    style = {"width": "100%"}
    if height:
        style["height"] = height
    return style


def get_grid_class_name() -> str:
    """Get the standard AG Grid class name for Vizro theming.

    Returns:
        AG Grid class name string.
    """
    return AG_GRID_CLASS


# Column definitions for different table types


def get_search_results_column_defs() -> list[dict[str, Any]]:
    """Get column definitions for game search results table.

    Returns:
        List of column definitions.
    """
    return [
        {
            "field": "name",
            "headerName": "Game",
            "cellRenderer": "GameInfo",
            "flex": 2,
            "minWidth": 200,
            "filter": "agTextColumnFilter",
            "autoHeight": True,
            "wrapText": True,
        },
        {
            "field": "bayes_average",
            "headerName": "Geek Rating",
            "flex": 1,
            "minWidth": 100,
            "valueFormatter": {"function": "d3.format('.2f')(params.value)"},
            "filter": "agNumberColumnFilter",
            "valueFormatter": {"function": "d3.format('.2f')(params.value)"},
            "cellStyle": {"textAlign": "center"},
        },
        {
            "field": "average_rating",
            "headerName": "Avg Rating",
            "flex": 1,
            "minWidth": 100,
            "filter": "agNumberColumnFilter",
            "valueFormatter": {"function": "d3.format('.2f')(params.value)"},
            "cellStyle": {"textAlign": "center"},
        },
        {
            "field": "average_weight",
            "headerName": "Complexity",
            "flex": 1,
            "minWidth": 100,
            "filter": "agNumberColumnFilter",
            "cellRenderer": "ComplexityNumber",
        },
        {
            "field": "playtime",
            "headerName": "Playtime",
            "flex": 1,
            "minWidth": 100,
            "valueGetter": {
                "function": "params.data.min_playtime === params.data.max_playtime ? (params.data.min_playtime || '-') + 'm' : (params.data.min_playtime || '?') + '-' + (params.data.max_playtime || '?') + 'm'"
            },
            "filter": "agTextColumnFilter",
            "cellStyle": {"textAlign": "center"},
        },
        {
            "field": "players",
            "headerName": "Players",
            "headerClass": "ag-header-center",
            "flex": 1,
            "minWidth": 120,
            "filter": "agTextColumnFilter",
            "cellRenderer": "PlayerCountPills",
            "cellStyle": {"textAlign": "center"},
        },
    ]


def get_new_games_column_defs() -> list[dict[str, Any]]:
    """Get column definitions for new games monitoring table.

    Returns:
        List of column definitions.
    """
    return [
        {
            "field": "name",
            "headerName": "Game",
            "flex": 2,
            "minWidth": 200,
            "cellRenderer": "GameInfo",
            "filter": "agTextColumnFilter",
            "autoHeight": True,
            "wrapText": True,
        },
        {
            "field": "designers",
            "headerName": "Designers",
            "flex": 1,
            "minWidth": 150,
            "cellRenderer": "BadgeList",
            "cellRendererParams": {"badgeColor": "#6366f1", "maxVisible": 3},
            "filter": "agTextColumnFilter",
            "autoHeight": True,
        },
        {
            "field": "publishers",
            "headerName": "Publishers",
            "flex": 1,
            "minWidth": 150,
            "cellRenderer": "BadgeList",
            "cellRendererParams": {"badgeColor": "#4b5563", "maxVisible": 3},
            "filter": "agTextColumnFilter",
            "autoHeight": True,
        },
        {
            "field": "categories",
            "headerName": "Categories",
            "flex": 1,
            "minWidth": 150,
            "cellRenderer": "BadgeList",
            "cellRendererParams": {"badgeColor": "#0d9488", "maxVisible": 3},
            "filter": "agTextColumnFilter",
            "autoHeight": True,
        },
        {
            "field": "load_date",
            "headerName": "Added",
            "width": 140,
            "cellRenderer": "DateTimeStacked",
            "filter": "agTextColumnFilter",
            "autoHeight": True,
        },
    ]


def get_predictions_column_defs() -> list[dict[str, Any]]:
    """Get column definitions for predictions table.

    Returns:
        List of column definitions.
    """
    return [
        {
            "field": "name",
            "headerName": "Game",
            "cellRenderer": "GameInfo",
            "flex": 2,
            "minWidth": 200,
            "filter": "agTextColumnFilter",
            "autoHeight": True,
            "wrapText": True,
        },
        {
            "headerName": "Estimated",
            "headerClass": "ag-header-center",
            "children": [
                {
                    "field": "predicted_geek_rating",
                    "headerName": "Geek Rating",
                    "flex": 1,
                    "minWidth": 110,
                    "valueFormatter": {"function": "d3.format('.3f')(params.value)"},
                    "filter": "agNumberColumnFilter",
                },
                {
                    "field": "predicted_hurdle_prob",
                    "headerName": "Hurdle Prob",
                    "flex": 1,
                    "minWidth": 110,
                    "valueFormatter": {"function": "d3.format('.3f')(params.value)"},
                    "filter": "agNumberColumnFilter",
                },
                {
                    "field": "predicted_complexity",
                    "headerName": "Complexity",
                    "flex": 1,
                    "minWidth": 100,
                    "valueFormatter": {"function": "d3.format('.2f')(params.value)"},
                    "filter": "agNumberColumnFilter",
                },
                {
                    "field": "predicted_rating",
                    "headerName": "Rating",
                    "flex": 1,
                    "minWidth": 90,
                    "valueFormatter": {"function": "d3.format('.2f')(params.value)"},
                    "filter": "agNumberColumnFilter",
                },
                {
                    "field": "predicted_users_rated",
                    "headerName": "Users Rated",
                    "flex": 1,
                    "minWidth": 110,
                    "valueFormatter": {"function": "d3.format(',.0f')(params.value)"},
                    "filter": "agNumberColumnFilter",
                },
            ],
        },
    ]


def get_jobs_column_defs() -> list[dict[str, Any]]:
    """Get column definitions for prediction jobs table.

    Returns:
        List of column definitions.
    """
    return [
        {
            "field": "job_id",
            "headerName": "Job ID",
            "width": 280,
            "filter": "agTextColumnFilter",
            "cellStyle": {"fontFamily": "monospace", "fontSize": "12px"},
        },
        {
            "field": "num_predictions",
            "headerName": "# Predictions",
            "width": 120,
            "valueFormatter": {"function": "d3.format(',')(params.value)"},
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "latest_prediction",
            "headerName": "Latest",
            "width": 160,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "earliest_prediction",
            "headerName": "Earliest",
            "width": 160,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "min_year",
            "headerName": "Min Year",
            "width": 100,
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "max_year",
            "headerName": "Max Year",
            "width": 100,
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "avg_predicted_rating",
            "headerName": "Avg Rating",
            "width": 110,
            "valueFormatter": {"function": "d3.format('.3f')(params.value)"},
            "filter": "agNumberColumnFilter",
        },
        {
            "field": "hurdle_experiment",
            "headerName": "Hurdle Model",
            "width": 140,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "complexity_experiment",
            "headerName": "Complexity Model",
            "width": 150,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "rating_experiment",
            "headerName": "Rating Model",
            "width": 140,
            "filter": "agTextColumnFilter",
        },
        {
            "field": "users_rated_experiment",
            "headerName": "Users Rated Model",
            "width": 160,
            "filter": "agTextColumnFilter",
        },
    ]
