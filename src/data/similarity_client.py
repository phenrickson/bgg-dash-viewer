"""Client for game similarity search - supports both direct BigQuery and service modes."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


@dataclass
class SimilarityFilters:
    """Filters for similarity search."""

    min_year: Optional[int] = None
    max_year: Optional[int] = None
    min_users_rated: Optional[int] = None
    max_users_rated: Optional[int] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_geek_rating: Optional[float] = None
    max_geek_rating: Optional[float] = None
    min_complexity: Optional[float] = None
    max_complexity: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert filters to dictionary, excluding None values."""
        return {k: v for k, v in {
            "min_year": self.min_year,
            "max_year": self.max_year,
            "min_users_rated": self.min_users_rated,
            "max_users_rated": self.max_users_rated,
            "min_rating": self.min_rating,
            "max_rating": self.max_rating,
            "min_geek_rating": self.min_geek_rating,
            "max_geek_rating": self.max_geek_rating,
            "min_complexity": self.min_complexity,
            "max_complexity": self.max_complexity,
        }.items() if v is not None}

    def has_filters(self) -> bool:
        """Check if any filters are set."""
        return any([
            self.min_year, self.max_year,
            self.min_users_rated, self.max_users_rated,
            self.min_rating, self.max_rating,
            self.min_geek_rating, self.max_geek_rating,
            self.min_complexity, self.max_complexity,
        ])


class BaseSimilarityClient(ABC):
    """Abstract base class for similarity search clients."""

    @abstractmethod
    def find_similar_games(
        self,
        game_id: int,
        top_k: int = 10,
        distance_type: str = "cosine",
        filters: Optional[SimilarityFilters] = None,
        embedding_dims: Optional[int] = None,
    ) -> pd.DataFrame:
        """Find games similar to a given game."""
        pass

    @abstractmethod
    def find_games_like(
        self,
        game_ids: List[int],
        top_k: int = 10,
        distance_type: str = "cosine",
        filters: Optional[SimilarityFilters] = None,
        embedding_dims: Optional[int] = None,
    ) -> pd.DataFrame:
        """Find games similar to a set of games."""
        pass


class BigQuerySimilarityClient(BaseSimilarityClient):
    """Direct BigQuery client for similarity search - no service required."""

    # Default table for similarity search (in data warehouse)
    DEFAULT_TABLE = "bgg-data-warehouse.analytics.game_similarity_search"

    def __init__(self, table_id: Optional[str] = None):
        """Initialize BigQuery similarity client.

        Args:
            table_id: Full BigQuery table ID. Defaults to game_similarity_search.
        """
        self.table_id = table_id or os.getenv(
            "SIMILARITY_TABLE_ID", self.DEFAULT_TABLE
        )
        # Extract project from table_id (format: project.dataset.table)
        project_id = self.table_id.split(".")[0]
        self.client = self._initialize_client(project_id)
        logger.info(f"BigQuerySimilarityClient initialized with table={self.table_id}, project={project_id}")

    def _initialize_client(self, project_id: str) -> bigquery.Client:
        """Initialize the BigQuery client with credentials.

        Args:
            project_id: GCP project ID.

        Returns:
            Configured BigQuery client.
        """
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            return bigquery.Client(credentials=credentials, project=project_id)
        return bigquery.Client(project=project_id)

    def _build_filter_clause(self, filters: Optional[SimilarityFilters]) -> str:
        """Build SQL WHERE clause from filters."""
        if not filters or not filters.has_filters():
            return ""

        conditions = []
        if filters.min_year is not None:
            conditions.append(f"year_published >= {filters.min_year}")
        if filters.max_year is not None:
            conditions.append(f"year_published <= {filters.max_year}")
        if filters.min_users_rated is not None:
            conditions.append(f"users_rated >= {filters.min_users_rated}")
        if filters.max_users_rated is not None:
            conditions.append(f"users_rated <= {filters.max_users_rated}")
        if filters.min_rating is not None:
            conditions.append(f"average_rating >= {filters.min_rating}")
        if filters.max_rating is not None:
            conditions.append(f"average_rating <= {filters.max_rating}")
        if filters.min_geek_rating is not None:
            conditions.append(f"geek_rating >= {filters.min_geek_rating}")
        if filters.max_geek_rating is not None:
            conditions.append(f"geek_rating <= {filters.max_geek_rating}")
        if filters.min_complexity is not None:
            conditions.append(f"complexity >= {filters.min_complexity}")
        if filters.max_complexity is not None:
            conditions.append(f"complexity <= {filters.max_complexity}")

        return " AND " + " AND ".join(conditions) if conditions else ""

    def _get_embedding_column(self, embedding_dims: Optional[int] = None) -> str:
        """Get the embedding column name for the requested dimensions."""
        if embedding_dims is None or embedding_dims == 64:
            return "embedding"
        if embedding_dims in [8, 16, 32]:
            return f"embedding_{embedding_dims}"
        return "embedding"

    def find_similar_games(
        self,
        game_id: int,
        top_k: int = 10,
        distance_type: str = "cosine",
        filters: Optional[SimilarityFilters] = None,
        embedding_dims: Optional[int] = None,
    ) -> pd.DataFrame:
        """Find games similar to a given game using BigQuery ML.DISTANCE.

        Args:
            game_id: Source game ID to find similar games for.
            top_k: Number of similar games to return.
            distance_type: Distance metric (cosine, euclidean, dot_product).
            filters: Optional filters for year, rating, complexity, etc.
            embedding_dims: Embedding dimensions to use (8, 16, 32, or 64/None for full).

        Returns:
            DataFrame with similar games.
        """
        logger.info(f"Finding similar games for game_id={game_id}, top_k={top_k}, dims={embedding_dims}")

        filter_clause = self._build_filter_clause(filters)
        distance_type_upper = distance_type.upper()
        emb_col = self._get_embedding_column(embedding_dims)

        query = f"""
        WITH source_game AS (
            SELECT {emb_col} as embedding, game_id as source_game_id
            FROM `{self.table_id}`
            WHERE game_id = @game_id
            LIMIT 1
        ),
        candidates AS (
            SELECT game_id, name, year_published, {emb_col} as embedding,
                   users_rated, average_rating, geek_rating, complexity, thumbnail
            FROM `{self.table_id}`
            WHERE game_id != @game_id{filter_clause}
        )
        SELECT
            c.game_id,
            c.name,
            c.year_published,
            c.users_rated,
            c.average_rating,
            c.geek_rating,
            c.complexity,
            c.thumbnail,
            ML.DISTANCE(c.embedding, s.embedding, '{distance_type_upper}') as distance
        FROM candidates c
        CROSS JOIN source_game s
        ORDER BY distance ASC
        LIMIT @top_k
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("game_id", "INT64", game_id),
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            ]
        )

        result = self.client.query(query, job_config=job_config).to_dataframe()
        return result

    def find_games_like(
        self,
        game_ids: List[int],
        top_k: int = 10,
        distance_type: str = "cosine",
        filters: Optional[SimilarityFilters] = None,
        embedding_dims: Optional[int] = None,
    ) -> pd.DataFrame:
        """Find games similar to a set of games (using average embedding).

        Args:
            game_ids: List of game IDs to combine and find similar games for.
            top_k: Number of similar games to return.
            distance_type: Distance metric.
            filters: Optional filters.
            embedding_dims: Embedding dimensions to use (8, 16, 32, or 64/None for full).

        Returns:
            DataFrame with similar games.
        """
        logger.info(f"Finding games like game_ids={game_ids}, top_k={top_k}, dims={embedding_dims}")

        filter_clause = self._build_filter_clause(filters)
        distance_type_upper = distance_type.upper()
        game_ids_str = ",".join(str(g) for g in game_ids)
        emb_col = self._get_embedding_column(embedding_dims)

        query = f"""
        WITH source_games AS (
            SELECT {emb_col} as embedding
            FROM `{self.table_id}`
            WHERE game_id IN ({game_ids_str})
        ),
        avg_embedding AS (
            SELECT ARRAY_AGG(e) as embedding
            FROM source_games,
            UNNEST(embedding) as e WITH OFFSET pos
            GROUP BY pos
            ORDER BY pos
        ),
        query_embedding AS (
            SELECT ARRAY(SELECT AVG(e) FROM UNNEST(embedding) as e) as embedding
            FROM avg_embedding
        ),
        candidates AS (
            SELECT game_id, name, year_published, {emb_col} as embedding,
                   users_rated, average_rating, geek_rating, complexity, thumbnail
            FROM `{self.table_id}`
            WHERE game_id NOT IN ({game_ids_str}){filter_clause}
        )
        SELECT
            c.game_id,
            c.name,
            c.year_published,
            c.users_rated,
            c.average_rating,
            c.geek_rating,
            c.complexity,
            c.thumbnail,
            ML.DISTANCE(c.embedding, q.embedding, '{distance_type_upper}') as distance
        FROM candidates c
        CROSS JOIN query_embedding q
        ORDER BY distance ASC
        LIMIT @top_k
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            ]
        )

        result = self.client.query(query, job_config=job_config).to_dataframe()
        return result


class ServiceSimilarityClient(BaseSimilarityClient):
    """HTTP client for the embeddings service."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the service client.

        Args:
            base_url: Base URL for the embeddings service.
            timeout: Request timeout in seconds.
        """
        import requests
        self._requests = requests
        self.base_url = base_url
        self.timeout = timeout
        logger.info(f"ServiceSimilarityClient initialized with base_url={self.base_url}")

    def health_check(self) -> Dict[str, Any]:
        """Check if the embeddings service is healthy."""
        response = self._requests.get(
            f"{self.base_url}/health",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def find_similar_games(
        self,
        game_id: int,
        top_k: int = 10,
        distance_type: str = "cosine",
        filters: Optional[SimilarityFilters] = None,
        embedding_dims: Optional[int] = None,
    ) -> pd.DataFrame:
        """Find games similar to a given game via the service."""
        payload: Dict[str, Any] = {
            "game_id": game_id,
            "top_k": top_k,
            "distance_type": distance_type,
        }

        if embedding_dims:
            payload["embedding_dims"] = embedding_dims

        if filters:
            payload.update(filters.to_dict())

        logger.info(f"Finding similar games for game_id={game_id}, top_k={top_k}, dims={embedding_dims}")

        response = self._requests.post(
            f"{self.base_url}/similar",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results)

    def find_games_like(
        self,
        game_ids: List[int],
        top_k: int = 10,
        distance_type: str = "cosine",
        filters: Optional[SimilarityFilters] = None,
        embedding_dims: Optional[int] = None,
    ) -> pd.DataFrame:
        """Find games similar to a set of games via the service."""
        payload: Dict[str, Any] = {
            "game_ids": game_ids,
            "top_k": top_k,
            "distance_type": distance_type,
        }

        if embedding_dims:
            payload["embedding_dims"] = embedding_dims

        if filters:
            payload.update(filters.to_dict())

        logger.info(f"Finding games like game_ids={game_ids}, top_k={top_k}, dims={embedding_dims}")

        response = self._requests.post(
            f"{self.base_url}/similar",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results)

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about stored embeddings."""
        response = self._requests.get(
            f"{self.base_url}/embedding_stats",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def list_models(self) -> List[Dict[str, Any]]:
        """List available embedding models."""
        response = self._requests.get(
            f"{self.base_url}/models",
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])


def get_similarity_client() -> BaseSimilarityClient:
    """Factory function to get the appropriate similarity client.

    Returns BigQuerySimilarityClient by default (local dev).
    Returns ServiceSimilarityClient if SIMILARITY_SERVICE_URL is set.

    Returns:
        Configured similarity client.
    """
    service_url = os.getenv("SIMILARITY_SERVICE_URL")

    if service_url:
        timeout = int(os.getenv("SIMILARITY_SERVICE_TIMEOUT", "30"))
        logger.info(f"Using ServiceSimilarityClient with URL: {service_url}")
        return ServiceSimilarityClient(base_url=service_url, timeout=timeout)
    else:
        logger.info("Using BigQuerySimilarityClient (direct query mode)")
        return BigQuerySimilarityClient()


# Backwards compatibility alias
SimilaritySearchClient = BigQuerySimilarityClient
