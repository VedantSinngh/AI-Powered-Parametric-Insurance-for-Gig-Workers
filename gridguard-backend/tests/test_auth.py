"""
GridGuard AI — Auth Tests
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuth:
    """Test authentication endpoints."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful partner registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "device_id": "test_device_001",
                "phone_number": "+919876543210",
                "full_name": "Rahul Sharma",
                "platform": "zomato",
                "city": "mumbai",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "partner_id" in data
        assert "otp_session_token" in data

    async def test_register_duplicate_device(self, client: AsyncClient):
        """Test registration fails for duplicate device_id."""
        payload = {
            "device_id": "duplicate_device",
            "phone_number": "+919876543211",
            "full_name": "Test User 1",
            "platform": "swiggy",
            "city": "delhi",
        }
        # First registration
        await client.post("/api/v1/auth/register", json=payload)
        # Duplicate
        response = await client.post(
            "/api/v1/auth/register",
            json={**payload, "phone_number": "+919876543212"},
        )
        assert response.status_code == 409

    async def test_register_invalid_platform(self, client: AsyncClient):
        """Test registration fails for invalid platform."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "device_id": "test_device_bad",
                "phone_number": "+919876543215",
                "full_name": "Bad Platform User",
                "platform": "uber",  # Invalid
                "city": "mumbai",
            },
        )
        assert response.status_code == 422

    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        """Test /auth/me returns partner profile."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["full_name"] == "Test Partner"

    async def test_get_me_unauthorized(self, client: AsyncClient):
        """Test /auth/me fails without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check endpoints."""

    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_root(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["service"] == "GridGuard AI"
