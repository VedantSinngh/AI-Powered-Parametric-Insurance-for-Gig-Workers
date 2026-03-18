"""
GridGuard AI — Payout ORM Model (TimescaleDB hypertable)
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PayoutStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    paid = "paid"
    failed = "failed"
    reversed = "reversed"


class Payout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payouts"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False, index=True
    )
    grid_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grid_events.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    rate_per_hour: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    upi_reference: Mapped[str | None] = mapped_column(String(128))
    razorpay_batch_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[PayoutStatusEnum] = mapped_column(
        Enum(PayoutStatusEnum, name="payout_status_enum"),
        default=PayoutStatusEnum.pending,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text)

    # Relationships
    partner = relationship("Partner", back_populates="payouts")
    policy = relationship("Policy", back_populates="payouts")
    grid_event = relationship("GridEvent", back_populates="payouts")
    fraud_flags = relationship("FraudFlag", back_populates="payout", lazy="selectin")

    __table_args__ = (
        Index("ix_payouts_partner_status", "partner_id", "status"),
        Index("ix_payouts_paid_at", "paid_at"),
    )
