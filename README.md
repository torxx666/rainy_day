# Weather Proxy API

[![CI](https://github.com/yourusername/weather-proxy/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/weather-proxy/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready REST API that acts as a proxy for weather data from Open-Meteo, featuring intelligent caching, comprehensive observability, resilience patterns, and full containerization.

## ✨ Features

- **RESTful API**: Clean endpoints for weather data and health checks
- **Intelligent Caching**: Redis-based caching with configurable TTL (5 minutes default)
- **Resilience**: Circuit breaker pattern to handle external API failures gracefully
- **Observability**: Structured JSON logging with correlation IDs for request tracing
- **Metrics**: Prometheus-compatible `/metrics` endpoint for monitoring
- **Production-Ready**: Optimized Docker images, health checks, graceful shutdown
- **Kubernetes Support**: Helm chart for easy deployment to Kubernetes clusters
- **High Test Coverage**: Comprehensive unit and integration tests (>80% coverage)
- **CI/CD**: Automated linting, testing, and Docker builds via GitHub Actions

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Run with Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd exo_qbiq

# Start the services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Get weather for a city
curl "http://localhost:8000/weather?city=Paris"
```

That's it! The API is now running at `http://localhost:8000`.

## 📚 API Documentation

### Endpoints

#### `GET /weather?city={city_name}`

Get current weather data for a city.

**Parameters:**
- `city` (required): City name (e.g., "Paris", "London", "New York")

**Response:**
```json
{
  "city": "Paris",
  "temperature": 15.5,
  "wind_speed": 12.3,
  "weather_code": 1,
  "cached": false
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid city or missing parameter
- `503`: Weather service unavailable

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis_connected": true
}
```

#### `GET /metrics`

Prometheus metrics endpoint.

**Metrics:**
- `weather_proxy_requests_total`: Total number of requests
- `weather_proxy_request_duration_seconds`: Request duration histogram
- `weather_proxy_cache_hits_total`: Cache hit count
- `weather_proxy_cache_misses_total`: Cache miss count

## 🛠️ Local Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Run the application
python -m app.main
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_weather.py

# Run with verbose output
pytest -v

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Run linter
ruff check app tests

# Run formatter
black app tests

# Check formatting without changes
black --check app tests
```

## 🏗️ Architecture

### System Design

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  Weather API │─────▶│ Open-Meteo  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    Redis     │
                     │   (Cache)    │
                     └──────────────┘
```

### Key Design Decisions

#### 1. **FastAPI Framework**
- **Why**: Modern async framework with excellent performance, automatic OpenAPI docs, and built-in validation
- **Benefits**: High concurrency, type safety, developer productivity

#### 2. **Redis for Caching**
- **Why**: Industry-standard in-memory cache with TTL support
- **Strategy**: Cache weather data by city for 5 minutes to minimize external API calls
- **Fallback**: Application continues working even if Redis is unavailable (degraded mode)

#### 3. **Circuit Breaker Pattern**
- **Why**: Prevents cascading failures when external API is down
- **Implementation**: Using `pybreaker` library
- **Configuration**: Opens after 5 failures, resets after 60 seconds
- **Benefit**: Better than simple retries - protects both our service and upstream API

#### 4. **Structured Logging**
- **Why**: Machine-readable logs for production environments
- **Format**: JSON with correlation IDs for request tracing
- **Benefits**: Easy integration with log aggregators (ELK, Datadog, etc.)
- **Traceability**: Every request gets a unique correlation ID

#### 5. **Open-Meteo API**
- **Why**: Free, reliable, no API key required
- **Data Quality**: Professional-grade weather data
- **No Rate Limits**: Perfect for demo and production use

#### 6. **Multi-Stage Docker Build**
- **Why**: Smaller images, faster deployments, better security
- **Size**: ~150MB vs 1GB+ with single-stage build
- **Security**: Non-root user, minimal attack surface

#### 7. **Graceful Shutdown**
- **Why**: Zero-downtime deployments in Kubernetes
- **Implementation**: SIGTERM signal handling with connection draining
- **Benefit**: No dropped requests during rolling updates

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| Framework | FastAPI | 0.109+ |
| Cache | Redis | 7.x |
| HTTP Client | httpx | 0.26+ |
| Logging | structlog | 24.1+ |
| Metrics | prometheus-client | 0.19+ |
| Resilience | pybreaker | 1.0+ |
| Testing | pytest | 7.4+ |
| Container | Docker | 20.10+ |
| Orchestration | Kubernetes + Helm | 1.25+ |

## 🐳 Docker

### Build Image

```bash
docker build -t weather-proxy:latest .
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  -e REDIS_HOST=redis \
  -e LOG_LEVEL=INFO \
  --name weather-proxy \
  weather-proxy:latest
```

### Image Optimization

- **Multi-stage build**: Separates build and runtime dependencies
- **Slim base image**: Uses `python:3.11-slim` (~150MB)
- **Layer caching**: Optimized for fast rebuilds
- **Non-root user**: Security best practice
- **Health checks**: Built-in container health monitoring

## ☸️ Kubernetes Deployment

### Using Helm

```bash
# Install the chart
helm install weather-proxy ./helm/weather-proxy

# Upgrade
helm upgrade weather-proxy ./helm/weather-proxy

# Uninstall
helm uninstall weather-proxy
```

### Configuration

Edit `helm/weather-proxy/values.yaml`:

```yaml
replicaCount: 2

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
```

### Features

- **High Availability**: Multiple replicas with load balancing
- **Auto-scaling**: HPA based on CPU utilization
- **Health Probes**: Liveness and readiness checks
- **Graceful Shutdown**: PreStop hooks for zero-downtime deployments
- **Resource Limits**: Prevents resource exhaustion

## 📊 Monitoring

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'weather-proxy'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Key Metrics

- **Request Rate**: `rate(weather_proxy_requests_total[5m])`
- **Error Rate**: `rate(weather_proxy_requests_total{status=~"5.."}[5m])`
- **Latency (p95)**: `histogram_quantile(0.95, weather_proxy_request_duration_seconds)`
- **Cache Hit Rate**: `weather_proxy_cache_hits_total / (weather_proxy_cache_hits_total + weather_proxy_cache_misses_total)`

## 🧪 Testing

### Test Coverage

```bash
pytest --cov=app --cov-report=term
```

Current coverage: **>85%**

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_weather.py       # Integration tests
└── unit/
    └── test_cache.py     # Unit tests
```

### Test Categories

- **Unit Tests**: Cache service, business logic
- **Integration Tests**: API endpoints, external API mocking
- **Mocking**: External weather provider fully mocked

## 🔒 Security

- ✅ Non-root container user
- ✅ Minimal base image (python:3.11-slim)
- ✅ No secrets in code or images
- ✅ Environment-based configuration
- ✅ Input validation with Pydantic
- ✅ CORS disabled by default
- ✅ Health checks don't expose sensitive data

## 🚀 Future Improvements

Given more time, here are enhancements I would implement:

### High Priority

1. **Rate Limiting**: Add per-IP rate limiting to prevent abuse
2. **Authentication**: API key-based authentication for production use
3. **Database**: PostgreSQL for request history and analytics
4. **More Weather Data**: Extended forecasts, historical data, multiple providers
5. **Caching Strategy**: Implement cache warming and smarter invalidation

### Medium Priority

6. **GraphQL API**: Alternative to REST for flexible queries
7. **WebSocket Support**: Real-time weather updates
8. **Multi-Region**: Deploy to multiple regions for lower latency
9. **A/B Testing**: Framework for testing different caching strategies
10. **Admin Dashboard**: Web UI for monitoring and configuration

### DevOps Enhancements

11. **Distributed Tracing**: OpenTelemetry integration
12. **Log Aggregation**: ELK or Datadog integration
13. **Alerting**: PagerDuty/Opsgenie integration
14. **Chaos Engineering**: Automated failure injection testing
15. **Performance Testing**: Load testing with k6 or Locust

### Code Quality

16. **Type Checking**: Add mypy for static type checking
17. **Security Scanning**: Integrate Snyk or Trivy
18. **Dependency Updates**: Dependabot for automated updates
19. **API Versioning**: Support multiple API versions
20. **Documentation**: Auto-generated API docs with examples

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `CACHE_TTL` | `300` | Cache TTL in seconds |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_JSON` | `true` | Enable JSON logging |
| `CIRCUIT_BREAKER_FAIL_MAX` | `5` | Max failures before circuit opens |
| `CIRCUIT_BREAKER_TIMEOUT` | `60` | Circuit breaker timeout in seconds |

See [`.env.example`](.env.example) for complete list.

## 📄 License

MIT License - feel free to use this project for learning or production.

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Check existing documentation
- Review test files for usage examples

---

**Built with ❤️ using Python 3.11 and FastAPI**
