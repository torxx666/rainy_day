"""Tests for cache warming functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.cache_warmer import warm_cache, warm_city
from app.core.config import settings


@pytest.mark.asyncio
async def test_warm_city_success(mock_redis):
    """Test warming cache for a single city successfully."""
    from app.services.cache import cache
    cache.redis = mock_redis
    
    with patch("app.services.cache_warmer.weather_service.get_weather") as mock_get:
        mock_get.return_value = AsyncMock()
        
        result = await warm_city("Paris")
        
        assert result is True
        mock_get.assert_called_once_with("Paris")


@pytest.mark.asyncio
async def test_warm_city_failure(mock_redis):
    """Test warming cache when weather service fails."""
    from app.services.cache import cache
    from app.services.weather import WeatherServiceError
    cache.redis = mock_redis
    
    with patch("app.services.cache_warmer.weather_service.get_weather") as mock_get:
        mock_get.side_effect = WeatherServiceError("City not found")
        
        result = await warm_city("InvalidCity")
        
        assert result is False


@pytest.mark.asyncio
async def test_warm_cache_success(mock_redis, monkeypatch):
    """Test warming cache for multiple cities."""
    from app.services.cache import cache
    cache.redis = mock_redis
    
    # Use a small list for testing
    test_cities = ["Paris", "London", "Tokyo"]
    monkeypatch.setattr(settings, "popular_cities", test_cities)
    
    with patch("app.services.cache_warmer.weather_service.get_weather") as mock_get:
        mock_get.return_value = AsyncMock()
        
        result = await warm_cache()
        
        assert result["success"] == 3
        assert result["failed"] == 0
        assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_warm_cache_partial_failure(mock_redis, monkeypatch):
    """Test warming cache with some failures."""
    from app.services.cache import cache
    from app.services.weather import WeatherServiceError
    cache.redis = mock_redis
    
    test_cities = ["Paris", "InvalidCity", "London"]
    monkeypatch.setattr(settings, "popular_cities", test_cities)
    
    async def mock_get_weather(city):
        if city == "InvalidCity":
            raise WeatherServiceError("City not found")
        return AsyncMock()
    
    with patch("app.services.cache_warmer.weather_service.get_weather") as mock_get:
        mock_get.side_effect = mock_get_weather
        
        result = await warm_cache()
        
        assert result["success"] == 2
        assert result["failed"] == 1


@pytest.mark.asyncio
async def test_warm_cache_disabled(monkeypatch):
    """Test that cache warming can be disabled."""
    monkeypatch.setattr(settings, "cache_warming_enabled", False)
    
    result = await warm_cache()
    
    assert result["success"] == 0
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_warm_cache_custom_cities(mock_redis):
    """Test warming cache with custom city list."""
    from app.services.cache import cache
    cache.redis = mock_redis
    
    custom_cities = ["Berlin", "Sydney"]
    
    with patch("app.services.cache_warmer.weather_service.get_weather") as mock_get:
        mock_get.return_value = AsyncMock()
        
        result = await warm_cache(cities=custom_cities)
        
        assert result["success"] == 2
        assert mock_get.call_count == 2
