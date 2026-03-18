"""
GridGuard AI — Grid Event ORM Model (TimescaleDB hypertable)
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class EventTypeEnum(str, enum.Enum):
    rainfall = "rainfall"
    heat = "heat"
    aqi = "aqi"
    road_saturation = "road_saturation"
    app_outage = "app_outage"


class GridEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grid_events"

    h3_cell: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    event_type: Mapped[EventTypeEnum] = mapped_column(
        Enum(EventTypeEnum, name="event_type_enum"), nullable=False
    )
    severity: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    raw_value: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    workability_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_api: Mapped[str | None] = mapped_column(String(64))

    # Relationships
    payouts = relationship("Payout", back_populates="grid_event", lazy="selectin")

    __table_args__ = (
        Index("ix_grid_events_cell_time", "h3_cell", "event_time"),
        Index("ix_grid_events_type", "event_type"),
        Index("ix_grid_events_resolved", "resolved_at"),
    )
