"""
PremiumPrediction Document — ML-generated premium predictions
Collection: premium_predictions
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Literal


class PremiumPrediction(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_id: str = Indexed()
    h3_cell: str
    predicted_for_week: str = Indexed()  # ISO date
    risk_score: float
    premium_tier: Literal["tier1", "tier2", "tier3", "tier4", "tier5"]
    premium_amount: float
    model_version: str
    feature_vector: dict = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "premium_predictions"
