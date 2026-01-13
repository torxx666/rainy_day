"""Integration tests for advanced caching functionality."""

import pytest
from app.services.cache import cache


@pytest.mark.asyncio
async def test_cache_get_stale(mock_redis):
    """Test getting stale cache values."""
    cache.redis = mock_redis
    
    # Set a value
    test_data = {"city": "Paris", "temperature": 15.5}
    await cache.set("test_key", test_data)
    
    # Get stale value (should work even if TTL expired)
    stale_value = await cache.get_stale("test_key")
    assert stale_value is not None
    assert stale_value["city"] == "Paris"


@pytest.mark.asyncio
async def test_cache_get_stale_not_found(mock_redis):
    """Test getting stale value for non-existent key."""
    cache.redis = mock_redis
    
    stale_value = await cache.get_stale("nonexistent_key")
    assert stale_value is None


@pytest.mark.asyncio
async def test_cache_get_stale_no_redis():
    """Test getting stale value when Redis is not connected."""
    cache.redis = None
    
    stale_value = await cache.get_stale("test_key")
    assert stale_value is None


@pytest.mark.asyncio
async def test_cache_set_and_get(mock_redis):
    """Test basic cache set and get operations."""
    cache.redis = mock_redis
    
    test_data = {"city": "London", "temperature": 12.0}
    
    # Set value
    result = await cache.set("test_key", test_data)
    assert result is True
    
    # Get value
    cached_value = await cache.get("test_key")
    assert cached_value is not None
    assert cached_value["city"] == "London"


@pytest.mark.asyncio
async def test_cache_miss(mock_redis):
    """Test cache miss scenario."""
    cache.redis = mock_redis
    
    value = await cache.get("nonexistent_key")
    assert value is None
