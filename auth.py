"""
auth.py — SentiVox Authentication & Access Control Layer

Features:
- Password hashing with passlib/bcrypt
- JWT access & refresh token creation/verification
- FastAPI dependency guards: get_current_user, require_role
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db, User

# ─── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "sentivox-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ─── Password Hashing ────────────────────────────────────────────────────────

import bcrypt as _bcrypt

security_scheme = HTTPBearer(auto_error=False)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    password_bytes = plain_password.encode("utf-8")
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ─── JWT Token Operations ────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str, role: str) -> str:
    """Create a JWT access token with 30-minute expiry."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a JWT refresh token with 7-day expiry."""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


# ─── FastAPI Dependency Guards ────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency: Extract JWT from Authorization header, decode it,
    and return the authenticated User ORM object.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token."
        )

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required."
        )

    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated."
        )

    return user


def require_role(allowed_roles: list):
    """
    Factory function returning a FastAPI dependency that checks if the
    current user's role is in the allowed_roles list.

    Usage: Depends(require_role(["ADMIN"]))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}. Your role: {current_user.role}"
            )
        return current_user

    return role_checker
