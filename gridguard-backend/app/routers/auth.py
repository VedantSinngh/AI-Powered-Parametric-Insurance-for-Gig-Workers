"""
GridGuard AI — Auth Router
Device-ID based registration with OTP verification, JWT tokens.
"""

import logging
import secrets
import random
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.partner import Partner, PlatformEnum
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.partner import PartnerProfile
from app.utils.dependencies import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_partner,
    limiter,
)
from app.utils.redis_client import store_otp, verify_otp
from app.utils.h3_helpers import gps_to_h3
from app.services.notification import send_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new partner.
    1. Validate device_id uniqueness
    2. Send OTP to phone_number via Twilio
    3. Create partner record with status=pending
    4. Return partner_id + otp_session_token
    """
    # Check device_id uniqueness
    existing = await db.execute(
        select(Partner).where(Partner.device_id == request.device_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already registered",
        )

    # Check phone uniqueness
    existing_phone = await db.execute(
        select(Partner).where(Partner.phone_number == request.phone_number)
    )
    if existing_phone.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )

    # Validate platform enum
    try:
        platform = PlatformEnum(request.platform)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid platform. Must be one of: {[e.value for e in PlatformEnum]}",
        )

    # Create partner record (pending activation)
    h3_cell = None
    if request.gps_lat and request.gps_lng:
        h3_cell = gps_to_h3(request.gps_lat, request.gps_lng)

    partner = Partner(
        device_id=request.device_id,
        full_name=request.full_name,
        phone_number=request.phone_number,
        city=request.city,
        platform=platform,
        primary_zone_h3=h3_cell,
        is_active=False,  # Pending OTP verification
    )
    db.add(partner)
    await db.flush()

    # Generate OTP and session token
    otp_code = f"{random.randint(1000, 9999)}"
    session_token = secrets.token_urlsafe(32)

    # Store OTP in Redis (5-min TTL)
    await store_otp(session_token, otp_code, str(partner.id))

    # Send OTP via SMS
    await send_sms(
        to=request.phone_number,
        message=f"Your GridGuard verification code is: {otp_code}. Valid for 5 minutes.",
    )

    logger.info(f"Partner registered: {partner.id}, OTP sent to {request.phone_number}")

    return RegisterResponse(
        partner_id=partner.id,
        otp_session_token=session_token,
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp_endpoint(
    request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and activate partner.
    Returns JWT access + refresh tokens.
    """
    # Verify OTP from Redis
    otp_data = await verify_otp(request.otp_session_token, request.otp_code)
    if not otp_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    partner_id = otp_data["partner_id"]

    # Activate partner
    result = await db.execute(select(Partner).where(Partner.id == UUID(partner_id)))
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    partner.is_active = True
    partner.onboarded_at = datetime.now(timezone.utc)
    await db.flush()

    # Create tokens
    access_token = create_access_token(partner_id)
    refresh_token = create_refresh_token(partner_id)

    logger.info(f"Partner verified and activated: {partner_id}")

    return VerifyOTPResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        partner_id=partner.id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh an access token using a valid refresh token."""
    payload = decode_token(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected refresh token",
        )

    partner_id = payload.get("sub")
    new_access_token = create_access_token(partner_id)

    return TokenResponse(access_token=new_access_token)


@router.get("/me", response_model=PartnerProfile)
async def get_me(partner: Partner = Depends(get_current_partner)):
    """Get the current authenticated partner's profile."""
    return PartnerProfile.model_validate(partner)
