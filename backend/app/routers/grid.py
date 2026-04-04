"""
GridGuard AI — Grid / Workability Router
Endpoints for workability scores, event ingestion, and management
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
import redis.asyncio as aioredis
import h3

from app.config import settings
from app.models.grid_event import GridEvent
from app.models.partner import Partner
from app.schemas.schemas import (
    GridEventIngest,
    GridEventResponse,
    WorkabilityResponse,
)
from app.services.workability import workability_service
from app.core.dependencies import get_current_partner, admin_only, internal_only
from app.core.websocket_manager import manager
from app.utils.h3_helpers import get_city_cells, h3_to_latlng

router = APIRouter(prefix="/grid", tags=["grid"])

VALID_DATA_MODES = {"real", "demo"}
DATA_MODE_REDIS_KEY = "grid:data_mode"


CITY_AREA_POINTS: dict[str, list[tuple[str, float, float]]] = {
    "bengaluru": [
        ("Koramangala", 12.9352, 77.6245),
        ("Indiranagar", 12.9719, 77.6412),
        ("Whitefield", 12.9698, 77.7499),
        ("Hebbal", 13.0358, 77.5970),
        ("Jayanagar", 12.9308, 77.5838),
        ("Electronic City", 12.8399, 77.6770),
        ("HSR Layout", 12.9116, 77.6474),
        ("Bellandur", 12.9250, 77.6762),
        ("Marathahalli", 12.9560, 77.7019),
        ("Rajajinagar", 12.9917, 77.5551),
        ("Yelahanka", 13.0990, 77.5963),
        ("Kengeri", 12.9056, 77.4820),
        ("Devanahalli", 13.2425, 77.7132),
        ("Hoskote", 13.0760, 77.7981),
    ],
    "mumbai": [
        ("Haji Ali", 18.9826, 72.8089),
        ("CST/Fort", 18.9398, 72.8355),
        ("Dadar", 19.0178, 72.8478),
        ("Bandra", 19.0544, 72.8406),
        ("Andheri", 19.1136, 72.8697),
        ("Worli", 19.0119, 72.8188),
        ("Powai", 19.1176, 72.9060),
        ("Chembur", 19.0522, 72.9005),
        ("Ghatkopar", 19.0800, 72.9080),
        ("Borivali", 19.2307, 72.8567),
        ("Thane", 19.2183, 72.9781),
        ("Vashi", 19.0760, 72.9980),
        ("Panvel", 18.9894, 73.1175),
        ("Mira Road", 19.2870, 72.8700),
        ("Kalyan", 19.2403, 73.1305),
    ],
    "chennai": [
        ("T Nagar", 13.0405, 80.2337),
        ("Anna Nagar", 13.0849, 80.2101),
        ("Velachery", 12.9791, 80.2209),
        ("Guindy", 13.0106, 80.2209),
        ("Adyar", 13.0012, 80.2565),
        ("Porur", 13.0382, 80.1565),
        ("Perambur", 13.1066, 80.2337),
        ("Ambattur", 13.1143, 80.1548),
        ("Tambaram", 12.9249, 80.1275),
        ("Avadi", 13.1143, 80.1015),
        ("Sholinganallur", 12.9007, 80.2279),
        ("Ennore", 13.2140, 80.3203),
        ("Poonamallee", 13.0480, 80.1082),
        ("Siruseri", 12.8352, 80.2276),
    ],
    "delhi": [
        ("Connaught Place", 28.6315, 77.2167),
        ("Karol Bagh", 28.6519, 77.1909),
        ("Dwarka", 28.5921, 77.0460),
        ("Rohini", 28.7495, 77.0565),
        ("Lajpat Nagar", 28.5677, 77.2433),
        ("Saket", 28.5245, 77.2066),
        ("Janakpuri", 28.6219, 77.0878),
        ("Pitampura", 28.6980, 77.1338),
        ("Vasant Kunj", 28.5273, 77.1544),
        ("Noida", 28.5355, 77.3910),
        ("Gurugram", 28.4595, 77.0266),
        ("Ghaziabad", 28.6692, 77.4538),
        ("Faridabad", 28.4089, 77.3178),
        ("Narela", 28.8526, 77.0929),
    ],
    "hyderabad": [
        ("Hitech City", 17.4435, 78.3772),
        ("Banjara Hills", 17.4126, 78.4347),
        ("Gachibowli", 17.4401, 78.3489),
        ("Secunderabad", 17.4399, 78.4983),
        ("Kukatpally", 17.4948, 78.3996),
        ("Miyapur", 17.4967, 78.3560),
        ("Ameerpet", 17.4374, 78.4482),
        ("Begumpet", 17.4446, 78.4636),
        ("LB Nagar", 17.3457, 78.5522),
        ("Uppal", 17.4058, 78.5591),
        ("Shamshabad", 17.2511, 78.4294),
        ("Patancheru", 17.5288, 78.2668),
        ("Medchal", 17.6290, 78.4818),
        ("Kompally", 17.5437, 78.4831),
    ],
    "pune": [
        ("Shivajinagar", 18.5314, 73.8446),
        ("Kothrud", 18.5074, 73.8077),
        ("Hadapsar", 18.5089, 73.9260),
        ("Viman Nagar", 18.5679, 73.9143),
        ("Hinjawadi", 18.5912, 73.7389),
        ("Baner", 18.5590, 73.7868),
        ("Aundh", 18.5594, 73.8077),
        ("Kharadi", 18.5519, 73.9425),
        ("Magarpatta", 18.5166, 73.9315),
        ("Pimpri", 18.6298, 73.7997),
        ("Wagholi", 18.5793, 73.9890),
        ("Undri", 18.4497, 73.9155),
        ("Talegaon", 18.7357, 73.6757),
        ("Chakan", 18.7597, 73.8629),
    ],
    "kolkata": [
        ("Park Street", 22.5534, 88.3525),
        ("Salt Lake", 22.5867, 88.4170),
        ("Howrah", 22.5958, 88.2636),
        ("New Town", 22.5750, 88.4795),
        ("Dum Dum", 22.6200, 88.4230),
        ("Rajarhat", 22.6225, 88.4500),
        ("Barrackpore", 22.7600, 88.3700),
        ("Behala", 22.5010, 88.3189),
        ("Jadavpur", 22.4987, 88.3702),
        ("Tollygunge", 22.4916, 88.3473),
        ("Garia", 22.4628, 88.3866),
        ("Sealdah", 22.5697, 88.3698),
        ("Baruipur", 22.3594, 88.4370),
        ("Konnagar", 22.7056, 88.3459),
    ],
}


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _normalize_data_mode(value: str | None) -> str:
    mode = (value or "real").strip().lower()
    if mode in VALID_DATA_MODES:
        return mode
    return "real"


async def _get_data_mode(r: aioredis.Redis) -> str:
    configured_mode = await r.get(DATA_MODE_REDIS_KEY)
    return _normalize_data_mode(configured_mode or settings.GRID_DATA_MODE)


def _is_demo_source(source_api: str | None) -> bool:
    source = (source_api or "").strip().lower()
    return source.startswith("manual")


def _filter_event_dicts_by_mode(event_dicts: list[dict], mode: str) -> list[dict]:
    normalized_mode = _normalize_data_mode(mode)
    if normalized_mode == "demo":
        return [event for event in event_dicts if _is_demo_source(event.get("source_api"))]
    return [event for event in event_dicts if not _is_demo_source(event.get("source_api"))]


def _to_event_dict(event: GridEvent) -> dict:
    return {
        "event_type": event.event_type,
        "severity": event.severity,
        "raw_value": event.raw_value,
        "source_api": event.source_api,
    }


def _event_influence_weight(distance: int) -> float:
    if distance <= 0:
        return 1.0
    if distance == 1:
        return 0.75
    if distance == 2:
        return 0.55
    if distance == 3:
        return 0.35
    return 0.0


def _collapse_events_by_type(events: list[dict]) -> list[dict]:
    strongest: dict[str, dict] = {}

    for event in events:
        event_type = str(event.get("event_type") or "").strip()
        if not event_type:
            continue
        current = strongest.get(event_type)
        current_severity = float(current.get("severity", 0.0)) if current else -1.0
        incoming_severity = float(event.get("severity", 0.0) or 0.0)
        if current is None or incoming_severity >= current_severity:
            strongest[event_type] = {
                "event_type": event_type,
                "severity": round(incoming_severity, 4),
                "raw_value": round(float(event.get("raw_value", 0.0) or 0.0), 4),
                "source_api": event.get("source_api"),
            }

    return list(strongest.values())


def _effective_city_events_for_cell(
    target_cell: str,
    city_events_by_cell: dict[str, list[dict]],
) -> list[dict]:
    if not city_events_by_cell:
        return []

    effective_events: list[dict] = []
    for source_cell, events in city_events_by_cell.items():
        if not events:
            continue

        try:
            distance = h3.grid_distance(target_cell, source_cell)
        except Exception:
            continue

        weight = _event_influence_weight(distance)
        if weight <= 0:
            continue

        for event in events:
            effective_events.append({
                "event_type": event.get("event_type"),
                "severity": float(event.get("severity", 0.0) or 0.0) * weight,
                "raw_value": float(event.get("raw_value", 0.0) or 0.0) * weight,
                "source_api": event.get("source_api"),
            })

    return _collapse_events_by_type(effective_events)


def _risk_tier_from_score(risk_score: float) -> str:
    if risk_score < 0.30:
        return "low"
    if risk_score < 0.60:
        return "medium"
    if risk_score < 0.80:
        return "high"
    return "critical"


def _zone_code_from_h3(h3_cell: str | None) -> str:
    if not h3_cell:
        return "N/A"
    sanitized = "".join(ch for ch in h3_cell.upper() if ch.isalnum())
    if not sanitized:
        return "N/A"

    meaningful = sanitized.rstrip("F")
    if len(meaningful) >= 4:
        return meaningful[-4:]
    if len(sanitized) >= 6:
        return sanitized[2:6]
    return sanitized


def _risk_code_from_score(score: float) -> str:
    if score >= 0.70:
        return "R1"
    if score >= 0.40:
        return "R2"
    if score >= 0.20:
        return "R3"
    return "R4"


def _distance_sq(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    return (lat_a - lat_b) ** 2 + (lng_a - lng_b) ** 2


def _infer_area_name(city: str, h3_cell: str) -> str | None:
    points = CITY_AREA_POINTS.get(city.lower())
    if not points:
        return None

    try:
        lat, lng = h3_to_latlng(h3_cell)
    except Exception:
        return None

    nearest = min(points, key=lambda item: _distance_sq(lat, lng, item[1], item[2]))
    return nearest[0]


def _looks_generic_area_name(area_name: str | None, city: str) -> bool:
    if not area_name:
        return True

    normalized = area_name.strip().lower()
    if not normalized:
        return True

    city_token = city.strip().lower()
    if normalized == city_token:
        return True

    return normalized.startswith(f"{city_token} - zone")


def _normalize_area_key(area_name: str | None) -> str:
    return (area_name or "").strip().lower()


def _disambiguate_duplicate_area_names(cells: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for cell in cells:
        key = _normalize_area_key(cell.get("area_name"))
        if key:
            counts[key] = counts.get(key, 0) + 1

    output: list[dict] = []
    for cell in cells:
        item = dict(cell)
        area_name = str(item.get("area_name") or "").strip()
        key = _normalize_area_key(area_name)
        if area_name and counts.get(key, 0) > 1:
            zone_code = _zone_code_from_h3(str(item.get("h3_cell", "")))
            if zone_code != "N/A":
                item["area_name"] = f"{area_name} ({zone_code})"
        output.append(item)

    return output


def _enrich_city_cell_payload(cell_payload: dict, city: str) -> dict:
    enriched = dict(cell_payload)
    active_events = enriched.get("active_events", []) or []

    if "payout_rate_hr" not in enriched:
        dominant = workability_service.get_dominant_event_type(active_events)
        enriched["payout_rate_hr"] = workability_service.get_payout_rate(dominant) if dominant else 0.0

    score = float(enriched.get("workability_score", 1.0))
    zone_code = _zone_code_from_h3(str(enriched.get("h3_cell", "")))
    city_label = city.strip().title() if city else "Unknown"

    current_area_name = enriched.get("area_name")
    inferred_area_name = _infer_area_name(city_label, str(enriched.get("h3_cell", "")))
    if _looks_generic_area_name(current_area_name, city_label):
        enriched["area_name"] = inferred_area_name or f"{city_label} - Zone {zone_code}"
    else:
        enriched["area_name"] = current_area_name

    enriched["risk_code"] = _risk_code_from_score(score)

    return enriched


def _summarize_city_cells(cells: list[dict]) -> dict:
    total_cells = len(cells)
    if total_cells == 0:
        return {
            "avg_workability_score": 1.0,
            "risk_score": 0.0,
            "risk_tier": "low",
            "status": "safe",
            "safe_cells": 0,
            "caution_cells": 0,
            "disrupted_cells": 0,
            "active_events": 0,
        }

    safe_cells = 0
    caution_cells = 0
    disrupted_cells = 0
    total_score = 0.0
    min_score = 1.0
    active_events = 0
    severity_values: list[float] = []

    for cell in cells:
        score = float(cell.get("workability_score", 1.0))
        total_score += score
        min_score = min(min_score, score)

        status = workability_service.get_status(score)
        if status == "safe":
            safe_cells += 1
        elif status == "caution":
            caution_cells += 1
        else:
            disrupted_cells += 1

        events = cell.get("active_events", []) or []
        active_events += len(events)
        for event in events:
            severity = event.get("severity")
            if isinstance(severity, (int, float)):
                severity_values.append(float(severity))

    avg_workability_score = round(total_score / total_cells, 4)
    disrupted_ratio = disrupted_cells / total_cells
    caution_ratio = caution_cells / total_cells
    avg_severity = round(sum(severity_values) / len(severity_values), 4) if severity_values else 0.0

    # Blend live city workability + disruption density + event severity into a 0-1 risk score.
    risk_score = round(
        min(
            max(
                (1 - avg_workability_score) * 0.40
                + disrupted_ratio * 0.20
                + caution_ratio * 0.05
                + avg_severity * 0.10
                + (1 - min_score) * 0.25,
                0.0,
            ),
            1.0,
        ),
        4,
    )

    return {
        "avg_workability_score": avg_workability_score,
        "risk_score": risk_score,
        "risk_tier": _risk_tier_from_score(risk_score),
        "status": workability_service.get_status(avg_workability_score),
        "safe_cells": safe_cells,
        "caution_cells": caution_cells,
        "disrupted_cells": disrupted_cells,
        "active_events": active_events,
    }


@router.get("/workability/{h3_cell}", response_model=WorkabilityResponse)
async def get_workability(
    h3_cell: str,
    partner: Partner = Depends(get_current_partner),
):
    """
    Get current workability score for an H3 cell.
    Checks Redis cache first (TTL 900s), falls back to DB query.
    """
    r = await _get_redis()
    data_mode = await _get_data_mode(r)
    cache_key = f"grid:{data_mode}:{h3_cell}"

    # Check Redis cache
    cached = await r.get(cache_key)
    if cached:
        data = json.loads(cached)
        data = _enrich_city_cell_payload(data, partner.city)
        if "payout_rate_hr" not in data:
            dominant = workability_service.get_dominant_event_type(data.get("active_events", []) or [])
            data["payout_rate_hr"] = workability_service.get_payout_rate(dominant) if dominant else 0.0
        # Check if partner has active coverage
        from app.models.policy import Policy

        today = datetime.utcnow().strftime("%Y-%m-%d")
        active_policy = await Policy.find_one(
            Policy.partner_id == partner.id,
            Policy.status == "active",
            Policy.week_start <= today,
            Policy.week_end >= today,
        )
        data["coverage_active"] = active_policy is not None
        await r.aclose()
        return WorkabilityResponse(**data)

    # Query active events and then filter based on selected data mode.
    all_active_events = await GridEvent.find(
        GridEvent.h3_cell == h3_cell,
        GridEvent.resolved_at == None,  # noqa: E711
    ).to_list()

    event_dicts_all = [_to_event_dict(event) for event in all_active_events]
    event_dicts = _filter_event_dicts_by_mode(event_dicts_all, data_mode)

    score = workability_service.calculate_score(event_dicts)
    status_str = workability_service.get_status(score)

    dominant = workability_service.get_dominant_event_type(event_dicts)
    payout_rate = workability_service.get_payout_rate(dominant) if dominant else 0.0

    # Check coverage
    from app.models.policy import Policy

    today = datetime.utcnow().strftime("%Y-%m-%d")
    active_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )

    result = {
        "h3_cell": h3_cell,
        "workability_score": score,
        "status": status_str,
        "active_events": event_dicts,
        "payout_rate_hr": payout_rate,
        "coverage_active": active_policy is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }
    result = _enrich_city_cell_payload(result, partner.city)

    # Cache in Redis (15 min TTL)
    await r.setex(cache_key, 900, json.dumps(result, default=str))
    await r.aclose()

    return WorkabilityResponse(**result)


@router.get("/workability/city/{city}")
async def get_city_workability(city: str):
    """
    Get workability scores for all cells in a city.
    No auth required — used for public map rendering.
    """
    cells = get_city_cells(city)
    if not cells:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown city: {city}",
        )

    r = await _get_redis()
    data_mode = await _get_data_mode(r)

    all_city_events = await GridEvent.find(
        GridEvent.city == city.lower(),
        GridEvent.resolved_at == None,  # noqa: E711
    ).to_list()

    city_events_by_cell: dict[str, list[dict]] = {}
    city_resolution = h3.get_resolution(cells[0]) if cells else 9
    for event in all_city_events:
        event_dict = _to_event_dict(event)
        filtered = _filter_event_dicts_by_mode([event_dict], data_mode)
        if not filtered:
            continue

        mapped_cell = event.h3_cell
        try:
            event_resolution = h3.get_resolution(event.h3_cell)
            if event_resolution > city_resolution:
                mapped_cell = h3.cell_to_parent(event.h3_cell, city_resolution)
        except Exception:
            mapped_cell = event.h3_cell

        city_events_by_cell.setdefault(mapped_cell, []).append(filtered[0])

    results = []
    computed_at = datetime.utcnow().isoformat()

    for cell in cells:
        event_dicts = _effective_city_events_for_cell(cell, city_events_by_cell)
        score = workability_service.calculate_score(event_dicts)
        dominant = workability_service.get_dominant_event_type(event_dicts)
        payout_rate = workability_service.get_payout_rate(dominant) if dominant else 0.0

        result = {
            "h3_cell": cell,
            "workability_score": score,
            "status": workability_service.get_status(score),
            "active_events": event_dicts,
            "payout_rate_hr": payout_rate,
            "timestamp": computed_at,
        }
        results.append(_enrich_city_cell_payload(result, city))

    await r.aclose()
    results = _disambiguate_duplicate_area_names(results)

    summary = _summarize_city_cells(results)
    return {
        "city": city,
        "data_mode": data_mode,
        "cells": results,
        "total": len(results),
        "summary": {
            **summary,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


@router.post("/events/ingest", response_model=GridEventResponse)
async def ingest_event(
    req: GridEventIngest,
    _: bool = Depends(internal_only),
):
    """
    Ingest a new grid event (internal API only).
    1. Upsert unresolved event state by event_type
    2. Recalculate workability for h3_cell
    3. Cache in Redis
    4. Publish WS updates
    5. Trigger payout eligibility only on threshold crossing
    """
    r = await _get_redis()
    active_mode = await _get_data_mode(r)

    # Get existing active events for this cell
    existing_events = await GridEvent.find(
        GridEvent.h3_cell == req.h3_cell,
        GridEvent.resolved_at == None,  # noqa: E711
    ).to_list()

    events_by_type = {
        e.event_type: {
            "event_type": e.event_type,
            "severity": e.severity,
            "raw_value": e.raw_value,
            "source_api": e.source_api,
        }
        for e in existing_events
    }

    previous_event_dicts = _filter_event_dicts_by_mode(list(events_by_type.values()), active_mode)
    previous_score = workability_service.calculate_score(previous_event_dicts)

    # Upsert event state for this event type
    incoming_event = {
        "event_type": req.event_type,
        "severity": req.severity,
        "raw_value": req.raw_value,
        "source_api": req.source_api,
    }
    events_by_type[req.event_type] = incoming_event
    event_dicts = list(events_by_type.values())

    active_mode_events = _filter_event_dicts_by_mode(event_dicts, active_mode)
    score = workability_service.calculate_score(active_mode_events)

    now = datetime.utcnow()
    grid_event = None
    same_type_events = [e for e in existing_events if e.event_type == req.event_type]
    if same_type_events:
        grid_event = max(same_type_events, key=lambda e: e.event_time)
        grid_event.city = req.city
        grid_event.severity = req.severity
        grid_event.raw_value = req.raw_value
        grid_event.workability_score = score
        grid_event.event_time = now
        grid_event.source_api = req.source_api
        grid_event.consecutive_low_count = 0
        await grid_event.save()
    else:
        grid_event = GridEvent(
            h3_cell=req.h3_cell,
            city=req.city,
            event_type=req.event_type,
            severity=req.severity,
            raw_value=req.raw_value,
            workability_score=score,
            event_time=now,
            source_api=req.source_api,
        )
        await grid_event.insert()

    mode_cache_data: dict[str, dict] = {}
    for mode_name in VALID_DATA_MODES:
        mode_events = _filter_event_dicts_by_mode(event_dicts, mode_name)
        mode_score = workability_service.calculate_score(mode_events)
        mode_status = workability_service.get_status(mode_score)
        mode_dominant = workability_service.get_dominant_event_type(mode_events)
        mode_payout_rate = workability_service.get_payout_rate(mode_dominant) if mode_dominant else 0.0
        payload = {
            "h3_cell": req.h3_cell,
            "workability_score": mode_score,
            "status": mode_status,
            "active_events": mode_events,
            "payout_rate_hr": mode_payout_rate,
            "timestamp": datetime.utcnow().isoformat(),
        }
        mode_cache_data[mode_name] = payload
        await r.setex(f"grid:{mode_name}:{req.h3_cell}", 900, json.dumps(payload, default=str))

    # Clear legacy cache key if it exists from previous versions.
    await r.delete(f"grid:{req.h3_cell}")

    active_cache_data = mode_cache_data[active_mode]

    # Publish WS updates
    ws_msg = {
        "type": "workability_update",
        "data_mode": active_mode,
        **active_cache_data,
    }
    await r.publish(f"ws:grid:{req.h3_cell}", json.dumps(ws_msg, default=str))
    await r.publish("ws:admin:feed", json.dumps({
        "type": "new_grid_event",
        "event_id": grid_event.id,
        "h3_cell": req.h3_cell,
        "event_type": req.event_type,
        "severity": req.severity,
        "workability_score": score,
        "data_mode": active_mode,
        "city": req.city,
        "timestamp": datetime.utcnow().isoformat(),
    }, default=str))
    await r.aclose()

    # Trigger payout eligibility if disrupted
    payout_triggered = previous_score >= 0.40 and score < 0.40
    if payout_triggered:
        # Schedule Celery task (imported lazily to avoid circular imports)
        try:
            from app.tasks.payout_eligibility import check_payout_eligibility
            check_payout_eligibility.delay(req.h3_cell, grid_event.id)
        except Exception as e:
            print(f"⚠️  Celery task dispatch failed: {e}")

    return GridEventResponse(
        event_id=grid_event.id,
        workability_score=score,
        payout_triggered=payout_triggered,
    )


@router.patch("/events/{event_id}/resolve")
async def resolve_event(
    event_id: str,
    _admin: Partner = Depends(admin_only),
):
    """Resolve a grid event (admin only)."""
    event = await GridEvent.get(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    event.resolved_at = datetime.utcnow()
    await event.save()

    # Clear Redis cache
    r = await _get_redis()
    await r.delete(
        f"grid:{event.h3_cell}",
        f"grid:real:{event.h3_cell}",
        f"grid:demo:{event.h3_cell}",
    )

    # Publish resolved status
    await r.publish(f"ws:grid:{event.h3_cell}", json.dumps({
        "type": "event_resolved",
        "event_id": event_id,
        "h3_cell": event.h3_cell,
        "event_type": event.event_type,
        "timestamp": datetime.utcnow().isoformat(),
    }, default=str))
    await r.aclose()

    return {"status": "resolved", "event_id": event_id}


@router.get("/events/active")
async def get_active_events(
    _admin: Partner = Depends(admin_only),
):
    """Get all unresolved grid events (admin only)."""
    events = await GridEvent.find(
        GridEvent.resolved_at == None,  # noqa: E711
    ).sort(-GridEvent.event_time).to_list()

    return {
        "events": [e.dict() for e in events],
        "total": len(events),
    }
