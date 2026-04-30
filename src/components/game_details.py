"""Shared inline-expanded details renderer for game cards.

Used by the Game Search tab and the Similar Games > Game Neighbors tab to
render a consistent expanded body when a card is clicked. Expects a game
dict with the standard feature columns from the warehouse:
image/thumbnail, description, bayes_average, average_weight,
average_rating, users_rated, min_players, max_players, min_playtime,
max_playtime, categories, mechanics, designers, publishers, families.
"""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import html


def render_extra_details(game: dict[str, Any]) -> html.Div:
    """Build an inline expansion that adds info NOT already in the closed
    card (cover image, avg rating, ratings count, designers, publishers,
    description, BGG link). Designed to live inside the same card as the
    closed view so clicking just makes the card grow taller.
    """
    image = game.get("image") or game.get("thumbnail")
    game_id = game.get("game_id")
    description = game.get("description") or ""
    avg_rating = game.get("average_rating") or 0
    users_rated = game.get("users_rated") or 0

    designers = list(game.get("designers")) if game.get("designers") is not None and len(game.get("designers")) > 0 else []
    publishers = list(game.get("publishers")) if game.get("publishers") is not None and len(game.get("publishers")) > 0 else []

    def _badges(items: list, color: str, max_items: int | None = None) -> list:
        if max_items is None or len(items) <= max_items:
            return [
                dbc.Badge(str(item), color=color, className="me-1 mb-1", pill=True)
                for item in items
            ]
        shown = [
            dbc.Badge(str(item), color=color, className="me-1 mb-1", pill=True)
            for item in items[:max_items]
        ]
        shown.append(
            dbc.Badge(
                f"+{len(items) - max_items} more",
                color="secondary",
                className="me-1 mb-1",
                pill=True,
            )
        )
        return shown

    extra_stats = dbc.Row(
        [
            dbc.Col(
                [
                    html.Small("Avg Rating", className="text-muted d-block"),
                    html.Strong(f"{avg_rating:.2f}" if avg_rating else "—"),
                ],
                xs=6,
                md=4,
            ),
            dbc.Col(
                [
                    html.Small("Ratings", className="text-muted d-block"),
                    html.Strong(f"{users_rated:,}" if users_rated else "—"),
                ],
                xs=6,
                md=4,
            ),
        ],
        className="mb-3 g-2",
    )

    sections = []
    for label, items, color, cap in [
        ("Designers", designers, "success", 6),
        ("Publishers", publishers, "primary", 6),
    ]:
        if items:
            sections.append(
                html.Div(
                    [
                        html.Small(f"{label}: ", className="text-muted me-1"),
                        *_badges(items, color, max_items=cap),
                    ],
                    className="mb-2",
                )
            )

    bgg_link = html.A(
        [html.I(className="fas fa-external-link-alt me-2"), "View on BoardGameGeek"],
        href=f"https://boardgamegeek.com/boardgame/{game_id}",
        target="_blank",
        rel="noopener noreferrer",
        className="btn btn-outline-primary btn-sm mt-2",
    )

    left_col = (
        html.Img(
            src=image,
            style={
                "maxWidth": "200px",
                "maxHeight": "200px",
                "width": "100%",
                "objectFit": "contain",
                "borderRadius": "6px",
            },
        )
        if image
        else html.Div()
    )

    right_col = html.Div([extra_stats, *sections, bgg_link])

    body_children = [
        html.Hr(className="my-3"),
        dbc.Row(
            [
                dbc.Col(left_col, width="auto"),
                dbc.Col(right_col),
            ],
            className="g-3",
        ),
    ]
    if description:
        body_children.append(html.Hr(className="my-3"))
        body_children.append(
            html.Div(
                description,
                className="text-muted small",
                style={"whiteSpace": "pre-wrap"},
            )
        )

    return html.Div(body_children)


def render_details_body(game: dict[str, Any]) -> html.Div:
    """Build the inline expanded-details body for a selected game."""
    image = game.get("image") or game.get("thumbnail")
    game_id = game.get("game_id")
    description = game.get("description") or ""

    rating = game.get("bayes_average") or 0
    complexity = game.get("average_weight") or 0
    avg_rating = game.get("average_rating") or 0
    users_rated = game.get("users_rated") or 0

    def _fmt_int(x):
        try:
            return int(x) if x is not None else "?"
        except (TypeError, ValueError):
            return "?"

    min_players = _fmt_int(game.get("min_players"))
    max_players = _fmt_int(game.get("max_players"))
    min_playtime = _fmt_int(game.get("min_playtime"))
    max_playtime = _fmt_int(game.get("max_playtime"))
    players_str = (
        f"{min_players}" if min_players == max_players else f"{min_players}–{max_players}"
    )
    playtime_str = (
        f"{min_playtime} min"
        if min_playtime == max_playtime
        else f"{min_playtime}–{max_playtime} min"
    )

    def _badges(items: list | None, color: str, max_items: int | None = None) -> list:
        if not items:
            return [html.Small("—", className="text-muted")]
        if max_items is None or len(items) <= max_items:
            return [
                dbc.Badge(str(item), color=color, className="me-1 mb-1", pill=True)
                for item in items
            ]
        shown = [
            dbc.Badge(str(item), color=color, className="me-1 mb-1", pill=True)
            for item in items[:max_items]
        ]
        shown.append(
            dbc.Badge(
                f"+{len(items) - max_items} more",
                color="secondary",
                className="me-1 mb-1",
                pill=True,
            )
        )
        return shown

    stats = dbc.Row(
        [
            dbc.Col(
                [
                    html.Small("Geek Rating", className="text-muted d-block"),
                    html.Strong(f"{rating:.2f}" if rating else "—"),
                ],
                xs=6,
                md=3,
            ),
            dbc.Col(
                [
                    html.Small("Avg Rating", className="text-muted d-block"),
                    html.Strong(f"{avg_rating:.2f}" if avg_rating else "—"),
                ],
                xs=6,
                md=3,
            ),
            dbc.Col(
                [
                    html.Small("Complexity", className="text-muted d-block"),
                    html.Strong(f"{complexity:.2f}" if complexity else "—"),
                ],
                xs=6,
                md=3,
            ),
            dbc.Col(
                [
                    html.Small("Ratings", className="text-muted d-block"),
                    html.Strong(f"{users_rated:,}" if users_rated else "—"),
                ],
                xs=6,
                md=3,
            ),
        ],
        className="mb-3 g-2",
    )

    meta = html.Div(
        [
            dbc.Badge(f"{players_str} players", color="light", text_color="dark", className="me-2 mb-1"),
            dbc.Badge(playtime_str, color="light", text_color="dark", className="me-2 mb-1"),
        ],
        className="mb-3",
    )

    sections = []
    for label, key, color, cap in [
        ("Categories", "categories", "secondary", None),
        ("Mechanics", "mechanics", "info", None),
        ("Designers", "designers", "success", 6),
        ("Publishers", "publishers", "primary", 6),
        ("Families", "families", "secondary", 10),
    ]:
        items = game.get(key) or []
        if items:
            sections.append(
                html.Div(
                    [
                        html.Small(f"{label}: ", className="text-muted me-1"),
                        *_badges(items, color, max_items=cap),
                    ],
                    className="mb-2",
                )
            )

    bgg_link = html.A(
        [html.I(className="fas fa-external-link-alt me-2"), "View on BoardGameGeek"],
        href=f"https://boardgamegeek.com/boardgame/{game_id}",
        target="_blank",
        rel="noopener noreferrer",
        className="btn btn-outline-primary btn-sm mt-3",
    )

    left_col = (
        html.Img(
            src=image,
            style={
                "maxWidth": "240px",
                "maxHeight": "240px",
                "width": "100%",
                "objectFit": "contain",
                "borderRadius": "6px",
            },
        )
        if image
        else html.Div()
    )

    right_col = html.Div(
        [stats, meta, *sections, bgg_link],
    )

    body_children = [
        dbc.Row(
            [
                dbc.Col(left_col, width="auto"),
                dbc.Col(right_col),
            ],
            className="g-3",
        )
    ]
    if description:
        body_children.append(html.Hr())
        body_children.append(
            html.Div(
                description,
                className="text-muted",
                style={"whiteSpace": "pre-wrap"},
            )
        )

    return html.Div(body_children)
