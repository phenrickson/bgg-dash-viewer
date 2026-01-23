"""Tests for authentication module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.auth.utils import hash_password, verify_password
from src.auth.user import User, UserRepository


class TestPasswordUtils:
    """Tests for password hashing utilities."""

    def test_hash_password_returns_string(self):
        """hash_password should return a string."""
        result = hash_password("testpassword")
        assert isinstance(result, str)

    def test_hash_password_produces_bcrypt_hash(self):
        """hash_password should produce a bcrypt hash starting with $2b$."""
        result = hash_password("testpassword")
        assert result.startswith("$2b$")

    def test_hash_password_different_for_same_input(self):
        """hash_password should produce different hashes due to salt."""
        hash1 = hash_password("testpassword")
        hash2 = hash_password("testpassword")
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for wrong password."""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_password(self):
        """verify_password should handle empty password."""
        hashed = hash_password("realpassword")
        assert verify_password("", hashed) is False


class TestUserModel:
    """Tests for User model."""

    def test_user_get_id(self):
        """User.get_id() should return user_id."""
        user = User(
            user_id="test-uuid-123",
            email="test@example.com",
            password_hash="$2b$12$hash",
            display_name="Test User",
            created_at=datetime.now(timezone.utc),
            last_login=None,
            active=True,
        )
        assert user.get_id() == "test-uuid-123"

    def test_user_is_active_true(self):
        """User.is_active should return True when active=True."""
        user = User(
            user_id="test-uuid",
            email="test@example.com",
            password_hash="hash",
            display_name=None,
            created_at=datetime.now(timezone.utc),
            last_login=None,
            active=True,
        )
        assert user.is_active is True

    def test_user_is_active_false(self):
        """User.is_active should return False when active=False."""
        user = User(
            user_id="test-uuid",
            email="test@example.com",
            password_hash="hash",
            display_name=None,
            created_at=datetime.now(timezone.utc),
            last_login=None,
            active=False,
        )
        assert user.is_active is False


class TestUserRepository:
    """Tests for UserRepository with mocked BigQuery."""

    @pytest.fixture
    def mock_bigquery_client(self):
        """Create a mock BigQuery client."""
        with patch("src.auth.user.BigQueryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.project_id = "test-project"
            mock_client.core_dataset = "core"
            mock_client_class.return_value = mock_client
            yield mock_client

    def test_get_by_email_found(self, mock_bigquery_client):
        """get_by_email should return User when found."""
        mock_row = MagicMock()
        mock_row.user_id = "user-123"
        mock_row.email = "test@example.com"
        mock_row.password_hash = "$2b$12$hash"
        mock_row.display_name = "Test"
        mock_row.created_at = datetime.now(timezone.utc)
        mock_row.last_login = None
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([mock_row])
        mock_bigquery_client.client.query.return_value.result.return_value = mock_result

        repo = UserRepository()
        user = repo.get_by_email("test@example.com")

        assert user is not None
        assert user.email == "test@example.com"
        assert user.user_id == "user-123"

    def test_get_by_email_not_found(self, mock_bigquery_client):
        """get_by_email should return None when not found."""
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([])
        mock_bigquery_client.client.query.return_value.result.return_value = mock_result

        repo = UserRepository()
        user = repo.get_by_email("notfound@example.com")

        assert user is None

    def test_create_user(self, mock_bigquery_client):
        """create should insert user and return User object."""
        mock_bigquery_client.client.query.return_value.result.return_value = None

        repo = UserRepository()
        user = repo.create(
            email="new@example.com",
            password_hash="$2b$12$newhash",
            display_name="New User",
        )

        assert user is not None
        assert user.email == "new@example.com"
        assert user.display_name == "New User"
        assert user.is_active is True
        mock_bigquery_client.client.query.assert_called_once()


class TestAuthRoutes:
    """Tests for authentication Flask routes."""

    @pytest.fixture
    def app(self):
        """Create test Flask app with auth routes."""
        from flask import Flask
        from flask_login import LoginManager
        from src.auth.routes import auth_bp

        app = Flask(__name__, template_folder="../templates")
        app.secret_key = "test-secret-key"
        app.config["TESTING"] = True

        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = "auth.login"

        @login_manager.user_loader
        def load_user(user_id):
            return None

        app.register_blueprint(auth_bp)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_login_page_accessible(self, client):
        """Login page should be accessible without auth."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_register_page_accessible(self, client):
        """Register page should be accessible without auth."""
        response = client.get("/register")
        assert response.status_code == 200
        assert b"Register" in response.data or b"Create Account" in response.data

    @patch("src.auth.routes.get_user_repo")
    def test_register_password_mismatch(self, mock_get_repo, client):
        """Registration should fail if passwords do not match."""
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = None
        mock_get_repo.return_value = mock_repo

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "password": "password123",
                "confirm_password": "different456",
                "display_name": "",
            },
            follow_redirects=True,
        )

        assert b"Passwords do not match" in response.data

    @patch("src.auth.routes.get_user_repo")
    def test_register_password_too_short(self, mock_get_repo, client):
        """Registration should fail if password is too short."""
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = None
        mock_get_repo.return_value = mock_repo

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "password": "short",
                "confirm_password": "short",
                "display_name": "",
            },
            follow_redirects=True,
        )

        assert b"at least 8 characters" in response.data

    @patch("src.auth.routes.get_user_repo")
    def test_login_invalid_credentials(self, mock_get_repo, client):
        """Login should fail with invalid credentials."""
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = None
        mock_get_repo.return_value = mock_repo

        response = client.post(
            "/login",
            data={
                "email": "notfound@example.com",
                "password": "anypassword",
            },
            follow_redirects=True,
        )

        assert b"Invalid email or password" in response.data
