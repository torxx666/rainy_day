# 📊 Manual Grafana Setup

## ⚠️ Important Note

Due to automatic provisioning issues, we'll configure Grafana manually. It's very simple and takes only 2 minutes!

## 🚀 Setup Steps

### 1. Access Grafana
- Open http://localhost:3000
- Username: `admin`
- Password: `admin`

### 2. Add Prometheus Datasource

1. Click the hamburger menu (☰) in the top left
2. Go to **"Connections"** → **"Data sources"**
3. Click **"Add data source"**
4. Select **"Prometheus"**
5. Configure:
   - **Name**: `Prometheus`
   - **URL**: `http://prometheus:9090`
   - Leave other parameters as default
6. Click **"Save & Test"** at the bottom
7. You should see a green message ✅ "Successfully queried the Prometheus API"

### 3. Import Dashboard

1. Click menu (☰) → **"Dashboards"**
2. Click **"New"** → **"Import"**
3. Click **"Upload dashboard JSON file"**
4. Select the file: `d:\DCO\EXO_Boite\exo_qbiq\monitoring\grafana-dashboard.json`
5. On the import page:
   - **Name**: Weather Proxy API Dashboard
   - **Folder**: General
   - **Prometheus**: Select "Prometheus" (the datasource you just created)
6. Click **"Import"**

### 4. View Metrics

The dashboard should now display 6 panels:
- Request Rate
- Error Rate  
- Request Latency
- Cache Hit Rate
- Requests by Status Code
- Total Requests

## 🎯 Generate Traffic

To see data in the graphs:

```powershell
# PowerShell
for ($i=1; $i -le 20; $i++) { 
    curl "http://localhost:8000/weather?city=Paris"
    curl "http://localhost:8000/weather?city=London"
    curl "http://localhost:8000/health"
    Start-Sleep -Milliseconds 200
}
```

After a few seconds, refresh the dashboard and you'll see the metrics!

## 📈 Available Metrics

Here are the PromQL queries used in the dashboard:

### Request Rate
```promql
rate(weather_proxy_requests_total[5m])
```

### Error Rate
```promql
rate(weather_proxy_requests_total{status=~"5.."}[5m]) / rate(weather_proxy_requests_total[5m])
```

### Latency p95
```promql
histogram_quantile(0.95, rate(weather_proxy_request_duration_seconds_bucket[5m]))
```

### Cache Hit Rate
```promql
weather_proxy_cache_hits_total / (weather_proxy_cache_hits_total + weather_proxy_cache_misses_total)
```

## 🔧 Troubleshooting

### Datasource Won't Connect
```bash
# Check Prometheus is running
docker logs weather-proxy-prometheus

# Test from Grafana
docker exec weather-proxy-grafana wget -O- http://prometheus:9090/api/v1/query?query=up
```

### No Data in Graphs
1. Check Prometheus is scraping the API: http://localhost:9090/targets
2. Generate traffic with the commands above
3. Wait 15-30 seconds
4. Refresh the dashboard

## ✅ Quick Verification

```bash
# Check all services are running
docker-compose ps

# Test the API
curl http://localhost:8000/health

# View raw metrics
curl http://localhost:8000/metrics

# Check Prometheus
curl http://localhost:9090/api/v1/query?query=up
```

Happy monitoring! 📊
