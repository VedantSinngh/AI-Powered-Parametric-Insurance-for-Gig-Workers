"""
GridGuard AI — Partner Activity Log ORM Model (TimescaleDB hypertable)
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PlatformStatusEnum(str, enum.Enum):
    online = "online"
    offline = "offline"
    on_delivery = "on_delivery"
    idle = "idle"


class PartnerActivityLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partner_activity_logs"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True
    )
    h3_cell: Mapped[str | None] = mapped_column(String(16), index=True)
    gps_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    gps_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    is_online: Mapped[bool | None] = mapped_column(Boolean)
    accelerometer_variance: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    platform_status: Mapped[PlatformStatusEnum | None] = mapped_column(
        Enum(PlatformStatusEnum, name="platform_status_enum")
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relationships
    partner = relationship("Partner", back_populates="activity_logs")

    __table_args__ = (
        Index("ix_activity_logs_partner_time", "partner_id", "logged_at"),
        Index("ix_activity_logs_h3_cell", "h3_cell"),
    )
