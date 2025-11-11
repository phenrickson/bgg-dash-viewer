"""Tests for the BigQuery client."""

import unittest
from unittest.mock import patch, MagicMock

import pandas as pd
from google.cloud import bigquery

from src.data.bigquery_client import BigQueryClient


class TestBigQueryClient(unittest.TestCase):
    """Test cases for the BigQuery client."""

    @patch("src.data.bigquery_client.get_bigquery_config")
    @patch("src.data.bigquery_client.bigquery.Client")
    def setUp(self, mock_client, mock_get_config):
        """Set up test fixtures."""
        # Mock the BigQuery configuration
        mock_get_config.return_value = {
            "project": {
                "id": "test-project",
                "dataset": "test_dataset",
                "location": "US",
            },
            "datasets": {
                "raw": "test_raw_dataset",
            },
            "tables": {},
            "raw_tables": {},
        }

        # Mock the BigQuery client
        self.mock_client_instance = MagicMock()
        mock_client.return_value = self.mock_client_instance

        # Create the BigQueryClient instance
        self.bq_client = BigQueryClient()

    def test_initialization(self):
        """Test that the client initializes correctly."""
        self.assertEqual(self.bq_client.project_id, "test-project")
        self.assertEqual(self.bq_client.dataset, "test_dataset")
        self.assertEqual(self.bq_client.raw_dataset, "test_raw_dataset")
        self.assertEqual(self.bq_client.client, self.mock_client_instance)

    def test_execute_query(self):
        """Test that execute_query formats the query and returns a DataFrame."""
        # Mock the query result
        mock_query_job = MagicMock()
        mock_dataframe = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        mock_query_job.to_dataframe.return_value = mock_dataframe
        self.mock_client_instance.query.return_value = mock_query_job

        # Execute a query
        query = "SELECT * FROM `${project_id}.${dataset}.table` WHERE x = ${raw_dataset}"
        result = self.bq_client.execute_query(query)

        # Check that the query was formatted correctly
        expected_query = (
            "SELECT * FROM `test-project.test_dataset.table` WHERE x = test_raw_dataset"
        )
        self.mock_client_instance.query.assert_called_once()
        actual_query = self.mock_client_instance.query.call_args[0][0]
        self.assertEqual(actual_query, expected_query)

        # Check that the result is the expected DataFrame
        pd.testing.assert_frame_equal(result, mock_dataframe)

    @patch("src.data.bigquery_client.BigQueryClient.execute_query")
    def test_get_games(self, mock_execute_query):
        """Test that get_games builds the correct query."""
        # Mock the query result
        mock_dataframe = pd.DataFrame({"game_id": [1, 2], "name": ["Game 1", "Game 2"]})
        mock_execute_query.return_value = mock_dataframe

        # Call get_games with various filters
        result = self.bq_client.get_games(
            limit=10,
            offset=5,
            min_rating=7.0,
            max_rating=9.0,
            min_year=2000,
            max_year=2020,
            min_complexity=2.0,
            max_complexity=4.0,
            publishers=[1, 2],
            designers=[3, 4],
            categories=[5, 6],
            mechanics=[7, 8],
            min_player_count=2,
            max_player_count=4,
            sort_by="bayes_average",
            sort_order="DESC",
        )

        # Check that execute_query was called
        mock_execute_query.assert_called_once()

        # Check that the query contains the expected filters
        query = mock_execute_query.call_args[0][0]
        self.assertIn("g.bayes_average >= 7.0", query)
        self.assertIn("g.bayes_average <= 9.0", query)
        self.assertIn("g.year_published >= 2000", query)
        self.assertIn("g.year_published <= 2020", query)
        self.assertIn("g.average_weight >= 2.0", query)
        self.assertIn("g.average_weight <= 4.0", query)
        self.assertIn("publisher_id IN (1, 2)", query)
        self.assertIn("designer_id IN (3, 4)", query)
        self.assertIn("category_id IN (5, 6)", query)
        self.assertIn("mechanic_id IN (7, 8)", query)
        self.assertIn("pcr.player_count >= 2", query)
        self.assertIn("pcr.player_count <= 4", query)
        self.assertIn("ORDER BY bayes_average DESC", query)
        self.assertIn("LIMIT 10", query)
        self.assertIn("OFFSET 5", query)

        # Check that the result is the expected DataFrame
        pd.testing.assert_frame_equal(result, mock_dataframe)

    @patch("src.data.bigquery_client.BigQueryClient.execute_query")
    def test_get_game_details(self, mock_execute_query):
        """Test that get_game_details builds the correct queries."""
        # Mock the query results
        game_df = pd.DataFrame(
            {
                "game_id": [123],
                "name": ["Test Game"],
                "year_published": [2020],
                "bayes_average": [7.5],
                "average_weight": [2.5],
                "users_rated": [1000],
                "min_players": [2],
                "max_players": [4],
                "playing_time": [60],
            }
        )
        categories_df = pd.DataFrame(
            {
                "category_id": [1, 2],
                "name": ["Category 1", "Category 2"],
            }
        )
        mechanics_df = pd.DataFrame(
            {
                "mechanic_id": [3, 4],
                "name": ["Mechanic 1", "Mechanic 2"],
            }
        )
        designers_df = pd.DataFrame(
            {
                "designer_id": [5, 6],
                "name": ["Designer 1", "Designer 2"],
            }
        )
        publishers_df = pd.DataFrame(
            {
                "publisher_id": [7, 8],
                "name": ["Publisher 1", "Publisher 2"],
            }
        )
        player_counts_df = pd.DataFrame(
            {
                "player_count": [2, 3, 4],
                "best_percentage": [20, 60, 20],
                "recommended_percentage": [80, 90, 70],
            }
        )

        # Set up the mock to return different DataFrames for different queries
        def side_effect(query):
            if "FROM `${project_id}.${dataset}.games_active`" in query:
                return game_df
            elif "FROM `${project_id}.${dataset}.categories`" in query:
                return categories_df
            elif "FROM `${project_id}.${dataset}.mechanics`" in query:
                return mechanics_df
            elif "FROM `${project_id}.${dataset}.designers`" in query:
                return designers_df
            elif "FROM `${project_id}.${dataset}.publishers`" in query:
                return publishers_df
            elif "FROM `${project_id}.${dataset}.player_count_recommendations`" in query:
                return player_counts_df
            return pd.DataFrame()

        mock_execute_query.side_effect = side_effect

        # Call get_game_details
        result = self.bq_client.get_game_details(123)

        # Check that execute_query was called multiple times
        self.assertEqual(mock_execute_query.call_count, 6)

        # Check that the result contains the expected data
        self.assertEqual(result["game_id"], 123)
        self.assertEqual(result["name"], "Test Game")
        self.assertEqual(result["year_published"], 2020)
        self.assertEqual(result["bayes_average"], 7.5)
        self.assertEqual(result["average_weight"], 2.5)
        self.assertEqual(result["users_rated"], 1000)
        self.assertEqual(result["min_players"], 2)
        self.assertEqual(result["max_players"], 4)
        self.assertEqual(result["playing_time"], 60)

        # Check that the related entities are included
        self.assertEqual(len(result["categories"]), 2)
        self.assertEqual(result["categories"][0]["name"], "Category 1")
        self.assertEqual(len(result["mechanics"]), 2)
        self.assertEqual(result["mechanics"][0]["name"], "Mechanic 1")
        self.assertEqual(len(result["designers"]), 2)
        self.assertEqual(result["designers"][0]["name"], "Designer 1")
        self.assertEqual(len(result["publishers"]), 2)
        self.assertEqual(result["publishers"][0]["name"], "Publisher 1")
        self.assertEqual(len(result["player_counts"]), 3)
        self.assertEqual(result["player_counts"][0]["player_count"], 2)


if __name__ == "__main__":
    unittest.main()
