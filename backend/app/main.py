"""
GridGuard AI — FastAPI Application Entry Point
Uses async lifespan context manager (NOT on_event)
Includes WebSocket routes and all API routers
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db, close_db
from app.core.websocket_manager import manager
from app.core.rate_limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + Redis subscriber. Shutdown: close connections."""
    # ── Startup ──
    print("🚀 GridGuard AI starting up...")
    await init_db()
    print("✅ MongoDB connected & Beanie initialized")

    # Sentry SDK init (if DSN configured)
    if settings.SENTRY_DSN and settings.SENTRY_DSN != "your-sentry-dsn":
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[FastApiIntegration()],
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.2,
            )
            print("✅ Sentry initialized")
        except Exception as e:
            print(f"⚠️  Sentry init failed: {e}")

    # Start Redis pub/sub subscriber as background task
    redis_task = asyncio.create_task(manager.redis_subscriber())
    print("✅ Redis pub/sub subscriber started")

    yield

    # ── Shutdown ──
    print("🛑 GridGuard AI shutting down...")
    redis_task.cancel()
    try:
        await redis_task
    except asyncio.CancelledError:
        pass
    await close_db()
    print("✅ MongoDB disconnected")


app = FastAPI(
    title="GridGuard AI",
    description="Real-Time Parametric Income Protection for India's Gig Economy",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]
if not cors_origins:
    cors_origins = ["http://localhost:3000"]
allow_all_origins = "*" in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register API Routers ──
from app.routers.auth import router as auth_router
from app.routers.grid import router as grid_router
from app.routers.policies import router as policies_router
from app.routers.payouts import router as payouts_router
from app.routers.wallet import router as wallet_router
from app.routers.fraud import router as fraud_router
from app.routers.admin import router as admin_router
from app.routers.activity import router as activity_router

app.include_router(auth_router)
app.include_router(grid_router)
app.include_router(policies_router)
app.include_router(payouts_router)
app.include_router(wallet_router)
app.include_router(fraud_router)
app.include_router(admin_router)
app.include_router(activity_router)


# ── Health Check ──
@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "service": "GridGuard AI",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "payout_provider": settings.PAYOUT_PROVIDER,
        "payout_fallback_to_mock": settings.RAZORPAY_FALLBACK_TO_MOCK,
        "ws_connections": manager.get_connection_count(),
    }


# ══════════════════════════════════════════════
# WebSocket Routes
# ══════════════════════════════════════════════


@app.websocket("/ws/grid/{h3_cell}")
async def ws_grid(websocket: WebSocket, h3_cell: str):
    """
    Real-time workability updates for a specific H3 cell.
    Message format: { type, h3_cell, workability_score, status,
                      active_events, payout_rate_hr, timestamp }
    """
    channel = f"grid:{h3_cell}"
    await manager.connect(websocket, channel)
    try:
        while True:
            # Keep alive — ping every 30s
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        manager.disconnect(websocket, channel)


@app.websocket("/ws/partner/{partner_id}")
async def ws_partner(websocket: WebSocket, partner_id: str):
    """
    Partner-specific notifications: payout_credited,
    policy_activated, zone_status_changed, premium_deducted.
    Each event includes sound_type: 'success' | 'alert' | 'info'
    """
    channel = f"partner:{partner_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        manager.disconnect(websocket, channel)


@app.websocket("/ws/admin/live-feed")
async def ws_admin_feed(websocket: WebSocket):
    """
    Admin live feed: new_grid_event, payout_batch_completed,
    fraud_flag_raised, partner_suspended, system_health_metrics.
    """
    channel = "admin:feed"
    await manager.connect(websocket, channel)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
    except Exception:
        manager.disconnect(websocket, channel)
