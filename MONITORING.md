# 📊 Monitoring with Prometheus & Grafana

## 🚀 Quick Start

```bash
# Stop current services
docker-compose down

# Start all services (API + Redis + Prometheus + Grafana)
docker-compose up -d

# Check everything is running
docker-compose ps
```

## 🌐 Service Access

### Grafana Dashboard
- **URL**: http://localhost:3000
- **Username**: `admin`
- **Password**: `admin`
- **Dashboard**: "Weather Proxy API Dashboard" (pre-configured)

### Prometheus
- **URL**: http://localhost:9090
- **Targets**: http://localhost:9090/targets

### Weather API
- **URL**: http://localhost:8000
- **Metrics**: http://localhost:8000/metrics

## 📈 Grafana Dashboard - Available Panels

The pre-configured dashboard contains 6 panels:

### 1. **Request Rate**
- Shows requests per second
- Separated by endpoint and status code
- Useful for real-time traffic monitoring

### 2. **Error Rate**
- Percentage of errors (5xx) over total requests
- Gauge with thresholds:
  - 🟢 Green: < 0.5% errors
  - 🟡 Yellow: 0.5% - 1% errors
  - 🔴 Red: > 1% errors

### 3. **Request Latency**
- Shows p50 (median) and p95 (95th percentile)
- Helps detect slowdowns
- In seconds

### 4. **Cache Hit Rate**
- Percentage of requests served from cache
- Gauge with thresholds:
  - 🟢 Green: > 80% (excellent)
  - 🟡 Yellow: 50% - 80% (good)
  - 🔴 Red: < 50% (needs improvement)

### 5. **Requests by Status Code**
- Pie chart
- Shows distribution of HTTP codes (200, 400, 503, etc.)

### 6. **Total Requests**
- Total counter since startup
- With evolution graph

## 🔍 Available Metrics

### Request Metrics
```promql
# Request rate per second
rate(weather_proxy_requests_total[5m])

# Requests by endpoint
sum by (endpoint) (weather_proxy_requests_total)

# Requests by status
sum by (status) (weather_proxy_requests_total)
```

### Latency Metrics
```promql
# p95 latency
histogram_quantile(0.95, rate(weather_proxy_request_duration_seconds_bucket[5m]))

# p50 latency (median)
histogram_quantile(0.50, rate(weather_proxy_request_duration_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(weather_proxy_request_duration_seconds_bucket[5m]))
```

### Cache Metrics
```promql
# Cache hit rate
weather_proxy_cache_hits_total / (weather_proxy_cache_hits_total + weather_proxy_cache_misses_total)

# Cache hits
weather_proxy_cache_hits_total

# Cache misses
weather_proxy_cache_misses_total
```

### Error Metrics
```promql
# Error rate
rate(weather_proxy_requests_total{status=~"5.."}[5m]) / rate(weather_proxy_requests_total[5m])

# Number of 5xx errors
sum(weather_proxy_requests_total{status=~"5.."})
```

## 🎯 Usage

### 1. Generate Traffic
```bash
# A few requests to populate metrics
curl "http://localhost:8000/weather?city=Paris"
curl "http://localhost:8000/weather?city=London"
curl "http://localhost:8000/weather?city=Tokyo"
curl "http://localhost:8000/weather?city=Paris"  # Cache hit
curl "http://localhost:8000/health"
```

### 2. View Raw Metrics
```bash
curl http://localhost:8000/metrics
```

### 3. Access Grafana
1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. The "Weather Proxy API Dashboard" is already configured
4. Click on the dashboard to view your metrics

### 4. Explore Prometheus
1. Open http://localhost:9090
2. Go to "Status" > "Targets" to see if the API is being scraped
3. Use the "Graph" tab to execute PromQL queries

## 🛠️ Configuration

### Modify Prometheus Scrape Interval
Edit `monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s  # Modify here (default: 15s)
```

### Add Alerts
Create `monitoring/alerts.yml` and add to `prometheus.yml`:
```yaml
rule_files:
  - "alerts.yml"
```

### Customize Dashboard
1. Modify dashboard in Grafana UI
2. Export JSON
3. Replace `monitoring/grafana-dashboard.json`

## 📊 Ports Used

| Service | Port | URL |
|---------|------|-----|
| Weather API | 8000 | http://localhost:8000 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |
| Redis | 6379 | localhost:6379 |

## 🔧 Troubleshooting

### Grafana Can't Connect to Prometheus
```bash
# Check Prometheus is running
docker logs weather-proxy-prometheus

# Check network connection
docker exec weather-proxy-grafana ping prometheus
```

### No Data in Grafana
```bash
# Check API is being scraped
curl http://localhost:9090/api/v1/targets

# Generate traffic
for i in {1..10}; do curl "http://localhost:8000/weather?city=Paris"; done
```

### Reset Grafana
```bash
docker-compose down
docker volume rm exo_qbiq_grafana-data
docker-compose up -d
```

## 📝 Configuration Files

```
monitoring/
├── prometheus.yml              # Prometheus config
├── grafana-datasource.yml      # Prometheus datasource
├── grafana-dashboards.yml      # Dashboard provisioning
└── grafana-dashboard.json      # Weather Proxy dashboard
```

## 🎨 Dashboard Customization

The dashboard is fully customizable in Grafana:
- Add/remove panels
- Modify PromQL queries
- Change colors and thresholds
- Add alerts
- Create template variables

Happy monitoring! 📊✨
