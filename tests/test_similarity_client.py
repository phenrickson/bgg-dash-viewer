"""Tests for the similarity search client."""

import os
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

from src.data.similarity_client import (
    SimilarityFilters,
    BigQuerySimilarityClient,
    ServiceSimilarityClient,
    get_similarity_client,
)


class TestSimilarityFilters(unittest.TestCase):
    """Test cases for SimilarityFilters."""

    def test_to_dict_empty(self):
        """Test that empty filters return empty dict."""
        filters = SimilarityFilters()
        self.assertEqual(filters.to_dict(), {})

    def test_to_dict_partial(self):
        """Test that partial filters only include set values."""
        filters = SimilarityFilters(min_year=2000, max_complexity=3.5)
        result = filters.to_dict()
        self.assertEqual(result, {"min_year": 2000, "max_complexity": 3.5})

    def test_to_dict_full(self):
        """Test that all filters are included when set."""
        filters = SimilarityFilters(
            min_year=2000,
            max_year=2024,
            min_users_rated=100,
            max_users_rated=10000,
            min_rating=6.0,
            max_rating=9.0,
            min_geek_rating=5.5,
            max_geek_rating=8.5,
            min_complexity=1.5,
            max_complexity=4.0,
        )
        result = filters.to_dict()
        self.assertEqual(len(result), 10)

    def test_has_filters_empty(self):
        """Test has_filters returns False when empty."""
        filters = SimilarityFilters()
        self.assertFalse(filters.has_filters())

    def test_has_filters_with_value(self):
        """Test has_filters returns True when any filter set."""
        filters = SimilarityFilters(min_year=2000)
        self.assertTrue(filters.has_filters())


class TestBigQuerySimilarityClient(unittest.TestCase):
    """Test cases for BigQuerySimilarityClient."""

    @patch("src.data.similarity_client.bigquery.Client")
    def setUp(self, mock_client):
        """Set up test fixtures."""
        self.mock_client_instance = MagicMock()
        mock_client.return_value = self.mock_client_instance
        self.client = BigQuerySimilarityClient(
            table_id="test-project.test-dataset.test-table"
        )

    def test_initialization(self):
        """Test that client initializes with correct table."""
        self.assertEqual(
            self.client.table_id, "test-project.test-dataset.test-table"
        )

    def test_build_filter_clause_empty(self):
        """Test filter clause is empty when no filters."""
        clause = self.client._build_filter_clause(None)
        self.assertEqual(clause, "")

        clause = self.client._build_filter_clause(SimilarityFilters())
        self.assertEqual(clause, "")

    def test_build_filter_clause_with_filters(self):
        """Test filter clause is built correctly."""
        filters = SimilarityFilters(
            min_year=2000,
            max_year=2024,
            min_complexity=2.0,
        )
        clause = self.client._build_filter_clause(filters)
        self.assertIn("year_published >= 2000", clause)
        self.assertIn("year_published <= 2024", clause)
        self.assertIn("complexity >= 2.0", clause)
        self.assertTrue(clause.startswith(" AND "))

    def test_find_similar_games(self):
        """Test find_similar_games builds correct query."""
        # Mock query result
        mock_query_job = MagicMock()
        mock_df = pd.DataFrame({
            "game_id": [1, 2, 3],
            "name": ["Game A", "Game B", "Game C"],
            "distance": [0.1, 0.2, 0.3],
        })
        mock_query_job.to_dataframe.return_value = mock_df
        self.mock_client_instance.query.return_value = mock_query_job

        result = self.client.find_similar_games(
            game_id=123,
            top_k=10,
            distance_type="cosine",
        )

        # Verify query was called
        self.mock_client_instance.query.assert_called_once()
        query = self.mock_client_instance.query.call_args[0][0]

        # Check query structure
        self.assertIn("ML.DISTANCE", query)
        self.assertIn("COSINE", query)
        self.assertIn("LIMIT @top_k", query)
        self.assertIn("game_id = @game_id", query)

        # Check result
        pd.testing.assert_frame_equal(result, mock_df)

    def test_find_similar_games_with_filters(self):
        """Test find_similar_games applies filters."""
        mock_query_job = MagicMock()
        mock_query_job.to_dataframe.return_value = pd.DataFrame()
        self.mock_client_instance.query.return_value = mock_query_job

        filters = SimilarityFilters(min_year=2010, min_users_rated=100)
        self.client.find_similar_games(
            game_id=123,
            top_k=10,
            filters=filters,
        )

        query = self.mock_client_instance.query.call_args[0][0]
        self.assertIn("year_published >= 2010", query)
        self.assertIn("users_rated >= 100", query)


class TestServiceSimilarityClient(unittest.TestCase):
    """Test cases for ServiceSimilarityClient."""

    @patch("src.data.similarity_client.requests")
    def test_find_similar_games(self, mock_requests):
        """Test find_similar_games calls correct endpoint."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"game_id": 1, "name": "Game A", "distance": 0.1},
                {"game_id": 2, "name": "Game B", "distance": 0.2},
            ]
        }
        mock_requests.post.return_value = mock_response

        client = ServiceSimilarityClient(base_url="http://test:8080")
        result = client.find_similar_games(game_id=123, top_k=10)

        # Verify POST was called correctly
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        self.assertEqual(call_args[0][0], "http://test:8080/similar")
        self.assertEqual(call_args[1]["json"]["game_id"], 123)
        self.assertEqual(call_args[1]["json"]["top_k"], 10)

        # Check result
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["game_id"], 1)

    @patch("src.data.similarity_client.requests")
    def test_health_check(self, mock_requests):
        """Test health_check calls correct endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_requests.get.return_value = mock_response

        client = ServiceSimilarityClient(base_url="http://test:8080")
        result = client.health_check()

        mock_requests.get.assert_called_once()
        self.assertEqual(result["status"], "healthy")


class TestGetSimilarityClient(unittest.TestCase):
    """Test cases for get_similarity_client factory."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.data.similarity_client.bigquery.Client")
    def test_returns_bigquery_client_by_default(self, mock_bq):
        """Test returns BigQuery client when no URL set."""
        # Remove SIMILARITY_SERVICE_URL if set
        os.environ.pop("SIMILARITY_SERVICE_URL", None)
        client = get_similarity_client()
        self.assertIsInstance(client, BigQuerySimilarityClient)

    @patch.dict(os.environ, {"SIMILARITY_SERVICE_URL": "http://test:8080"})
    def test_returns_service_client_when_url_set(self):
        """Test returns service client when URL is set."""
        client = get_similarity_client()
        self.assertIsInstance(client, ServiceSimilarityClient)
        self.assertEqual(client.base_url, "http://test:8080")


if __name__ == "__main__":
    unittest.main()
