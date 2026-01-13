"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from fakeredis import FakeAsyncRedis

from app.main import app
from app.services.cache import cache


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
async def mock_redis(monkeypatch):
    """Mock Redis with fakeredis."""
    fake_redis = FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(cache, "redis", fake_redis)
    return fake_redis


@pytest.fixture
def mock_geocoding_response():
    """Mock geocoding API response."""
    return {
        "results": [
            {
                "id": 2988507,
                "name": "Paris",
                "latitude": 48.85341,
                "longitude": 2.3488,
                "country": "France",
            }
        ]
    }


@pytest.fixture
def mock_weather_response():
    """Mock weather API response."""
    return {
        "current_weather": {
            "temperature": 15.5,
            "windspeed": 12.3,
            "weathercode": 1,
            "time": "2024-01-13T12:00",
        }
    }
