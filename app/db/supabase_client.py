"""
Async Supabase client singleton.

Provides:
  • `get_supabase()`  – returns the async Supabase client
  • `get_pg_pool()`   – returns a raw asyncpg connection pool
                        (used by the NOTIFY listener and direct queries)
"""

from __future__ import annotations

from typing import Optional

import asyncpg
import structlog
from supabase import create_client, Client

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# ── Supabase REST client (PostgREST wrapper) ─
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Return the Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.supabase.url,
            settings.supabase.service_key,
        )
        logger.info("supabase.client_created")
    return _supabase_client


# ── Raw asyncpg pool (for LISTEN/NOTIFY & advanced queries) ─
_pg_pool: Optional[asyncpg.Pool] = None


async def get_pg_pool() -> asyncpg.Pool:
    """Return a shared asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is None:
        # Convert the SQLAlchemy-style URL to a plain DSN
        dsn = settings.supabase.connection_string.replace("postgresql+asyncpg://", "postgresql://")
        _pg_pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
            statement_cache_size=0,  # Required for Supabase pgbouncer pooler
        )
        logger.info("asyncpg.pool_created", min=2, max=10)
    return _pg_pool


async def close_pg_pool() -> None:
    """Gracefully close the connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("asyncpg.pool_closed")
