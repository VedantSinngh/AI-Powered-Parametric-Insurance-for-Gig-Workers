"""
GridGuard AI — Auth Dependencies & Middleware
JWT auth, admin auth, internal API key auth, and rate limiting.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.database import get_db
from app.models.partner import Partner

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

# ── Rate Limiter ──
limiter = Limiter(key_func=get_remote_address)

# ── Admin device IDs (in production, use a proper roles table) ──
ADMIN_DEVICE_IDS = {"admin_device_001", "admin_device_002"}


def create_access_token(partner_id: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.access_token_expire_days)
    )
    to_encode = {
        "sub": str(partner_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(partner_id: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {
        "sub": str(partner_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_partner(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Partner:
    """FastAPI dependency — extracts and validates the current partner from JWT."""
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    partner_id = payload.get("sub")
    if not partner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(Partner).where(Partner.id == UUID(partner_id)))
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner account is suspended",
        )

    return partner


async def get_admin_partner(
    partner: Partner = Depends(get_current_partner),
) -> Partner:
    """FastAPI dependency — ensures the current partner is an admin."""
    if partner.device_id not in ADMIN_DEVICE_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return partner


async def verify_internal_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> bool:
    """FastAPI dependency — validates internal API key for service-to-service calls."""
    if x_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return True
