"""
GridGuard AI — JWT Token Handler
HS256 token creation and verification using python-jose
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from app.config import settings


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta
        or timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token (60-day expiry)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=60)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    })
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None
