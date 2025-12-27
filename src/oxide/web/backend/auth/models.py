"""
Authentication data models.
"""
from pydantic import BaseModel, Field
from typing import Optional


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Data stored in JWT token"""
    username: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    """Login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class User(BaseModel):
    """User model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    is_admin: bool = False


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class APIKey(BaseModel):
    """API Key model"""
    key: str
    name: str
    username: str  # Owner of the API key
    created_at: str
    last_used: Optional[str] = None
    disabled: bool = False
