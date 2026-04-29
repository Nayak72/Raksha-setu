"""
FastAPI application factory with lifespan management.

Wires up:
  • UDP broadcast layer
  • Supabase Realtime listener
  • Structured logging
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as api_router

from app.services.simulation import engine
from app.db.listener import start_pg_listener, stop_pg_listener

logger = structlog.get_logger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage async resources across the application lifecycle."""
    logger.info("raksha.startup", env=settings.app_env)

    # Start the simulation loop
    engine.start()
    logger.info("simulation.auto_started")
    
    # Start the Postgres listener for event-driven workflow
    asyncio.create_task(start_pg_listener())
    logger.info("pg_listener.auto_started")

    yield  # ← application is running

    # Shutdown
    logger.info("raksha.shutdown")
    await engine.stop()
    await stop_pg_listener()


# ─────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────
def create_app() -> FastAPI:
    """Build and return the configured FastAPI instance."""
    app = FastAPI(
        title="RakshaSethu – Disaster Response API",
        description=(
            "Agentic backend for real-time disaster detection, "
            "volunteer dispatch, shelter management, and alert broadcast."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS – allow all origins in dev; lock down in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=False if settings.app_debug else True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API router
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
