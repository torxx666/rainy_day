"""FastAPI application with observability and graceful shutdown."""

import signal
import sys
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.models.weather import ErrorResponse, HealthResponse, WeatherData
from app.services.cache import cache
from app.services.weather import WeatherServiceError, weather_service

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "weather_proxy_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "weather_proxy_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)
CACHE_HITS = Counter("weather_proxy_cache_hits_total", "Total number of cache hits")
CACHE_MISSES = Counter("weather_proxy_cache_misses_total", "Total number of cache misses")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("application_starting", version=settings.app_version)
    
    try:
        await cache.connect()
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise
    
    logger.info("application_started")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    await cache.disconnect()
    await weather_service.close()
    logger.info("application_stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to each request for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    
    # Bind correlation ID to structlog context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics."""
    method = request.method
    path = request.url.path
    
    with REQUEST_DURATION.labels(method=method, endpoint=path).time():
        response = await call_next(request)
    
    REQUEST_COUNT.labels(method=method, endpoint=path, status=response.status_code).inc()
    
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    
    Returns service health status and Redis connection state.
    """
    redis_connected = await cache.is_connected()
    
    logger.info("health_check", redis_connected=redis_connected)
    
    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        version=settings.app_version,
        redis_connected=redis_connected,
    )


@app.get("/weather", response_model=WeatherData, responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def get_weather(city: str):
    """Get weather data for a city.
    
    Args:
        city: City name (e.g., "Paris", "London")
        
    Returns:
        Weather data including temperature, wind speed, and weather code
        
    Raises:
        HTTPException: If city not found or service unavailable
    """
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")
    
    try:
        weather_data = await weather_service.get_weather(city)
        
        # Update cache metrics
        if weather_data.cached:
            CACHE_HITS.inc()
        else:
            CACHE_MISSES.inc()
        
        return weather_data
    
    except WeatherServiceError as e:
        logger.error("weather_request_failed", city=city, error=str(e))
        
        if "not found" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format.
    """
    return generate_latest()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals for graceful shutdown."""
    logger.info("shutdown_signal_received", signal=signum)
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
