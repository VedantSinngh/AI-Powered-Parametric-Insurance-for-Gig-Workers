"""
GridGuard AI — Risk Engine Service
ML model interface for risk scoring (TFT model via TorchServe + XGBoost fallback).
"""

import logging
from decimal import Decimal

import httpx
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Premium Tier Mapping ──
PREMIUM_TIERS = {
    "tier1": {"range": (0.0, 0.2), "amount": Decimal("12.00")},
    "tier2": {"range": (0.2, 0.4), "amount": Decimal("18.00")},
    "tier3": {"range": (0.4, 0.6), "amount": Decimal("24.00")},
    "tier4": {"range": (0.6, 0.8), "amount": Decimal("36.00")},
    "tier5": {"range": (0.8, 1.0), "amount": Decimal("48.00")},
}


def score_to_premium_tier(risk_score: float) -> tuple[str, Decimal]:
    """Map a risk score (0.0–1.0) to a premium tier and amount."""
    for tier, config in PREMIUM_TIERS.items():
        low, high = config["range"]
        if low <= risk_score < high:
            return tier, config["amount"]
    # Edge case: score == 1.0
    return "tier5", Decimal("48.00")


async def get_risk_score_tft(
    partner_id: str,
    h3_cell: str,
    historical_features: dict | None = None,
) -> float | None:
    """
    Call TorchServe TFT model for risk scoring.
    Returns risk_score (0.0–1.0) or None if model unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "instances": [
                    {
                        "partner_id": partner_id,
                        "h3_cell": h3_cell,
                        **(historical_features or {}),
                    }
                ]
            }

            response = await client.post(
                f"{settings.torchserve_url}/predictions/tft_risk_model",
                json=payload,
            )

            if response.status_code == 200:
                result = response.json()
                risk_score = float(result.get("predictions", [0.5])[0])
                return max(0.0, min(1.0, risk_score))  # Clamp to [0, 1]
            else:
                logger.warning(
                    f"TorchServe returned {response.status_code}: {response.text}"
                )
                return None

    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.error(f"TorchServe request failed: {e}")
        return None


async def get_risk_score_xgboost_fallback(
    partner_id: str,
    h3_cell: str,
    historical_features: dict | None = None,
) -> float:
    """
    XGBoost fallback risk scoring.
    Uses a simplified feature set when TFT model is unavailable.
    In production, this would load a trained XGBoost model.
    """
    try:
        # Simplified risk calculation based on available features
        # In production: load XGBoost model and predict
        features = historical_features or {}

        # Default risk factors
        base_risk = 0.3
        zone_risk = features.get("zone_risk_modifier", 0.0)
        activity_risk = features.get("activity_risk_modifier", 0.0)
        weather_risk = features.get("weather_risk_modifier", 0.0)

        risk_score = base_risk + zone_risk + activity_risk + weather_risk
        risk_score = max(0.0, min(1.0, risk_score))

        return risk_score

    except Exception as e:
        logger.error(f"XGBoost fallback failed: {e}")
        return 0.5  # Default medium risk


async def get_risk_score(
    partner_id: str,
    h3_cell: str,
    historical_features: dict | None = None,
) -> float:
    """
    Get risk score with TFT primary, XGBoost fallback.
    """
    # Try TFT model first
    tft_score = await get_risk_score_tft(partner_id, h3_cell, historical_features)
    if tft_score is not None:
        logger.info(f"TFT risk score for {partner_id}: {tft_score}")
        return tft_score

    # Fallback to XGBoost
    logger.info(f"Falling back to XGBoost for {partner_id}")
    xgb_score = await get_risk_score_xgboost_fallback(
        partner_id, h3_cell, historical_features
    )
    return xgb_score
