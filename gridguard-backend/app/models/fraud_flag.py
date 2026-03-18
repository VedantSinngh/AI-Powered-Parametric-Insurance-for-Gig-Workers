"""
GridGuard AI — Fraud Flag ORM Model
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class FraudFlagTypeEnum(str, enum.Enum):
    stationary_device = "stationary_device"
    no_pre_activity = "no_pre_activity"
    wrong_zone = "wrong_zone"
    multi_account = "multi_account"
    velocity_abuse = "velocity_abuse"


class FraudSeverityEnum(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class FraudFlagStatusEnum(str, enum.Enum):
    pending = "pending"
    dismissed = "dismissed"
    escalated = "escalated"
    confirmed = "confirmed"


class FraudFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fraud_flags"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True
    )
    payout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payouts.id"), index=True
    )
    flag_type: Mapped[FraudFlagTypeEnum] = mapped_column(
        Enum(FraudFlagTypeEnum, name="fraud_flag_type_enum"), nullable=False
    )
    severity: Mapped[FraudSeverityEnum] = mapped_column(
        Enum(FraudSeverityEnum, name="fraud_severity_enum"), nullable=False
    )
    gps_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    gps_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    accelerometer_variance: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    rule_triggered: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[FraudFlagStatusEnum] = mapped_column(
        Enum(FraudFlagStatusEnum, name="fraud_flag_status_enum"),
        default=FraudFlagStatusEnum.pending,
    )
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(64))

    # Relationships
    partner = relationship("Partner", back_populates="fraud_flags")
    payout = relationship("Payout", back_populates="fraud_flags")

    __table_args__ = (
        Index("ix_fraud_flags_partner_status", "partner_id", "status"),
        Index("ix_fraud_flags_severity", "severity"),
        Index("ix_fraud_flags_type", "flag_type"),
    )
