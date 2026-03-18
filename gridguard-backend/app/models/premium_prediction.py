"""
GridGuard AI — Premium Prediction ORM Model
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PremiumTierEnum(str, enum.Enum):
    tier1 = "tier1"
    tier2 = "tier2"
    tier3 = "tier3"
    tier4 = "tier4"
    tier5 = "tier5"


class PremiumPrediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "premium_predictions"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True
    )
    h3_cell: Mapped[str | None] = mapped_column(String(16), index=True)
    predicted_for_week: Mapped[date | None] = mapped_column(Date)
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    premium_tier: Mapped[PremiumTierEnum | None] = mapped_column(
        Enum(PremiumTierEnum, name="premium_tier_enum")
    )
    premium_amount: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    model_version: Mapped[str | None] = mapped_column(String(32))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    partner = relationship("Partner", back_populates="premium_predictions")

    __table_args__ = (
        Index("ix_premium_predictions_partner_week", "partner_id", "predicted_for_week"),
    )
