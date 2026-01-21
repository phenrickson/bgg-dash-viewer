"""Game comparison components for explaining similarity."""

from typing import Any

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from ..theme import PLOTLY_TEMPLATE, get_plotly_layout_defaults
from ..utils.charts import apply_standard_layout


def create_feature_comparison(
    source_game: dict[str, Any],
    neighbor_game: dict[str, Any],
    similarity_pct: float,
) -> html.Div:
    """Create a side-by-side feature comparison of two games.

    Args:
        source_game: Source game data dict with mechanics, categories, etc.
        neighbor_game: Neighbor game data dict.
        similarity_pct: Similarity percentage (0-100).

    Returns:
        Div containing the comparison layout.
    """
    # Extract features
    source_mechanics = set(source_game.get("mechanics") or [])
    source_categories = set(source_game.get("categories") or [])
    source_families = set(source_game.get("families") or [])
    neighbor_mechanics = set(neighbor_game.get("mechanics") or [])
    neighbor_categories = set(neighbor_game.get("categories") or [])
    neighbor_families = set(neighbor_game.get("families") or [])

    # Find shared and unique
    shared_mechanics = source_mechanics & neighbor_mechanics
    shared_categories = source_categories & neighbor_categories
    shared_families = source_families & neighbor_families

    # Create comparison sections
    def create_feature_badges(items: set, shared: set, color_shared: str, color_unique: str) -> list:
        """Create badges with shared items highlighted."""
        badges = []
        # Shared items first (highlighted)
        for item in sorted(shared):
            badges.append(
                dbc.Badge(
                    item,
                    color=color_shared,
                    className="me-1 mb-1",
                    pill=True,
                )
            )
        # Unique items (muted)
        for item in sorted(items - shared):
            badges.append(
                dbc.Badge(
                    item,
                    color=color_unique,
                    className="me-1 mb-1",
                    pill=True,
                    style={"opacity": "0.6"},
                )
            )
        return badges

    # Build game headers (15% larger)
    source_header = html.Div([
        html.Img(
            src=source_game.get("thumbnail", ""),
            style={"height": "70px", "width": "70px", "objectFit": "contain"},
            className="rounded me-3",
        ) if source_game.get("thumbnail") else None,
        html.Div([
            html.H4(source_game.get("name", "Source Game"), className="mb-0", style={"fontSize": "1.4rem"}),
            html.Span(
                f"({source_game.get('year_published', '')})" if source_game.get("year_published") else "",
                className="text-muted",
                style={"fontSize": "1.1rem"},
            ),
        ]),
    ], className="d-flex align-items-center mb-3")

    neighbor_header = html.Div([
        html.Img(
            src=neighbor_game.get("thumbnail", ""),
            style={"height": "70px", "width": "70px", "objectFit": "contain"},
            className="rounded me-3",
        ) if neighbor_game.get("thumbnail") else None,
        html.Div([
            html.H4(neighbor_game.get("name", "Neighbor Game"), className="mb-0", style={"fontSize": "1.4rem"}),
            html.Span(
                f"({neighbor_game.get('year_published', '')})" if neighbor_game.get("year_published") else "",
                className="text-muted",
                style={"fontSize": "1.1rem"},
            ),
        ]),
    ], className="d-flex align-items-center mb-3")

    # Similarity badge
    similarity_badge = dbc.Badge(
        f"{similarity_pct:.1f}% similar",
        color="success" if similarity_pct >= 90 else "info" if similarity_pct >= 70 else "warning",
        className="fs-6 mb-3",
    )

    # Stats comparison helpers
    def format_stat(value, suffix=""):
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.1f}{suffix}"
        return f"{value}{suffix}"

    def format_players(min_p, max_p):
        if min_p is None and max_p is None:
            return "N/A"
        if min_p == max_p:
            return f"{int(min_p)}"
        if max_p is None:
            return f"{int(min_p)}+"
        return f"{int(min_p)}-{int(max_p)}"

    def format_playtime(min_t, max_t):
        if min_t is None and max_t is None:
            return "N/A"
        if min_t == max_t:
            return f"{int(min_t)} min"
        if max_t is None:
            return f"{int(min_t)}+ min"
        return f"{int(min_t)}-{int(max_t)} min"

    # Similarity check helpers
    def complexity_similar(c1, c2, threshold=0.5):
        """Check if complexities are within threshold."""
        if c1 is None or c2 is None:
            return False
        return abs(float(c1) - float(c2)) <= threshold

    def players_overlap(s_min, s_max, n_min, n_max):
        """Check if player ranges overlap."""
        if s_min is None or n_min is None:
            return False
        s_max = s_max or s_min
        n_max = n_max or n_min
        return not (s_max < n_min or n_max < s_min)

    def playtime_similar(s_min, s_max, n_min, n_max, threshold=30):
        """Check if playtimes are similar (within threshold minutes)."""
        if s_min is None or n_min is None:
            return False
        s_avg = (s_min + (s_max or s_min)) / 2
        n_avg = (n_min + (n_max or n_min)) / 2
        return abs(s_avg - n_avg) <= threshold

    # Get similarity status for each stat
    source_complexity = source_game.get("average_weight") or source_game.get("complexity")
    neighbor_complexity = neighbor_game.get("average_weight") or neighbor_game.get("complexity")
    is_complexity_similar = complexity_similar(source_complexity, neighbor_complexity)

    is_players_similar = players_overlap(
        source_game.get("min_players"), source_game.get("max_players"),
        neighbor_game.get("min_players"), neighbor_game.get("max_players")
    )

    is_playtime_similar = playtime_similar(
        source_game.get("min_playtime"), source_game.get("max_playtime"),
        neighbor_game.get("min_playtime"), neighbor_game.get("max_playtime")
    )

    # Style helpers for similar vs different values
    def get_value_style(is_similar: bool) -> dict:
        base = {"fontSize": "1.15rem"}
        if is_similar:
            return {**base, "color": "#28a745", "fontWeight": "bold"}
        return {**base, "color": "#6c757d"}

    def get_row_style(is_similar: bool) -> dict:
        if is_similar:
            return {"backgroundColor": "rgba(40, 167, 69, 0.1)", "borderRadius": "4px"}
        return {}

    # Build stats rows with color coding
    stats_comparison = html.Div([
        # Header row
        dbc.Row([
            dbc.Col(html.Span("", className="text-muted"), width=3),
            dbc.Col(html.Span("Source", className="text-muted fw-bold", style={"fontSize": "1.1rem"}), className="text-center", width=4),
            dbc.Col(html.Span("Neighbor", className="text-muted fw-bold", style={"fontSize": "1.1rem"}), className="text-center", width=4),
        ], className="mb-2"),
        # Complexity row
        dbc.Row([
            dbc.Col(html.Span("Complexity", style={"fontSize": "1.05rem"}), width=3),
            dbc.Col(
                html.Span(format_stat(source_complexity), style=get_value_style(is_complexity_similar)),
                className="text-center",
                width=4,
            ),
            dbc.Col(
                html.Span(format_stat(neighbor_complexity), style=get_value_style(is_complexity_similar)),
                className="text-center",
                width=4,
            ),
        ], className="mb-2 py-1", style=get_row_style(is_complexity_similar)),
        # Players row
        dbc.Row([
            dbc.Col(html.Span("Players", style={"fontSize": "1.05rem"}), width=3),
            dbc.Col(
                html.Span(
                    format_players(source_game.get("min_players"), source_game.get("max_players")),
                    style=get_value_style(is_players_similar),
                ),
                className="text-center",
                width=4,
            ),
            dbc.Col(
                html.Span(
                    format_players(neighbor_game.get("min_players"), neighbor_game.get("max_players")),
                    style=get_value_style(is_players_similar),
                ),
                className="text-center",
                width=4,
            ),
        ], className="mb-2 py-1", style=get_row_style(is_players_similar)),
        # Playtime row
        dbc.Row([
            dbc.Col(html.Span("Playtime", style={"fontSize": "1.05rem"}), width=3),
            dbc.Col(
                html.Span(
                    format_playtime(source_game.get("min_playtime"), source_game.get("max_playtime")),
                    style=get_value_style(is_playtime_similar),
                ),
                className="text-center",
                width=4,
            ),
            dbc.Col(
                html.Span(
                    format_playtime(neighbor_game.get("min_playtime"), neighbor_game.get("max_playtime")),
                    style=get_value_style(is_playtime_similar),
                ),
                className="text-center",
                width=4,
            ),
        ], className="mb-2 py-1", style=get_row_style(is_playtime_similar)),
    ], className="mb-3")

    # Mechanics comparison
    mechanics_section = html.Div([
        html.H6([
            "Mechanics ",
            dbc.Badge(
                f"{len(shared_mechanics)} shared",
                color="success",
                pill=True,
                className="ms-2",
            ),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                *create_feature_badges(source_mechanics, shared_mechanics, "success", "secondary"),
            ] if source_mechanics else [html.Small("None", className="text-muted")]),
            dbc.Col([
                *create_feature_badges(neighbor_mechanics, shared_mechanics, "success", "secondary"),
            ] if neighbor_mechanics else [html.Small("None", className="text-muted")]),
        ]),
    ], className="mb-4")

    # Categories comparison
    categories_section = html.Div([
        html.H6([
            "Categories ",
            dbc.Badge(
                f"{len(shared_categories)} shared",
                color="success",
                pill=True,
                className="ms-2",
            ),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                *create_feature_badges(source_categories, shared_categories, "success", "secondary"),
            ] if source_categories else [html.Small("None", className="text-muted")]),
            dbc.Col([
                *create_feature_badges(neighbor_categories, shared_categories, "success", "secondary"),
            ] if neighbor_categories else [html.Small("None", className="text-muted")]),
        ]),
    ], className="mb-4")

    # Families comparison
    families_section = html.Div([
        html.H6([
            "Families ",
            dbc.Badge(
                f"{len(shared_families)} shared",
                color="success",
                pill=True,
                className="ms-2",
            ),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                *create_feature_badges(source_families, shared_families, "success", "secondary"),
            ] if source_families else [html.Small("None", className="text-muted")]),
            dbc.Col([
                *create_feature_badges(neighbor_families, shared_families, "success", "secondary"),
            ] if neighbor_families else [html.Small("None", className="text-muted")]),
        ]),
    ], className="mb-4")

    return html.Div([
        html.Div(similarity_badge, className="text-center"),
        dbc.Row([
            dbc.Col(source_header, md=6),
            dbc.Col(neighbor_header, md=6),
        ]),
        html.Hr(),
        html.H6("Stats Comparison", className="mb-2"),
        stats_comparison,
        html.Hr(),
        mechanics_section,
        categories_section,
        families_section,
    ])


def create_embedding_chart(
    source_game: dict[str, Any],
    neighbor_game: dict[str, Any],
    source_embedding: list[float],
    neighbor_embedding: list[float],
) -> dcc.Graph:
    """Create a bar chart comparing embedding components.

    Args:
        source_game: Source game data dict.
        neighbor_game: Neighbor game data dict.
        source_embedding: Source game embedding vector.
        neighbor_embedding: Neighbor game embedding vector.

    Returns:
        Plotly Graph component.
    """
    n_components = len(source_embedding)
    components = list(range(1, n_components + 1))

    fig = go.Figure()

    # Add source game bars
    fig.add_trace(go.Bar(
        name=source_game.get("name", "Source"),
        x=components,
        y=source_embedding,
        marker_color="rgba(99, 110, 250, 0.7)",
    ))

    # Add neighbor game bars
    fig.add_trace(go.Bar(
        name=neighbor_game.get("name", "Neighbor"),
        x=components,
        y=neighbor_embedding,
        marker_color="rgba(239, 85, 59, 0.7)",
    ))

    fig.update_layout(
        title="Embedding Components Comparison",
        xaxis_title="Component",
        yaxis_title="Value",
        barmode="group",
        template=PLOTLY_TEMPLATE,
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    return dcc.Graph(figure=apply_standard_layout(fig), config={"displayModeBar": False})


def create_umap_scatter(
    games_data: list[dict[str, Any]],
    source_game_id: int,
    selected_neighbor_id: int | None = None,
) -> dcc.Graph:
    """Create a UMAP scatter plot showing games in embedding space.

    Args:
        games_data: List of game dicts with umap_1, umap_2 coordinates.
        source_game_id: ID of the source game to highlight.
        selected_neighbor_id: ID of the selected neighbor to highlight.

    Returns:
        Plotly Graph component.
    """
    df = pd.DataFrame(games_data)

    if "umap_1" not in df.columns or "umap_2" not in df.columns:
        return html.Div(
            html.Small("UMAP coordinates not available", className="text-muted"),
            className="text-center py-3",
        )

    # Assign colors based on role
    def get_color(row):
        if row["game_id"] == source_game_id:
            return "Source Game"
        elif selected_neighbor_id and row["game_id"] == selected_neighbor_id:
            return "Selected Neighbor"
        else:
            return "Other Neighbors"

    df["role"] = df.apply(get_color, axis=1)

    # Define color mapping
    color_map = {
        "Source Game": "#636EFA",
        "Selected Neighbor": "#EF553B",
        "Other Neighbors": "rgba(150, 150, 150, 0.5)",
    }

    fig = go.Figure()

    # Plot each category separately for legend control
    for role, color in color_map.items():
        subset = df[df["role"] == role]
        if len(subset) > 0:
            fig.add_trace(go.Scatter(
                x=subset["umap_1"],
                y=subset["umap_2"],
                mode="markers+text" if role != "Other Neighbors" else "markers",
                name=role,
                text=subset["name"] if role != "Other Neighbors" else None,
                textposition="top center",
                marker=dict(
                    color=color,
                    size=12 if role != "Other Neighbors" else 8,
                    symbol="star" if role == "Source Game" else "circle",
                ),
                hovertemplate="<b>%{text}</b><br>UMAP: (%{x:.2f}, %{y:.2f})<extra></extra>"
                if role != "Other Neighbors" else "<b>%{customdata}</b><extra></extra>",
                customdata=subset["name"] if role == "Other Neighbors" else None,
            ))

    fig.update_layout(
        title="Games in Embedding Space (UMAP)",
        xaxis_title="UMAP 1",
        yaxis_title="UMAP 2",
        template=PLOTLY_TEMPLATE,
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        showlegend=True,
    )

    return dcc.Graph(figure=apply_standard_layout(fig), config={"displayModeBar": False})


def create_neighbor_card(
    game_data: dict[str, Any],
    similarity_pct: float,
    is_selected: bool = False,
) -> dbc.Card:
    """Create a clickable neighbor card for the list.

    Args:
        game_data: Game data dict.
        similarity_pct: Similarity percentage.
        is_selected: Whether this card is currently selected.

    Returns:
        Card component.
    """
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(
                    html.Img(
                        src=game_data.get("thumbnail", ""),
                        style={"height": "50px", "width": "50px", "objectFit": "contain"},
                        className="rounded",
                    ) if game_data.get("thumbnail") else None,
                    width="auto",
                ),
                dbc.Col([
                    html.Div(
                        game_data.get("name", "Unknown"),
                        className="fw-bold text-truncate",
                        style={"maxWidth": "150px"},
                    ),
                    html.Small(
                        f"{similarity_pct:.0f}% similar",
                        className="text-success" if similarity_pct >= 90 else "text-info",
                    ),
                ]),
            ], align="center"),
        ], className="py-2"),
        className=f"mb-2 {'border-primary border-2' if is_selected else ''} cursor-pointer",
        style={"cursor": "pointer"},
    )
