"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "Weather Proxy API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    cache_ttl: int = 300  # 5 minutes

    # Weather API
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    geocoding_api_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    request_timeout: int = 10

    # Circuit Breaker
    circuit_breaker_fail_max: int = 5
    circuit_breaker_timeout: int = 60

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # Cache Warming
    cache_warming_enabled: bool = True
    popular_cities: list[str] = ["Netanya","Raanana",
        "Paris", "London", "New York", "Tokyo", "Berlin",
        "Sydney", "Moscow", "Dubai", "Singapore", "Los Angeles"
    ]


settings = Settings()
