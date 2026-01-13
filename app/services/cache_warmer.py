"""Cache warming service to pre-populate cache with popular cities."""

import asyncio
from typing import List

from prometheus_client import Counter, Histogram

from app.core.config import settings
from app.core.logging import get_logger
from app.services.weather import WeatherServiceError, weather_service

logger = get_logger(__name__)

# Metrics
CACHE_WARMING_DURATION = Histogram(
    "weather_proxy_cache_warming_duration_seconds",
    "Time taken to warm cache",
)
CACHE_WARMING_CITIES = Counter(
    "weather_proxy_cache_warming_cities_total",
    "Number of cities warmed in cache",
    ["status"],
)


async def warm_city(city: str) -> bool:
    """Warm cache for a single city.
    
    Args:
        city: City name to warm cache for
        
    Returns:
        True if successful, False otherwise
    """
    try:
        await weather_service.get_weather(city)
        logger.info("cache_warming_city_success", city=city)
        CACHE_WARMING_CITIES.labels(status="success").inc()
        return True
    except WeatherServiceError as e:
        logger.warning("cache_warming_city_failed", city=city, error=str(e))
        CACHE_WARMING_CITIES.labels(status="failed").inc()
        return False
    except Exception as e:
        logger.error("cache_warming_city_error", city=city, error=str(e))
        CACHE_WARMING_CITIES.labels(status="error").inc()
        return False


@CACHE_WARMING_DURATION.time()
async def warm_cache(cities: List[str] | None = None) -> dict[str, int]:
    """Warm cache with weather data for popular cities.
    
    Args:
        cities: Optional list of cities to warm. Uses settings.popular_cities if None.
        
    Returns:
        Dictionary with success and failure counts
    """
    if not settings.cache_warming_enabled:
        logger.info("cache_warming_disabled")
        return {"success": 0, "failed": 0}
    
    cities_to_warm = cities or settings.popular_cities
    
    logger.info(
        "cache_warming_started",
        cities_count=len(cities_to_warm),
        cities=cities_to_warm,
    )
    
    # Warm cities concurrently
    tasks = [warm_city(city) for city in cities_to_warm]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    success_count = sum(1 for r in results if r is True)
    failed_count = len(results) - success_count
    
    logger.info(
        "cache_warming_completed",
        total=len(cities_to_warm),
        success=success_count,
        failed=failed_count,
    )
    
    return {"success": success_count, "failed": failed_count}
