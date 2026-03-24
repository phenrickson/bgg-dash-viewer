"""Callbacks for the ML experiments page."""

import logging

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, html, dcc, no_update
from dash.exceptions import PreventUpdate

from ..data.experiment_loader import get_experiment_loader
from ..components.ag_grid_config import get_default_column_def, get_grid_class_name

logger = logging.getLogger(__name__)

# Feature category prefixes matching bgg-predictive-models
FEATURE_CATEGORIES = {
    "all": None,
    "designer_": "designer_",
    "publisher_": "publisher_",
    "artist_": "artist_",
    "mechanic_": "mechanic_",
    "category_": "category_",
    "family_": "family_",
    "emb_": "emb_",
    "__other__": "__other__",
}

KNOWN_PREFIXES = [
    "designer_", "publisher_", "artist_", "mechanic_",
    "category_", "family_", "emb_",
]


def register_experiments_callbacks(app, cache):
    """Register all callbacks for the experiments page."""

    @cache.memoize(timeout=600)
    def _get_model_types_cached() -> list[str]:
        try:
            loader = get_experiment_loader()
            return loader.list_model_types()
        except Exception as e:
            logger.error(f"Error loading model types: {e}")
            return []

    @cache.memoize(timeout=300)
    def _get_experiments_cached(model_type: str) -> list[dict]:
        try:
            loader = get_experiment_loader()
            return loader.list_experiments(model_type)
        except Exception as e:
            logger.error(f"Error loading experiments for {model_type}: {e}")
            return []

    @cache.memoize(timeout=300)
    def _get_feature_importance_cached(
        model_type: str, exp_name: str, version: str | None = None
    ) -> dict | None:
        try:
            loader = get_experiment_loader()
            df = loader.load_feature_importance(model_type, exp_name, version)
            if df is not None:
                return df.to_dict("records")
            return None
        except Exception as e:
            logger.error(f"Error loading feature importance: {e}")
            return None

    @cache.memoize(timeout=300)
    def _get_predictions_cached(
        model_type: str, exp_name: str, dataset: str, version: str | None = None
    ) -> dict | None:
        try:
            loader = get_experiment_loader()
            df = loader.load_predictions(model_type, exp_name, dataset, version)
            if df is not None:
                return df.to_dict("records")
            return None
        except Exception as e:
            logger.error(f"Error loading predictions: {e}")
            return None

    # =========================================================
    # Callback 1: Load model types on page load
    # =========================================================
    @app.callback(
        Output("model-type-dropdown", "options"),
        Input("url", "pathname"),
    )
    def load_model_types(pathname: str):
        if pathname != "/app/experiments":
            raise PreventUpdate

        model_types = _get_model_types_cached()
        return [{"label": mt, "value": mt} for mt in model_types]

    # =========================================================
    # Callback 2: Load experiments when model type is selected
    # =========================================================
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
        eval_count = sum(1 for e in experiments if e.get("is_eval"))
        finalized_count = sum(1 for e in experiments if e.get("is_finalized"))
        latest_ts = experiments[0].get("timestamp", "N/A") if experiments else "N/A"
        if latest_ts and len(latest_ts) > 10:
            latest_ts = latest_ts[:10]

        summary_parts = [f"{total} experiments"]
        if eval_count:
            summary_parts.append(f"{eval_count} eval")
        if finalized_count:
            summary_parts.append(f"{finalized_count} finalized")
        summary_parts.append(f"Latest: {latest_ts}")

        summary = html.Span(
            [
                summary_parts[0],
                *[
                    item
                    for part in summary_parts[1:]
                    for item in [html.Span(" | ", className="mx-2"), part]
                ],
            ]
        )

        # Build experiment options
        exp_options = [
            {
                "label": exp["experiment_name"],
                "value": exp["experiment_name"],
            }
            for exp in experiments
        ]

        return experiments, summary, exp_options, exp_options, exp_options

    # =========================================================
    # Version selector callbacks (populate versions when experiment changes)
    # =========================================================
    def _make_version_callback(exp_selector_id, version_selector_id):
        @app.callback(
            [
                Output(version_selector_id, "options"),
                Output(version_selector_id, "value"),
            ],
            Input(exp_selector_id, "value"),
            State("experiments-data-store", "data"),
            prevent_initial_call=True,
        )
        def update_version_selector(exp_name, experiments_data):
            if not exp_name or not experiments_data:
                return [], None
            experiment = next(
                (e for e in experiments_data if e["experiment_name"] == exp_name), None
            )
            if not experiment:
                return [], None
            versions = experiment.get("versions", ["v1"])
            options = [{"label": v, "value": v} for v in versions]
            return options, versions[-1]  # Default to latest

        return update_version_selector

    _make_version_callback("details-experiment-selector", "details-version-selector")
    _make_version_callback("fi-experiment-selector", "fi-version-selector")
    _make_version_callback("predictions-experiment-selector", "predictions-version-selector")

    # =========================================================
    # Callback 3: Update metrics table and chart
    # =========================================================
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
                    "version": exp.get("version", ""),
                    "timestamp": exp.get("timestamp", "")[:10] if exp.get("timestamp") else "",
                }
                # Add test_through if available
                test_through = exp.get("test_through")
                if test_through is not None:
                    row["test_year"] = test_through
                # Filter out MAPE for users_rated model type
                if model_type and "users_rated" in model_type:
                    metrics = {k: v for k, v in metrics.items() if k.lower() != "mape"}
                # Only include scalar metrics
                for k, v in metrics.items():
                    if isinstance(v, (int, float)):
                        row[k] = v
                rows.append(row)

        if not rows:
            return (
                html.Div(f"No {dataset} metrics available.", className="text-muted"),
                html.Div(),
            )

        df = pd.DataFrame(rows)

        # Create AG Grid column definitions
        column_defs = [
            {"field": "experiment", "headerName": "Experiment", "pinned": "left"},
            {"field": "version", "headerName": "Version", "width": 90},
        ]
        if "test_year" in df.columns:
            column_defs.append({"field": "test_year", "headerName": "Test Year", "width": 100})
        column_defs.append({"field": "timestamp", "headerName": "Date", "width": 100})

        # Add metric columns
        skip_cols = {"experiment", "version", "timestamp", "test_year"}
        metric_cols = [c for c in df.columns if c not in skip_cols]
        for col in metric_cols:
            column_defs.append({
                "field": col,
                "headerName": col.upper().replace("_", " "),
                "valueFormatter": {"function": "d3.format('.4f')(params.value)"},
                "width": 120,
            })

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

        # Create performance chart
        chart = html.Div()
        if len(metric_cols) > 0 and len(rows) > 1:
            # Determine x-axis: use test_year if available, otherwise experiment name
            has_test_year = "test_year" in df.columns and df["test_year"].notna().any()

            if has_test_year:
                # Faceted line chart colored by version, like the Streamlit app
                chart_metrics = metric_cols[:6]
                melted = df.melt(
                    id_vars=["experiment", "version", "test_year"],
                    value_vars=chart_metrics,
                    var_name="metric",
                    value_name="value",
                )
                melted = melted.sort_values("test_year")

                fig = px.line(
                    melted,
                    x="test_year",
                    y="value",
                    color="version",
                    facet_col="metric",
                    facet_col_wrap=3,
                    facet_col_spacing=0.08,
                    facet_row_spacing=0.12,
                    markers=True,
                    custom_data=["experiment", "version", "metric"],
                )
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{customdata[2]}</b>: %{y:.4f}<br>"
                        "Year: %{x}<br>"
                        "Model: %{customdata[0]} (%{customdata[1]})"
                        "<extra></extra>"
                    )
                )
                fig.update_yaxes(matches=None, rangemode="tozero", showticklabels=True)
                fig.update_xaxes(matches=None)
                fig.update_annotations(font_size=12)
                n_rows = (len(chart_metrics) + 2) // 3
                fig.update_layout(
                    title="Metrics Over Time",
                    xaxis_title="Test Year",
                    hovermode="closest",
                    height=350 * n_rows,
                    margin=dict(t=60, b=40),
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
            else:
                # Fallback: simple line chart over experiments
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

            chart = dbc.Card(
                dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": False})),
                className="panel-card",
            )

        return (
            dbc.Card(dbc.CardBody(grid), className="panel-card"),
            chart,
        )

    # =========================================================
    # Callback 4: Update experiment details
    # =========================================================
    @app.callback(
        [
            Output("parameters-table-container", "children"),
            Output("model-info-container", "children"),
            Output("experiment-metrics-container", "children"),
            Output("details-finalized-badge", "children"),
        ],
        [
            Input("details-experiment-selector", "value"),
            Input("details-version-selector", "value"),
        ],
        [
            State("experiments-data-store", "data"),
            State("model-type-dropdown", "value"),
        ],
    )
    def update_experiment_details(
        exp_name: str | None,
        version: str | None,
        experiments_data: list[dict] | None,
        model_type: str | None,
    ):
        placeholder = html.Div(
            "Select an experiment to view details.", className="text-muted"
        )
        if not exp_name or not experiments_data:
            return placeholder, placeholder, placeholder, html.Div()

        # Find the experiment
        experiment = next(
            (e for e in experiments_data if e["experiment_name"] == exp_name), None
        )
        if not experiment:
            return (
                html.Div("Experiment not found.", className="text-warning"),
                html.Div(),
                html.Div(),
                html.Div(),
            )

        # Finalized badge
        badge = html.Div()
        if experiment.get("is_finalized"):
            badge = dbc.Badge(
                "Finalized (Production Model)",
                color="success",
                className="fs-6 mb-2",
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
        for ds in ["train", "tune", "test"]:
            metrics = experiment.get("metrics", {}).get(ds, {})
            if metrics:
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
                                    html.H5(
                                        f"{v:.4f}" if isinstance(v, float) else str(v),
                                        className="mb-0",
                                    ),
                                ]
                            ),
                            className="text-center",
                        ),
                        width=2,
                    )
                    for k, v in list(metrics.items())[:6]
                    if isinstance(v, (int, float))
                ]
                metrics_content.append(
                    html.Div(
                        [
                            html.H6(ds.capitalize(), className="text-primary mb-2"),
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

        return params_table, info_table, metrics_display, badge

    # =========================================================
    # Callback 5: Update features visualization
    # =========================================================
    @app.callback(
        [
            Output("feature-importance-chart-container", "children"),
            Output("coefficients-by-year-container", "children"),
        ],
        [
            Input("fi-experiment-selector", "value"),
            Input("fi-version-selector", "value"),
            Input("feature-importance-top-n", "value"),
            Input("fi-category-selector", "value"),
        ],
        [
            State("model-type-dropdown", "value"),
            State("experiments-data-store", "data"),
        ],
    )
    def update_features(
        exp_name: str | None,
        version: str | None,
        top_n: int,
        category: str,
        model_type: str | None,
        experiments_data: list[dict] | None,
    ):
        if not exp_name or not model_type:
            return (
                html.Div(
                    "Select an experiment to view features.",
                    className="text-muted",
                ),
                html.Div(),
            )

        # Load feature importance for the selected experiment
        fi_data = _get_feature_importance_cached(model_type, exp_name, version)

        if not fi_data:
            return (
                html.Div(
                    "Feature data not available for this experiment.",
                    className="text-warning",
                ),
                html.Div(),
            )

        df = pd.DataFrame(fi_data)

        # Determine column names
        feature_col = "feature"
        if "feature" not in df.columns:
            for col in df.columns:
                if "feature" in col.lower() or "name" in col.lower():
                    feature_col = col
                    break

        importance_col = None
        for col in ["coefficient", "importance", "coef", "weight", "value"]:
            if col in df.columns:
                importance_col = col
                break

        if importance_col is None:
            numeric_cols = df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                importance_col = numeric_cols[0]
            else:
                return (
                    html.Div("Could not determine importance column.", className="text-warning"),
                    html.Div(),
                )

        is_coefficient = importance_col == "coefficient" or df[importance_col].min() < 0
        has_uncertainty = "std" in df.columns

        # Apply category filter
        df = _filter_by_category(df, feature_col, category)

        if df.empty:
            return (
                html.Div(f"No features found for this category.", className="text-muted"),
                html.Div(),
            )

        # Drop zero coefficients (ARD shrinks many to exactly zero)
        if is_coefficient:
            df = df[df[importance_col] != 0]

        # Clean display names
        df = df.copy()
        df["display_name"] = df[feature_col].apply(
            lambda x: _clean_feature_name(x, category)
        )

        # Sort by absolute value and take top N
        df["abs_importance"] = df[importance_col].abs()
        df_sorted = df.nlargest(top_n, "abs_importance").sort_values(
            importance_col, ascending=True
        )

        # Create main chart
        if is_coefficient and has_uncertainty:
            # Dot plot with error bars for coefficients with uncertainty
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_sorted[importance_col],
                    y=df_sorted["display_name"],
                    mode="markers",
                    marker=dict(
                        size=8,
                        color=df_sorted[importance_col],
                        colorscale="RdBu",
                        cmid=0,
                        showscale=True,
                        colorbar=dict(title="Coefficient"),
                    ),
                    error_x=dict(
                        type="data",
                        symmetric=False,
                        array=(df_sorted["upper_95"] - df_sorted[importance_col]).values
                        if "upper_95" in df_sorted.columns
                        else df_sorted["std"].values * 1.96,
                        arrayminus=(df_sorted[importance_col] - df_sorted["lower_95"]).values
                        if "lower_95" in df_sorted.columns
                        else df_sorted["std"].values * 1.96,
                    ) if has_uncertainty else None,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Coefficient: %{x:.4f}<br>"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                )
            )
            fig.add_vline(x=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=f"Top {top_n} Coefficients",
                xaxis_title="Coefficient",
                yaxis_title="",
                height=max(400, len(df_sorted) * 22),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
        else:
            # Bar chart for feature importance (tree models)
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
                yaxis_title="",
                height=max(400, len(df_sorted) * 20),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            if is_coefficient:
                fig.add_vline(x=0, line_dash="dash", line_color="gray")

        main_chart = dbc.Card(
            dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": False})),
            className="panel-card",
        )

        # Build coefficients-by-year chart for eval experiments
        by_year_chart = html.Div()
        if experiments_data and is_coefficient:
            eval_exps = [e for e in experiments_data if e.get("is_eval")]
            if eval_exps:
                by_year_chart = _build_coefficients_by_year(
                    eval_exps, model_type, top_n, category, feature_col, importance_col
                )

        return main_chart, by_year_chart

    def _build_coefficients_by_year(
        eval_exps, model_type, top_n, category, feature_col, importance_col
    ):
        """Build a dot plot of coefficients across years, colored by version."""
        frames = []
        for exp in eval_exps:
            test_year = exp.get("test_through")
            if test_year is None:
                continue
            # Use latest version for each experiment
            fi_data = _get_feature_importance_cached(
                model_type, exp["experiment_name"], exp.get("version")
            )
            if not fi_data:
                continue
            exp_df = pd.DataFrame(fi_data)
            if importance_col not in exp_df.columns or feature_col not in exp_df.columns:
                continue
            exp_df = _filter_by_category(exp_df, feature_col, category)
            if exp_df.empty:
                continue
            exp_df = exp_df[exp_df[importance_col] != 0]
            exp_df["year"] = str(int(test_year))
            exp_df["display_name"] = exp_df[feature_col].apply(
                lambda x: _clean_feature_name(x, category)
            )
            frames.append(exp_df[[feature_col, "display_name", importance_col, "year"]])

        if not frames:
            return html.Div()

        combined = pd.concat(frames, ignore_index=True)

        # Pick top N features by max absolute coefficient across all years
        feature_max = (
            combined.groupby("display_name")[importance_col]
            .apply(lambda x: x.abs().max())
            .nlargest(top_n)
            .index
        )
        plot_df = combined[combined["display_name"].isin(feature_max)]

        # Sort features by mean coefficient
        feature_order = (
            plot_df.groupby("display_name")[importance_col]
            .mean()
            .sort_values(ascending=True)
            .index.tolist()
        )

        fig = go.Figure()
        years = sorted(plot_df["year"].unique())

        # Color scale sampled from viridis
        from plotly.colors import sample_colorscale
        scale_positions = [
            0.15 + 0.70 * i / max(len(years) - 1, 1) for i in range(len(years))
        ]
        year_colors = sample_colorscale("Viridis", scale_positions)

        for year, color in zip(years, year_colors):
            year_df = plot_df[plot_df["year"] == year]
            year_df = year_df.set_index("display_name").reindex(feature_order).reset_index()
            fig.add_trace(go.Scatter(
                x=year_df[importance_col],
                y=year_df["display_name"],
                mode="markers",
                marker=dict(size=8, color=color),
                name=str(year),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Coefficient: %{x:.4f}<br>"
                    "Year: %{fullData.name}"
                    "<extra></extra>"
                ),
            ))

        fig.add_vline(x=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            title="Coefficients by Year (Eval Experiments)",
            height=max(400, len(feature_order) * 22),
            yaxis=dict(
                title="",
                type="category",
                categoryorder="array",
                categoryarray=feature_order,
            ),
            xaxis_title="Coefficient",
            legend_title="Year",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        return dbc.Card(
            dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": False})),
            className="panel-card",
        )

    # =========================================================
    # Callback 6: Update predictions visualization
    # =========================================================
    @app.callback(
        [
            Output("predictions-results-container", "children"),
            Output("predictions-loading", "children"),
        ],
        [
            Input("predictions-experiment-selector", "value"),
            Input("predictions-version-selector", "value"),
            Input("predictions-dataset-selector", "value"),
        ],
        State("model-type-dropdown", "value"),
    )
    def update_predictions(
        exp_name: str | None, version: str | None, dataset: str, model_type: str | None
    ):
        placeholder = html.Div(
            "Select an experiment to view predictions.", className="text-muted"
        )

        if not exp_name or not model_type:
            return placeholder, ""

        predictions_data = _get_predictions_cached(model_type, exp_name, dataset, version)

        if not predictions_data:
            return (
                html.Div(
                    f"No {dataset} predictions available for this experiment.",
                    className="text-warning",
                ),
                "",
            )

        df = pd.DataFrame(predictions_data)

        pred_col = "prediction" if "prediction" in df.columns else None
        actual_col = "actual" if "actual" in df.columns else None

        if pred_col is None or actual_col is None:
            return (
                html.Div(
                    f"Could not find prediction/actual columns. "
                    f"Available: {list(df.columns)}",
                    className="text-warning",
                ),
                "",
            )

        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        import numpy as np

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

        metrics_cards = dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H6("RMSE", className="text-muted mb-1 small"),
                            html.H4(f"{rmse:.4f}", className="mb-0"),
                        ]),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H6("MAE", className="text-muted mb-1 small"),
                            html.H4(f"{mae:.4f}", className="mb-0"),
                        ]),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H6("R\u00b2", className="text-muted mb-1 small"),
                            html.H4(f"{r2:.4f}", className="mb-0"),
                        ]),
                        className="text-center",
                    ),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            html.H6("N Samples", className="text-muted mb-1 small"),
                            html.H4(f"{len(df_valid):,}", className="mb-0"),
                        ]),
                        className="text-center",
                    ),
                    width=3,
                ),
            ],
            className="g-3",
        )

        # Scatter plot
        fig = go.Figure()

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

        fig.add_trace(
            go.Scattergl(
                x=df_valid[pred_col],
                y=df_valid[actual_col],
                mode="markers",
                marker=dict(size=5, opacity=0.5, color="#6366f1"),
                name="Predictions",
                hovertemplate="%{text}<extra></extra>",
                text=hover_text,
            )
        )

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

        # Predictions table
        display_cols = []
        for col in ["year_published", "game_id", "name", pred_col, actual_col]:
            if col in df_valid.columns:
                display_cols.append(col)

        df_display = df_valid[display_cols].sort_values(pred_col, ascending=False).head(500)

        header_names = {
            "year_published": "Year",
            "game_id": "Game ID",
            "name": "Name",
            "prediction": "Predicted",
            "actual": "Actual",
        }

        column_defs = [
            {
                "field": "year_published",
                "headerName": "Year",
                "width": 90,
                "valueFormatter": {"function": "d3.format('d')(params.value)"},
            },
            {
                "field": "game_id",
                "headerName": "Game ID",
                "width": 100,
            },
            {
                "field": "name",
                "headerName": "Name",
                "cellRenderer": "markdown",
                "flex": 2,
                "minWidth": 250,
            },
            {
                "field": pred_col,
                "headerName": "Predicted",
                "width": 120,
                "valueFormatter": {"function": "d3.format('.4f')(params.value)"},
            },
            {
                "field": actual_col,
                "headerName": "Actual",
                "width": 120,
                "valueFormatter": {"function": "d3.format('.4f')(params.value)"},
            },
        ]
        # Filter to only columns that exist
        column_defs = [c for c in column_defs if c["field"] in df_display.columns]

        df_display = df_display.copy()
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

        results = html.Div(
            [
                # Metrics cards row
                metrics_cards,
                # Scatter plot in a card
                dbc.Card(
                    dbc.CardBody(scatter_chart),
                    className="panel-card mt-4",
                ),
                # Predictions table in a card
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H5("Predictions Data", className="mb-3"),
                            grid,
                        ]
                    ),
                    className="panel-card mt-4",
                ),
            ]
        )
        return results, ""


def _filter_by_category(df: pd.DataFrame, feature_col: str, category: str) -> pd.DataFrame:
    """Filter features DataFrame by category prefix."""
    if category == "all" or category is None:
        return df
    if category == "__other__":
        mask = ~df[feature_col].apply(
            lambda f: any(f.startswith(p) for p in KNOWN_PREFIXES)
        )
        return df[mask]
    return df[df[feature_col].str.startswith(category, na=False)]


def _clean_feature_name(name: str, category: str) -> str:
    """Clean feature name for display: strip prefix, replace underscores, title case."""
    if category and category not in ("all", "__other__"):
        if name.startswith(category):
            name = name[len(category):]
    name = name.replace("_", " ").strip()
    if len(name) > 40:
        name = name[:37] + "..."
    return name.title() if name else name
