"""Initial schema — All tables with TimescaleDB hypertables

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable TimescaleDB extension ──
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # ── Enum Types ──
    op.execute("""
        CREATE TYPE platform_enum AS ENUM ('zomato', 'swiggy', 'zepto', 'blinkit', 'other');
        CREATE TYPE risk_tier_enum AS ENUM ('low', 'medium', 'high', 'critical');
        CREATE TYPE policy_status_enum AS ENUM ('active', 'expired', 'cancelled', 'suspended');
        CREATE TYPE event_type_enum AS ENUM ('rainfall', 'heat', 'aqi', 'road_saturation', 'app_outage');
        CREATE TYPE payout_status_enum AS ENUM ('pending', 'processing', 'paid', 'failed', 'reversed');
        CREATE TYPE fraud_flag_type_enum AS ENUM ('stationary_device', 'no_pre_activity', 'wrong_zone', 'multi_account', 'velocity_abuse');
        CREATE TYPE fraud_severity_enum AS ENUM ('info', 'warning', 'critical');
        CREATE TYPE fraud_flag_status_enum AS ENUM ('pending', 'dismissed', 'escalated', 'confirmed');
        CREATE TYPE platform_status_enum AS ENUM ('online', 'offline', 'on_delivery', 'idle');
        CREATE TYPE premium_tier_enum AS ENUM ('tier1', 'tier2', 'tier3', 'tier4', 'tier5');
    """)

    # ── TABLE 1: partners ──
    op.create_table(
        "partners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(128), unique=True, nullable=False),
        sa.Column("full_name", sa.String(128)),
        sa.Column("phone_number", sa.String(15), unique=True),
        sa.Column("upi_handle", sa.String(64)),
        sa.Column("primary_zone_h3", sa.String(16), index=True),
        sa.Column("city", sa.String(64), index=True),
        sa.Column("platform", sa.Enum("zomato", "swiggy", "zepto", "blinkit", "other", name="platform_enum", create_type=False)),
        sa.Column("risk_tier", sa.Enum("low", "medium", "high", "critical", name="risk_tier_enum", create_type=False), server_default="low"),
        sa.Column("is_active", sa.Boolean, server_default="true", index=True),
        sa.Column("onboarded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_partners_device_id", "partners", ["device_id"])
    op.create_index("ix_partners_platform", "partners", ["platform"])
    op.create_index("ix_partners_risk_tier", "partners", ["risk_tier"])

    # ── TABLE 2: policies ──
    op.create_table(
        "policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", UUID(as_uuid=True), sa.ForeignKey("partners.id"), nullable=False, index=True),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("week_end", sa.Date, nullable=False),
        sa.Column("premium_amount", sa.Numeric(8, 2)),
        sa.Column("risk_score", sa.Numeric(4, 3)),
        sa.Column("status", sa.Enum("active", "expired", "cancelled", "suspended", name="policy_status_enum", create_type=False), server_default="active"),
        sa.Column("deducted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_policies_partner_week", "policies", ["partner_id", "week_start"])
    op.create_index("ix_policies_status", "policies", ["status"])

    # ── TABLE 3: grid_events (TimescaleDB hypertable) ──
    op.create_table(
        "grid_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("h3_cell", sa.String(16), nullable=False, index=True),
        sa.Column("city", sa.String(64), index=True),
        sa.Column("event_type", sa.Enum("rainfall", "heat", "aqi", "road_saturation", "app_outage", name="event_type_enum", create_type=False), nullable=False),
        sa.Column("severity", sa.Numeric(4, 3), nullable=False),
        sa.Column("raw_value", sa.Numeric(8, 2)),
        sa.Column("workability_score", sa.Numeric(4, 3)),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("source_api", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_grid_events_cell_time", "grid_events", ["h3_cell", "event_time"])
    op.create_index("ix_grid_events_type", "grid_events", ["event_type"])
    op.create_index("ix_grid_events_resolved", "grid_events", ["resolved_at"])
    op.execute("SELECT create_hypertable('grid_events', 'event_time', if_not_exists => TRUE);")

    # ── TABLE 4: payouts (TimescaleDB hypertable) ──
    op.create_table(
        "payouts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", UUID(as_uuid=True), sa.ForeignKey("partners.id"), nullable=False, index=True),
        sa.Column("policy_id", UUID(as_uuid=True), sa.ForeignKey("policies.id"), nullable=False, index=True),
        sa.Column("grid_event_id", UUID(as_uuid=True), sa.ForeignKey("grid_events.id"), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("duration_hours", sa.Numeric(4, 2)),
        sa.Column("rate_per_hour", sa.Numeric(6, 2)),
        sa.Column("upi_reference", sa.String(128)),
        sa.Column("razorpay_batch_id", sa.String(128)),
        sa.Column("status", sa.Enum("pending", "processing", "paid", "failed", "reversed", name="payout_status_enum", create_type=False), server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), index=True),
        sa.Column("failure_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_payouts_partner_status", "payouts", ["partner_id", "status"])
    op.create_index("ix_payouts_paid_at", "payouts", ["paid_at"])
    op.execute("SELECT create_hypertable('payouts', 'paid_at', if_not_exists => TRUE, migrate_data => TRUE);")

    # ── TABLE 5: fraud_flags ──
    op.create_table(
        "fraud_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", UUID(as_uuid=True), sa.ForeignKey("partners.id"), nullable=False, index=True),
        sa.Column("payout_id", UUID(as_uuid=True), sa.ForeignKey("payouts.id"), index=True),
        sa.Column("flag_type", sa.Enum("stationary_device", "no_pre_activity", "wrong_zone", "multi_account", "velocity_abuse", name="fraud_flag_type_enum", create_type=False), nullable=False),
        sa.Column("severity", sa.Enum("info", "warning", "critical", name="fraud_severity_enum", create_type=False), nullable=False),
        sa.Column("gps_lat", sa.Numeric(10, 7)),
        sa.Column("gps_lng", sa.Numeric(10, 7)),
        sa.Column("accelerometer_variance", sa.Numeric(10, 6)),
        sa.Column("rule_triggered", sa.String(128)),
        sa.Column("status", sa.Enum("pending", "dismissed", "escalated", "confirmed", name="fraud_flag_status_enum", create_type=False), server_default="pending"),
        sa.Column("flagged_at", sa.DateTime(timezone=True), index=True),
        sa.Column("reviewed_by", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_fraud_flags_partner_status", "fraud_flags", ["partner_id", "status"])
    op.create_index("ix_fraud_flags_severity", "fraud_flags", ["severity"])
    op.create_index("ix_fraud_flags_type", "fraud_flags", ["flag_type"])

    # ── TABLE 6: partner_activity_logs (TimescaleDB hypertable) ──
    op.create_table(
        "partner_activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", UUID(as_uuid=True), sa.ForeignKey("partners.id"), nullable=False, index=True),
        sa.Column("h3_cell", sa.String(16), index=True),
        sa.Column("gps_lat", sa.Numeric(10, 7)),
        sa.Column("gps_lng", sa.Numeric(10, 7)),
        sa.Column("is_online", sa.Boolean),
        sa.Column("accelerometer_variance", sa.Numeric(10, 6)),
        sa.Column("platform_status", sa.Enum("online", "offline", "on_delivery", "idle", name="platform_status_enum", create_type=False)),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_activity_logs_partner_time", "partner_activity_logs", ["partner_id", "logged_at"])
    op.create_index("ix_activity_logs_h3_cell", "partner_activity_logs", ["h3_cell"])
    op.execute("SELECT create_hypertable('partner_activity_logs', 'logged_at', if_not_exists => TRUE);")

    # ── TABLE 7: premium_predictions ──
    op.create_table(
        "premium_predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", UUID(as_uuid=True), sa.ForeignKey("partners.id"), nullable=False, index=True),
        sa.Column("h3_cell", sa.String(16), index=True),
        sa.Column("predicted_for_week", sa.Date),
        sa.Column("risk_score", sa.Numeric(4, 3)),
        sa.Column("premium_tier", sa.Enum("tier1", "tier2", "tier3", "tier4", "tier5", name="premium_tier_enum", create_type=False)),
        sa.Column("premium_amount", sa.Numeric(8, 2)),
        sa.Column("model_version", sa.String(32)),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_premium_predictions_partner_week", "premium_predictions", ["partner_id", "predicted_for_week"])


def downgrade() -> None:
    op.drop_table("premium_predictions")
    op.drop_table("partner_activity_logs")
    op.drop_table("fraud_flags")
    op.drop_table("payouts")
    op.drop_table("grid_events")
    op.drop_table("policies")
    op.drop_table("partners")

    op.execute("""
        DROP TYPE IF EXISTS premium_tier_enum;
        DROP TYPE IF EXISTS platform_status_enum;
        DROP TYPE IF EXISTS fraud_flag_status_enum;
        DROP TYPE IF EXISTS fraud_severity_enum;
        DROP TYPE IF EXISTS fraud_flag_type_enum;
        DROP TYPE IF EXISTS payout_status_enum;
        DROP TYPE IF EXISTS event_type_enum;
        DROP TYPE IF EXISTS policy_status_enum;
        DROP TYPE IF EXISTS risk_tier_enum;
        DROP TYPE IF EXISTS platform_enum;
    """)
