"""
GridGuard AI — Fraud Detection Tests
"""

import pytest
from decimal import Decimal

from app.services.fraud_eye import (
    GPS_ZONE_DISTANCE_THRESHOLD_M,
    ACCELEROMETER_MIN_VARIANCE,
)


@pytest.mark.asyncio
class TestFraudDetection:
    """Test fraud detection logic."""

    async def test_fraud_evaluate_requires_api_key(self, client):
        """Test fraud evaluation requires internal API key."""
        response = await client.post(
            "/api/v1/fraud/evaluate",
            json={
                "partner_id": "00000000-0000-0000-0000-000000000000",
                "h3_cell": "891e2040547ffff",
                "gps_lat": "19.0760",
                "gps_lng": "72.8777",
                "accelerometer_variance": "0.25",
                "event_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code in (401, 422)

    async def test_fraud_flags_requires_admin(self, client, auth_headers):
        """Test fraud flags endpoint requires admin access."""
        response = await client.get(
            "/api/v1/fraud/flags",
            headers=auth_headers,
        )
        # Regular partner should get 403
        assert response.status_code == 403

    def test_thresholds_are_configured(self):
        """Test that fraud thresholds are properly configured."""
        assert GPS_ZONE_DISTANCE_THRESHOLD_M == 750.0
        assert ACCELEROMETER_MIN_VARIANCE == 0.15
