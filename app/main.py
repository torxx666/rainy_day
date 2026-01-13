"""FastAPI application with observability and graceful shutdown."""

import asyncio
import signal
import sys
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    
    # Warm cache in background (non-blocking) after a small delay
    if settings.cache_warming_enabled:
        logger.info("cache_warming_task_scheduled")
        
        async def delayed_cache_warming():
            try:
                await asyncio.sleep(2)  # Wait 2 seconds for everything to be ready
                logger.info("cache_warming_task_starting")
                from app.services.cache_warmer import warm_cache
                result = await warm_cache()
                logger.info("cache_warming_task_completed", result=result)
            except Exception as e:
                logger.error("cache_warming_task_failed", error=str(e), exc_info=True)
        
        asyncio.create_task(delayed_cache_warming())
    else:
        logger.info("cache_warming_disabled_in_config")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    await cache.disconnect()
    await weather_service.close()
    logger.info("application_stopped")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-ready weather proxy API with caching, monitoring, and resilience patterns",
    lifespan=lifespan,
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Combined health check",
    description="Returns overall service health including Redis connection status",
    tags=["Health"],
)
async def health_check():
    """Combined health check endpoint.
    
    Returns service health status and Redis connection state.
    This endpoint checks both application liveness and readiness.
    """
    redis_connected = await cache.is_connected()
    
    logger.info("health_check", redis_connected=redis_connected)
    
    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        version=settings.app_version,
        redis_connected=redis_connected,
    )


@app.get(
    "/health/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe - checks if application is running",
    tags=["Health"],
    status_code=200,
)
async def liveness():
    """Liveness probe for Kubernetes.
    
    Returns 200 if the application is alive and running.
    This endpoint should always return 200 unless the application is completely dead.
    """
    return {"status": "alive"}


@app.get(
    "/health/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Kubernetes readiness probe - checks if application can serve traffic",
    tags=["Health"],
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"},
    },
)
async def readiness():
    """Readiness probe for Kubernetes.
    
    Returns 200 if the application is ready to serve traffic.
    Checks Redis connectivity and other critical dependencies.
    
    Raises:
        HTTPException: 503 if service is not ready
    """
    redis_connected = await cache.is_connected()
    
    if not redis_connected:
        logger.warning("readiness_check_failed", redis_connected=False)
        raise HTTPException(
            status_code=503,
            detail="Service not ready: Redis not connected",
        )
    
    return HealthResponse(
        status="ready",
        version=settings.app_version,
        redis_connected=redis_connected,
    )


@app.get(
    "/weather",
    response_model=WeatherData,
    summary="Get weather for a city",
    description="""Fetch current weather data for a specified city.
    
    This endpoint returns real-time weather information including temperature,
    wind speed, and weather conditions. Results are cached for 5 minutes to
    optimize performance and reduce external API calls.
    
    **Rate Limit**: 100 requests per minute per IP address
    """,
    response_description="Weather data with temperature in Celsius, wind speed in km/h",
    tags=["Weather"],
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "city": "Paris",
                        "temperature": 15.5,
                        "wind_speed": 12.3,
                        "weather_code": 1,
                        "cached": False,
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid city name or city not found",
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Rate limit exceeded",
                        "detail": "Too many requests. Limit: 100 per 1 minute",
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Weather service unavailable",
        },
    },
)
@limiter.limit("100/minute")
async def get_weather(request: Request, city: str):
    """Get weather data for a city.
    
    Args:
        request: FastAPI request object (for rate limiting)
        city: City name (e.g., "Paris", "London", "Tokyo")
        
    Returns:
        Weather data including temperature, wind speed, and weather code
        
    Raises:
        HTTPException: If city not found (400) or service unavailable (503)
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


@app.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Exposes application metrics in Prometheus format for monitoring and alerting",
    tags=["Monitoring"],
)
async def metrics():
    """Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format including:
    - Request counts by endpoint and status code
    - Request duration histograms
    - Cache hit/miss counters
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
