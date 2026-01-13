"""Integration tests for weather API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.cache import cache


@pytest.mark.asyncio
async def test_health_endpoint(mock_redis):
    """Test health check endpoint."""
    cache.redis = mock_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "redis_connected" in data


@pytest.mark.asyncio
async def test_weather_endpoint_success(mock_redis, mock_geocoding_response, mock_weather_response):
    """Test successful weather retrieval."""
    cache.redis = mock_redis
    
    with patch("app.services.weather.weather_service.client.get") as mock_get:
        # Mock geocoding and weather API calls
        mock_get.side_effect = [
            AsyncMock(
                status_code=200,
                json=lambda: mock_geocoding_response,
                raise_for_status=lambda: None,
            ),
            AsyncMock(
                status_code=200,
                json=lambda: mock_weather_response,
                raise_for_status=lambda: None,
            ),
        ]
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/weather?city=Paris")
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Paris"
        assert data["temperature"] == 15.5
        assert data["wind_speed"] == 12.3
        assert data["weather_code"] == 1
        assert data["cached"] is False


@pytest.mark.asyncio
async def test_weather_endpoint_cached(mock_redis):
    """Test cached weather retrieval."""
    cache.redis = mock_redis
    
    # Pre-populate cache
    cached_data = {
        "city": "London",
        "temperature": 12.0,
        "wind_speed": 8.5,
        "weather_code": 2,
    }
    await cache.set("weather:98d6f4e4aaf0a59e1b0e1e2e1e1e1e1e", cached_data)
    
    # Mock the cache key generation to match
    with patch("app.services.weather.WeatherService._generate_cache_key") as mock_key:
        mock_key.return_value = "weather:98d6f4e4aaf0a59e1b0e1e2e1e1e1e1e"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/weather?city=London")
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "London"
        assert data["cached"] is True


@pytest.mark.asyncio
async def test_weather_endpoint_invalid_city(mock_redis):
    """Test weather endpoint with invalid city."""
    cache.redis = mock_redis
    
    with patch("app.services.weather.weather_service.client.get") as mock_get:
        # Mock geocoding API returning no results
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"results": []},
            raise_for_status=lambda: None,
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/weather?city=InvalidCity123")
        
        assert response.status_code == 400
        data = response.json()
        assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_weather_endpoint_missing_city(mock_redis):
    """Test weather endpoint without city parameter."""
    cache.redis = mock_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/weather?city=")
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_weather_endpoint_api_failure(mock_redis, mock_geocoding_response):
    """Test weather endpoint when external API fails."""
    cache.redis = mock_redis
    
    with patch("app.services.weather.weather_service.client.get") as mock_get:
        # Mock successful geocoding but failed weather API
        async def side_effect(*args, **kwargs):
            if "geocoding" in args[0]:
                return AsyncMock(
                    status_code=200,
                    json=lambda: mock_geocoding_response,
                    raise_for_status=lambda: None,
                )
            else:
                # Create a mock that raises when raise_for_status is called
                mock_response = AsyncMock()
                
                def raise_error():
                    raise Exception("API Error")
                
                mock_response.raise_for_status = raise_error
                return mock_response
        
        mock_get.side_effect = side_effect
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/weather?city=Paris")
        
        assert response.status_code == 503



@pytest.mark.asyncio
async def test_metrics_endpoint(mock_redis):
    """Test Prometheus metrics endpoint."""
    cache.redis = mock_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    
    assert response.status_code == 200
    assert "weather_proxy_requests_total" in response.text


@pytest.mark.asyncio
async def test_correlation_id_header(mock_redis):
    """Test that correlation ID is added to responses."""
    cache.redis = mock_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    
    assert "X-Correlation-ID" in response.headers
