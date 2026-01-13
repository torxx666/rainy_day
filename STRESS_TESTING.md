# Stress Testing Guide

## 🎯 Purpose

These scripts perform progressive load testing to find the breaking point of your Weather Proxy API. They gradually increase the load and monitor:
- Response times (avg, min, max, p50, p95, p99)
- Success/failure rates
- Requests per second
- Breaking points

## 📋 Available Scripts

### 1. Python Script (Recommended)
**File**: `stress_test.py`

**Requirements**:
```bash
pip install requests rich
```

**Usage**:
```bash
python stress_test.py
```

**Features**:
- Beautiful colored output with tables
- Progressive load testing (10 → 2000 requests)
- Automatic breaking point detection
- Detailed statistics

---

### 2. PowerShell Script (Windows)
**File**: `stress_test.ps1`

**Usage**:
```powershell
.\stress_test.ps1
```

**Features**:
- Native Windows support
- Parallel job execution
- Same progressive testing as Python version

---

## 🚀 Test Progression

Both scripts run the following test sequence:

| Test | Requests | Concurrent Workers | Description |
|------|----------|-------------------|-------------|
| 1 | 10 | 2 | Warm-up |
| 2 | 50 | 5 | Light load |
| 3 | 100 | 10 | Medium load |
| 4 | 200 | 20 | Heavy load |
| 5 | 500 | 50 | Very heavy load |
| 6 | 1000 | 100 | Extreme load |
| 7 | 2000 | 200 | Breaking point test |

The test **stops automatically** when:
- Success rate drops below 95%
- Average response time exceeds 5 seconds

## 📊 Metrics Reported

For each test, you'll see:

### Request Statistics
- Total requests sent
- Successful requests (count + percentage)
- Failed requests (count + percentage)
- Test duration
- Requests per second

### Response Time Statistics
- Average response time
- Minimum response time
- Maximum response time
- p50 (median)
- p95 (95th percentile)
- p99 (99th percentile)

## 🎯 How to Use

### Step 1: Start Your API
```bash
docker-compose up -d
```

### Step 2: Run Stress Test

**Python**:
```bash
python stress_test.py
```

**PowerShell**:
```powershell
.\stress_test.ps1
```

### Step 3: Monitor in Grafana

While the test runs, open Grafana to see real-time impact:
- **URL**: http://localhost:3000
- **Dashboard**: "Weather Proxy API Dashboard"

You'll see:
- Request rate spike
- Latency increase
- Cache hit rate
- Error rate (if breaking point is reached)

### Step 4: Analyze Results

The script will tell you:
- ✅ **Success**: API handled the load well
- ⚠️ **Warning**: High latency detected
- 🔴 **Breaking Point**: API started failing

## 📈 Expected Results

### Healthy API
```
Test: Medium load
Requests: 100, Concurrent workers: 10

Total Requests:     100
Successful:         100 (100.0%)
Failed:             0
Duration:           2.34s
Requests/sec:       42.74

Avg Response Time:  234.56ms
p95:                456.78ms
p99:                567.89ms
```

### Breaking Point
```
Test: Extreme load
Requests: 1000, Concurrent workers: 100

Total Requests:     1000
Successful:         923 (92.3%)  ← Below 95%
Failed:             77
Duration:           45.67s

⚠️  API Breaking Point Detected!
Breaking point: ~100 concurrent requests
```

## 🔧 Customization

### Modify Test Levels (Python)

Edit `stress_test.py`:
```python
test_configs = [
    (50, 5, "Custom test 1"),
    (100, 10, "Custom test 2"),
    # Add your own configurations
]
```

### Modify Test Levels (PowerShell)

Edit `stress_test.ps1`:
```powershell
$tests = @(
    @{ Requests = 50;  Concurrent = 5;  Description = "Custom test 1" },
    @{ Requests = 100; Concurrent = 10; Description = "Custom test 2" }
)
```

### Change API URL

**Python**:
```python
API_URL = "http://your-api-url:8000"
```

**PowerShell**:
```powershell
.\stress_test.ps1 -ApiUrl "http://your-api-url:8000"
```

## 💡 Tips

### 1. Warm Up First
Always run a warm-up test before heavy load to:
- Prime the cache
- Establish connections
- Load any lazy resources

### 2. Monitor System Resources
While testing, check:
```bash
# Docker stats
docker stats

# Container logs
docker logs weather-proxy-api -f
```

### 3. Test Different Scenarios

**Cache Hit Scenario**:
```python
# Modify to use same city repeatedly
CITIES = ["Paris"] * 8  # All requests hit cache
```

**Cache Miss Scenario**:
```python
# Use many different cities
CITIES = ["Paris", "London", "Tokyo", ...100 cities...]
```

### 4. Circuit Breaker Testing

To test circuit breaker:
1. Stop Prometheus temporarily: `docker stop weather-proxy-prometheus`
2. Run stress test
3. Watch circuit breaker open after 5 failures
4. Restart Prometheus: `docker start weather-proxy-prometheus`

## 🎓 Understanding Results

### Good Performance Indicators
- ✅ Success rate: 100%
- ✅ p95 latency: < 500ms
- ✅ p99 latency: < 1000ms
- ✅ Requests/sec: > 50

### Warning Signs
- ⚠️ Success rate: 95-99%
- ⚠️ p95 latency: 500-1000ms
- ⚠️ Increasing error rate

### Breaking Point Indicators
- 🔴 Success rate: < 95%
- 🔴 p95 latency: > 2000ms
- 🔴 Timeouts and connection errors

## 🔍 Troubleshooting

### Script Can't Connect
```bash
# Check API is running
docker-compose ps

# Check API health
curl http://localhost:8000/health
```

### High Failure Rate Immediately
- Check Redis is running
- Check external API (Open-Meteo) is accessible
- Review API logs: `docker logs weather-proxy-api`

### Python Script Missing Dependencies
```bash
pip install requests rich
```

## 📚 Next Steps

After stress testing:
1. **Optimize**: Identify bottlenecks from results
2. **Scale**: Adjust resource limits in `docker-compose.yml`
3. **Cache**: Tune cache TTL based on hit rates
4. **Monitor**: Set up alerts in Grafana for high latency

Happy stress testing! 🚀
