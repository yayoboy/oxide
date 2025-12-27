"""
Authentication module for Oxide API.
"""
from .utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    generate_api_key,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .models import Token, TokenData, LoginRequest, User, UserInDB, APIKey
from .dependencies import (
    get_current_user,
    get_current_user_from_token,
    get_current_user_from_api_key,
    require_admin
)
from .database import (
    get_user,
    create_user,
    update_user,
    create_api_key,
    get_api_key,
    revoke_api_key,
    initialize_default_user
)

__all__ = [
    # Utils
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "generate_api_key",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    # Models
    "Token",
    "TokenData",
    "LoginRequest",
    "User",
    "UserInDB",
    "APIKey",
    # Dependencies
    "get_current_user",
    "get_current_user_from_token",
    "get_current_user_from_api_key",
    "require_admin",
    # Database
    "get_user",
    "create_user",
    "update_user",
    "create_api_key",
    "get_api_key",
    "revoke_api_key",
    "initialize_default_user",
]
