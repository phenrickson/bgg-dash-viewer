"""Callbacks for the ML experiments page."""

import logging

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, html, dcc
from dash.exceptions import PreventUpdate

from ..data.experiment_loader import get_experiment_loader
from ..components.ag_grid_config import get_default_column_def, get_grid_class_name

logger = logging.getLogger(__name__)


def register_experiments_callbacks(app, cache):
    """Register all callbacks for the experiments page.

    Args:
        app: Dash app instance
        cache: Flask-Caching instance
    """

    @cache.memoize(timeout=600)  # Cache for 10 minutes
    def _get_model_types_cached() -> list[str]:
        """Get available model types from GCS."""
        try:
            loader = get_experiment_loader()
            return loader.list_model_types()
        except Exception as e:
            logger.error(f"Error loading model types: {e}")
            return []

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def _get_experiments_cached(model_type: str) -> list[dict]:
        """Get experiments for a model type from GCS."""
        try:
            loader = get_experiment_loader()
            return loader.list_experiments(model_type)
        except Exception as e:
            logger.error(f"Error loading experiments for {model_type}: {e}")
            return []

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def _get_feature_importance_cached(
        model_type: str, exp_name: str
    ) -> dict | None:
        """Get feature importance for an experiment."""
        try:
            loader = get_experiment_loader()
            df = loader.load_feature_importance(model_type, exp_name)
            if df is not None:
                return df.to_dict("records")
            return None
        except Exception as e:
            logger.error(f"Error loading feature importance: {e}")
            return None

    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def _get_predictions_cached(
        model_type: str, exp_name: str, dataset: str
    ) -> dict | None:
        """Get predictions for an experiment."""
        try:
            loader = get_experiment_loader()
            df = loader.load_predictions(model_type, exp_name, dataset)
            if df is not None:
                return df.to_dict("records")
            return None
        except Exception as e:
            logger.error(f"Error loading predictions: {e}")
            return None

    # Callback 1: Load model types on page load
    @app.callback(
        Output("model-type-dropdown", "options"),
        Input("url", "pathname"),
    )
    def load_model_types(pathname: str):
        """Load available model types when page loads."""
        if pathname != "/app/experiments":
            raise PreventUpdate

        model_types = _get_model_types_cached()
        return [{"label": mt, "value": mt} for mt in model_types]

    # Callback 2: Load experiments when model type is selected
    @app.callback(
        [
            Output("experiments-data-store", "data"),
            Output("experiments-summary-stats", "children"),
            Output("details-experiment-selector", "options"),
            Output("fi-experiment-selector", "options"),
            Output("predictions-experiment-selector", "options"),
        ],
        Input("model-type-dropdown", "value"),
        prevent_initial_call=True,
    )
    def load_experiments(model_type: str | None):
        """Load experiments for the selected model type."""
        if not model_type:
            return [], "", [], [], []

        experiments = _get_experiments_cached(model_type)

        if not experiments:
            return (
                [],
                html.Span("No experiments found.", className="text-warning"),
                [],
                [],
                [],
            )

        # Build summary
        total = len(experiments)
        latest_ts = experiments[0].get("timestamp", "N/A") if experiments else "N/A"
        if latest_ts and len(latest_ts) > 10:
            latest_ts = latest_ts[:10]  # Just the date

        summary = html.Span(
            [
                f"{total} experiments",
                html.Span(" | ", className="mx-2"),
                f"Latest: {latest_ts}",
            ]
        )

        # Build experiment options
        exp_options = [
            {"label": exp["experiment_name"], "value": exp["experiment_name"]}
            for exp in experiments
        ]

        return experiments, summary, exp_options, exp_options, exp_options

    # Callback 3: Update metrics table and chart
    @app.callback(
        [
            Output("metrics-table-container", "children"),
            Output("metrics-chart-container", "children"),
        ],
        [
            Input("experiments-data-store", "data"),
            Input("metrics-dataset-selector", "value"),
        ],
        State("model-type-dropdown", "value"),
    )
    def update_metrics_display(
        experiments_data: list[dict] | None, dataset: str, model_type: str | None
    ):
        """Update the metrics table and performance chart."""
        if not experiments_data:
            return (
                html.Div("Select a model type to view experiments.", className="text-muted"),
                html.Div(),
            )

        # Build metrics dataframe
        rows = []
        for exp in experiments_data:
            metrics = exp.get("metrics", {}).get(dataset, {})
            if metrics:
                row = {
                    "experiment": exp["experiment_name"],
                    "timestamp": exp.get("timestamp", "")[:10] if exp.get("timestamp") else "",
                }
                # Filter out MAPE for users_rated model type
                if model_type and "users_rated" in model_type:
                    metrics = {k: v for k, v in metrics.items() if k.lower() != "mape"}
                row.update(metrics)
                rows.append(row)

        if not rows:
            return (
                html.Div(f"No {dataset} metrics available.", className="text-muted"),
                html.Div(),
            )

        df = pd.DataFrame(rows)

        # Create AG Grid column definitions
        column_defs = [{"field": "experiment", "headerName": "Experiment", "pinned": "left"}]
        column_defs.append({"field": "timestamp", "headerName": "Date", "width": 100})

        # Add metric columns
        metric_cols = [c for c in df.columns if c not in ["experiment", "timestamp"]]
        for col in metric_cols:
            column_defs.append({
                "field": col,
                "headerName": col.upper().replace("_", " "),
                "valueFormatter": {"function": "d3.format('.4f')(params.value)"},
                "width": 120,
            })

        # Create AG Grid
        grid = dag.AgGrid(
            id="metrics-table",
            rowData=df.to_dict("records"),
            columnDefs=column_defs,
            defaultColDef=get_default_column_def(),
            dashGridOptions={
                "domLayout": "autoHeight",
                "pagination": False,
            },
            className=get_grid_class_name(),
            style={"width": "100%"},
        )

        # Create performance chart (line chart of key metrics over experiments)
        chart = html.Div()
        if len(metric_cols) > 0 and len(rows) > 1:
            # Use first few metrics for the chart
            chart_metrics = metric_cols[:4]
            fig = go.Figure()

            for metric in chart_metrics:
                fig.add_trace(
                    go.Scatter(
                        x=df["experiment"],
                        y=df[metric],
                        mode="lines+markers",
                        name=metric.upper(),
                    )
                )

            fig.update_layout(
                title="Performance Across Experiments",
                xaxis_title="Experiment",
                yaxis_title="Value",
                height=400,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )

            chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

        return grid, chart

    # Callback 4: Update experiment details (parameters and model info)
    @app.callback(
        [
            Output("parameters-table-container", "children"),
            Output("model-info-container", "children"),
            Output("experiment-metrics-container", "children"),
        ],
        Input("details-experiment-selector", "value"),
        [
            State("experiments-data-store", "data"),
            State("model-type-dropdown", "value"),
        ],
    )
    def update_experiment_details(
        exp_name: str | None,
        experiments_data: list[dict] | None,
        model_type: str | None,
    ):
        """Update the experiment details display."""
        if not exp_name or not experiments_data:
            placeholder = html.Div(
                "Select an experiment to view details.", className="text-muted"
            )
            return placeholder, placeholder, placeholder

        # Find the experiment
        experiment = next(
            (e for e in experiments_data if e["experiment_name"] == exp_name), None
        )
        if not experiment:
            return (
                html.Div("Experiment not found.", className="text-warning"),
                html.Div(),
                html.Div(),
            )

        # Parameters table
        params = experiment.get("parameters", {})
        if params:
            params_items = [
                html.Tr([html.Td(k, className="fw-bold"), html.Td(str(v))])
                for k, v in sorted(params.items())
            ]
            params_table = dbc.Table(
                html.Tbody(params_items),
                bordered=True,
                hover=True,
                size="sm",
                className="table-dark",
            )
        else:
            params_table = html.Div("No parameters available.", className="text-muted")

        # Model info
        model_info = experiment.get("model_info", {})
        if model_info:
            info_items = [
                html.Tr([html.Td(k, className="fw-bold"), html.Td(str(v))])
                for k, v in sorted(model_info.items())
            ]
            info_table = dbc.Table(
                html.Tbody(info_items),
                bordered=True,
                hover=True,
                size="sm",
                className="table-dark",
            )
        else:
            info_table = html.Div("No model info available.", className="text-muted")

        # Filter out MAPE for users_rated model type
        hide_mape = model_type and "users_rated" in model_type

        # Metrics comparison (train/tune/test side by side)
        metrics_content = []
        for dataset in ["train", "tune", "test"]:
            metrics = experiment.get("metrics", {}).get(dataset, {})
            if metrics:
                # Filter MAPE if needed
                if hide_mape:
                    metrics = {k: v for k, v in metrics.items() if k.lower() != "mape"}
                metric_cards = [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H6(
                                        k.upper().replace("_", " "),
                                        className="text-muted mb-1 small",
                                    ),
                                    html.H5(f"{v:.4f}", className="mb-0"),
                                ]
                            ),
                            className="text-center",
                        ),
                        width=2,
                    )
                    for k, v in list(metrics.items())[:6]
                ]
                metrics_content.append(
                    html.Div(
                        [
                            html.H6(
                                dataset.capitalize(),
                                className="text-primary mb-2",
                            ),
                            dbc.Row(metric_cards, className="g-2"),
                        ],
                        className="mb-3",
                    )
                )

        metrics_display = (
            html.Div(metrics_content)
            if metrics_content
            else html.Div("No metrics available.", className="text-muted")
        )

        return params_table, info_table, metrics_display

    # Callback 5: Update feature importance visualization
    @app.callback(
        [
            Output("feature-importance-chart-container", "children"),
            Output("feature-category-tabs", "children"),
            Output("feature-category-container", "style"),
        ],
        [
            Input("fi-experiment-selector", "value"),
            Input("feature-importance-top-n", "value"),
        ],
        State("model-type-dropdown", "value"),
    )
    def update_feature_importance(
        exp_name: str | None, top_n: int, model_type: str | None
    ):
        """Update the feature importance visualization."""
        hidden_style = {"display": "none"}
        visible_style = {"display": "block"}

        if not exp_name or not model_type:
            return (
                html.Div(
                    "Select an experiment to view feature importance.",
                    className="text-muted",
                ),
                [],
                hidden_style,
            )

        # Load feature importance
        fi_data = _get_feature_importance_cached(model_type, exp_name)

        if not fi_data:
            return (
                html.Div(
                    "Feature importance not available for this experiment.",
                    className="text-warning",
                ),
                [],
                hidden_style,
            )

        df = pd.DataFrame(fi_data)

        # Determine column names (different experiments may use different names)
        feature_col = "feature"
        if "feature" not in df.columns:
            # Try to find feature column
            for col in df.columns:
                if "feature" in col.lower() or "name" in col.lower():
                    feature_col = col
                    break

        # Determine importance column
        importance_col = None
        for col in ["coefficient", "importance", "coef", "weight", "value"]:
            if col in df.columns:
                importance_col = col
                break

        if importance_col is None:
            # Use first numeric column
            numeric_cols = df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                importance_col = numeric_cols[0]
            else:
                return (
                    html.Div(
                        "Could not determine importance column.",
                        className="text-warning",
                    ),
                    [],
                    hidden_style,
                )

        # Determine if coefficients (can be negative) or importance (always positive)
        is_coefficient = df[importance_col].min() < 0

        # Sort by absolute value and take top N
        df["abs_importance"] = df[importance_col].abs()
        df_sorted = df.nlargest(top_n, "abs_importance").sort_values(
            importance_col, ascending=True
        )

        # Create abbreviated feature names for display
        df_sorted["display_name"] = df_sorted[feature_col].apply(
            lambda x: x[:40] + "..." if len(str(x)) > 40 else str(x)
        )

        # Create main feature importance chart
        color_scale = "RdBu" if is_coefficient else "Viridis"
        color_midpoint = 0 if is_coefficient else None

        fig = px.bar(
            df_sorted,
            y="display_name",
            x=importance_col,
            orientation="h",
            color=importance_col,
            color_continuous_scale=color_scale,
            color_continuous_midpoint=color_midpoint,
            hover_data={feature_col: True, importance_col: ":.4f"},
        )

        fig.update_layout(
            title=f"Top {top_n} Features by {'Coefficient' if is_coefficient else 'Importance'}",
            xaxis_title="Coefficient" if is_coefficient else "Importance",
            yaxis_title="Feature",
            height=max(400, len(df_sorted) * 20),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        # Add zero line for coefficients
        if is_coefficient:
            fig.add_vline(x=0, line_dash="dash", line_color="gray")

        main_chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

        # Create category breakdown tabs
        category_prefixes = {
            "Publisher": "publisher_",
            "Designer": "designer_",
            "Artist": "artist_",
            "Mechanic": "mechanic_",
            "Category": "category_",
            "Family": "family_",
        }

        category_tabs = []
        for cat_name, prefix in category_prefixes.items():
            cat_df = df[df[feature_col].str.startswith(prefix, na=False)]
            if len(cat_df) > 0:
                cat_df = cat_df.nlargest(20, "abs_importance").sort_values(
                    importance_col, ascending=True
                )
                cat_df["display_name"] = cat_df[feature_col].str.replace(
                    prefix, "", regex=False
                )

                cat_fig = px.bar(
                    cat_df,
                    y="display_name",
                    x=importance_col,
                    orientation="h",
                    color=importance_col,
                    color_continuous_scale=color_scale,
                    color_continuous_midpoint=color_midpoint,
                )

                cat_fig.update_layout(
                    height=max(300, len(cat_df) * 25),
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    xaxis_title="Coefficient" if is_coefficient else "Importance",
                    yaxis_title=cat_name,
                )

                if is_coefficient:
                    cat_fig.add_vline(x=0, line_dash="dash", line_color="gray")

                category_tabs.append(
                    dbc.Tab(
                        dcc.Graph(figure=cat_fig, config={"displayModeBar": False}),
                        label=f"{cat_name} ({len(cat_df)})",
                    )
                )

        show_categories = visible_style if category_tabs else hidden_style

        return main_chart, category_tabs, show_categories

    # Callback 6: Update predictions visualization
    @app.callback(
        [
            Output("predictions-results-container", "children"),
            Output("predictions-loading", "children"),
        ],
        [
            Input("predictions-experiment-selector", "value"),
            Input("predictions-dataset-selector", "value"),
        ],
        State("model-type-dropdown", "value"),
    )
    def update_predictions(
        exp_name: str | None, dataset: str, model_type: str | None
    ):
        """Update the predictions visualization."""
        placeholder = html.Div(
            "Select an experiment to view predictions.", className="text-muted"
        )

        if not exp_name or not model_type:
            return placeholder, ""

        # Load predictions
        predictions_data = _get_predictions_cached(model_type, exp_name, dataset)

        if not predictions_data:
            return (
                html.Div(
                    f"No {dataset} predictions available for this experiment.",
                    className="text-warning",
                ),
                "",
            )

        df = pd.DataFrame(predictions_data)

        # Use standard prediction/actual columns
        pred_col = "prediction" if "prediction" in df.columns else None
        actual_col = "actual" if "actual" in df.columns else None

        if pred_col is None or actual_col is None:
            return (
                html.Div(
                    f"Could not find prediction/actual columns for {model_type}. "
                    f"Available: {list(df.columns)}",
                    className="text-warning",
                ),
                "",
            )

        # Calculate metrics
        from sklearn.metrics import (
            mean_squared_error,
            mean_absolute_error,
            r2_score,
        )
        import numpy as np

        # Filter out any NaN values
        mask = df[pred_col].notna() & df[actual_col].notna()
        df_valid = df[mask]

        if len(df_valid) == 0:
            return (
                html.Div("No valid predictions found.", className="text-warning"),
                "",
            )

        mse = mean_squared_error(df_valid[actual_col], df_valid[pred_col])
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(df_valid[actual_col], df_valid[pred_col])
        r2 = r2_score(df_valid[actual_col], df_valid[pred_col])

        # Create metrics cards
        metrics_cards = dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("RMSE", className="text-muted mb-1 small"),
                                html.H4(f"{rmse:.4f}", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("MAE", className="text-muted mb-1 small"),
                                html.H4(f"{mae:.4f}", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("R²", className="text-muted mb-1 small"),
                                html.H4(f"{r2:.4f}", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("N Samples", className="text-muted mb-1 small"),
                                html.H4(f"{len(df_valid):,}", className="mb-0"),
                            ]
                        ),
                        className="text-center",
                    ),
                    width=3,
                ),
            ],
            className="g-3",
        )

        # Create scatter plot
        fig = go.Figure()

        # Build custom hover text with game details
        hover_text = []
        for _, row in df_valid.iterrows():
            text = f"Predicted: {row[pred_col]:.3f}<br>Actual: {row[actual_col]:.3f}"
            if "name" in df_valid.columns:
                text += f"<br>Name: {row['name']}"
            if "game_id" in df_valid.columns:
                text += f"<br>Game ID: {row['game_id']}"
            if "year_published" in df_valid.columns:
                text += f"<br>Year: {row['year_published']}"
            hover_text.append(text)

        # Add scatter points
        fig.add_trace(
            go.Scattergl(
                x=df_valid[pred_col],
                y=df_valid[actual_col],
                mode="markers",
                marker=dict(
                    size=5,
                    opacity=0.5,
                    color="#6366f1",
                ),
                name="Predictions",
                hovertemplate="%{text}<extra></extra>",
                text=hover_text,
            )
        )

        # Add perfect prediction line
        min_val = min(df_valid[pred_col].min(), df_valid[actual_col].min())
        max_val = max(df_valid[pred_col].max(), df_valid[actual_col].max())
        fig.add_trace(
            go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode="lines",
                line=dict(color="red", dash="dash"),
                name="Perfect Prediction",
            )
        )

        fig.update_layout(
            title="Predicted vs Actual",
            xaxis_title="Predicted",
            yaxis_title="Actual",
            height=500,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )

        scatter_chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

        # Create predictions table with specific column order
        display_cols = []
        for col in ["year_published", "game_id", "name", pred_col, actual_col]:
            if col in df_valid.columns:
                display_cols.append(col)

        # Sort by prediction descending
        df_display = df_valid[display_cols].sort_values(pred_col, ascending=False).head(500)

        # Clean column header names
        header_names = {
            "year_published": "Year",
            "game_id": "Game ID",
            "name": "Name",
            "prediction": "Predicted",
            "actual": "Actual",
        }

        column_defs = []
        for col in display_cols:
            col_def = {"field": col, "headerName": header_names.get(col, col)}
            if col == "year_published":
                col_def["valueFormatter"] = {"function": "d3.format('d')(params.value)"}
            elif col == "name":
                col_def["cellRenderer"] = "markdown"
            elif df_display[col].dtype in ["float64", "float32"]:
                col_def["valueFormatter"] = {"function": "d3.format('.4f')(params.value)"}
            column_defs.append(col_def)

        # Add BGG link to name column
        df_display["name"] = df_display.apply(
            lambda row: f"[{row['name']}](https://boardgamegeek.com/boardgame/{row['game_id']})"
            if "game_id" in row and "name" in row else row.get("name", ""),
            axis=1,
        )

        grid = dag.AgGrid(
            id="predictions-table",
            rowData=df_display.to_dict("records"),
            columnDefs=column_defs,
            defaultColDef=get_default_column_def(),
            dashGridOptions={
                "domLayout": "autoHeight",
                "pagination": True,
                "paginationPageSize": 50,
            },
            className=get_grid_class_name(),
            style={"width": "100%"},
        )

        # Combine all content into results container
        results = html.Div(
            [
                metrics_cards,
                html.Div(scatter_chart, className="mt-4"),
                html.Div(
                    [
                        html.H5("Predictions Data", className="mb-3 mt-4"),
                        grid,
                    ]
                ),
            ]
        )
        return results, ""
