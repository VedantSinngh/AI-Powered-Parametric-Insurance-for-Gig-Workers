"""
GridGuard AI — Payout Tests
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPayouts:
    """Test payout endpoints."""

    async def test_payout_history_authenticated(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test payout history returns empty for new partner."""
        response = await client.get(
            "/api/v1/payouts/my-history",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["payouts"] == []

    async def test_payout_history_unauthorized(self, client: AsyncClient):
        """Test payout history requires auth."""
        response = await client.get("/api/v1/payouts/my-history")
        assert response.status_code == 403

    async def test_payout_detail_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test payout detail returns 404 for non-existent payout."""
        response = await client.get(
            "/api/v1/payouts/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_trigger_payout_requires_api_key(self, client: AsyncClient):
        """Test payout trigger requires internal API key."""
        response = await client.post(
            "/api/v1/payouts/trigger",
            json={
                "partner_id": "00000000-0000-0000-0000-000000000000",
                "grid_event_id": "00000000-0000-0000-0000-000000000000",
                "duration_hours": "1.0",
            },
        )
        assert response.status_code in (401, 422)
