"""User model and BigQuery operations."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from flask_login import UserMixin
from google.cloud import bigquery

from src.data.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


class User(UserMixin):
    """User model for Flask-Login."""

    def __init__(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        display_name: Optional[str],
        created_at: datetime,
        last_login: Optional[datetime],
        active: bool,
    ):
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.display_name = display_name
        self.created_at = created_at
        self.last_login = last_login
        self._active = active

    def get_id(self) -> str:
        """Return user ID for Flask-Login."""
        return self.user_id

    @property
    def is_active(self) -> bool:
        """Return whether user is active."""
        return self._active


class UserRepository:
    """BigQuery operations for users."""

    def __init__(self):
        """Initialize repository with BigQuery client."""
        self._client: Optional[BigQueryClient] = None

    @property
    def client(self) -> BigQueryClient:
        """Lazy-load BigQuery client."""
        if self._client is None:
            self._client = BigQueryClient()
        return self._client

    @property
    def table(self) -> str:
        """Get fully qualified table name."""
        return f"{self.client.project_id}.{self.client.core_dataset}.users"

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Load user by ID.

        Args:
            user_id: User's UUID

        Returns:
            User object or None if not found
        """
        query = f"""
        SELECT user_id, email, password_hash, display_name,
               created_at, last_login, is_active
        FROM `{self.table}`
        WHERE user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        try:
            results = self.client.client.query(query, job_config=job_config).result()
            row = next(iter(results), None)
            return self._row_to_user(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by ID: {e}")
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """Load user by email (case-insensitive).

        Args:
            email: User's email address

        Returns:
            User object or None if not found
        """
        query = f"""
        SELECT user_id, email, password_hash, display_name,
               created_at, last_login, is_active
        FROM `{self.table}`
        WHERE LOWER(email) = LOWER(@email)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("email", "STRING", email)]
        )
        try:
            results = self.client.client.query(query, job_config=job_config).result()
            row = next(iter(results), None)
            return self._row_to_user(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None

    def create(
        self, email: str, password_hash: str, display_name: Optional[str] = None
    ) -> Optional[User]:
        """Create a new user.

        Args:
            email: User's email address
            password_hash: bcrypt hashed password
            display_name: Optional display name

        Returns:
            Created User object or None on failure
        """
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        query = f"""
        INSERT INTO `{self.table}`
        (user_id, email, password_hash, display_name, created_at, is_active)
        VALUES (@user_id, @email, @password_hash, @display_name, @created_at, TRUE)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("email", "STRING", email),
                bigquery.ScalarQueryParameter("password_hash", "STRING", password_hash),
                bigquery.ScalarQueryParameter("display_name", "STRING", display_name),
                bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", now),
            ]
        )
        try:
            self.client.client.query(query, job_config=job_config).result()
            logger.info(f"Created new user: {email}")
            return User(
                user_id=user_id,
                email=email,
                password_hash=password_hash,
                display_name=display_name,
                created_at=now,
                last_login=None,
                active=True,
            )
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def update_last_login(self, user_id: str) -> bool:
        """Update last login timestamp.

        Args:
            user_id: User's UUID

        Returns:
            True on success, False on failure
        """
        query = f"""
        UPDATE `{self.table}`
        SET last_login = CURRENT_TIMESTAMP()
        WHERE user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        try:
            self.client.client.query(query, job_config=job_config).result()
            return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    def _row_to_user(self, row) -> User:
        """Convert BigQuery row to User object.

        Args:
            row: BigQuery row

        Returns:
            User object
        """
        return User(
            user_id=row.user_id,
            email=row.email,
            password_hash=row.password_hash,
            display_name=row.display_name,
            created_at=row.created_at,
            last_login=row.last_login,
            active=row.is_active,
        )
