# Authentication Implementation Plan

## Overview

Add basic user registration and login to bgg-dash-viewer so only registered users can access the app modules.

**Approach:** Flask-Login with BigQuery as the user store, session managed via signed cookies.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        bgg-dash-viewer                          │
├─────────────────────────────────────────────────────────────────┤
│  Flask Server (app.server)                                      │
│  ├── /              → Landing page (public)                     │
│  ├── /login         → Login form (public)                       │
│  ├── /register      → Registration form (public)                │
│  ├── /logout        → Logout action                             │
│  └── /app/*         → Dash app (PROTECTED - requires login)     │
├─────────────────────────────────────────────────────────────────┤
│  Session: Flask signed cookie (no server-side storage needed)   │
├─────────────────────────────────────────────────────────────────┤
│  User Store: BigQuery `core.users` table                        │
│  (Only queried at login/register, not on every request)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. BigQuery Users Table

**Location:** `bgg-data-warehouse/terraform/auth.tf` (new file)

```hcl
resource "google_bigquery_table" "users" {
  dataset_id          = google_bigquery_dataset.bgg_data.dataset_id
  table_id            = "users"
  project             = var.project_id
  description         = "Application users for bgg-dash-viewer"
  deletion_protection = true

  schema = jsonencode([
    {
      name = "user_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "UUID primary key"
    },
    {
      name = "email"
      type = "STRING"
      mode = "REQUIRED"
      description = "User email (unique)"
    },
    {
      name = "password_hash"
      type = "STRING"
      mode = "REQUIRED"
      description = "bcrypt password hash"
    },
    {
      name = "display_name"
      type = "STRING"
      mode = "NULLABLE"
      description = "Optional display name"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "Account creation timestamp"
    },
    {
      name = "last_login"
      type = "TIMESTAMP"
      mode = "NULLABLE"
      description = "Last successful login"
    },
    {
      name = "is_active"
      type = "BOOLEAN"
      mode = "REQUIRED"
      description = "Account active status"
    }
  ])
}
```

**Alternative:** Create table manually or via Python script if you don't want to modify the warehouse terraform.

---

### 2. New Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "flask-login>=0.6.3",
    "bcrypt>=4.1.0",
]
```

---

### 3. New Files in bgg-dash-viewer

```text
src/
├── auth/
│   ├── __init__.py         # Export auth components
│   ├── user.py             # User class and BigQuery queries
│   ├── routes.py           # Flask routes for login/register/logout
│   └── utils.py            # Password hashing, decorators
├── layouts/
│   ├── login.py            # Login page layout
│   └── register.py         # Registration page layout
├── templates/
│   ├── login.html          # Login form template
│   └── register.html       # Register form template
```

---

### 4. Implementation Details

#### 4.1 User Model (`src/auth/user.py`)

```python
"""User model and BigQuery operations."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from flask_login import UserMixin
from google.cloud import bigquery

from src.data.bigquery_client import get_bigquery_client


@dataclass
class User(UserMixin):
    """User model for Flask-Login."""

    user_id: str
    email: str
    password_hash: str
    display_name: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool

    def get_id(self) -> str:
        """Return user ID for Flask-Login."""
        return self.user_id


class UserRepository:
    """BigQuery operations for users."""

    def __init__(self):
        self.client = get_bigquery_client()
        self.table = f"{self.client.project_id}.core.users"

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Load user by ID."""
        query = f"""
        SELECT user_id, email, password_hash, display_name,
               created_at, last_login, is_active
        FROM `{self.table}`
        WHERE user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        results = self.client.client.query(query, job_config=job_config).result()
        row = next(iter(results), None)
        return self._row_to_user(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        """Load user by email."""
        query = f"""
        SELECT user_id, email, password_hash, display_name,
               created_at, last_login, is_active
        FROM `{self.table}`
        WHERE LOWER(email) = LOWER(@email)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("email", "STRING", email)
            ]
        )
        results = self.client.client.query(query, job_config=job_config).result()
        row = next(iter(results), None)
        return self._row_to_user(row) if row else None

    def create(self, email: str, password_hash: str, display_name: str = None) -> User:
        """Create a new user."""
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
        self.client.client.query(query, job_config=job_config).result()

        return User(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            created_at=now,
            last_login=None,
            is_active=True,
        )

    def update_last_login(self, user_id: str) -> None:
        """Update last login timestamp."""
        query = f"""
        UPDATE `{self.table}`
        SET last_login = CURRENT_TIMESTAMP()
        WHERE user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        self.client.client.query(query, job_config=job_config).result()

    def _row_to_user(self, row) -> User:
        """Convert BigQuery row to User object."""
        return User(
            user_id=row.user_id,
            email=row.email,
            password_hash=row.password_hash,
            display_name=row.display_name,
            created_at=row.created_at,
            last_login=row.last_login,
            is_active=row.is_active,
        )
```

#### 4.2 Password Utilities (`src/auth/utils.py`)

```python
"""Authentication utilities."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
```

#### 4.3 Flask Routes (`src/auth/routes.py`)

```python
"""Authentication routes."""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from src.auth.user import UserRepository
from src.auth.utils import hash_password, verify_password

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, template_folder="../templates")

user_repo = UserRepository()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and handler."""
    if current_user.is_authenticated:
        return redirect("/app/")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = user_repo.get_by_email(email)

        if user and user.is_active and verify_password(password, user.password_hash):
            login_user(user)
            user_repo.update_last_login(user.user_id)
            logger.info(f"User logged in: {email}")

            next_page = request.args.get("next", "/app/")
            return redirect(next_page)
        else:
            flash("Invalid email or password", "error")
            logger.warning(f"Failed login attempt for: {email}")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration page and handler."""
    if current_user.is_authenticated:
        return redirect("/app/")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        display_name = request.form.get("display_name", "").strip() or None

        # Validation
        errors = []
        if not email:
            errors.append("Email is required")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if password != confirm_password:
            errors.append("Passwords do not match")
        if user_repo.get_by_email(email):
            errors.append("Email already registered")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            password_hash = hash_password(password)
            user = user_repo.create(email, password_hash, display_name)
            login_user(user)
            logger.info(f"New user registered: {email}")
            return redirect("/app/")

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout handler."""
    logout_user()
    return redirect("/")
```

#### 4.4 Integration in `dash_app.py`

```python
# Add these imports at the top
from flask_login import LoginManager
from src.auth.routes import auth_bp
from src.auth.user import UserRepository

# After app initialization, add:

# Configure Flask session secret key (required for signed cookies)
app.server.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app.server)
login_manager.login_view = "auth.login"

user_repo = UserRepository()

@login_manager.user_loader
def load_user(user_id: str):
    """Load user for Flask-Login."""
    return user_repo.get_by_id(user_id)

# Register auth blueprint
app.server.register_blueprint(auth_bp)

# Protect Dash routes
@app.server.before_request
def require_login():
    """Require login for all /app/ routes."""
    from flask import request
    from flask_login import current_user

    # Allow static assets and public routes
    public_paths = ["/", "/login", "/register", "/static", "/_dash", "/assets"]

    if request.path.startswith("/app/"):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
```

---

### 5. HTML Templates

#### 5.1 Login Template (`templates/login.html`)

```html
<!DOCTYPE html>
<html data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Board Game Data Explorer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark">
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-md-4">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h2 class="card-title text-center mb-4">Login</h2>

                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ 'danger' if category == 'error' else 'info' }}">
                                        {{ message }}
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}

                        <form method="POST">
                            <div class="mb-3">
                                <label for="email" class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" name="email" required>
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">Password</label>
                                <input type="password" class="form-control" id="password" name="password" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Login</button>
                        </form>

                        <p class="text-center mt-3">
                            Don't have an account? <a href="/register">Register</a>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

#### 5.2 Register Template (`templates/register.html`)

```html
<!DOCTYPE html>
<html data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - Board Game Data Explorer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark">
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-md-4">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h2 class="card-title text-center mb-4">Register</h2>

                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ 'danger' if category == 'error' else 'info' }}">
                                        {{ message }}
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}

                        <form method="POST">
                            <div class="mb-3">
                                <label for="email" class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" name="email" required>
                            </div>
                            <div class="mb-3">
                                <label for="display_name" class="form-label">Display Name (optional)</label>
                                <input type="text" class="form-control" id="display_name" name="display_name">
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">Password</label>
                                <input type="password" class="form-control" id="password" name="password"
                                       minlength="8" required>
                                <div class="form-text">At least 8 characters</div>
                            </div>
                            <div class="mb-3">
                                <label for="confirm_password" class="form-label">Confirm Password</label>
                                <input type="password" class="form-control" id="confirm_password"
                                       name="confirm_password" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Register</button>
                        </form>

                        <p class="text-center mt-3">
                            Already have an account? <a href="/login">Login</a>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

---

## Environment Variables

Add to `.env`:

```bash
# Auth configuration
SECRET_KEY=generate-a-real-secret-key-here  # Required for session cookies
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Implementation Checklist

### Phase 1: Infrastructure
- [ ] Create BigQuery `users` table (Terraform or manual)
- [ ] Add `flask-login` and `bcrypt` to dependencies
- [ ] Add `SECRET_KEY` to environment config

### Phase 2: Backend
- [ ] Create `src/auth/` module
- [ ] Implement `User` model and `UserRepository`
- [ ] Implement password hashing utilities
- [ ] Create Flask routes for login/register/logout

### Phase 3: Frontend
- [ ] Create `login.html` template
- [ ] Create `register.html` template
- [ ] Style templates to match app theme

### Phase 4: Integration
- [ ] Initialize Flask-Login in `dash_app.py`
- [ ] Register auth blueprint
- [ ] Add `before_request` protection for `/app/*` routes
- [ ] Test login flow end-to-end

### Phase 5: Polish
- [ ] Add "logout" link to app header
- [ ] Show current user in header
- [ ] Handle edge cases (expired sessions, etc.)
- [ ] Add rate limiting for login attempts (optional)

---

## Security Considerations

1. **Password Storage:** bcrypt with automatic salt
2. **Session Security:** Flask signed cookies (cryptographically signed, not encrypted)
3. **HTTPS:** Required in production (Cloud Run handles this)
4. **Rate Limiting:** Consider adding for login attempts
5. **CSRF:** Flask-WTF can be added if needed (forms are simple enough without)

---

## Future Enhancements (Not in Scope)

- Password reset via email
- OAuth (Google login)
- User roles/permissions
- Session timeout configuration
- Two-factor authentication
- Audit logging

---

## Testing

```python
# tests/test_auth.py

def test_password_hashing():
    from src.auth.utils import hash_password, verify_password

    password = "testpassword123"
    hashed = hash_password(password)

    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_user_creation():
    # Would need test BigQuery dataset or mocking
    pass
```

---

## Notes

- BigQuery is only queried at login/register time, not on every request
- Session data lives in signed cookies - no server-side session storage needed
- This is intentionally simple - no email verification, no password reset
- Works with Cloud Run because there's no server-side state to persist
