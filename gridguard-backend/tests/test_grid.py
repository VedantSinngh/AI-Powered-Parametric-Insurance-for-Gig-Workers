"""
GridGuard AI — Grid & Workability Tests
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from httpx import AsyncClient


@pytest.mark.asyncio
class TestGridWorkability:
    """Test grid workability endpoints."""

    async def test_get_workability_authenticated(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test workability score retrieval for an H3 cell."""
        response = await client.get(
            "/api/v1/grid/workability/891e2040547ffff",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "workability_score" in data
        assert "status" in data

    async def test_get_workability_unauthorized(self, client: AsyncClient):
        """Test workability endpoint requires auth."""
        response = await client.get("/api/v1/grid/workability/891e2040547ffff")
        assert response.status_code == 403

    async def test_city_workability_public(self, client: AsyncClient):
        """Test city workability is publicly accessible."""
        response = await client.get("/api/v1/grid/workability/city/mumbai")
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "mumbai"
        assert "cells" in data

    async def test_ingest_event_requires_api_key(self, client: AsyncClient):
        """Test event ingestion requires internal API key."""
        response = await client.post(
            "/api/v1/grid/events/ingest",
            json={
                "source": "test",
                "h3_cell": "891e2040547ffff",
                "event_type": "rainfall",
                "raw_value": "15.5",
                "severity": "0.65",
                "event_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        # Should fail without X-API-Key header
        assert response.status_code == 422 or response.status_code == 401
