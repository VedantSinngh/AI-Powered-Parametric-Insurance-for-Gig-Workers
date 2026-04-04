"""
GridGuard AI — Auth Router
POST /auth/register, POST /auth/verify-otp,
POST /auth/refresh, GET /auth/me
"""

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, status
import h3

from app.models.partner import Partner
from app.models.otp_session import OTPSession
from app.models.wallet_transaction import WalletTransaction
from app.models.policy import Policy
from app.config import settings
from app.schemas.schemas import (
    RegisterRequest,
    RegisterResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    AdminRequestOTPRequest,
    AdminRequestOTPResponse,
    RefreshTokenRequest,
    UpdateUpiRequest,
    UpdatePreferencesRequest,
    TokenResponse,
    PartnerWithPolicy,
    PartnerProfile,
)
from app.utils.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.utils.email_otp import generate_otp, hash_otp, verify_otp, send_otp_email
from app.core.dependencies import get_current_partner
from app.core.websocket_manager import manager
from app.models.payout import Payout
from app.models.grid_event import GridEvent

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


def get_admin_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in settings.ADMIN_EMAILS.split(",")
        if email.strip()
    }


async def _refresh_primary_zone_from_activity(partner: Partner) -> Partner:
    """Sync partner primary zone to their most serviced H3 area from recent logs."""
    from app.database import get_database

    db = get_database()
    lookback_start = datetime.utcnow() - timedelta(days=14)

    pipeline = [
        {
            "$match": {
                "partner_id": partner.id,
                "logged_at": {"$gte": lookback_start},
            }
        },
        {
            "$group": {
                "_id": "$h3_cell",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 1},
    ]

    cursor = await db["partner_activity_logs"].aggregate(pipeline)
    top_zone = await cursor.to_list(length=1)
    if not top_zone:
        return partner

    recent_logs = await db["partner_activity_logs"].count_documents({
        "partner_id": partner.id,
        "logged_at": {"$gte": lookback_start},
    })
    if recent_logs < 8:
        return partner

    dominant_h3 = top_zone[0].get("_id")
    if dominant_h3 and dominant_h3 != partner.primary_zone_h3:
        partner.primary_zone_h3 = dominant_h3
        partner.updated_at = datetime.utcnow()
        await partner.save()

    return partner


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

    admin_emails = get_admin_emails()

    # Create partner (inactive until OTP verified)
    partner = Partner(
        device_id=req.device_id,
        full_name=req.full_name,
        email=req.email,
        city=city_lower,
        platform=req.platform,
        is_admin=req.email.lower() in admin_emails,
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


@router.post("/admin/request-otp", response_model=AdminRequestOTPResponse)
async def request_admin_otp(req: AdminRequestOTPRequest):
    """Start admin sign-in by sending an OTP to an approved admin email."""
    email = req.email.strip().lower()
    admin_emails = get_admin_emails()

    if email not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not authorized for admin access",
        )

    partner = await Partner.find_one(Partner.email == email)
    if partner is None:
        partner = Partner(
            device_id=f"DEV-ADMIN-{uuid4().hex[:8].upper()}",
            full_name="GridGuard Operations",
            email=email,
            city="bengaluru",
            platform="other",
            is_admin=True,
            is_active=True,
            mock_wallet_balance=100.0,
        )
        await partner.insert()
    elif not partner.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email exists but does not have admin role",
        )

    otp = generate_otp()
    otp_hashed = hash_otp(otp)

    otp_session = OTPSession(
        email=email,
        otp_hash=otp_hashed,
    )
    await otp_session.insert()

    await send_otp_email(email, otp, partner.full_name)

    return AdminRequestOTPResponse(otp_session_id=otp_session.id)


@router.post("/admin/verify-otp", response_model=VerifyOTPResponse)
async def verify_admin_otp(req: VerifyOTPRequest):
    """Complete admin sign-in by verifying OTP and issuing auth tokens."""
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

    if not verify_otp(req.otp_code, otp_session.otp_hash):
        otp_session.attempts += 1
        await otp_session.save()
        remaining = 3 - otp_session.attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OTP. {remaining} attempts remaining.",
        )

    otp_session.verified = True
    await otp_session.save()

    admin_emails = get_admin_emails()
    if otp_session.email.lower() not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not authorized for admin access",
        )

    partner = await Partner.find_one(Partner.email == otp_session.email.lower())
    if partner is None or not partner.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account not found",
        )

    if not partner.is_active:
        partner.is_active = True
        partner.updated_at = datetime.utcnow()
        await partner.save()

    access_token = create_access_token({"sub": partner.id})
    refresh_token = create_refresh_token({"sub": partner.id})

    return VerifyOTPResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        partner_id=partner.id,
        wallet_balance=partner.mock_wallet_balance,
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

    # Ensure a policy exists immediately so riders can see active weekly pricing.
    today_date = datetime.utcnow().date()
    week_start_date = today_date - timedelta(days=today_date.weekday())
    week_end_date = week_start_date + timedelta(days=6)
    week_start = week_start_date.isoformat()
    week_end = week_end_date.isoformat()

    existing_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= week_start,
        Policy.week_end >= week_start,
    )

    if existing_policy is None:
        from app.services.risk_engine import risk_engine

        try:
            features = await risk_engine.extract_features(
                partner.id,
                partner.primary_zone_h3 or "",
            )
            risk_score = risk_engine.predict_risk_score(features)
        except Exception:
            risk_score = 0.35

        _, premium_amount = risk_engine.score_to_premium(risk_score)
        partner.risk_tier = risk_engine.score_to_risk_tier(risk_score)
        partner.updated_at = datetime.utcnow()
        await partner.save()

        await Policy(
            partner_id=partner.id,
            week_start=week_start,
            week_end=week_end,
            premium_amount=premium_amount,
            risk_score=risk_score,
            status="active",
        ).insert()

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

    partner = await _refresh_primary_zone_from_activity(partner)

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


@router.patch("/me/upi")
async def update_upi(
    req: UpdateUpiRequest,
    partner: Partner = Depends(get_current_partner),
):
    """Update partner UPI handle for real Razorpay payouts."""
    upi_handle = req.upi_handle.strip().lower()
    if "@" not in upi_handle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UPI handle format",
        )

    partner.upi_handle = upi_handle
    # Reset cached fund account to ensure it matches latest UPI handle.
    partner.razorpay_fund_account_id = None
    partner.updated_at = datetime.utcnow()
    await partner.save()

    return {
        "status": "updated",
        "upi_handle": upi_handle,
    }


@router.patch("/me/preferences")
async def update_preferences(
    req: UpdatePreferencesRequest,
    partner: Partner = Depends(get_current_partner),
):
    """Persist rider UI preferences used by profile and dashboard."""
    if req.preferred_language is not None:
        partner.preferred_language = req.preferred_language

    if req.auto_premium_deduction is not None:
        partner.auto_premium_deduction = req.auto_premium_deduction

    partner.updated_at = datetime.utcnow()
    await partner.save()

    return {
        "status": "updated",
        "preferred_language": partner.preferred_language,
        "auto_premium_deduction": partner.auto_premium_deduction,
    }


@router.get("/notifications/summary")
async def get_notification_summary(
    partner: Partner = Depends(get_current_partner),
):
    """Return rider-facing live counts for header notification badges."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    processing_payouts = await Payout.find(
        Payout.partner_id == partner.id,
        Payout.status == "processing",
    ).count()

    paid_today = await Payout.find(
        Payout.partner_id == partner.id,
        Payout.status == "paid",
        Payout.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
    ).count()

    active_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )

    active_disruptions = 0
    if partner.primary_zone_h3:
        active_disruptions = await GridEvent.find(
            GridEvent.h3_cell == partner.primary_zone_h3,
            GridEvent.resolved_at == None,  # noqa: E711
        ).count()

    total = processing_payouts + paid_today + active_disruptions
    return {
        "total": total,
        "processing_payouts": processing_payouts,
        "paid_today": paid_today,
        "active_disruptions": active_disruptions,
        "has_active_policy": active_policy is not None,
    }
