"""
GridGuard AI — Test Configuration & Fixtures
"""

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base, get_db
from app.main import app
from app.models.partner import Partner, PlatformEnum, RiskTierEnum
from app.utils.dependencies import create_access_token


# ── Test Database ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before tests, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide an async test client with overridden DB dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_partner(db_session: AsyncSession) -> Partner:
    """Create a test partner in the database."""
    partner = Partner(
        id=uuid.uuid4(),
        device_id=f"test_device_{uuid.uuid4().hex[:8]}",
        full_name="Test Partner",
        phone_number=f"+91{uuid.uuid4().int % 10**10:010d}",
        upi_handle="test@upi",
        city="mumbai",
        platform=PlatformEnum.zomato,
        risk_tier=RiskTierEnum.low,
        is_active=True,
        onboarded_at=datetime.now(timezone.utc),
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


@pytest_asyncio.fixture
async def auth_headers(test_partner: Partner) -> dict:
    """Create auth headers with a valid JWT for the test partner."""
    token = create_access_token(str(test_partner.id))
    return {"Authorization": f"Bearer {token}"}
