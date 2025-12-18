"""New games monitoring callbacks for the Board Game Data Explorer."""

import logging
from typing import Any

import dash
from dash import html, dcc, ctx
from dash.dependencies import Input, Output, State
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from flask_caching import Cache
import pandas as pd
import plotly.graph_objects as go

from ..data.bigquery_client import BigQueryClient
from ..components.ag_grid_config import (
    get_default_grid_options,
    get_default_column_def,
    get_grid_style,
    get_grid_class_name,
    get_new_games_column_defs,
)
from ..theme import PLOTLY_TEMPLATE, get_plotly_layout_defaults

logger = logging.getLogger(__name__)


def register_new_games_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register new games monitoring callbacks.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """
    # Lazy-load BigQuery client to reduce startup time
    def get_bq_client() -> BigQueryClient:
        """Get or create BigQuery client instance."""
        if not hasattr(get_bq_client, '_client'):
            get_bq_client._client = BigQueryClient()
        return get_bq_client._client

    @app.callback(
        [
            Output("new-games-days-back", "data"),
            Output("btn-filter-7days", "active"),
            Output("btn-filter-30days", "active"),
            Output("btn-filter-365days", "active"),
        ],
        [
            Input("btn-filter-7days", "n_clicks"),
            Input("btn-filter-30days", "n_clicks"),
            Input("btn-filter-365days", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def update_days_back(
        btn_7days: int,
        btn_30days: int,
        btn_365days: int,
    ) -> tuple[int, bool, bool, bool]:
        """Update days back based on quick filter button clicks.

        Args:
            btn_7days: Click count for 7 days button
            btn_30days: Click count for 30 days button
            btn_365days: Click count for 365 days button

        Returns:
            Tuple of (days_back, btn7_active, btn30_active, btn365_active)
        """
        triggered_id = ctx.triggered_id

        if triggered_id == "btn-filter-7days":
            return (7, True, False, False)
        elif triggered_id == "btn-filter-30days":
            return (30, False, True, False)
        elif triggered_id == "btn-filter-365days":
            return (365, False, False, True)

        # Default: 7 days
        return (7, True, False, False)

    @app.callback(
        [
            Output("new-games-results-container", "children"),
            Output("new-games-loading", "children"),
        ],
        [
            Input("btn-filter-7days", "n_clicks"),
            Input("btn-filter-30days", "n_clicks"),
            Input("btn-filter-365days", "n_clicks"),
        ],
        [
            State("new-games-days-back", "data"),
        ],
    )
    def update_new_games_results(
        btn_7days: int,
        btn_30days: int,
        btn_365days: int,
        days_back: int,
    ) -> tuple[Any, str]:
        """Update the new games results table and visualizations.

        Args:
            btn_7days: Click count for 7 days button
            btn_30days: Click count for 30 days button
            btn_365days: Click count for 365 days button
            days_back: Number of days to look back

        Returns:
            Tuple of (results_content, loading_indicator)
        """
        try:
            # Determine days_back from triggered button
            triggered_id = ctx.triggered_id
            if triggered_id == "btn-filter-7days":
                days_back = 7
            elif triggered_id == "btn-filter-30days":
                days_back = 30
            elif triggered_id == "btn-filter-365days":
                days_back = 365
            elif days_back is None:
                days_back = 7

            logger.info(f"Fetching new games from last {days_back} days")

            # Fetch new games data
            client = get_bq_client()
            df = client.get_new_games(
                days_back=days_back,
                limit=500,
            )

            logger.info(f"Query returned {len(df) if isinstance(df, pd.DataFrame) else 0} games")

            # Check if df is valid DataFrame
            if not isinstance(df, pd.DataFrame):
                logger.error(f"Expected DataFrame but got {type(df)}")
                return (
                    dbc.Alert(
                        "Error: Unexpected data type returned from query",
                        color="danger",
                        className="mt-3",
                    ),
                    "",
                )

            if df.empty:
                return (
                    dbc.Alert(
                        "No new games found for the selected time range.",
                        color="info",
                        className="mt-3",
                    ),
                    "",
                )

            # Get summary statistics
            summary = client.get_new_games_summary(days_back=days_back)
            logger.info(f"Summary data: {summary}")

            # Extract values safely
            fetched_val = summary.get('new_games_fetched', 0)
            processed_val = summary.get('new_games_processed', 0)

            # Handle potential None or dict values
            new_games_fetched = int(fetched_val) if isinstance(fetched_val, (int, float)) and fetched_val is not None else 0
            new_games_processed = int(processed_val) if isinstance(processed_val, (int, float)) and processed_val is not None else 0

            logger.info(f"Fetched: {new_games_fetched}, Processed: {new_games_processed}")

            # Prepare daily aggregation for chart
            df_chart = df.copy()
            df_chart['date'] = pd.to_datetime(df_chart['load_timestamp']).dt.date
            daily_counts = df_chart.groupby('date').size().reset_index(name='count')
            daily_counts = daily_counts.sort_values('date')

            # Create time series chart with Vizro theming
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_counts['date'],
                y=daily_counts['count'],
                mode='lines+markers',
                line=dict(color='var(--bs-primary)', width=2),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(46, 134, 171, 0.2)',
            ))
            layout_defaults = get_plotly_layout_defaults()
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                xaxis_title="Date",
                yaxis_title="New Games Count",
                height=300,
                **{k: v for k, v in layout_defaults.items() if k != 'template'},
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            )

            # Prepare table data
            df_table = df.copy()
            df_table['load_timestamp'] = pd.to_datetime(df_table['load_timestamp']).dt.strftime('%m/%d/%y %H:%M:%S')
            df_table['users_rated'] = df_table['users_rated'].fillna(0).astype(int)

            # Create BGG link column as markdown
            df_table['bgg_link'] = df_table['game_id'].apply(
                lambda x: f'[BGG](https://boardgamegeek.com/boardgame/{x})'
            )

            # Create AG Grid with Vizro theming
            grid = dag.AgGrid(
                id='new-games-table',
                rowData=df_table[['game_id', 'bgg_link', 'name', 'year_published', 'users_rated', 'load_timestamp']].to_dict('records'),
                columnDefs=get_new_games_column_defs(),
                defaultColDef=get_default_column_def(),
                dashGridOptions=get_default_grid_options(),
                className=get_grid_class_name(),
                style=get_grid_style("500px"),
            )

            # Create summary stats section
            time_range_text = f"Last {days_back} Day" + ("s" if days_back > 1 else "")
            stats_section = html.Div([
                html.H3(f"New Games Activity ({time_range_text})", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("New Games Fetched", className="text-muted mb-1"),
                        html.H2(f"{new_games_fetched:,}", className="mb-0"),
                    ], md=6),
                    dbc.Col([
                        html.P("New Games Processed", className="text-muted mb-1"),
                        html.H2(f"{new_games_processed:,}", className="mb-0"),
                    ], md=6),
                ], className="mb-4"),
            ])

            # Combine all components
            results = html.Div([
                stats_section,
                html.H3("Daily New Games Fetched", className="mb-3 mt-4"),
                dcc.Graph(figure=fig, config={'displayModeBar': False}),
                html.H3("Latest New Games Added", className="mb-3 mt-4"),
                grid,
            ])

            return results, ""

        except Exception as e:
            logger.error(f"Error fetching new games: {str(e)}", exc_info=True)
            return (
                dbc.Alert(
                    f"Error loading new games: {str(e)}",
                    color="danger",
                    className="mt-3",
                ),
                "",
            )
