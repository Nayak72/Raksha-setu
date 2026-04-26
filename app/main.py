"""
FastAPI application factory with lifespan management.

Wires up:
  • MQTT client connect / disconnect
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
from app.mqtt.client import mqtt_manager
from app.db.listener import start_pg_listener, stop_pg_listener
from app.services.simulation_service import start_simulation, stop_simulation

logger = structlog.get_logger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────
# Lifespan: startup / shutdown hooks
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage async resources across the application lifecycle."""
    logger.info("raksha.startup", env=settings.app_env)

    # 1. Connect MQTT
    await mqtt_manager.connect()
    logger.info("mqtt.connected", broker=settings.mqtt.broker_host)

    # 2. Start Postgres NOTIFY listener (event-driven agents)
    listener_task = asyncio.create_task(start_pg_listener())
    logger.info("pg_listener.started")

    # 3. Start background auto-simulation (every 5s)
    start_simulation()
    logger.info("simulation.auto_started")

    yield  # ← application is running

    # Shutdown
    logger.info("raksha.shutdown")

    # Stop simulation loop
    await stop_simulation()
    
    # Signal stop and cancel the listener task
    await stop_pg_listener()
    listener_task.cancel()
    try:
        await listener_task
    except (asyncio.CancelledError, Exception):
        pass
        
    from app.db.supabase_client import close_pg_pool
    await close_pg_pool()
    
    await mqtt_manager.disconnect()
    logger.info("mqtt.disconnected")


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
