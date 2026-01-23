"""Authentication utilities."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        bcrypt hash string
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: bcrypt hash to check against

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
