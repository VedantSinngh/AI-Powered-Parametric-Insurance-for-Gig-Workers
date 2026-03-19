"""
GridGuard AI — Admin Analytics Router
Partner management + analytics summary + loss ratio
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.partner import Partner
from app.models.policy import Policy
from app.models.payout import Payout
from app.models.fraud_flag import FraudFlag
from app.models.grid_event import GridEvent
from app.core.dependencies import admin_only
from app.core.websocket_manager import manager

import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/partners")
async def list_partners(
    city: str | None = Query(None),
    risk_tier: str | None = Query(None),
    is_active: bool | None = Query(None, alias="status"),
    search: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: Partner = Depends(admin_only),
):
    """List partners with filters (admin only)."""
    from app.database import get_database

    db = get_database()

    match_filter: dict = {}
    if city:
        match_filter["city"] = city
    if risk_tier:
        match_filter["risk_tier"] = risk_tier
    if is_active is not None:
        match_filter["is_active"] = is_active
    if search:
        match_filter["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    pipeline = [
        {"$match": match_filter},
        {"$sort": {"created_at": -1}},
        {"$skip": offset},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "policies",
                "let": {"pid": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$partner_id", "$$pid"]},
                            "status": "active",
                        }
                    },
                    {"$sort": {"week_start": -1}},
                    {"$limit": 1},
                ],
                "as": "current_policy",
            }
        },
        {
            "$lookup": {
                "from": "payouts",
                "let": {"pid": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$partner_id", "$$pid"]},
                        }
                    },
                    {"$sort": {"created_at": -1}},
                    {"$limit": 1},
                ],
                "as": "last_payout",
            }
        },
    ]

    results = await db["partners"].aggregate(pipeline).to_list(length=limit)
    total = await db["partners"].count_documents(match_filter)

    return {
        "partners": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/partners/{partner_id}")
async def get_partner_detail(
    partner_id: str,
    _admin: Partner = Depends(admin_only),
):
    """Full partner profile + history (admin only)."""
    partner = await Partner.get(partner_id)
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    policies = (
        await Policy.find(Policy.partner_id == partner_id)
        .sort(-Policy.created_at)
        .limit(50)
        .to_list()
    )

    payouts = (
        await Payout.find(Payout.partner_id == partner_id)
        .sort(-Payout.created_at)
        .limit(50)
        .to_list()
    )

    flags = (
        await FraudFlag.find(FraudFlag.partner_id == partner_id)
        .sort(-FraudFlag.flagged_at)
        .limit(20)
        .to_list()
    )

    return {
        "partner": partner.dict(),
        "policies": [p.dict() for p in policies],
        "payouts": [p.dict() for p in payouts],
        "fraud_flags": [f.dict() for f in flags],
    }


@router.patch("/partners/{partner_id}/suspend")
async def suspend_partner(
    partner_id: str,
    admin: Partner = Depends(admin_only),
):
    """Suspend a partner (admin only)."""
    partner = await Partner.get(partner_id)
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    partner.is_active = False
    partner.updated_at = datetime.utcnow()
    await partner.save()

    # Cancel active policy
    today = datetime.utcnow().strftime("%Y-%m-%d")
    active_policy = await Policy.find_one(
        Policy.partner_id == partner_id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )
    if active_policy:
        active_policy.status = "cancelled"
        await active_policy.save()

    # Notify partner
    try:
        await manager.publish_to_redis(f"ws:partner:{partner_id}", {
            "type": "account_suspended",
            "message": "Your account has been suspended by admin",
            "sound": "alert",
            "timestamp": datetime.utcnow().isoformat(),
        })

        await manager.publish_to_redis("ws:admin:feed", {
            "type": "partner_suspended",
            "partner_id": partner_id,
            "full_name": partner.full_name,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception:
        pass

    return {"status": "suspended", "partner_id": partner_id}


@router.get("/analytics/summary")
async def get_analytics_summary(
    _admin: Partner = Depends(admin_only),
):
    """Get admin analytics summary via aggregation pipeline."""
    from app.database import get_database

    db = get_database()
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active partners count
    active_partners = await db["partners"].count_documents({"is_active": True})

    # Payouts today
    payouts_today = await db["payouts"].aggregate([
        {"$match": {"created_at": {"$gte": today_start}, "status": "paid"}},
        {
            "$group": {
                "_id": None,
                "total_amount": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
    ]).to_list(length=1)

    payouts_today_amount = payouts_today[0]["total_amount"] if payouts_today else 0
    payouts_today_count = payouts_today[0]["count"] if payouts_today else 0

    # Loss ratio 30d
    payouts_30d = await db["payouts"].aggregate([
        {"$match": {"created_at": {"$gte": thirty_days_ago}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(length=1)

    premiums_30d = await db["policies"].aggregate([
        {
            "$match": {
                "created_at": {"$gte": thirty_days_ago},
                "status": {"$in": ["active", "expired"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$premium_amount"}}},
    ]).to_list(length=1)

    total_payouts = payouts_30d[0]["total"] if payouts_30d else 0
    total_premiums = premiums_30d[0]["total"] if premiums_30d else 1
    loss_ratio = round(total_payouts / max(total_premiums, 1), 4)

    # Fraud flags pending
    fraud_pending = await db["fraud_flags"].count_documents({"status": "pending"})

    # Premium collected this week
    premium_week = await db["policies"].aggregate([
        {
            "$match": {
                "deducted_at": {"$gte": week_start},
                "status": {"$in": ["active", "expired"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$premium_amount"}}},
    ]).to_list(length=1)

    premium_collected = premium_week[0]["total"] if premium_week else 0

    # Top disrupted zones
    top_zones = await db["grid_events"].aggregate([
        {"$match": {"resolved_at": None}},
        {
            "$group": {
                "_id": "$h3_cell",
                "event_count": {"$sum": 1},
                "avg_severity": {"$avg": "$severity"},
                "city": {"$first": "$city"},
            }
        },
        {"$sort": {"event_count": -1}},
        {"$limit": 10},
    ]).to_list(length=10)

    # System health
    system_health = {
        "ws_connections": manager.get_connection_count(),
        "redis_ping_ms": -1,
        "db_ping_ms": -1,
    }

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        start = datetime.utcnow()
        await r.ping()
        system_health["redis_ping_ms"] = int(
            (datetime.utcnow() - start).total_seconds() * 1000
        )
        await r.aclose()
    except Exception:
        pass

    try:
        start = datetime.utcnow()
        await db.command("ping")
        system_health["db_ping_ms"] = int(
            (datetime.utcnow() - start).total_seconds() * 1000
        )
    except Exception:
        pass

    return {
        "active_partners": active_partners,
        "payouts_today_amount": payouts_today_amount,
        "payouts_today_count": payouts_today_count,
        "loss_ratio_30d": loss_ratio,
        "fraud_flags_pending": fraud_pending,
        "premium_collected_this_week": premium_collected,
        "top_disrupted_zones": top_zones,
        "system_health": system_health,
    }


@router.get("/analytics/loss-ratio")
async def get_loss_ratio(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    city: str | None = Query(None),
    granularity: str = Query("week"),
    _admin: Partner = Depends(admin_only),
):
    """Time-series loss ratio by day/week/month."""
    from app.database import get_database

    db = get_database()

    date_format_map = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%V",
        "month": "%Y-%m",
    }

    match_filter: dict = {"status": "paid"}
    if date_from:
        match_filter["created_at"] = {"$gte": datetime.fromisoformat(date_from)}
    if date_to:
        match_filter.setdefault("created_at", {})["$lte"] = datetime.fromisoformat(date_to)

    # Payouts time series
    payouts_series = await db["payouts"].aggregate([
        {"$match": match_filter},
        {
            "$group": {
                "_id": {"$dateToString": {"format": date_format_map.get(granularity, "%Y-%m-%d"), "date": "$created_at"}},
                "total_payouts": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]).to_list(length=365)

    return {
        "granularity": granularity,
        "data": payouts_series,
    }
