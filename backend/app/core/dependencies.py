"""
GridGuard AI — FastAPI Dependencies
Auth guards: get_current_partner, admin_only, internal_only
"""

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.models.partner import Partner
from app.utils.jwt_handler import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_partner(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Partner:
    """Decode JWT Bearer token and return the Partner document."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    partner_id = payload.get("sub")
    if not partner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    partner = await Partner.get(partner_id)
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    return partner


async def admin_only(
    partner: Partner = Depends(get_current_partner),
) -> Partner:
    """Require admin role or configured admin allowlist email."""
    admin_emails = {
        email.strip().lower()
        for email in settings.ADMIN_EMAILS.split(",")
        if email.strip()
    }
    if not partner.is_admin and partner.email.lower() not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return partner


async def internal_only(
    x_internal_key: str = Header(alias="X-Internal-Key"),
) -> bool:
    """Verify internal API key for service-to-service calls."""
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )
    return True
