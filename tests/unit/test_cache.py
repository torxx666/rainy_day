"""Unit tests for cache service."""

import json

import pytest

from app.services.cache import CacheService


@pytest.mark.asyncio
async def test_cache_set_and_get(mock_redis):
    """Test setting and getting cache values."""
    cache_service = CacheService()
    cache_service.redis = mock_redis

    # Set value
    test_data = {"city": "Paris", "temperature": 15.5}
    result = await cache_service.set("test_key", test_data)
    assert result is True

    # Get value
    cached_value = await cache_service.get("test_key")
    assert cached_value == test_data


@pytest.mark.asyncio
async def test_cache_miss(mock_redis):
    """Test cache miss returns None."""
    cache_service = CacheService()
    cache_service.redis = mock_redis

    result = await cache_service.get("nonexistent_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_without_redis():
    """Test cache operations when Redis is not connected."""
    cache_service = CacheService()
    cache_service.redis = None

    # Set should return False
    result = await cache_service.set("key", {"data": "value"})
    assert result is False

    # Get should return None
    result = await cache_service.get("key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_is_connected(mock_redis):
    """Test Redis connection check."""
    cache_service = CacheService()
    cache_service.redis = mock_redis

    is_connected = await cache_service.is_connected()
    assert is_connected is True


@pytest.mark.asyncio
async def test_cache_is_not_connected():
    """Test Redis connection check when not connected."""
    cache_service = CacheService()
    cache_service.redis = None

    is_connected = await cache_service.is_connected()
    assert is_connected is False
