"""
Middleware for authentication, rate limiting, and security.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Optional
import os

from .auth import decode_access_token, get_user, get_api_key


# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)


def get_auth_enabled() -> bool:
    """Check if authentication is enabled via environment variable."""
    return os.getenv("OXIDE_AUTH_ENABLED", "false").lower() == "true"


async def optional_auth_middleware(request: Request, call_next):
    """
    Optional authentication middleware.

    Only enforces auth if OXIDE_AUTH_ENABLED=true.
    Checks for JWT token or API key in headers.
    """
    # Skip auth if disabled
    if not get_auth_enabled():
        return await call_next(request)

    # Skip auth for public endpoints
    public_paths = [
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/auth/login",
        "/auth/logout",
        "/assets/",
    ]

    path = request.url.path
    if any(path.startswith(public) for public in public_paths):
        return await call_next(request)

    # Check for authentication
    user = None

    # Try Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if payload:
            username = payload.get("sub")
            if username:
                user = get_user(username)

    # Try API key
    if not user:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            key_data = get_api_key(api_key)
            if key_data and not key_data.disabled:
                user = get_user(key_data.username)

    # Require authentication
    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication required",
                "detail": "Please provide a valid JWT token or API key"
            }
        )

    # Check if user is disabled
    if user.disabled:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Account disabled",
                "detail": "Your account has been disabled"
            }
        )

    # Add user to request state
    request.state.user = user

    return await call_next(request)


def get_current_user_from_request(request: Request) -> Optional[dict]:
    """
    Get current user from request state.

    Returns None if auth is disabled or user not authenticated.
    """
    return getattr(request.state, "user", None)
