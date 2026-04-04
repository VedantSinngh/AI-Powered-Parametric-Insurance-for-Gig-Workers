"""
Presentation demo dataset seeder for GridGuard AI.

Usage (from backend container):
    python scripts/seed_presentation_demo.py

This script clears business/demo collections and inserts a clean, deterministic
set of admin/rider/policy/grid-event/payout/fraud records for presentations.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import h3
from pymongo import MongoClient


CITY_CENTROIDS = {
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
}

TARGET_COLLECTIONS = [
    "partners",
    "policies",
    "grid_events",
    "payouts",
    "fraud_flags",
    "partner_activity_logs",
    "premium_predictions",
    "otp_sessions",
    "wallet_transactions",
]

PITCH_STORYLINE = {
    "title": "Peak-shift disruption narrative",
    "focus_city": "bengaluru",
    "beats": [
        "Bengaluru rider gets a live rainfall-triggered payout",
        "Mumbai rider payout remains queued in provider processing",
        "Delhi AQI payout fails and appears in finance + fraud triage",
    ],
}


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


def get_week_bounds() -> tuple[str, str]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start.isoformat(), week_end.isoformat()


def city_cell(city: str, resolution: int = 8) -> str:
    lat, lng = CITY_CENTROIDS[city]
    return h3.latlng_to_cell(lat, lng, resolution)


def main() -> None:
    mongo_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "gridguard")

    client = MongoClient(mongo_url)
    db = client[db_name]

    # 1) Clear existing demo/business records while preserving indexes.
    for collection in TARGET_COLLECTIONS:
        db[collection].delete_many({})

    ts = now_utc()
    week_start, week_end = get_week_bounds()

    bengaluru_center = city_cell("bengaluru", 8)
    mumbai_center = city_cell("mumbai", 8)
    chennai_center = city_cell("chennai", 8)
    delhi_center = city_cell("delhi", 8)

    # 2) Seed partners.
    partners = [
        {
            "_id": "admin-demo-001",
            "device_id": "DEV-ADMIN-001",
            "full_name": "GridGuard Admin",
            "email": "vedaantsinngh@gmail.com",
            "city": "bengaluru",
            "platform": "other",
            "risk_tier": "low",
            "preferred_language": "en",
            "auto_premium_deduction": True,
            "is_admin": True,
            "is_active": True,
            "mock_wallet_balance": 1000.0,
            "primary_zone_h3": bengaluru_center,
            "onboarded_at": ts - timedelta(days=60),
            "created_at": ts - timedelta(days=60),
            "updated_at": ts,
        },
        {
            "_id": "rider-demo-001",
            "device_id": "DEV-RIDER-001",
            "full_name": "Aarav Kumar",
            "email": "aarav.demo@gridguard.ai",
            "upi_handle": "aarav@oksbi",
            "city": "bengaluru",
            "platform": "zomato",
            "risk_tier": "medium",
            "preferred_language": "en",
            "auto_premium_deduction": True,
            "is_admin": False,
            "is_active": True,
            "mock_wallet_balance": 540.0,
            "primary_zone_h3": list(h3.grid_disk(bengaluru_center, 1))[2],
            "onboarded_at": ts - timedelta(days=18),
            "created_at": ts - timedelta(days=18),
            "updated_at": ts,
        },
        {
            "_id": "rider-demo-002",
            "device_id": "DEV-RIDER-002",
            "full_name": "Nisha Verma",
            "email": "nisha.demo@gridguard.ai",
            "upi_handle": "nisha@okhdfcbank",
            "city": "mumbai",
            "platform": "swiggy",
            "risk_tier": "high",
            "preferred_language": "hi",
            "auto_premium_deduction": False,
            "is_admin": False,
            "is_active": True,
            "mock_wallet_balance": 315.0,
            "primary_zone_h3": list(h3.grid_disk(mumbai_center, 1))[3],
            "onboarded_at": ts - timedelta(days=24),
            "created_at": ts - timedelta(days=24),
            "updated_at": ts,
        },
        {
            "_id": "rider-demo-003",
            "device_id": "DEV-RIDER-003",
            "full_name": "Megha Iyer",
            "email": "megha.demo@gridguard.ai",
            "upi_handle": "megha@okaxis",
            "city": "chennai",
            "platform": "zepto",
            "risk_tier": "low",
            "preferred_language": "ta",
            "auto_premium_deduction": True,
            "is_admin": False,
            "is_active": True,
            "mock_wallet_balance": 770.0,
            "primary_zone_h3": list(h3.grid_disk(chennai_center, 1))[4],
            "onboarded_at": ts - timedelta(days=30),
            "created_at": ts - timedelta(days=30),
            "updated_at": ts,
        },
        {
            "_id": "rider-demo-004",
            "device_id": "DEV-RIDER-004",
            "full_name": "Rohit Singh",
            "email": "rohit.demo@gridguard.ai",
            "upi_handle": "rohit@okicici",
            "city": "delhi",
            "platform": "blinkit",
            "risk_tier": "critical",
            "preferred_language": "hi",
            "auto_premium_deduction": True,
            "is_admin": False,
            "is_active": True,
            "mock_wallet_balance": 245.0,
            "primary_zone_h3": list(h3.grid_disk(delhi_center, 1))[5],
            "onboarded_at": ts - timedelta(days=12),
            "created_at": ts - timedelta(days=12),
            "updated_at": ts,
        },
    ]
    db["partners"].insert_many(partners)

    # 3) Seed active weekly policies.
    policies = [
        {
            "_id": "policy-demo-001",
            "partner_id": "rider-demo-001",
            "week_start": week_start,
            "week_end": week_end,
            "premium_amount": 22.0,
            "risk_score": 0.52,
            "status": "active",
            "deducted_at": ts - timedelta(days=5),
            "created_at": ts - timedelta(days=6),
            "updated_at": ts,
        },
        {
            "_id": "policy-demo-002",
            "partner_id": "rider-demo-002",
            "week_start": week_start,
            "week_end": week_end,
            "premium_amount": 26.0,
            "risk_score": 0.67,
            "status": "active",
            "deducted_at": ts - timedelta(days=5),
            "created_at": ts - timedelta(days=7),
            "updated_at": ts,
        },
        {
            "_id": "policy-demo-003",
            "partner_id": "rider-demo-003",
            "week_start": week_start,
            "week_end": week_end,
            "premium_amount": 18.0,
            "risk_score": 0.39,
            "status": "active",
            "deducted_at": ts - timedelta(days=5),
            "created_at": ts - timedelta(days=9),
            "updated_at": ts,
        },
        {
            "_id": "policy-demo-004",
            "partner_id": "rider-demo-004",
            "week_start": week_start,
            "week_end": week_end,
            "premium_amount": 30.0,
            "risk_score": 0.81,
            "status": "active",
            "deducted_at": ts - timedelta(days=5),
            "created_at": ts - timedelta(days=4),
            "updated_at": ts,
        },
    ]
    db["policies"].insert_many(policies)

    # 4) Seed grid events across cities with a pitch-friendly timeline.
    bengaluru_cells = list(h3.grid_disk(bengaluru_center, 2))
    mumbai_cells = list(h3.grid_disk(mumbai_center, 2))
    delhi_cells = list(h3.grid_disk(delhi_center, 2))

    grid_events = [
        {
            "_id": "event-demo-001",
            "h3_cell": bengaluru_cells[3],
            "city": "bengaluru",
            "event_type": "rainfall",
            "severity": 0.92,
            "raw_value": 72.0,
            "workability_score": 0.26,
            "event_time": ts - timedelta(minutes=55),
            "resolved_at": None,
            "source_api": "presentation_seed",
            "consecutive_low_count": 3,
            "created_at": ts - timedelta(minutes=56),
        },
        {
            "_id": "event-demo-002",
            "h3_cell": mumbai_cells[5],
            "city": "mumbai",
            "event_type": "rainfall",
            "severity": 0.79,
            "raw_value": 46.0,
            "workability_score": 0.38,
            "event_time": ts - timedelta(hours=2, minutes=10),
            "resolved_at": None,
            "source_api": "presentation_seed",
            "consecutive_low_count": 2,
            "created_at": ts - timedelta(hours=2, minutes=10),
        },
        {
            "_id": "event-demo-003",
            "h3_cell": delhi_cells[2],
            "city": "delhi",
            "event_type": "aqi",
            "severity": 0.94,
            "raw_value": 368.0,
            "workability_score": 0.22,
            "event_time": ts - timedelta(minutes=35),
            "resolved_at": None,
            "source_api": "presentation_seed",
            "consecutive_low_count": 3,
            "created_at": ts - timedelta(minutes=35),
        },
        {
            "_id": "event-demo-004",
            "h3_cell": chennai_center,
            "city": "chennai",
            "event_type": "heat",
            "severity": 0.64,
            "raw_value": 41.0,
            "workability_score": 0.46,
            "event_time": ts - timedelta(days=1, hours=4),
            "resolved_at": ts - timedelta(days=1, hours=2),
            "source_api": "presentation_seed",
            "consecutive_low_count": 0,
            "created_at": ts - timedelta(days=1, hours=4),
        },
    ]
    db["grid_events"].insert_many(grid_events)

    # 5) Seed payouts with paid/processing/failed provider mix.
    payouts = [
        {
            "_id": "payout-demo-001",
            "partner_id": "rider-demo-001",
            "policy_id": "policy-demo-001",
            "grid_event_id": "event-demo-001",
            "amount": 150.0,
            "duration_hours": 3.0,
            "rate_per_hour": 50.0,
            "provider": "mock",
            "provider_payout_id": None,
            "provider_status": "processed",
            "provider_reference": "MOCK-PAID-001",
            "mock_reference": "MOCK-PAID-001",
            "status": "paid",
            "paid_at": ts - timedelta(minutes=38),
            "failure_reason": None,
            "ws_notified": True,
            "created_at": ts - timedelta(minutes=45),
        },
        {
            "_id": "payout-demo-002",
            "partner_id": "rider-demo-002",
            "policy_id": "policy-demo-002",
            "grid_event_id": "event-demo-002",
            "amount": 98.0,
            "duration_hours": 2.8,
            "rate_per_hour": 35.0,
            "provider": "razorpay",
            "provider_payout_id": "pout_demo_processing_002",
            "provider_status": "queued",
            "provider_reference": "RAZOR-DEMO-QUEUED-002",
            "mock_reference": "RAZOR-DEMO-QUEUED-002",
            "status": "processing",
            "paid_at": None,
            "failure_reason": None,
            "ws_notified": True,
            "created_at": ts - timedelta(hours=1, minutes=50),
        },
        {
            "_id": "payout-demo-003",
            "partner_id": "rider-demo-004",
            "policy_id": "policy-demo-004",
            "grid_event_id": "event-demo-003",
            "amount": 96.0,
            "duration_hours": 2.4,
            "rate_per_hour": 40.0,
            "provider": "razorpay",
            "provider_payout_id": "pout_demo_failed_003",
            "provider_status": "failed",
            "provider_reference": "RAZOR-DEMO-FAILED-003",
            "mock_reference": "RAZOR-DEMO-FAILED-003",
            "status": "failed",
            "paid_at": None,
            "failure_reason": "Beneficiary bank timeout in Razorpay test mode",
            "ws_notified": True,
            "created_at": ts - timedelta(minutes=28),
        },
        {
            "_id": "payout-demo-004",
            "partner_id": "rider-demo-003",
            "policy_id": "policy-demo-003",
            "grid_event_id": "event-demo-004",
            "amount": 54.0,
            "duration_hours": 1.2,
            "rate_per_hour": 45.0,
            "provider": "mock",
            "provider_payout_id": None,
            "provider_status": "processed",
            "provider_reference": "MOCK-PAID-004",
            "mock_reference": "MOCK-PAID-004",
            "status": "paid",
            "paid_at": ts - timedelta(days=1, hours=1, minutes=30),
            "failure_reason": None,
            "ws_notified": True,
            "created_at": ts - timedelta(days=1, hours=1, minutes=45),
        },
    ]
    db["payouts"].insert_many(payouts)

    # 6) Seed fraud flags for support/fraud/audit views.
    fraud_flags = [
        {
            "_id": "fraud-demo-001",
            "partner_id": "rider-demo-004",
            "payout_id": "payout-demo-003",
            "flag_type": "velocity_abuse",
            "severity": "critical",
            "gps_lat": 28.621,
            "gps_lng": 77.22,
            "accelerometer_variance": 0.03,
            "rule_triggered": "3 disruption claims in 24h during AQI emergency",
            "fraud_score": 0.93,
            "checks_failed": ["frequency_spike", "route_mismatch"],
            "status": "pending",
            "flagged_at": ts - timedelta(minutes=24),
            "reviewed_by": None,
            "reviewer_note": None,
        },
        {
            "_id": "fraud-demo-002",
            "partner_id": "rider-demo-002",
            "payout_id": "payout-demo-002",
            "flag_type": "stationary_device",
            "severity": "warning",
            "gps_lat": 19.08,
            "gps_lng": 72.88,
            "accelerometer_variance": 0.02,
            "rule_triggered": "Device stationary through monsoon disruption window",
            "fraud_score": 0.68,
            "checks_failed": ["low_mobility"],
            "status": "escalated",
            "flagged_at": ts - timedelta(hours=1, minutes=45),
            "reviewed_by": "admin-demo-001",
            "reviewer_note": "Needs partner call verification",
        },
        {
            "_id": "fraud-demo-003",
            "partner_id": "rider-demo-001",
            "payout_id": "payout-demo-001",
            "flag_type": "no_pre_activity",
            "severity": "info",
            "gps_lat": 12.97,
            "gps_lng": 77.59,
            "accelerometer_variance": 0.52,
            "rule_triggered": "No completed rides in prior 60 minutes",
            "fraud_score": 0.32,
            "checks_failed": ["activity_window"],
            "status": "dismissed",
            "flagged_at": ts - timedelta(days=1, hours=1),
            "reviewed_by": "admin-demo-001",
            "reviewer_note": "Verified from platform logs",
        },
    ]
    db["fraud_flags"].insert_many(fraud_flags)

    # 7) Seed wallet transactions for rider story continuity.
    wallet_transactions = [
        {
            "_id": uid("wallet"),
            "partner_id": "rider-demo-001",
            "type": "credit",
            "amount": 150.0,
            "reference": "MOCK-PAID-001",
            "description": "Rainfall disruption payout",
            "balance_after": 540.0,
            "created_at": ts - timedelta(minutes=38),
        },
        {
            "_id": uid("wallet"),
            "partner_id": "rider-demo-002",
            "type": "debit",
            "amount": 26.0,
            "reference": "PREMIUM-WEEKLY-002",
            "description": "Weekly premium deduction",
            "balance_after": 315.0,
            "created_at": ts - timedelta(days=5),
        },
    ]
    db["wallet_transactions"].insert_many(wallet_transactions)

    summary = {
        "status": "ok",
        "dataset": "presentation-demo",
        "db": db_name,
        "counts": {
            "partners": db["partners"].count_documents({}),
            "policies": db["policies"].count_documents({}),
            "grid_events": db["grid_events"].count_documents({}),
            "payouts": db["payouts"].count_documents({}),
            "fraud_flags": db["fraud_flags"].count_documents({}),
            "wallet_transactions": db["wallet_transactions"].count_documents({}),
        },
        "demo_accounts": {
            "admin_email": "vedaantsinngh@gmail.com",
            "rider_emails": [
                "aarav.demo@gridguard.ai",
                "nisha.demo@gridguard.ai",
                "megha.demo@gridguard.ai",
                "rohit.demo@gridguard.ai",
            ],
        },
        "week": {
            "start": week_start,
            "end": week_end,
        },
        "storyline": PITCH_STORYLINE,
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
