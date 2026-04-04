"""
GridGuard AI — Admin Analytics Router
Partner management + analytics summary + loss ratio
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

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

VALID_DATA_MODES = {"real", "demo"}
DATA_MODE_REDIS_KEY = "grid:data_mode"


class CreatePartnerRequest(BaseModel):
    full_name: str
    email: str
    city: str
    platform: str
    device_id: str
    upi_handle: str | None = None
    preferred_language: str = "en"


class UpdateDataModeRequest(BaseModel):
    mode: str


def _normalize_data_mode(value: str | None) -> str:
    normalized = (value or "real").strip().lower()
    if normalized in VALID_DATA_MODES:
        return normalized
    return "real"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _clear_grid_cache(r: aioredis.Redis) -> int:
    keys: list[str] = []
    async for key in r.scan_iter(match="grid:*"):
        if key == DATA_MODE_REDIS_KEY:
            continue
        keys.append(key)

    if not keys:
        return 0

    return int(await r.delete(*keys))


async def _aggregate_to_list(db, collection: str, pipeline: list[dict], length: int):
    """Run an aggregate pipeline with AsyncMongoClient and materialize results."""
    cursor = await db[collection].aggregate(pipeline)
    return await cursor.to_list(length=length)


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

    results = await _aggregate_to_list(db, "partners", pipeline, limit)
    total = await db["partners"].count_documents(match_filter)

    return {
        "partners": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/partners/create")
async def create_partner(
    req: CreatePartnerRequest,
    _admin: Partner = Depends(admin_only),
):
    """Create partner account directly from admin console."""
    email = req.email.strip().lower()
    if "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )

    existing_email = await Partner.find_one(Partner.email == email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    existing_device = await Partner.find_one(Partner.device_id == req.device_id)
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already registered",
        )

    city = req.city.strip().lower()
    platform = req.platform.strip().lower()
    if platform not in {"zomato", "swiggy", "zepto", "blinkit", "other"}:
        platform = "other"

    preferred_language = req.preferred_language.strip().lower()
    if preferred_language not in {"en", "hi", "ta", "te"}:
        preferred_language = "en"

    partner = Partner(
        device_id=req.device_id,
        full_name=req.full_name.strip(),
        email=email,
        upi_handle=req.upi_handle.strip().lower() if req.upi_handle else None,
        city=city,
        platform=platform,
        preferred_language=preferred_language,
        is_active=True,
        onboarded_at=datetime.utcnow(),
    )
    await partner.insert()

    return {
        "status": "created",
        "partner": partner.dict(),
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
    payouts_today = await _aggregate_to_list(db, "payouts", [
        {"$match": {"created_at": {"$gte": today_start}, "status": "paid"}},
        {
            "$group": {
                "_id": None,
                "total_amount": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }
        },
    ], 1)

    payouts_today_amount = payouts_today[0]["total_amount"] if payouts_today else 0
    payouts_today_count = payouts_today[0]["count"] if payouts_today else 0

    # Loss ratio 30d
    payouts_30d = await _aggregate_to_list(db, "payouts", [
        {"$match": {"created_at": {"$gte": thirty_days_ago}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ], 1)

    premiums_30d = await _aggregate_to_list(db, "policies", [
        {
            "$match": {
                "created_at": {"$gte": thirty_days_ago},
                "status": {"$in": ["active", "expired"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$premium_amount"}}},
    ], 1)

    total_payouts = payouts_30d[0]["total"] if payouts_30d else 0
    total_premiums = premiums_30d[0]["total"] if premiums_30d else 1
    loss_ratio = round(total_payouts / max(total_premiums, 1), 4)
    net_profit_30d = round(float(total_premiums) - float(total_payouts), 2)
    profit_margin_30d = round(net_profit_30d / max(float(total_premiums), 1.0), 4)

    # Fraud flags pending
    fraud_pending = await db["fraud_flags"].count_documents({"status": "pending"})

    # Premium collected this week
    premium_week = await _aggregate_to_list(db, "policies", [
        {
            "$match": {
                "deducted_at": {"$gte": week_start},
                "status": {"$in": ["active", "expired"]},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$premium_amount"}}},
    ], 1)

    premium_collected = premium_week[0]["total"] if premium_week else 0

    # Top disrupted zones
    top_zones = await _aggregate_to_list(db, "grid_events", [
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
    ], 10)

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
        "net_profit_30d": net_profit_30d,
        "profit_margin_30d": profit_margin_30d,
        "fraud_flags_pending": fraud_pending,
        "premium_collected_this_week": premium_collected,
        "top_disrupted_zones": top_zones,
        "system_health": system_health,
    }


@router.get("/notifications/summary")
async def get_admin_notification_summary(
    _admin: Partner = Depends(admin_only),
):
    """Return admin-facing counts for header notification badge."""
    pending_fraud = await FraudFlag.find(FraudFlag.status == "pending").count()
    processing_payouts = await Payout.find(Payout.status == "processing").count()
    active_events = await GridEvent.find(GridEvent.resolved_at == None).count()  # noqa: E711

    total = pending_fraud + processing_payouts + active_events
    return {
        "total": total,
        "pending_fraud": pending_fraud,
        "processing_payouts": processing_payouts,
        "active_events": active_events,
    }


@router.get("/data-mode")
async def get_data_mode(
    _admin: Partner = Depends(admin_only),
):
    """Get active grid data mode used by workability/risk endpoints."""
    r = await _get_redis()
    configured = await r.get(DATA_MODE_REDIS_KEY)
    mode = _normalize_data_mode(configured or settings.GRID_DATA_MODE)
    await r.aclose()

    return {
        "mode": mode,
        "available_modes": sorted(VALID_DATA_MODES),
        "description": {
            "real": "Uses live external API ingested events and excludes manual demo events.",
            "demo": "Uses manual/demo events and excludes live feed events.",
        },
    }


@router.patch("/data-mode")
async def update_data_mode(
    req: UpdateDataModeRequest,
    admin: Partner = Depends(admin_only),
):
    """Switch global grid data mode between demo and real."""
    raw_mode = (req.mode or "").strip().lower()
    if raw_mode not in VALID_DATA_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mode must be one of: demo, real",
        )
    next_mode = raw_mode

    r = await _get_redis()
    await r.set(DATA_MODE_REDIS_KEY, next_mode)
    cleared_keys = await _clear_grid_cache(r)

    try:
        await manager.publish_to_redis("ws:admin:feed", {
            "type": "data_mode_changed",
            "mode": next_mode,
            "changed_by": admin.email,
            "cleared_cache_keys": cleared_keys,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception:
        pass

    await r.aclose()

    return {
        "status": "updated",
        "mode": next_mode,
        "cleared_cache_keys": cleared_keys,
    }


@router.get("/payouts/recent")
async def get_recent_payouts(
    city: str | None = Query(None),
    event_type: str | None = Query(None),
    payout_status: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: Partner = Depends(admin_only),
):
    """Paginated recent payouts enriched with partner + event details (admin only)."""
    from app.database import get_database

    db = get_database()

    pipeline: list[dict] = [
        {
            "$lookup": {
                "from": "partners",
                "localField": "partner_id",
                "foreignField": "_id",
                "as": "partner",
            }
        },
        {
            "$unwind": {
                "path": "$partner",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$lookup": {
                "from": "grid_events",
                "localField": "grid_event_id",
                "foreignField": "_id",
                "as": "grid_event",
            }
        },
        {
            "$unwind": {
                "path": "$grid_event",
                "preserveNullAndEmptyArrays": True,
            }
        },
    ]

    match_filter: dict = {}
    if payout_status:
        match_filter["status"] = payout_status

    normalized_city = city.lower() if city else None
    if normalized_city:
        match_filter["$or"] = [
            {"partner.city": normalized_city},
            {"grid_event.city": normalized_city},
        ]

    if event_type:
        match_filter["grid_event.event_type"] = event_type

    if search:
        search_regex = {"$regex": search, "$options": "i"}
        search_terms = [
            {"partner.full_name": search_regex},
            {"partner.email": search_regex},
            {"mock_reference": search_regex},
            {"provider_reference": search_regex},
            {"provider_payout_id": search_regex},
        ]
        if "$or" in match_filter:
            search_terms.extend(match_filter["$or"])
            del match_filter["$or"]
        match_filter["$or"] = search_terms

    if match_filter:
        pipeline.append({"$match": match_filter})

    pipeline.extend([
        {"$sort": {"created_at": -1}},
        {
            "$facet": {
                "data": [
                    {"$skip": offset},
                    {"$limit": limit},
                    {
                        "$project": {
                            "_id": 0,
                            "id": "$_id",
                            "partner_id": "$partner_id",
                            "partner_name": "$partner.full_name",
                            "city": {
                                "$ifNull": ["$grid_event.city", "$partner.city"],
                            },
                            "event_type": "$grid_event.event_type",
                            "h3_cell": "$grid_event.h3_cell",
                            "amount": "$amount",
                            "duration_hours": "$duration_hours",
                            "rate_per_hour": "$rate_per_hour",
                            "status": "$status",
                            "provider": "$provider",
                            "provider_status": "$provider_status",
                            "failure_reason": "$failure_reason",
                            "reference": "$mock_reference",
                            "created_at": "$created_at",
                        }
                    },
                ],
                "meta": [
                    {"$count": "total"},
                ],
            }
        },
    ])

    result = await _aggregate_to_list(db, "payouts", pipeline, 1)
    payload = result[0] if result else {"data": [], "meta": []}
    total = payload["meta"][0]["total"] if payload["meta"] else 0

    return {
        "payouts": payload["data"],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/analytics/loss-ratio")
async def get_loss_ratio(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    city: str | None = Query(None),
    granularity: str = Query("week"),
    _admin: Partner = Depends(admin_only),
):
    """Time-series payouts, premiums, and computed loss ratio by period."""
    from app.database import get_database

    db = get_database()

    date_format_map = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%V",
        "month": "%Y-%m",
    }

    date_filter_payouts: dict = {}
    date_filter_premiums: dict = {"$ne": None}
    try:
        if date_from:
            date_filter_payouts["$gte"] = datetime.fromisoformat(date_from)
            date_filter_premiums["$gte"] = datetime.fromisoformat(date_from)
        if date_to:
            date_filter_payouts["$lte"] = datetime.fromisoformat(date_to)
            date_filter_premiums["$lte"] = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from/date_to must be valid ISO datetime strings",
        )

    payout_pipeline = [
        {
            "$match": {
                "status": "paid",
                **({"created_at": date_filter_payouts} if date_filter_payouts else {}),
            }
        }
    ]
    if city:
        payout_pipeline.extend([
            {
                "$lookup": {
                    "from": "grid_events",
                    "localField": "grid_event_id",
                    "foreignField": "_id",
                    "as": "grid_event",
                }
            },
            {"$unwind": "$grid_event"},
            {"$match": {"grid_event.city": city.lower()}},
        ])
    payout_pipeline.extend([
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": date_format_map.get(granularity, "%Y-%m-%d"),
                        "date": "$created_at",
                    }
                },
                "total_payouts": {"$sum": "$amount"},
                "payout_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ])

    premium_pipeline = [
        {
            "$match": {
                "status": {"$in": ["active", "expired", "suspended", "cancelled"]},
                "deducted_at": date_filter_premiums,
            }
        }
    ]
    if city:
        premium_pipeline.extend([
            {
                "$lookup": {
                    "from": "partners",
                    "localField": "partner_id",
                    "foreignField": "_id",
                    "as": "partner",
                }
            },
            {"$unwind": "$partner"},
            {"$match": {"partner.city": city.lower()}},
        ])
    premium_pipeline.extend([
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": date_format_map.get(granularity, "%Y-%m-%d"),
                        "date": "$deducted_at",
                    }
                },
                "total_premiums": {"$sum": "$premium_amount"},
                "policy_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ])

    payouts_series = await _aggregate_to_list(db, "payouts", payout_pipeline, 365)
    premiums_series = await _aggregate_to_list(db, "policies", premium_pipeline, 365)

    merged: dict[str, dict] = {}
    for row in payouts_series:
        period = row["_id"]
        merged.setdefault(
            period,
            {
                "period": period,
                "total_payouts": 0.0,
                "total_premiums": 0.0,
                "payout_count": 0,
                "policy_count": 0,
            },
        )
        merged[period]["total_payouts"] = round(float(row.get("total_payouts", 0.0)), 2)
        merged[period]["payout_count"] = int(row.get("payout_count", 0))

    for row in premiums_series:
        period = row["_id"]
        merged.setdefault(
            period,
            {
                "period": period,
                "total_payouts": 0.0,
                "total_premiums": 0.0,
                "payout_count": 0,
                "policy_count": 0,
            },
        )
        merged[period]["total_premiums"] = round(float(row.get("total_premiums", 0.0)), 2)
        merged[period]["policy_count"] = int(row.get("policy_count", 0))

    data = []
    for period in sorted(merged.keys()):
        row = merged[period]
        premiums = row["total_premiums"]
        row["net_profit"] = round(row["total_premiums"] - row["total_payouts"], 2)
        row["loss_ratio"] = round(row["total_payouts"] / premiums, 4) if premiums > 0 else None
        row["profit_margin"] = round(row["net_profit"] / premiums, 4) if premiums > 0 else None
        data.append(row)

    return {
        "granularity": granularity,
        "city": city.lower() if city else None,
        "data": data,
    }
