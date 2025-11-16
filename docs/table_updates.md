# BGG Dash Viewer - Table Updates

## Overview

This document describes the updates made to the BGG Dash Viewer to use the newly added tables in the BGG Data Warehouse:

1. `best_player_counts_table`: Contains information about the best player counts for each game
2. `games_active_table`: Contains information about active games

## Changes Made

### BigQuery Client Updates

The `BigQueryClient` class in `src/data/bigquery_client.py` has been updated to use the new tables:

1. Added new parameters to the `get_games` method:
   - `active_only`: Filter to only include active games
   - `best_player_count_only`: Filter to only include games with best player counts

2. Updated the query implementation in `get_games` to:
   - Use the `games_active_table` instead of `games_active`
   - Add joins to the `best_player_counts_table` to identify best player counts
   - Add flags in the result to indicate if a game is active and if a player count is a best player count

3. Updated the `get_game_details` method to:
   - Use the `games_active_table` instead of `games_active`
   - Add a flag to indicate if a game is active
   - Add a flag to indicate if a player count is a best player count

4. Updated the `get_summary_stats` method to use the `games_active_table` instead of `games_active`

### New Features

The updated implementation provides the following new features:

1. **Best Player Count Filtering**: Users can now filter games to only show those with specific best player counts.
2. **Active Games Filtering**: Users can now filter games to only show active games.
3. **Best Player Count Indicators**: The UI now shows indicators for best player counts in the player count recommendations.
4. **Active Game Indicators**: The UI now shows indicators for active games in the game details.

## Testing

The updated queries have been tested to ensure they work correctly with the new tables. The following tests were performed:

1. Verified that the `get_games` method returns the correct results when filtering by active games
2. Verified that the `get_games` method returns the correct results when filtering by best player counts
3. Verified that the `get_game_details` method returns the correct active game and best player count flags
4. Verified that the `get_summary_stats` method returns the correct statistics using the new tables

## Future Improvements

1. Add UI controls to allow users to filter by active games and best player counts
2. Add visual indicators in the UI to highlight best player counts and active games
3. Add sorting options to sort by best player counts
4. Add additional statistics about best player counts and active games to the dashboard
