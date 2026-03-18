"""
GridGuard AI — FastAPI Application Factory
Main entry point for the GridGuard AI backend.
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.utils.dependencies import limiter

settings = get_settings()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gridguard")


# ── Sentry ──
if settings.sentry_dsn and settings.is_production:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment=settings.environment,
    )


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 GridGuard AI backend starting up...")
    logger.info(f"   Environment: {settings.environment}")
    yield
    logger.info("🛑 GridGuard AI backend shutting down...")


# ── App Factory ──
app = FastAPI(
    title="GridGuard AI",
    description=(
        "AI-Powered Parametric Income Protection Platform for India's "
        "gig economy delivery partners. Real-time grid workability scoring, "
        "automated payouts, and intelligent fraud detection."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiter ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
        },
    )


# ── Register Routers ──
from app.routers.auth import router as auth_router
from app.routers.grid import router as grid_router
from app.routers.policies import router as policies_router
from app.routers.payouts import router as payouts_router
from app.routers.fraud import router as fraud_router
from app.routers.admin import router as admin_router
from app.routers.activity import router as activity_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(grid_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(payouts_router, prefix="/api/v1")
app.include_router(fraud_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")


# ── Health Checks ──
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "gridguard-ai", "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "GridGuard AI",
        "version": "1.0.0",
        "description": "AI-Powered Parametric Insurance for Gig Workers",
        "docs": "/docs",
    }
