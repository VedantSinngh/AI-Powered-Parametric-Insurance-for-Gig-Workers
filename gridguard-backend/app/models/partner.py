"""
GridGuard AI — Partner ORM Model
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PlatformEnum(str, enum.Enum):
    zomato = "zomato"
    swiggy = "swiggy"
    zepto = "zepto"
    blinkit = "blinkit"
    other = "other"


class RiskTierEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Partner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partners"

    device_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128))
    phone_number: Mapped[str | None] = mapped_column(String(15), unique=True)
    upi_handle: Mapped[str | None] = mapped_column(String(64))
    primary_zone_h3: Mapped[str | None] = mapped_column(String(16), index=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    platform: Mapped[PlatformEnum | None] = mapped_column(Enum(PlatformEnum, name="platform_enum"))
    risk_tier: Mapped[RiskTierEnum | None] = mapped_column(
        Enum(RiskTierEnum, name="risk_tier_enum"), default=RiskTierEnum.low
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    policies = relationship("Policy", back_populates="partner", lazy="selectin")
    payouts = relationship("Payout", back_populates="partner", lazy="selectin")
    fraud_flags = relationship("FraudFlag", back_populates="partner", lazy="selectin")
    activity_logs = relationship("PartnerActivityLog", back_populates="partner", lazy="selectin")
    premium_predictions = relationship("PremiumPrediction", back_populates="partner", lazy="selectin")

    __table_args__ = (
        Index("ix_partners_device_id", "device_id"),
        Index("ix_partners_platform", "platform"),
        Index("ix_partners_risk_tier", "risk_tier"),
    )
