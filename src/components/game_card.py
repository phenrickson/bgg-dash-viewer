"""Reusable game info card component."""

from typing import Any

from dash import html
import dash_bootstrap_components as dbc

from .loading import create_spinner


def create_badge_list(items: list, color: str, max_items: int = 5) -> list:
    """Create a list of pill badges with overflow indicator.

    Args:
        items: List of items to display as badges.
        color: Bootstrap color for the badges.
        max_items: Maximum number of badges to show before "+X more".

    Returns:
        List of dbc.Badge components.
    """
    badges = []
    # Use dark text for light-colored badges
    text_color = "dark" if color == "light" else None
    for item in items[:max_items]:
        badges.append(
            dbc.Badge(
                item,
                color=color,
                text_color=text_color,
                className="me-1 mb-1",
                pill=True,
            )
        )
    if len(items) > max_items:
        badges.append(
            dbc.Badge(
                f"+{len(items) - max_items} more",
                color="secondary",
                className="me-1 mb-1",
                pill=True,
            )
        )
    return badges


def format_player_count(min_players: int | None, max_players: int | None) -> str | None:
    """Format player count as a display string.

    Args:
        min_players: Minimum player count.
        max_players: Maximum player count.

    Returns:
        Formatted string like "2-4 players" or None if no data.
    """
    if min_players and max_players:
        if min_players == max_players:
            return f"{int(min_players)} players"
        elif max_players >= 8:
            return f"{int(min_players)}-8+ players"
        else:
            return f"{int(min_players)}-{int(max_players)} players"
    elif min_players:
        return f"{int(min_players)}+ players"
    elif max_players:
        return f"Up to {int(max_players)} players"
    return None


def _coerce_count_list(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    return [str(s).strip() for s in val if str(s).strip()]


def render_player_count_rows(
    best: str | list | None,
    recommended: str | list | None,
) -> list:
    """Render two labeled rows — "Best:" and "Recommended:" — as green/gray pills.

    Counts that are best are excluded from the Recommended row to avoid
    duplication. Returns an empty list if there's nothing to show.
    """
    best_list = sorted(
        set(_coerce_count_list(best)),
        key=lambda s: int(s) if s.isdigit() else 99,
    )
    rec_only = [c for c in _coerce_count_list(recommended) if c not in set(best_list)]
    rec_only = sorted(set(rec_only), key=lambda s: int(s) if s.isdigit() else 99)

    rows = []
    if best_list:
        rows.append(
            html.Div(
                [
                    html.Small("Best: ", className="text-muted me-1"),
                    *[
                        dbc.Badge(c, color="success", className="me-1", pill=True)
                        for c in best_list
                    ],
                ],
                className="mb-1",
            )
        )
    if rec_only:
        rows.append(
            html.Div(
                [
                    html.Small("Recommended: ", className="text-muted me-1"),
                    *[
                        dbc.Badge(c, color="secondary", className="me-1", pill=True)
                        for c in rec_only
                    ],
                ],
                className="mb-1",
            )
        )
    return rows


def format_playtime(min_playtime: int | None, max_playtime: int | None) -> str | None:
    """Format playtime as a display string.

    Args:
        min_playtime: Minimum playtime in minutes.
        max_playtime: Maximum playtime in minutes.

    Returns:
        Formatted string like "30-60 min" or None if no data.
    """
    if min_playtime and max_playtime:
        if min_playtime == max_playtime:
            return f"{int(min_playtime)} min"
        else:
            return f"{int(min_playtime)}-{int(max_playtime)} min"
    elif min_playtime:
        return f"{int(min_playtime)}+ min"
    elif max_playtime:
        return f"Up to {int(max_playtime)} min"
    return None


def create_game_info_card(
    game_data: dict[str, Any] | None,
    show_categories: bool = True,
    show_mechanics: bool = True,
    show_families: bool = True,
    show_player_count_rows: bool = True,
    max_categories: int = 4,
    max_mechanics: int = 4,
    max_families: int = 3,
    image_size: int = 140,
    title_href: str | None = "__bgg__",
) -> html.Div | None:
    """Create a game info card component.

    Args:
        game_data: Dictionary containing game information with keys:
            - game_id, name, year_published, bayes_average, average_weight
            - thumbnail, min_players, max_players, min_playtime, max_playtime
            - categories, mechanics, families (optional lists)
        show_categories: Whether to show category badges.
        show_mechanics: Whether to show mechanic badges.
        show_families: Whether to show family badges.
        max_categories: Max number of category badges to show.
        max_mechanics: Max number of mechanic badges to show.
        max_families: Max number of family badges to show.
        image_size: Size of the thumbnail image in pixels.

    Returns:
        Card content as html.Div, or None if no valid data.
    """
    if game_data is None or game_data.get("name") is None:
        return None

    # Extract game data
    game_id = game_data.get("game_id", "")
    thumbnail = game_data.get("thumbnail", "")
    name = game_data.get("name", "")
    year = game_data.get("year_published", "")
    rating = game_data.get("bayes_average", 0)
    complexity = game_data.get("average_weight", 0)
    min_players = game_data.get("min_players")
    max_players = game_data.get("max_players")
    min_playtime = game_data.get("min_playtime")
    max_playtime = game_data.get("max_playtime")
    # Convert to lists - BigQuery returns arrays that can't be evaluated as booleans
    raw_categories = game_data.get("categories")
    raw_mechanics = game_data.get("mechanics")
    raw_families = game_data.get("families")
    categories = list(raw_categories) if raw_categories is not None and len(raw_categories) > 0 else []
    mechanics = list(raw_mechanics) if raw_mechanics is not None and len(raw_mechanics) > 0 else []
    families = list(raw_families) if raw_families is not None and len(raw_families) > 0 else []

    # Format strings
    players_str = format_player_count(min_players, max_players)
    playtime_str = format_playtime(min_playtime, max_playtime)
    player_count_rows = (
        render_player_count_rows(
            game_data.get("best_player_counts"),
            game_data.get("recommended_player_counts"),
        )
        if show_player_count_rows
        else []
    )

    # Build BGG link
    bgg_url = f"https://boardgamegeek.com/boardgame/{game_id}"
    title_text = f"{name} ({int(year)})" if year else name

    # Resolve the title link destination.
    #   "__bgg__" (default)  → link to BGG (preserves legacy behavior)
    #   None                 → plain text (caller is wrapping the card in its own link)
    #   any other string     → link to that URL
    resolved_href = bgg_url if title_href == "__bgg__" else title_href

    if resolved_href is None:
        title_element = html.H4(title_text, className="mb-2")
    else:
        title_element = html.H4(
            html.A(
                title_text,
                href=resolved_href,
                target="_blank" if resolved_href.startswith("http") else "_self",
                rel="noopener noreferrer",
                style={"textDecoration": "none"},
            ),
            className="mb-2",
        )

    stat_badge_style = {"fontSize": "0.875rem", "padding": "0.4em 0.65em"}

    # Build info sections
    info_sections = [
        title_element,
        # Rating, complexity, players, and playtime badges
        html.Div(
            [
                dbc.Badge(
                    f"Rating: {rating:.1f}" if rating else "Unrated",
                    color="success" if rating and rating >= 7 else "light",
                    text_color="dark" if rating and rating < 7 else None,
                    className="me-2 mb-2",
                    style=stat_badge_style,
                ),
                dbc.Badge(
                    f"Complexity: {complexity:.1f}" if complexity else "N/A",
                    color="info",
                    className="me-2 mb-2",
                    style=stat_badge_style,
                ),
            ]
            + (
                [dbc.Badge(players_str, color="light", text_color="dark", className="me-2 mb-2", style=stat_badge_style)]
                if players_str
                else []
            )
            + (
                [dbc.Badge(playtime_str, color="light", text_color="dark", className="me-2 mb-2", style=stat_badge_style)]
                if playtime_str
                else []
            ),
            className="mb-2",
        ),
    ]

    if player_count_rows:
        info_sections.append(html.Div(player_count_rows, className="mb-2"))

    # Categories - use secondary (gray) for dark mode readability
    if show_categories and len(categories) > 0:
        info_sections.append(
            html.Div(
                [
                    html.Small("Categories: ", className="text-muted me-1"),
                    *create_badge_list(categories, "secondary", max_items=max_categories),
                ],
                className="mb-1",
            )
        )

    # Mechanics - use cyan/teal instead of yellow for readability
    if show_mechanics and len(mechanics) > 0:
        info_sections.append(
            html.Div(
                [
                    html.Small("Mechanics: ", className="text-muted me-1"),
                    *create_badge_list(mechanics, "info", max_items=max_mechanics),
                ],
                className="mb-1",
            )
        )

    # Families - use secondary (gray) for dark mode readability
    if show_families and len(families) > 0:
        info_sections.append(
            html.Div(
                [
                    html.Small("Families: ", className="text-muted me-1"),
                    *create_badge_list(families, "secondary", max_items=max_families),
                ],
            )
        )

    # Build the card content
    content = dbc.Row(
        [
            dbc.Col(
                html.Img(
                    src=thumbnail,
                    style={
                        "maxHeight": f"{image_size}px",
                        "maxWidth": f"{image_size}px",
                        "objectFit": "contain",
                    },
                    className="rounded shadow",
                )
                if thumbnail
                else html.Div(),
                width="auto",
            ),
            dbc.Col(info_sections),
        ],
        align="start",
    )

    return content


def create_game_info_card_with_loading(
    card_id: str,
    content_id: str,
) -> dbc.Spinner:
    """Create a game info card wrapper with loading spinner.

    Use this in layouts, then update the content via callback.

    Args:
        card_id: ID for the outer card element.
        content_id: ID for the inner content div (target for callback).

    Returns:
        Standardized spinner component wrapping a dbc.Card.
    """
    return create_spinner(
        dbc.Card(
            dbc.CardBody(html.Div(id=content_id)),
            id=card_id,
            className="mb-4 panel-card",
            style={"display": "none"},
        ),
    )
