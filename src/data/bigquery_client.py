"""BigQuery client for the Board Game Data Explorer."""

import os
from typing import Dict, List, Optional, Any, Union

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from ..config import get_bigquery_config


class BigQueryClient:
    """Client for interacting with the BGG data warehouse in BigQuery."""

    def __init__(self, environment: Optional[str] = None):
        """Initialize the BigQuery client.

        Args:
            environment: Optional environment name (dev/test/prod)
        """
        self.config = get_bigquery_config(environment)
        self.project_id = self.config["project"]["id"]
        self.dataset = self.config["project"]["dataset"]
        self.raw_dataset = self.config["datasets"]["raw"]
        self.client = self._initialize_client()

    def _initialize_client(self) -> bigquery.Client:
        """Initialize the BigQuery client with credentials.

        Returns:
            Configured BigQuery client
        """
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            return bigquery.Client(credentials=credentials, project=self.project_id)
        return bigquery.Client(project=self.project_id)

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a BigQuery SQL query and return results as a DataFrame.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            DataFrame with query results
        """
        # Replace template variables in query
        formatted_query = query.replace("${project_id}", self.project_id)
        formatted_query = formatted_query.replace("${dataset}", self.dataset)
        formatted_query = formatted_query.replace("${raw_dataset}", self.raw_dataset)

        # Execute query with parameters if provided
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = self._convert_params(params)
        else:
            job_config.query_parameters = []

        return self.client.query(formatted_query, job_config=job_config).to_dataframe()

    def _convert_params(self, params: Dict[str, Any]) -> List[bigquery.ScalarQueryParameter]:
        """Convert Python parameters to BigQuery query parameters.

        Args:
            params: Dictionary of parameter names and values

        Returns:
            List of BigQuery ScalarQueryParameter objects
        """
        query_params = []
        for name, value in params.items():
            param_type = self._get_param_type(value)
            query_params.append(bigquery.ScalarQueryParameter(name, param_type, value))
        return query_params

    def _get_param_type(self, value: Any) -> str:
        """Get BigQuery parameter type for a Python value.

        Args:
            value: Python value

        Returns:
            BigQuery parameter type string
        """
        if isinstance(value, bool):
            return "BOOL"
        elif isinstance(value, int):
            return "INT64"
        elif isinstance(value, float):
            return "FLOAT64"
        elif isinstance(value, str):
            return "STRING"
        elif isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
            return "ARRAY<STRING>"
        elif isinstance(value, (list, tuple)) and all(isinstance(x, int) for x in value):
            return "ARRAY<INT64>"
        elif isinstance(value, (list, tuple)) and all(isinstance(x, float) for x in value):
            return "ARRAY<FLOAT64>"
        else:
            return "STRING"  # Default to string for unknown types

    def get_games(
        self,
        limit: int = 100,
        offset: int = 0,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_complexity: Optional[float] = None,
        max_complexity: Optional[float] = None,
        publishers: Optional[List[int]] = None,
        designers: Optional[List[int]] = None,
        categories: Optional[List[int]] = None,
        mechanics: Optional[List[int]] = None,
        min_player_count: Optional[int] = None,
        max_player_count: Optional[int] = None,
        player_count: Optional[int] = None,
        player_count_type: Optional[str] = None,
        best_player_count_only: bool = False,
        sort_by: str = "bayes_average",
        sort_order: str = "DESC",
    ) -> pd.DataFrame:
        """Get games with filtering and sorting.

        Args:
            limit: Maximum number of games to return
            offset: Number of games to skip
            min_rating: Minimum Geek rating
            max_rating: Maximum Geek rating
            min_year: Minimum year published
            max_year: Maximum year published
            min_complexity: Minimum complexity weight
            max_complexity: Maximum complexity weight
            publishers: List of publisher IDs to filter by
            designers: List of designer IDs to filter by
            categories: List of category IDs to filter by
            mechanics: List of mechanic IDs to filter by
            min_player_count: Minimum recommended player count
            max_player_count: Maximum recommended player count
            sort_by: Field to sort by
            sort_order: Sort order (ASC or DESC)

        Returns:
            DataFrame with game data
        """
        # Build filter conditions
        filters = []
        if min_rating is not None:
            filters.append(f"g.bayes_average >= {min_rating}")
        if max_rating is not None:
            filters.append(f"g.bayes_average <= {max_rating}")
        if min_year is not None:
            filters.append(f"g.year_published >= {min_year}")
        if max_year is not None:
            filters.append(f"g.year_published <= {max_year}")
        if min_complexity is not None:
            filters.append(f"g.average_weight >= {min_complexity}")
        if max_complexity is not None:
            filters.append(f"g.average_weight <= {max_complexity}")

        # Build join conditions for related entities
        joins = []
        if publishers:
            publisher_ids = ", ".join(str(pid) for pid in publishers)
            joins.append(
                f"""
            JOIN `${{project_id}}.${{dataset}}.game_publishers` gp 
                ON g.game_id = gp.game_id AND gp.publisher_id IN ({publisher_ids})
            """
            )
        if designers:
            designer_ids = ", ".join(str(did) for did in designers)
            joins.append(
                f"""
            JOIN `${{project_id}}.${{dataset}}.game_designers` gd 
                ON g.game_id = gd.game_id AND gd.designer_id IN ({designer_ids})
            """
            )
        if categories:
            category_ids = ", ".join(str(cid) for cid in categories)
            joins.append(
                f"""
            JOIN `${{project_id}}.${{dataset}}.game_categories` gc 
                ON g.game_id = gc.game_id AND gc.category_id IN ({category_ids})
            """
            )
        if mechanics:
            mechanic_ids = ", ".join(str(mid) for mid in mechanics)
            joins.append(
                f"""
            JOIN `${{project_id}}.${{dataset}}.game_mechanics` gm 
                ON g.game_id = gm.game_id AND gm.mechanic_id IN ({mechanic_ids})
            """
            )

        # Combine all filters
        where_clause = "WHERE g.bayes_average IS NOT NULL AND g.bayes_average > 0"
        if filters:
            where_clause += " AND " + " AND ".join(filters)

        # Player count filtering using best_player_counts_table
        player_count_join = ""
        best_player_count_join = ""
        best_player_count_filter = ""

        if player_count is not None:
            best_player_count_join = f"""
            JOIN `${{project_id}}.${{dataset}}.best_player_counts_table` bpc 
                ON g.game_id = bpc.game_id
            """

            if player_count_type == "best":
                best_player_count_filter = f"""
                AND {player_count} BETWEEN bpc.min_best_player_count AND bpc.max_best_player_count
                """
            elif player_count_type == "recommended":
                best_player_count_filter = f"""
                AND {player_count} BETWEEN bpc.min_recommended_player_count AND bpc.max_recommended_player_count
                """
            else:
                # If no specific type, check both best and recommended
                best_player_count_filter = f"""
                AND ({player_count} BETWEEN bpc.min_best_player_count AND bpc.max_best_player_count
                     OR {player_count} BETWEEN bpc.min_recommended_player_count AND bpc.max_recommended_player_count)
                """
        elif best_player_count_only:
            best_player_count_join = f"""
            JOIN `${{project_id}}.${{dataset}}.best_player_counts_table` bpc 
                ON g.game_id = bpc.game_id
            """

        # Handle min/max player count range (legacy support)
        elif min_player_count is not None or max_player_count is not None:
            player_count_join = """
            LEFT JOIN `${project_id}.${dataset}.player_count_recommendations` pcr 
                ON g.game_id = pcr.game_id
            """
            player_count_filters = []
            if min_player_count is not None:
                player_count_filters.append(f"pcr.player_count >= {min_player_count}")
            if max_player_count is not None:
                player_count_filters.append(f"pcr.player_count <= {max_player_count}")
            if player_count_filters:
                where_clause += " AND " + " AND ".join(player_count_filters)

        # Always include a LEFT JOIN to best_player_counts_table to get all player count fields
        best_player_count_join = f"""
        LEFT JOIN `${{project_id}}.${{dataset}}.best_player_counts_table` bpc 
            ON g.game_id = bpc.game_id
        """

        # Include all player count fields from best_player_counts_table
        player_count_fields = """
            bpc.best_player_counts,
            bpc.recommended_player_counts,
            bpc.min_best_player_count,
            bpc.max_best_player_count,
            bpc.min_recommended_player_count,
            bpc.max_recommended_player_count
        """

        # Add player count filter if specified
        if player_count is not None:
            if player_count_type == "best":
                best_player_count_filter = f"""
                AND {player_count} BETWEEN bpc.min_best_player_count AND bpc.max_best_player_count
                """
            elif player_count_type == "recommended":
                best_player_count_filter = f"""
                AND {player_count} BETWEEN bpc.min_recommended_player_count AND bpc.max_recommended_player_count
                """
            else:
                # If no specific type, check both best and recommended
                best_player_count_filter = f"""
                AND ({player_count} BETWEEN bpc.min_best_player_count AND bpc.max_best_player_count
                     OR {player_count} BETWEEN bpc.min_recommended_player_count AND bpc.max_recommended_player_count)
                """

        query = f"""
        WITH filtered_games AS (
            SELECT DISTINCT g.*,
                   {player_count_fields}
            FROM `${{project_id}}.${{dataset}}.games_active_table` g
            {' '.join(joins)}
            {player_count_join}
            {best_player_count_join}
            {where_clause}
            {best_player_count_filter}
        )
        SELECT 
            game_id,
            name,
            year_published,
            average_rating,
            bayes_average,
            average_weight,
            users_rated,
            min_players,
            max_players,
            playing_time,
            min_playtime,
            max_playtime,
            min_age,
            thumbnail,
            image,
            best_player_counts,
            recommended_player_counts
        FROM filtered_games
        ORDER BY {sort_by} {sort_order}
        LIMIT {limit}
        OFFSET {offset}
        """

        return self.execute_query(query)

    def get_game_details(self, game_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific game.

        Args:
            game_id: ID of the game to retrieve

        Returns:
            Dictionary with game details
        """
        # Get basic game information
        game_query = f"""
        SELECT g.*
        FROM `${{project_id}}.${{dataset}}.games_active_table` g
        WHERE g.game_id = {game_id}
        """
        game_df = self.execute_query(game_query)

        if game_df.empty:
            return {}

        game_data = game_df.iloc[0].to_dict()

        # Get categories
        categories_query = f"""
        SELECT c.category_id, c.name
        FROM `${{project_id}}.${{dataset}}.categories` c
        JOIN `${{project_id}}.${{dataset}}.game_categories` gc ON c.category_id = gc.category_id
        WHERE gc.game_id = {game_id}
        """
        game_data["categories"] = self.execute_query(categories_query).to_dict("records")

        # Get mechanics
        mechanics_query = f"""
        SELECT m.mechanic_id, m.name
        FROM `${{project_id}}.${{dataset}}.mechanics` m
        JOIN `${{project_id}}.${{dataset}}.game_mechanics` gm ON m.mechanic_id = gm.mechanic_id
        WHERE gm.game_id = {game_id}
        """
        game_data["mechanics"] = self.execute_query(mechanics_query).to_dict("records")

        # Get designers
        designers_query = f"""
        SELECT d.designer_id, d.name
        FROM `${{project_id}}.${{dataset}}.designers` d
        JOIN `${{project_id}}.${{dataset}}.game_designers` gd ON d.designer_id = gd.designer_id
        WHERE gd.game_id = {game_id}
        """
        game_data["designers"] = self.execute_query(designers_query).to_dict("records")

        # Get publishers
        publishers_query = f"""
        SELECT p.publisher_id, p.name
        FROM `${{project_id}}.${{dataset}}.publishers` p
        JOIN `${{project_id}}.${{dataset}}.game_publishers` gp ON p.publisher_id = gp.publisher_id
        WHERE gp.game_id = {game_id}
        """
        game_data["publishers"] = self.execute_query(publishers_query).to_dict("records")

        # Get player count recommendations
        player_counts_query = f"""
        SELECT pcr.player_count, 
               pcr.best_votes, 
               pcr.recommended_votes, 
               pcr.not_recommended_votes,
               pcr.best_percentage, 
               pcr.recommended_percentage,
               CASE 
                 WHEN bpc.game_id IS NOT NULL AND 
                      pcr.player_count >= bpc.min_best_player_count AND 
                      pcr.player_count <= bpc.max_best_player_count 
                 THEN TRUE 
                 ELSE FALSE 
               END AS is_best_player_count,
               CASE 
                 WHEN bpc.game_id IS NOT NULL AND 
                      pcr.player_count >= bpc.min_recommended_player_count AND 
                      pcr.player_count <= bpc.max_recommended_player_count 
                 THEN TRUE 
                 ELSE FALSE 
               END AS is_recommended_player_count
        FROM `${{project_id}}.${{dataset}}.player_count_recommendations` pcr
        LEFT JOIN `${{project_id}}.${{dataset}}.best_player_counts_table` bpc 
            ON pcr.game_id = bpc.game_id
        WHERE pcr.game_id = {game_id}
        ORDER BY pcr.player_count
        """
        game_data["player_counts"] = self.execute_query(player_counts_query).to_dict("records")

        return game_data

    def get_publishers(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Get list of publishers.

        Args:
            limit: Maximum number of publishers to return

        Returns:
            List of publisher dictionaries with id and name
        """
        query = f"""        WITH publisher_counts AS (
            SELECT 
                p.publisher_id, 
                p.name, 
                COUNT(DISTINCT gp.game_id) as game_count,
                ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT gp.game_id) DESC) as rank
            FROM `${{project_id}}.${{dataset}}.publishers` p
            JOIN `${{project_id}}.${{dataset}}.game_publishers` gp 
                ON p.publisher_id = gp.publisher_id
            GROUP BY p.publisher_id, p.name
        )
        SELECT publisher_id, name, game_count
        FROM publisher_counts
        WHERE rank <= {limit}
        ORDER BY name

        """
        return self.execute_query(query).to_dict("records")

    def get_designers(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get list of designers.

        Args:
            limit: Maximum number of designers to return

        Returns:
            List of designer dictionaries with id and name
        """
        query = f"""
        WITH designer_counts AS (
            SELECT 
                d.designer_id, 
                d.name, 
                COUNT(DISTINCT gd.game_id) as game_count,
                ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT gd.game_id) DESC) as rank
            FROM `${{project_id}}.${{dataset}}.designers` d
            JOIN `${{project_id}}.${{dataset}}.game_designers` gd 
                ON d.designer_id = gd.designer_id
            GROUP BY d.designer_id, d.name
        )
        SELECT designer_id, name, game_count
        FROM designer_counts
        WHERE rank <= {limit}
        ORDER BY name
        """
        return self.execute_query(query).to_dict("records")

    def get_categories(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Get list of categories.

        Args:
            limit: Maximum number of categories to return

        Returns:
            List of category dictionaries with id and name
        """
        query = f"""
        WITH category_counts AS (
            SELECT 
                c.category_id, 
                c.name, 
                COUNT(DISTINCT gc.game_id) as game_count,
                ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT gc.game_id) DESC) as rank
            FROM `${{project_id}}.${{dataset}}.categories` c
            JOIN `${{project_id}}.${{dataset}}.game_categories` gc 
                ON c.category_id = gc.category_id
            GROUP BY c.category_id, c.name
        )
        SELECT category_id, name, game_count
        FROM category_counts
        WHERE rank <= {limit}
        ORDER BY name
        """
        return self.execute_query(query).to_dict("records")

    def get_mechanics(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Get list of mechanics.

        Args:
            limit: Maximum number of mechanics to return

        Returns:
            List of mechanic dictionaries with id and name
        """
        query = f"""
        WITH mechanic_counts AS (
            SELECT 
                m.mechanic_id, 
                m.name, 
                COUNT(DISTINCT gm.game_id) as game_count,
                ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT gm.game_id) DESC) as rank
            FROM `${{project_id}}.${{dataset}}.mechanics` m
            JOIN `${{project_id}}.${{dataset}}.game_mechanics` gm 
                ON m.mechanic_id = gm.mechanic_id
            GROUP BY m.mechanic_id, m.name
        )
        SELECT mechanic_id, name, game_count
        FROM mechanic_counts
        WHERE rank <= {limit}
        ORDER BY name
        """
        return self.execute_query(query).to_dict("records")

    def get_all_filter_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all filter options from pre-computed combined table.

        This method replaces the need to call get_publishers(), get_categories(),
        get_mechanics(), and get_designers() separately, providing significant
        performance improvement by using a single query.

        Returns:
            Dictionary with filter options for all entity types
        """
        query = """
        SELECT entity_type, entity_id, name, game_count
        FROM `${project_id}.${dataset}.filter_options_combined`
        ORDER BY entity_type, game_count DESC, name ASC
        """

        df = self.execute_query(query)

        # Initialize result dictionary
        result = {"publishers": [], "categories": [], "mechanics": [], "designers": []}

        # Map entity_type to correct ID field name and plural key
        entity_mapping = {
            "publisher": {"key": "publishers", "id_field": "publisher_id"},
            "category": {"key": "categories", "id_field": "category_id"},
            "mechanic": {"key": "mechanics", "id_field": "mechanic_id"},
            "designer": {"key": "designers", "id_field": "designer_id"},
        }

        # Group results by entity type
        for _, row in df.iterrows():
            entity_type = row["entity_type"]

            if entity_type in entity_mapping:
                mapping = entity_mapping[entity_type]
                result[mapping["key"]].append(
                    {
                        mapping["id_field"]: row["entity_id"],
                        "name": row["name"],
                        "game_count": row["game_count"],
                    }
                )

        return result

    def test_filter_options_combined(self) -> Dict[str, Any]:
        """Test method to debug the filter_options_combined table.

        Returns:
            Dictionary with debug information
        """
        query = """
        SELECT entity_type, COUNT(*) as count
        FROM `${project_id}.${dataset}.filter_options_combined`
        GROUP BY entity_type
        ORDER BY entity_type
        """

        df = self.execute_query(query)

        # Also get a sample of the data
        sample_query = """
        SELECT entity_type, entity_id, name, game_count
        FROM `${project_id}.${dataset}.filter_options_combined`
        ORDER BY entity_type, game_count DESC
        LIMIT 10
        """

        sample_df = self.execute_query(sample_query)

        return {
            "counts_by_type": df.to_dict("records"),
            "sample_data": sample_df.to_dict("records"),
        }

    def get_player_counts(self) -> List[Dict[str, Any]]:
        """Get list of player counts from best_player_counts table.

        Returns:
            List of player count dictionaries with values 1-8
        """
        query = """
        WITH player_counts AS (
            SELECT GENERATE_ARRAY(1, 8) as counts
        )
        SELECT count as player_count
        FROM player_counts, UNNEST(counts) as count
        ORDER BY player_count
        """
        return self.execute_query(query).to_dict("records")

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the dashboard.

        Returns:
            Dictionary with summary statistics
        """
        # Total games
        total_games_query = """
        SELECT COUNT(DISTINCT game_id) as total_games
        FROM `${project_id}.${dataset}.games_active_table`;
        """
        total_games = self.execute_query(total_games_query).iloc[0]["total_games"]

        # Games with ratings
        rated_games_query = """
        SELECT COUNT(DISTINCT game_id) as rated_games
        FROM `${project_id}.${dataset}.games_active_table`
        WHERE bayes_average IS NOT NULL 
          AND bayes_average > 0
          AND type = 'boardgame';
        """
        rated_games = self.execute_query(rated_games_query).iloc[0]["rated_games"]

        # Entity counts
        entity_counts_query = """
        SELECT
          (SELECT COUNT(DISTINCT category_id) FROM `${project_id}.${dataset}.categories`) as category_count,
          (SELECT COUNT(DISTINCT mechanic_id) FROM `${project_id}.${dataset}.mechanics`) as mechanic_count,
          (SELECT COUNT(DISTINCT designer_id) FROM `${project_id}.${dataset}.designers`) as designer_count,
          (SELECT COUNT(DISTINCT publisher_id) FROM `${project_id}.${dataset}.publishers`) as publisher_count
        FROM (SELECT 1) -- Dummy table to make the query valid
        """
        entity_counts = self.execute_query(entity_counts_query).iloc[0].to_dict()

        # Rating distribution
        rating_dist_query = """
        SELECT 
            FLOOR(bayes_average * 4) / 4 as rating_bin,
            COUNT(*) as game_count
        FROM `${project_id}.${dataset}.games_active_table`
        WHERE bayes_average IS NOT NULL AND bayes_average > 0
        GROUP BY rating_bin
        ORDER BY rating_bin
        """
        rating_dist = self.execute_query(rating_dist_query).to_dict("records")

        # Year distribution
        year_dist_query = """
        SELECT 
            year_published,
            COUNT(*) as game_count
        FROM `${project_id}.${dataset}.games_active_table`
        WHERE year_published BETWEEN 1970 AND 2025
        GROUP BY year_published
        ORDER BY year_published
        """
        year_dist = self.execute_query(year_dist_query).to_dict("records")

        return {
            "total_games": total_games,
            "rated_games": rated_games,
            "entity_counts": entity_counts,
            "rating_distribution": rating_dist,
            "year_distribution": year_dist,
        }
