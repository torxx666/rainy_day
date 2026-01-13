# Weather Proxy API - Stress Test (PowerShell)
# This script performs load testing to find the API breaking point

param(
    [int]$MaxConcurrent = 200,
    [string]$ApiUrl = "http://localhost:8000"
)

$cities = @("Paris", "London", "Tokyo", "New York", "Berlin", "Sydney", "Moscow", "Dubai")

Write-Host "`n🚀 Weather Proxy API - Stress Test`n" -ForegroundColor Cyan

# Check API is accessible
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 5
    Write-Host "✓ API is accessible" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot connect to API: $_" -ForegroundColor Red
    Write-Host "`nMake sure the API is running: docker-compose up -d"
    exit 1
}

function Run-LoadTest {
    param(
        [int]$NumRequests,
        [int]$Concurrent,
        [string]$Description
    )
    
    Write-Host "`n📊 Test: $Description" -ForegroundColor Yellow
    Write-Host "   Requests: $NumRequests, Concurrent: $Concurrent"
    
    $jobs = @()
    $results = @()
    $startTime = Get-Date
    
    # Create jobs
    for ($i = 0; $i -lt $NumRequests; $i++) {
        $city = $cities[$i % $cities.Length]
        
        $job = Start-Job -ScriptBlock {
            param($url, $city)
            $start = Get-Date
            try {
                $response = Invoke-RestMethod -Uri "$url/weather?city=$city" -TimeoutSec 10
                $duration = (Get-Date) - $start
                return @{
                    Success = $true
                    Duration = $duration.TotalSeconds
                    StatusCode = 200
                }
            } catch {
                $duration = (Get-Date) - $start
                return @{
                    Success = $false
                    Duration = $duration.TotalSeconds
                    StatusCode = 0
                    Error = $_.Exception.Message
                }
            }
        } -ArgumentList $ApiUrl, $city
        
        $jobs += $job
        
        # Limit concurrent jobs
        while ((Get-Job -State Running).Count -ge $Concurrent) {
            Start-Sleep -Milliseconds 10
        }
    }
    
    # Wait for all jobs to complete
    $jobs | Wait-Job | Out-Null
    
    # Collect results
    foreach ($job in $jobs) {
        $results += Receive-Job -Job $job
        Remove-Job -Job $job
    }
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    # Calculate statistics
    $total = $results.Count
    $successful = ($results | Where-Object { $_.Success }).Count
    $failed = $total - $successful
    $successRate = ($successful / $total) * 100
    
    $successfulResults = $results | Where-Object { $_.Success }
    if ($successfulResults.Count -gt 0) {
        $avgTime = ($successfulResults | Measure-Object -Property Duration -Average).Average
        $minTime = ($successfulResults | Measure-Object -Property Duration -Minimum).Minimum
        $maxTime = ($successfulResults | Measure-Object -Property Duration -Maximum).Maximum
        
        $sorted = $successfulResults | Sort-Object Duration
        $p50 = $sorted[[math]::Floor($sorted.Count * 0.50)].Duration
        $p95 = $sorted[[math]::Floor($sorted.Count * 0.95)].Duration
        $p99 = $sorted[[math]::Floor($sorted.Count * 0.99)].Duration
    } else {
        $avgTime = 0
        $minTime = 0
        $maxTime = 0
        $p50 = 0
        $p95 = 0
        $p99 = 0
    }
    
    $reqPerSec = $total / $duration
    
    # Display results
    Write-Host "`nResults:" -ForegroundColor Cyan
    Write-Host "  Total Requests:     $total"
    Write-Host "  Successful:         $successful ($([math]::Round($successRate, 1))%)" -ForegroundColor $(if ($successRate -ge 95) { "Green" } else { "Red" })
    Write-Host "  Failed:             $failed"
    Write-Host "  Duration:           $([math]::Round($duration, 2))s"
    Write-Host "  Requests/sec:       $([math]::Round($reqPerSec, 2))"
    Write-Host ""
    Write-Host "  Avg Response Time:  $([math]::Round($avgTime * 1000, 2))ms"
    Write-Host "  Min Response Time:  $([math]::Round($minTime * 1000, 2))ms"
    Write-Host "  Max Response Time:  $([math]::Round($maxTime * 1000, 2))ms"
    Write-Host "  p50 (median):       $([math]::Round($p50 * 1000, 2))ms"
    Write-Host "  p95:                $([math]::Round($p95 * 1000, 2))ms"
    Write-Host "  p99:                $([math]::Round($p99 * 1000, 2))ms"
    
    return @{
        SuccessRate = $successRate
        AvgResponseTime = $avgTime
        Concurrent = $Concurrent
    }
}

# Progressive load tests
$tests = @(
    @{ Requests = 10;   Concurrent = 2;   Description = "Warm-up" },
    @{ Requests = 50;   Concurrent = 5;   Description = "Light load" },
    @{ Requests = 100;  Concurrent = 10;  Description = "Medium load" },
    @{ Requests = 200;  Concurrent = 20;  Description = "Heavy load" },
    @{ Requests = 500;  Concurrent = 50;  Description = "Very heavy load" },
    @{ Requests = 1000; Concurrent = 100; Description = "Extreme load" },
    @{ Requests = 2000; Concurrent = 200; Description = "Breaking point test" }
)

foreach ($test in $tests) {
    $result = Run-LoadTest -NumRequests $test.Requests -Concurrent $test.Concurrent -Description $test.Description
    
    # Check for breaking point
    if ($result.SuccessRate -lt 95) {
        Write-Host "`n⚠️  API Breaking Point Detected!" -ForegroundColor Red
        Write-Host "Success rate dropped to $([math]::Round($result.SuccessRate, 1))%"
        Write-Host "Breaking point: ~$($result.Concurrent) concurrent requests"
        break
    }
    
    if ($result.AvgResponseTime -gt 5.0) {
        Write-Host "`n⚠️  High Latency Detected!" -ForegroundColor Yellow
        Write-Host "Average response time: $([math]::Round($result.AvgResponseTime * 1000, 2))ms"
    }
    
    Start-Sleep -Seconds 2
}

Write-Host "`n✅ Stress test completed!`n" -ForegroundColor Green
Write-Host "Tip: Check Grafana dashboard at http://localhost:3000 to see the impact" -ForegroundColor Gray
