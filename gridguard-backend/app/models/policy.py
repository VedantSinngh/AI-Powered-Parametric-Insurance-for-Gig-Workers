"""
GridGuard AI — Policy ORM Model
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


class PolicyStatusEnum(str, enum.Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    suspended = "suspended"


class Policy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policies"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    premium_amount: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    status: Mapped[PolicyStatusEnum] = mapped_column(
        Enum(PolicyStatusEnum, name="policy_status_enum"),
        default=PolicyStatusEnum.active,
    )
    deducted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    partner = relationship("Partner", back_populates="policies")
    payouts = relationship("Payout", back_populates="policy", lazy="selectin")

    __table_args__ = (
        Index("ix_policies_partner_week", "partner_id", "week_start"),
        Index("ix_policies_status", "status"),
    )
