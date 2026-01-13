"""Weather service with circuit breaker and caching."""

import hashlib
from typing import Any

import httpx
from pybreaker import CircuitBreaker, CircuitBreakerError

from app.core.config import settings
from app.core.logging import get_logger
from app.models.weather import WeatherData
from app.services.cache import cache

logger = get_logger(__name__)

# Circuit breaker for external API calls
weather_breaker = CircuitBreaker(
    fail_max=settings.circuit_breaker_fail_max,
    reset_timeout=settings.circuit_breaker_timeout,
    name="weather_api",
)


class WeatherServiceError(Exception):
    """Weather service error."""

    pass


class WeatherService:
    """Weather data service with caching and resilience."""

    def __init__(self):
        """Initialize weather service with optimized connection pooling."""
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0,
            ),
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.close()

    def _generate_cache_key(self, city: str) -> str:
        """Generate cache key for city.
        
        Args:
            city: City name
            
        Returns:
            Cache key
        """
        city_normalized = city.lower().strip()
        return f"weather:{hashlib.md5(city_normalized.encode()).hexdigest()}"

    async def _geocode_city(self, city: str) -> tuple[float, float]:
        """Get coordinates for city name.
        
        Args:
            city: City name
            
        Returns:
            Tuple of (latitude, longitude)
            
        Raises:
            WeatherServiceError: If city not found
        """
        try:
            response = await self.client.get(
                settings.geocoding_api_url,
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("results"):
                raise WeatherServiceError(f"City '{city}' not found")

            result = data["results"][0]
            return result["latitude"], result["longitude"]

        except httpx.HTTPError as e:
            logger.error("geocoding_failed", city=city, error=str(e))
            raise WeatherServiceError(f"Geocoding failed: {str(e)}")

    @weather_breaker
    async def _fetch_weather_data(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Fetch weather data from external API.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Weather data
            
        Raises:
            WeatherServiceError: If API call fails
        """
        try:
            response = await self.client.get(
                settings.weather_api_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current_weather": "true",
                },
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "weather_api_failed",
                latitude=latitude,
                longitude=longitude,
                error=str(e),
            )
            raise WeatherServiceError(f"Weather API failed: {str(e)}")

    async def get_weather(self, city: str) -> WeatherData:
        """Get weather data for city with caching.
        
        Args:
            city: City name
            
        Returns:
            Weather data
            
        Raises:
            WeatherServiceError: If weather data cannot be retrieved
        """
        logger.info("weather_request", city=city)

        # Check cache first
        cache_key = self._generate_cache_key(city)
        cached_data = await cache.get(cache_key)

        if cached_data:
            logger.info("weather_cache_hit", city=city)
            return WeatherData(**cached_data, cached=True)

        # Cache miss - fetch from API
        logger.info("weather_cache_miss", city=city)

        try:
            # Geocode city
            latitude, longitude = await self._geocode_city(city)
            logger.info("geocoding_success", city=city, latitude=latitude, longitude=longitude)

            # Fetch weather data
            weather_data = await self._fetch_weather_data(latitude, longitude)
            current = weather_data.get("current_weather", {})

            # Build response
            result = WeatherData(
                city=city,
                temperature=current.get("temperature", 0.0),
                wind_speed=current.get("windspeed", 0.0),
                weather_code=current.get("weathercode", 0),
                cached=False,
            )

            # Cache the result
            await cache.set(cache_key, result.model_dump(exclude={"cached"}))
            logger.info("weather_fetched", city=city, temperature=result.temperature)

            return result

        except CircuitBreakerError:
            logger.error("circuit_breaker_open", city=city)
            raise WeatherServiceError("Weather service temporarily unavailable (circuit breaker open)")

        except WeatherServiceError:
            raise

        except Exception as e:
            logger.error("weather_service_error", city=city, error=str(e))
            raise WeatherServiceError(f"Unexpected error: {str(e)}")


# Global weather service instance
weather_service = WeatherService()
