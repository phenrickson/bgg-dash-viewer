"""Authentication routes."""

import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from src.auth.user import UserRepository
from src.auth.utils import hash_password, verify_password

logger = logging.getLogger(__name__)

auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder="../../templates",
)

# Lazy-loaded repository
_user_repo: UserRepository | None = None


def get_user_repo() -> UserRepository:
    """Get or create UserRepository instance."""
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and handler."""
    if current_user.is_authenticated:
        return redirect("/app/")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user_repo = get_user_repo()
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

        user_repo = get_user_repo()

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
            hashed = hash_password(password)
            user = user_repo.create(email, hashed, display_name)
            if user:
                login_user(user)
                logger.info(f"New user registered: {email}")
                return redirect("/app/")
            else:
                flash("Registration failed. Please try again.", "error")

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout handler."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect("/")
