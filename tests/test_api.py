"""
Integration tests for the RakshaSethu API.

Uses httpx.AsyncClient for fully async test execution.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client that bypasses network listeners."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────
# Health / Status
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_status_endpoint(client: AsyncClient):
    """GET /status should return system health."""
    response = await client.get("/api/v1/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "operational"
    assert "udp_active" in data
    assert "pg_listener_active" in data
    assert "uptime_seconds" in data


# ─────────────────────────────────────────────
# Detection
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_detect_validation(client: AsyncClient):
    """POST /detect should reject invalid payloads."""
    # Missing required fields
    response = await client.post("/api/v1/detect", json={})
    assert response.status_code == 422

    # Negative count
    response = await client.post("/api/v1/detect", json={
        "zone_id": "00000000-0000-0000-0000-000000000001",
        "count": -1,
    })
    assert response.status_code == 422


# ─────────────────────────────────────────────
# Weather Simulation
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_weather_validation(client: AsyncClient):
    """POST /simulate-weather should validate intensity range."""
    response = await client.post("/api/v1/simulate-weather", json={
        "zone_id": "00000000-0000-0000-0000-000000000001",
        "event_type": "flood",
        "intensity": 15.0,  # exceeds max 10.0
    })
    assert response.status_code == 422


# ─────────────────────────────────────────────
# Alert Broadcast
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_alert_validation(client: AsyncClient):
    """POST /broadcast-alert should validate severity enum."""
    response = await client.post("/api/v1/broadcast-alert", json={
        "zone": "test-zone",
        "message": "Test alert",
        "severity": "invalid_level",
    })
    assert response.status_code == 422

