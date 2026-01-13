"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.cache import cache


@pytest.mark.asyncio
async def test_health_endpoint(mock_redis):
    """Test combined health check endpoint."""
    cache.redis = mock_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "redis_connected" in data


@pytest.mark.asyncio
async def test_liveness_probe():
    """Test liveness probe endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe_healthy(mock_redis):
    """Test readiness probe when service is ready."""
    cache.redis = mock_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["redis_connected"] is True


@pytest.mark.asyncio
async def test_readiness_probe_not_ready():
    """Test readiness probe when service is not ready."""
    # Disconnect cache to simulate not ready state
    cache.redis = None
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    
    assert response.status_code == 503
    data = response.json()
    assert "not ready" in data["detail"].lower()
