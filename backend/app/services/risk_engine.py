"""
GridGuard AI — XGBoost Risk Engine
Feature engineering + ML risk scoring + rule-based fallback
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from app.config import settings


PREMIUM_MAP = {
    0: ("tier1", 12.0),   # [0.0, 0.2)
    1: ("tier2", 18.0),   # [0.2, 0.4)
    2: ("tier3", 24.0),   # [0.4, 0.6)
    3: ("tier4", 36.0),   # [0.6, 0.8)
    4: ("tier5", 48.0),   # [0.8, 1.0]
}


class RiskEngine:
    """XGBoost-based risk scoring with rule-based fallback."""

    def __init__(self):
        self._model = None
        self._loaded = False

    def _load_model(self):
        """Load trained XGBoost model from disk."""
        if self._loaded:
            return

        model_path = settings.MODEL_PATH
        if os.path.exists(model_path):
            try:
                import joblib
                self._model = joblib.load(model_path)
                self._loaded = True
                print(f"✅ Risk model loaded from {model_path}")
            except Exception as e:
                print(f"⚠️  Failed to load risk model: {e}")
                self._model = None
        else:
            print(f"⚠️  Risk model not found at {model_path}, using rule-based fallback")

    async def extract_features(self, partner_id: str, h3_cell: str) -> dict:
        """Extract risk features from MongoDB using raw Motor aggregation."""
        from app.database import get_database

        db = get_database()
        now = datetime.utcnow()

        # avg_workability_7d
        seven_days_ago = now - timedelta(days=7)
        pipeline_workability = [
            {
                "$match": {
                    "h3_cell": h3_cell,
                    "event_time": {"$gte": seven_days_ago},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$workability_score"},
                }
            },
        ]
        cursor = db["grid_events"].aggregate(pipeline_workability)
        result = await cursor.to_list(length=1)
        avg_workability_7d = result[0]["avg_score"] if result else 1.0

        # online_hours_7d
        pipeline_online = [
            {
                "$match": {
                    "partner_id": partner_id,
                    "logged_at": {"$gte": seven_days_ago},
                    "is_online": True,
                }
            },
            {"$count": "total_logs"},
        ]
        cursor = db["partner_activity_logs"].aggregate(pipeline_online)
        result = await cursor.to_list(length=1)
        total_logs = result[0]["total_logs"] if result else 0
        online_hours_7d = total_logs * 5 / 60  # 5-min intervals

        # zone_event_freq_30d
        thirty_days_ago = now - timedelta(days=30)
        event_count = await db["grid_events"].count_documents({
            "h3_cell": h3_cell,
            "event_time": {"$gte": thirty_days_ago},
        })

        # city_risk_index
        partner_doc = await db["partners"].find_one({"_id": partner_id})
        city = partner_doc.get("city", "") if partner_doc else ""
        pipeline_city_risk = [
            {
                "$match": {
                    "city": city,
                    "event_time": {"$gte": seven_days_ago},
                }
            },
            {
                "$group": {"_id": None, "avg_severity": {"$avg": "$severity"}}
            },
        ]
        cursor = db["grid_events"].aggregate(pipeline_city_risk)
        result = await cursor.to_list(length=1)
        city_risk_index = result[0]["avg_severity"] if result else 0.0

        # partner_tenure_days
        onboarded_at = partner_doc.get("onboarded_at") if partner_doc else None
        tenure = (now - onboarded_at).days if onboarded_at else 30

        # payout_rate_30d
        payout_count = await db["payouts"].count_documents({
            "partner_id": partner_id,
            "created_at": {"$gte": thirty_days_ago},
            "status": "paid",
        })
        payout_rate_30d = payout_count / max(tenure, 1)

        return {
            "avg_workability_7d": avg_workability_7d,
            "online_hours_7d": online_hours_7d,
            "zone_event_freq_30d": event_count,
            "city_risk_index": city_risk_index,
            "partner_tenure_days": tenure,
            "payout_rate_30d": payout_rate_30d,
        }

    def predict_risk_score(self, features: dict) -> float:
        """Predict risk score using model or rule-based fallback."""
        self._load_model()

        if self._model is not None:
            # XGBoost prediction
            feature_array = np.array([[
                features["avg_workability_7d"],
                features["online_hours_7d"],
                features["zone_event_freq_30d"],
                features["city_risk_index"],
                features["partner_tenure_days"],
                features["payout_rate_30d"],
            ]])
            try:
                prediction = self._model.predict(feature_array)[0]
                # Map class (0-4) to score (0.0-1.0)
                return min(max((prediction + 0.5) / 5.0, 0.0), 1.0)
            except Exception as e:
                print(f"⚠️  Model prediction failed, using fallback: {e}")

        # Rule-based fallback
        return self._rule_based_score(features)

    def _rule_based_score(self, features: dict) -> float:
        """Rule-based risk scoring when ML model is unavailable."""
        score = (
            0.3 * (1 - features.get("avg_workability_7d", 1.0))
            + 0.3 * min(features.get("zone_event_freq_30d", 0) / 20.0, 1.0)
            + 0.2 * (1 - min(features.get("partner_tenure_days", 30) / 365.0, 1.0))
            + 0.2 * features.get("city_risk_index", 0.0)
        )
        return max(0.0, min(1.0, round(score, 4)))

    def score_to_premium(self, risk_score: float) -> tuple[str, float]:
        """Map risk score to premium tier and amount."""
        if risk_score < 0.2:
            return PREMIUM_MAP[0]
        elif risk_score < 0.4:
            return PREMIUM_MAP[1]
        elif risk_score < 0.6:
            return PREMIUM_MAP[2]
        elif risk_score < 0.8:
            return PREMIUM_MAP[3]
        else:
            return PREMIUM_MAP[4]

    def score_to_risk_tier(self, risk_score: float) -> str:
        """Map risk score to partner risk tier."""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.6:
            return "medium"
        elif risk_score < 0.8:
            return "high"
        else:
            return "critical"


risk_engine = RiskEngine()
