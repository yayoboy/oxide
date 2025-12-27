"""
Simple user and API key database.

For production, migrate to SQLite or PostgreSQL.
"""
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from .models import User, UserInDB, APIKey
from .utils import get_password_hash


# Storage path
STORAGE_DIR = Path.home() / ".oxide"
USERS_FILE = STORAGE_DIR / "users.json"
API_KEYS_FILE = STORAGE_DIR / "api_keys.json"

# Ensure storage directory exists
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _load_users() -> Dict[str, dict]:
    """Load users from JSON file."""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_users(users: Dict[str, dict]):
    """Save users to JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def _load_api_keys() -> Dict[str, dict]:
    """Load API keys from JSON file."""
    if API_KEYS_FILE.exists():
        with open(API_KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_api_keys(keys: Dict[str, dict]):
    """Save API keys to JSON file."""
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)


def get_user(username: str) -> Optional[UserInDB]:
    """
    Get user by username.

    Args:
        username: Username to look up

    Returns:
        UserInDB object or None if not found
    """
    users = _load_users()
    user_data = users.get(username)

    if user_data:
        return UserInDB(**user_data)

    return None


def create_user(username: str, password: str, email: Optional[str] = None,
                full_name: Optional[str] = None, is_admin: bool = False) -> UserInDB:
    """
    Create a new user.

    Args:
        username: Username
        password: Plain text password (will be hashed)
        email: Optional email
        full_name: Optional full name
        is_admin: Whether user is admin

    Returns:
        Created UserInDB object
    """
    users = _load_users()

    if username in users:
        raise ValueError(f"User {username} already exists")

    hashed_password = get_password_hash(password)

    user_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "hashed_password": hashed_password,
        "disabled": False,
        "is_admin": is_admin
    }

    users[username] = user_data
    _save_users(users)

    return UserInDB(**user_data)


def update_user(username: str, **kwargs) -> Optional[UserInDB]:
    """
    Update user attributes.

    Args:
        username: Username to update
        **kwargs: Attributes to update

    Returns:
        Updated UserInDB object or None if user not found
    """
    users = _load_users()

    if username not in users:
        return None

    # Update allowed fields
    allowed_fields = {"email", "full_name", "disabled", "is_admin"}
    for key, value in kwargs.items():
        if key in allowed_fields:
            users[username][key] = value

    # Handle password change separately
    if "password" in kwargs:
        users[username]["hashed_password"] = get_password_hash(kwargs["password"])

    _save_users(users)

    return UserInDB(**users[username])


def create_api_key(username: str, name: str, key: str) -> APIKey:
    """
    Create a new API key for a user.

    Args:
        username: Username who owns the key
        name: Descriptive name for the key
        key: The API key string

    Returns:
        Created APIKey object
    """
    keys = _load_api_keys()

    if key in keys:
        raise ValueError("API key already exists")

    key_data = {
        "key": key,
        "name": name,
        "username": username,
        "created_at": datetime.utcnow().isoformat(),
        "last_used": None,
        "disabled": False
    }

    keys[key] = key_data
    _save_api_keys(keys)

    return APIKey(**key_data)


def get_api_key(key: str) -> Optional[APIKey]:
    """
    Get API key by key string.

    Args:
        key: API key string

    Returns:
        APIKey object or None if not found
    """
    keys = _load_api_keys()
    key_data = keys.get(key)

    if key_data:
        # Update last_used timestamp
        key_data["last_used"] = datetime.utcnow().isoformat()
        keys[key] = key_data
        _save_api_keys(keys)

        return APIKey(**key_data)

    return None


def revoke_api_key(key: str) -> bool:
    """
    Revoke (disable) an API key.

    Args:
        key: API key to revoke

    Returns:
        True if revoked, False if not found
    """
    keys = _load_api_keys()

    if key in keys:
        keys[key]["disabled"] = True
        _save_api_keys(keys)
        return True

    return False


def initialize_default_user():
    """
    Initialize default admin user if no users exist.

    Default credentials:
    - Username: admin
    - Password: oxide_admin_2025
    """
    users = _load_users()

    if not users:
        print("No users found. Creating default admin user...")
        create_user(
            username="admin",
            password="oxide_admin_2025",
            email="admin@oxide.local",
            full_name="Administrator",
            is_admin=True
        )
        print("✓ Default admin user created:")
        print("  Username: admin")
        print("  Password: oxide_admin_2025")
        print("  ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
