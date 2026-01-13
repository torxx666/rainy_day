"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    """Weather data response model."""

    city: str = Field(..., description="City name")
    temperature: float = Field(..., description="Current temperature in Celsius")
    wind_speed: float = Field(..., description="Wind speed in km/h")
    weather_code: int = Field(..., description="WMO weather code")
    cached: bool = Field(default=False, description="Whether data was served from cache")


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    redis_connected: bool = Field(..., description="Redis connection status")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")
