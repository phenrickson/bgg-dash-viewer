"""Callbacks for the monitoring page."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from flask_caching import Cache

from ..data.bigquery_client import BigQueryClient
from ..layouts.monitoring import create_metric_card

logger = logging.getLogger(__name__)


def register_monitoring_callbacks(app: dash.Dash, cache: Cache) -> None:
    """Register callbacks for the monitoring page.

    Args:
        app: Dash application instance
        cache: Flask-Caching instance
    """

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get_table_counts() -> Dict[str, Any]:
        """Fetch row counts from BigQuery tables.

        Returns:
            Dictionary with table names and row counts
        """
        try:
            client = BigQueryClient()

            # Query to get counts from multiple tables
            query = """
            SELECT
                'games_features' as table_name,
                COUNT(DISTINCT game_id) as row_count
            FROM `${project_id}.${dataset}.games_features`

            UNION ALL

            SELECT
                'bgg_predictions' as table_name,
                COUNT(DISTINCT game_id) as row_count
            FROM `${project_id}.predictions.bgg_predictions`

            UNION ALL

            SELECT
                'complexity_predictions' as table_name,
                COUNT(DISTINCT game_id) as row_count
            FROM `${project_id}.predictions.bgg_complexity_predictions`

            UNION ALL

            SELECT
                'game_embeddings' as table_name,
                COUNT(DISTINCT game_id) as row_count
            FROM `${project_id}.predictions.bgg_game_embeddings`

            UNION ALL

            SELECT
                'new_games_7d' as table_name,
                COUNT(DISTINCT game_id) as row_count
            FROM (
                SELECT game_id, MIN(fetch_timestamp) as first_fetch
                FROM `${project_id}.${raw_dataset}.fetched_responses`
                WHERE fetch_status = 'success'
                GROUP BY game_id
                HAVING first_fetch > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            )
            """

            df = client.execute_query(query)

            # Convert to dictionary
            counts = {}
            for _, row in df.iterrows():
                counts[row["table_name"]] = int(row["row_count"])

            return {
                "counts": counts,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error fetching BigQuery table counts: {e}")
            return {
                "counts": {},
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get_deployed_models() -> Dict[str, Any]:
        """Fetch information about deployed ML models from the monitoring view.

        Returns:
            Dictionary with model info organized by category and type
        """
        try:
            client = BigQueryClient()

            # Query the consolidated deployed_models view from Dataform
            query = """
            SELECT
                model_category,
                model_type,
                model_name,
                model_version,
                experiment,
                algorithm,
                embedding_dim,
                document_method,
                games_count,
                last_updated
            FROM `${project_id}.monitoring.deployed_models`
            ORDER BY model_category, model_type, last_updated DESC
            """

            df = client.execute_query(query)

            if df.empty:
                return {
                    "models": [],
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                }

            # Convert to list of records
            models = df.to_dict("records")

            return {
                "models": models,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error fetching deployed models info: {e}")
            return {
                "models": [],
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    @cache.memoize(timeout=600)  # Cache for 10 minutes
    def get_datasets() -> List[str]:
        """Get list of datasets in the project.

        Returns:
            List of dataset names
        """
        try:
            client = BigQueryClient()
            query = """
            SELECT schema_name
            FROM `${project_id}.INFORMATION_SCHEMA.SCHEMATA`
            ORDER BY schema_name
            """
            df = client.execute_query(query)
            return df["schema_name"].tolist()
        except Exception as e:
            logger.error(f"Error fetching datasets: {e}")
            return []

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get_tables_for_dataset(dataset: str) -> Dict[str, Any]:
        """Get list of tables in a dataset with metadata.

        Args:
            dataset: Dataset name

        Returns:
            Dict with 'tables' list and 'error' if any
        """
        try:
            client = BigQueryClient()
            # Use INFORMATION_SCHEMA.TABLES for reliable metadata
            query = f"""
            SELECT
                table_name,
                table_type,
                creation_time as created,
                COALESCE(
                    (SELECT row_count
                     FROM `{client.project_id}.{dataset}.__TABLES__` t
                     WHERE t.table_id = table_name),
                    0
                ) as row_count
            FROM `{client.project_id}.{dataset}.INFORMATION_SCHEMA.TABLES`
            ORDER BY table_name
            """
            df = client.client.query(query).to_dataframe()
            return {"tables": df.to_dict("records"), "error": None}
        except Exception as e:
            logger.error(f"Error fetching tables for {dataset}: {e}")
            return {"tables": [], "error": str(e)}

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get_table_schema(dataset: str, table: str) -> List[Dict[str, Any]]:
        """Get schema for a specific table.

        Args:
            dataset: Dataset name
            table: Table name

        Returns:
            List of column info dictionaries
        """
        try:
            client = BigQueryClient()
            query = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                ordinal_position
            FROM `{client.project_id}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
            """
            df = client.client.query(query).to_dataframe()
            return df.to_dict("records")
        except Exception as e:
            logger.error(f"Error fetching schema for {dataset}.{table}: {e}")
            return []

    # -------------------------------------------------------------------------
    # Metrics Tab Callbacks
    # -------------------------------------------------------------------------

    @app.callback(
        [
            Output("bigquery-data-store", "data"),
            Output("bigquery-metrics-container", "children"),
            Output("bigquery-last-updated", "children"),
        ],
        [Input("bigquery-refresh-btn", "n_clicks")],
        prevent_initial_call=False,
    )
    def update_bigquery_metrics(
        n_clicks: Optional[int],
    ) -> Tuple[Dict[str, Any], Any, str]:
        """Update BigQuery metrics on page load or refresh."""
        # Clear cache if refresh button was clicked
        if n_clicks and n_clicks > 0:
            cache.delete_memoized(get_table_counts)

        data = get_table_counts()

        if data["status"] == "error":
            error_content = dbc.Alert(
                f"Error loading BigQuery data: {data.get('error', 'Unknown error')}",
                color="danger",
            )
            return data, error_content, f"Error at {data['timestamp']}"

        counts = data["counts"]

        # Create metric cards - two rows, no icons
        cards = html.Div(
            [
                # First row - Core tables
                dbc.Row(
                    [
                        dbc.Col(
                            create_metric_card(
                                title="Games Features",
                                value=f"{counts.get('games_features', 0):,}",
                                subtitle="Total games with features",
                            ),
                            md=4,
                            className="mb-3",
                        ),
                        dbc.Col(
                            create_metric_card(
                                title="BGG Predictions",
                                value=f"{counts.get('bgg_predictions', 0):,}",
                                subtitle="Games with predictions",
                            ),
                            md=4,
                            className="mb-3",
                        ),
                        dbc.Col(
                            create_metric_card(
                                title="New Games (7d)",
                                value=f"{counts.get('new_games_7d', 0):,}",
                                subtitle="Added in last 7 days",
                            ),
                            md=4,
                            className="mb-3",
                        ),
                    ],
                ),
                # Second row - ML tables
                dbc.Row(
                    [
                        dbc.Col(
                            create_metric_card(
                                title="Complexity Predictions",
                                value=f"{counts.get('complexity_predictions', 0):,}",
                                subtitle="Games with complexity scores",
                            ),
                            md=4,
                            className="mb-3",
                        ),
                        dbc.Col(
                            create_metric_card(
                                title="Game Embeddings",
                                value=f"{counts.get('game_embeddings', 0):,}",
                                subtitle="Games with embeddings",
                            ),
                            md=4,
                            className="mb-3",
                        ),
                    ],
                ),
            ]
        )

        # Format timestamp
        try:
            ts = datetime.fromisoformat(data["timestamp"])
            last_updated = f"Last updated: {ts.strftime('%Y-%m-%d %H:%M:%S')}"
        except (ValueError, KeyError):
            last_updated = "Last updated: Unknown"

        return data, cards, last_updated

    # -------------------------------------------------------------------------
    # Models Tab Callbacks
    # -------------------------------------------------------------------------

    def _format_timestamp(ts) -> str:
        """Format a timestamp for display."""
        if ts is None:
            return "Unknown"
        try:
            if hasattr(ts, "strftime"):
                return ts.strftime("%Y-%m-%d %H:%M")
            return str(ts)[:16]
        except Exception:
            return str(ts)[:16] if ts else "Unknown"

    def _create_model_card(
        title: str,
        model_name: str,
        version: Any,
        details: List[Tuple[str, str]],
        games_count: int,
        last_updated: Any,
    ) -> dbc.Card:
        """Create a card displaying model information."""
        detail_items = []
        for label, value in details:
            if value:
                detail_items.append(
                    html.Div(
                        [
                            html.Span(f"{label}: ", className="text-muted"),
                            html.Span(str(value), className="font-monospace"),
                        ],
                        className="small",
                    )
                )

        return dbc.Card(
            [
                dbc.CardHeader(
                    html.Div(
                        [
                            html.H6(title, className="mb-0 me-2"),
                            dbc.Badge(
                                f"v{version}" if version else "unknown",
                                color="info",
                                className="ms-auto",
                            ),
                        ],
                        className="d-flex align-items-center",
                    )
                ),
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.Strong(model_name or "Unknown", className="font-monospace"),
                            ],
                            className="mb-2",
                        ),
                        *detail_items,
                        html.Hr(className="my-2"),
                        html.Div(
                            [
                                html.Span(f"{games_count:,} games", className="text-muted small"),
                                html.Span(" | ", className="text-muted small"),
                                html.Span(
                                    f"Updated: {_format_timestamp(last_updated)}",
                                    className="text-muted small",
                                ),
                            ]
                        ),
                    ]
                ),
            ],
            className="panel-card h-100",
        )

    # Mapping of model_type to display title
    MODEL_TYPE_TITLES = {
        "hurdle": "Hurdle Model",
        "complexity": "Complexity Model",
        "rating": "Rating Model",
        "users_rated": "Users Rated Model",
        "game_embedding": "Game Embeddings",
        "text_embedding": "Text Embeddings",
    }

    @app.callback(
        [
            Output("models-container", "children"),
            Output("models-last-updated", "children"),
        ],
        [Input("models-refresh-btn", "n_clicks")],
        prevent_initial_call=False,
    )
    def update_models_display(
        n_clicks: Optional[int],
    ) -> Tuple[Any, str]:
        """Update deployed models display on page load or refresh."""
        # Clear cache if refresh button was clicked
        if n_clicks and n_clicks > 0:
            cache.delete_memoized(get_deployed_models)

        data = get_deployed_models()

        if data["status"] == "error":
            error_content = dbc.Alert(
                f"Error loading model info: {data.get('error', 'Unknown error')}",
                color="danger",
            )
            return error_content, f"Error at {data['timestamp']}"

        models = data.get("models", [])
        if not models:
            return (
                dbc.Alert("No model information available.", color="warning"),
                "Last updated: Unknown",
            )

        # Group models by category
        prediction_models = [m for m in models if m["model_category"] == "prediction"]
        embedding_models = [m for m in models if m["model_category"] == "embedding"]

        cards = []

        # Prediction models section
        if prediction_models:
            cards.append(html.H5("Prediction Models", className="mb-3"))
            pred_cols = []
            for model in prediction_models:
                details = [("Experiment", model.get("experiment"))]
                pred_cols.append(
                    dbc.Col(
                        _create_model_card(
                            title=MODEL_TYPE_TITLES.get(model["model_type"], model["model_type"]),
                            model_name=model.get("model_name"),
                            version=model.get("model_version"),
                            details=details,
                            games_count=model.get("games_count", 0),
                            last_updated=model.get("last_updated"),
                        ),
                        md=3,
                        className="mb-3",
                    )
                )
            cards.append(dbc.Row(pred_cols))

        # Embedding models section
        if embedding_models:
            cards.append(html.H5("Embedding Models", className="mb-3 mt-4"))
            emb_cols = []
            for model in embedding_models:
                details = [
                    ("Algorithm", model.get("algorithm")),
                    ("Dimensions", model.get("embedding_dim")),
                ]
                if model.get("document_method"):
                    details.append(("Document Method", model.get("document_method")))
                emb_cols.append(
                    dbc.Col(
                        _create_model_card(
                            title=MODEL_TYPE_TITLES.get(model["model_type"], model["model_type"]),
                            model_name=model.get("model_name"),
                            version=model.get("model_version"),
                            details=details,
                            games_count=model.get("games_count", 0),
                            last_updated=model.get("last_updated"),
                        ),
                        md=4,
                        className="mb-3",
                    )
                )
            cards.append(dbc.Row(emb_cols))

        # Format timestamp
        try:
            ts = datetime.fromisoformat(data["timestamp"])
            last_updated = f"Last updated: {ts.strftime('%Y-%m-%d %H:%M:%S')}"
        except (ValueError, KeyError):
            last_updated = "Last updated: Unknown"

        return html.Div(cards), last_updated

    # -------------------------------------------------------------------------
    # Data Catalog Tab Callbacks
    # -------------------------------------------------------------------------

    @app.callback(
        Output("catalog-dataset-dropdown", "options"),
        [Input("catalog-refresh-btn", "n_clicks")],
        prevent_initial_call=False,
    )
    def update_dataset_dropdown(n_clicks: Optional[int]) -> List[Dict[str, str]]:
        """Populate dataset dropdown on page load or refresh."""
        if n_clicks and n_clicks > 0:
            cache.delete_memoized(get_datasets)

        datasets = get_datasets()
        return [{"label": ds, "value": ds} for ds in datasets]

    @app.callback(
        [
            Output("bigquery-tables-store", "data"),
            Output("catalog-table-list", "children"),
        ],
        [Input("catalog-dataset-dropdown", "value")],
    )
    def update_table_list(
        dataset: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Any]:
        """Update table list when dataset is selected."""
        if not dataset:
            return [], html.Div(
                "Select a dataset to view tables",
                className="text-muted p-3",
            )

        result = get_tables_for_dataset(dataset)
        tables = result.get("tables", [])
        error = result.get("error")

        if error:
            return [], html.Div(
                [
                    html.Div("Error loading tables:", className="text-danger"),
                    html.Small(error, className="text-muted"),
                ],
                className="p-3",
            )

        if not tables:
            return [], html.Div(
                "No tables found in this dataset",
                className="text-muted p-3",
            )

        # Create clickable table list
        table_items = []
        for table in tables:
            row_count = table.get("row_count")
            row_text = f"{int(row_count):,} rows" if row_count else ""
            table_type = table.get("table_type", "TABLE")
            # Shorten table type display
            type_display = "VIEW" if "VIEW" in table_type else "TABLE"

            table_items.append(
                dbc.ListGroupItem(
                    [
                        html.Div(
                            [
                                html.Strong(table["table_name"]),
                                html.Span(
                                    f" ({type_display})",
                                    className="text-muted small",
                                ),
                            ]
                        ),
                        html.Small(row_text, className="text-muted") if row_text else None,
                    ],
                    id={"type": "table-item", "table": table["table_name"]},
                    action=True,
                    className="d-flex flex-column",
                )
            )

        return tables, dbc.ListGroup(table_items, flush=True)

    @app.callback(
        [
            Output("catalog-schema-header", "children"),
            Output("catalog-schema-display", "children"),
        ],
        [Input({"type": "table-item", "table": dash.ALL}, "n_clicks")],
        [
            State("catalog-dataset-dropdown", "value"),
            State({"type": "table-item", "table": dash.ALL}, "id"),
        ],
    )
    def update_schema_display(
        n_clicks_list: List[Optional[int]],
        dataset: Optional[str],
        ids: List[Dict[str, str]],
    ) -> Tuple[Any, Any]:
        """Display schema when a table is clicked."""
        # Check if any table was clicked
        if not n_clicks_list or not any(n_clicks_list) or not dataset:
            return (
                html.H6("Schema", className="mb-0"),
                html.Div(
                    "Click a table to view its schema",
                    className="text-muted",
                ),
            )

        # Find which table was clicked
        ctx = dash.callback_context
        if not ctx.triggered or ctx.triggered[0]["value"] is None:
            return (
                html.H6("Schema", className="mb-0"),
                html.Div(
                    "Click a table to view its schema",
                    className="text-muted",
                ),
            )

        # Extract table name from triggered id
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        import json

        try:
            triggered_dict = json.loads(triggered_id)
            table_name = triggered_dict.get("table")
        except (json.JSONDecodeError, KeyError):
            return (
                html.H6("Schema", className="mb-0"),
                html.Div("Error parsing table selection", className="text-danger"),
            )

        if not table_name:
            return (
                html.H6("Schema", className="mb-0"),
                html.Div(
                    "Click a table to view its schema",
                    className="text-muted",
                ),
            )

        # Get schema for selected table
        schema = get_table_schema(dataset, table_name)

        if not schema:
            return (
                html.H6(f"{dataset}.{table_name}", className="mb-0"),
                html.Div("No schema information available", className="text-muted"),
            )

        # Create schema table
        schema_rows = []
        for col in schema:
            schema_rows.append(
                html.Tr(
                    [
                        html.Td(col["column_name"], className="font-monospace"),
                        html.Td(col["data_type"], className="font-monospace text-muted"),
                        html.Td(
                            "NULL" if col["is_nullable"] == "YES" else "NOT NULL",
                            className="small text-muted",
                        ),
                    ]
                )
            )

        schema_table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Column"),
                            html.Th("Type"),
                            html.Th("Nullable"),
                        ]
                    )
                ),
                html.Tbody(schema_rows),
            ],
            bordered=True,
            hover=True,
            size="sm",
            className="mb-0",
        )

        return (
            html.H6(f"{dataset}.{table_name}", className="mb-0 font-monospace"),
            schema_table,
        )
