"""Tests for the BGG Dash Viewer application."""

import unittest
from unittest.mock import patch, MagicMock

import dash
from dash.testing.application_runners import import_app

from src.app import app


class TestApp(unittest.TestCase):
    """Test cases for the Dash application."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = app

    def test_app_initialization(self):
        """Test that the app initializes correctly."""
        self.assertIsInstance(self.app, dash.Dash)
        self.assertEqual(self.app.title, "BGG Dash Viewer")
        self.assertTrue(self.app.suppress_callback_exceptions)

    @patch("src.layouts.home.create_home_layout")
    def test_display_page_home(self, mock_create_home_layout):
        """Test that the home page is displayed correctly."""
        mock_create_home_layout.return_value = "Home Layout"
        from src.app import display_page

        result = display_page("/")

        mock_create_home_layout.assert_called_once()
        self.assertEqual(result, "Home Layout")

    @patch("src.layouts.game_search.create_game_search_layout")
    def test_display_page_search(self, mock_create_game_search_layout):
        """Test that the game search page is displayed correctly."""
        mock_create_game_search_layout.return_value = "Search Layout"
        from src.app import display_page

        result = display_page("/game-search")

        mock_create_game_search_layout.assert_called_once()
        self.assertEqual(result, "Search Layout")

    @patch("src.layouts.game_details.create_game_details_layout")
    def test_display_page_game_details(self, mock_create_game_details_layout):
        """Test that the game details page is displayed correctly."""
        mock_create_game_details_layout.return_value = "Details Layout"
        from src.app import display_page

        result = display_page("/game/12345")

        mock_create_game_details_layout.assert_called_once_with(12345)
        self.assertEqual(result, "Details Layout")


if __name__ == "__main__":
    unittest.main()
