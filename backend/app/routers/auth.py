"""
GridGuard AI — Auth Router
POST /auth/register, POST /auth/verify-otp,
POST /auth/refresh, GET /auth/me
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
import h3

from app.models.partner import Partner
from app.models.otp_session import OTPSession
from app.models.wallet_transaction import WalletTransaction
from app.schemas.schemas import (
    RegisterRequest,
    RegisterResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    RefreshTokenRequest,
    TokenResponse,
    PartnerWithPolicy,
    PartnerProfile,
)
from app.utils.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.utils.email_otp import generate_otp, hash_otp, verify_otp, send_otp_email
from app.core.dependencies import get_current_partner
from app.core.websocket_manager import manager

router = APIRouter(prefix="/auth", tags=["auth"])

# City centroids for H3 cell assignment
CITY_CENTROIDS = {
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
}


@router.post("/register", response_model=RegisterResponse)
async def register(req: RegisterRequest):
    """
    Register a new delivery partner.
    1. Check device_id + email uniqueness
    2. Generate & hash 6-digit OTP
    3. Store OTP session
    4. Send branded HTML email with OTP
    5. Create partner (is_active=False, ₹100 signup bonus)
    """
    # Check uniqueness
    existing_device = await Partner.find_one(Partner.device_id == req.device_id)
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already registered",
        )

    existing_email = await Partner.find_one(Partner.email == req.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate city
    city_lower = req.city.lower()
    if city_lower not in CITY_CENTROIDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"City must be one of: {', '.join(CITY_CENTROIDS.keys())}",
        )

    # Generate OTP
    otp = generate_otp()
    otp_hashed = hash_otp(otp)

    # Store OTP session
    otp_session = OTPSession(
        email=req.email,
        otp_hash=otp_hashed,
    )
    await otp_session.insert()

    # Create partner (inactive until OTP verified)
    partner = Partner(
        device_id=req.device_id,
        full_name=req.full_name,
        email=req.email,
        city=city_lower,
        platform=req.platform,
        is_active=False,
        mock_wallet_balance=100.0,
    )
    await partner.insert()

    # Send OTP email (non-blocking — log failure but don't block response)
    await send_otp_email(req.email, otp, req.full_name)

    return RegisterResponse(
        partner_id=partner.id,
        otp_session_id=otp_session.id,
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp_route(req: VerifyOTPRequest):
    """
    Verify OTP and activate partner account.
    1. Check attempts < 3
    2. bcrypt verify OTP
    3. Activate partner + set H3 zone
    4. Log signup bonus in wallet
    5. Publish admin event
    """
    otp_session = await OTPSession.get(req.otp_session_id)
    if otp_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OTP session not found or expired",
        )

    if otp_session.verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP already verified",
        )

    if otp_session.attempts >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum OTP attempts exceeded. Request a new code.",
        )

    # Verify OTP
    if not verify_otp(req.otp_code, otp_session.otp_hash):
        otp_session.attempts += 1
        await otp_session.save()
        remaining = 3 - otp_session.attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OTP. {remaining} attempts remaining.",
        )

    # Mark session verified
    otp_session.verified = True
    await otp_session.save()

    # Find and activate partner
    partner = await Partner.find_one(Partner.email == otp_session.email)
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found for this email",
        )

    # Set H3 zone from city centroid
    centroid = CITY_CENTROIDS.get(partner.city)
    if centroid:
        partner.primary_zone_h3 = h3.latlng_to_cell(centroid[0], centroid[1], 9)

    partner.is_active = True
    partner.onboarded_at = datetime.utcnow()
    partner.updated_at = datetime.utcnow()
    await partner.save()

    # Log signup bonus in wallet
    wallet_tx = WalletTransaction(
        partner_id=partner.id,
        type="credit",
        amount=100.0,
        reference="SIGNUP-BONUS",
        description="Welcome signup bonus",
        balance_after=100.0,
    )
    await wallet_tx.insert()

    # Publish to admin feed
    try:
        await manager.publish_to_redis("ws:admin:feed", {
            "type": "new_partner_onboarded",
            "partner_id": partner.id,
            "full_name": partner.full_name,
            "city": partner.city,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception:
        pass  # Non-critical

    # Generate tokens
    access_token = create_access_token({"sub": partner.id})
    refresh_token = create_refresh_token({"sub": partner.id})

    return VerifyOTPResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        partner_id=partner.id,
        wallet_balance=partner.mock_wallet_balance,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest):
    """Issue a new access token from a valid refresh token."""
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    partner_id = payload.get("sub")
    partner = await Partner.get(partner_id)
    if partner is None or not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Partner not found or suspended",
        )

    new_access_token = create_access_token({"sub": partner.id})
    return TokenResponse(access_token=new_access_token)


@router.get("/me", response_model=PartnerWithPolicy)
async def get_me(partner: Partner = Depends(get_current_partner)):
    """Return full partner profile + current active policy."""
    from app.models.policy import Policy

    # Find active policy for current week
    today = datetime.utcnow().strftime("%Y-%m-%d")
    active_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )

    return PartnerWithPolicy(
        partner=PartnerProfile(**partner.dict()),
        active_policy=active_policy.dict() if active_policy else None,
    )
