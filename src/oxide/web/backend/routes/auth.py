"""
Authentication routes - login, logout, user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import (
    LoginRequest,
    Token,
    User,
    create_access_token,
    verify_password,
    get_user,
    get_current_user,
    require_admin,
    create_user as db_create_user,
    create_api_key as db_create_api_key,
    generate_api_key,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: Request, credentials: LoginRequest):
    """
    Authenticate user and return JWT token.

    Rate limited to 5 attempts per minute to prevent brute force attacks.

    Args:
        request: FastAPI request (for rate limiting)
        credentials: Username and password

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user from database
    user = get_user(credentials.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint (client-side token removal).

    Note: JWTs are stateless, so actual logout happens client-side
    by removing the token. This endpoint exists for consistency.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    return {
        "message": "Successfully logged out",
        "user": current_user.username
    }


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User object without password
    """
    return current_user


@router.post("/users", response_model=User)
async def create_user(
    username: str,
    password: str,
    email: str = None,
    full_name: str = None,
    is_admin: bool = False,
    admin_user: User = Depends(require_admin)
):
    """
    Create a new user (admin only).

    Args:
        username: Username for new user
        password: Password for new user
        email: Optional email
        full_name: Optional full name
        is_admin: Whether user should be admin
        admin_user: Current admin user

    Returns:
        Created user object

    Raises:
        HTTPException: If user already exists
    """
    try:
        user = db_create_user(
            username=username,
            password=password,
            email=email,
            full_name=full_name,
            is_admin=is_admin
        )

        # Return user without password
        return User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            is_admin=user.is_admin
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/api-keys")
@limiter.limit("10/hour")  # Max 10 API keys per hour
async def create_api_key(
    request: Request,
    name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new API key for current user.

    Rate limited to 10 keys per hour to prevent abuse.

    Args:
        request: FastAPI request (for rate limiting)
        name: Descriptive name for the API key
        current_user: Current authenticated user

    Returns:
        Created API key

    Note:
        The full API key is only shown once during creation.
        Store it securely!
    """
    api_key = generate_api_key()

    key_data = db_create_api_key(
        username=current_user.username,
        name=name,
        key=api_key
    )

    return {
        "key": api_key,
        "name": key_data.name,
        "created_at": key_data.created_at,
        "message": "⚠️ Store this key securely. It will not be shown again!"
    }
