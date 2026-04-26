"""
RakshaSetu — Supabase / PostgreSQL Connection Manager
Provides connection pooling and query execution helpers for PostGIS-enabled Supabase.
"""

from psycopg2 import pool, extras
from contextlib import contextmanager
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Connection pool (min 2, max 10 connections)
_connection_pool = None


def init_pool():
    """Initialize the connection pool. Call once at startup."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=settings.supabase.db_host,
                port=settings.supabase.db_port,
                dbname=settings.supabase.db_name,
                user=settings.supabase.db_user,
                password=settings.supabase.db_password,
                sslmode="require",  # Supabase requires SSL
            )
            logger.info("Database connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize DB pool: {e}")
            raise
    return _connection_pool


@contextmanager
def get_connection():
    """Get a connection from the pool (context manager)."""
    if _connection_pool is None:
        init_pool()
    conn = _connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _connection_pool.putconn(conn)


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """Execute a query and optionally fetch results as dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                return [dict(row) for row in cur.fetchall()]
            return None


def execute_transaction(queries: list[tuple[str, tuple]]):
    """
    Execute multiple queries in a single atomic transaction.
    Each item is (query_string, params_tuple).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            for query, params in queries:
                cur.execute(query, params)
        # commit happens in context manager


def close_pool():
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed.")
