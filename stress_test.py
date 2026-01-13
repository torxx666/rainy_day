"""
Stress Test Script for Weather Proxy API

This script performs load testing to find the breaking point of the API.
It gradually increases load and monitors response times and errors.

Requirements:
    pip install requests rich

Usage:
    python stress_test.py
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List

import requests
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()

# Configuration
API_URL = "http://localhost:8000"
CITIES = ["Paris", "London", "Tokyo", "New York", "Berlin", "Sydney", "Moscow", "Dubai"]


@dataclass
class TestResult:
    """Result of a single request"""
    success: bool
    response_time: float
    status_code: int
    error: str = ""


class StressTest:
    """Stress testing orchestrator"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[TestResult] = []

    def make_request(self, city: str) -> TestResult:
        """Make a single request to the API"""
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.base_url}/weather",
                params={"city": city},
                timeout=10
            )
            response_time = time.time() - start_time
            
            return TestResult(
                success=response.status_code == 200,
                response_time=response_time,
                status_code=response.status_code
            )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                success=False,
                response_time=response_time,
                status_code=0,
                error=str(e)
            )

    def run_concurrent_requests(self, num_requests: int, num_workers: int) -> List[TestResult]:
        """Run multiple concurrent requests"""
        results = []
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for i in range(num_requests):
                city = CITIES[i % len(CITIES)]
                futures.append(executor.submit(self.make_request, city))
            
            for future in as_completed(futures):
                results.append(future.result())
        
        return results

    def generate_stats_table(self, results: List[TestResult], workers: int, duration: float) -> Table:
        """Generate statistics table"""
        table = Table(title=f"Stress Test Results ({workers} concurrent workers)")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        
        response_times = [r.response_time for r in results if r.success]
        avg_time = sum(response_times) / len(response_times) if response_times else 0
        min_time = min(response_times) if response_times else 0
        max_time = max(response_times) if response_times else 0
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p50 = sorted_times[len(sorted_times) // 2] if sorted_times else 0
        p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
        p99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        
        requests_per_sec = total / duration if duration > 0 else 0
        
        table.add_row("Total Requests", str(total))
        table.add_row("Successful", f"{successful} ({successful/total*100:.1f}%)")
        table.add_row("Failed", f"{failed} ({failed/total*100:.1f}%)")
        table.add_row("Duration", f"{duration:.2f}s")
        table.add_row("Requests/sec", f"{requests_per_sec:.2f}")
        table.add_row("", "")
        table.add_row("Avg Response Time", f"{avg_time*1000:.2f}ms")
        table.add_row("Min Response Time", f"{min_time*1000:.2f}ms")
        table.add_row("Max Response Time", f"{max_time*1000:.2f}ms")
        table.add_row("p50 (median)", f"{p50*1000:.2f}ms")
        table.add_row("p95", f"{p95*1000:.2f}ms")
        table.add_row("p99", f"{p99*1000:.2f}ms")
        
        return table

    def run_progressive_load_test(self):
        """Run progressive load test to find breaking point"""
        console.print("\n[bold cyan]🚀 Starting Progressive Load Test[/bold cyan]\n")
        console.print("This will gradually increase load until the API starts failing...\n")
        
        # Test configurations: (requests, workers)
        test_configs = [
            (10, 2, "Warm-up"),
            (50, 5, "Light load"),
            (100, 10, "Medium load"),
            (200, 20, "Heavy load"),
            (500, 50, "Very heavy load"),
            (1000, 100, "Extreme load"),
            (2000, 200, "Breaking point test"),
        ]
        
        for num_requests, num_workers, description in test_configs:
            console.print(f"\n[yellow]📊 Test: {description}[/yellow]")
            console.print(f"   Requests: {num_requests}, Concurrent workers: {num_workers}")
            
            start_time = time.time()
            results = self.run_concurrent_requests(num_requests, num_workers)
            duration = time.time() - start_time
            
            table = self.generate_stats_table(results, num_workers, duration)
            console.print(table)
            
            # Check if API is breaking
            success_rate = sum(1 for r in results if r.success) / len(results)
            avg_response_time = sum(r.response_time for r in results if r.success) / max(1, sum(1 for r in results if r.success))
            
            if success_rate < 0.95:
                console.print(f"\n[bold red]⚠️  API Breaking Point Detected![/bold red]")
                console.print(f"Success rate dropped to {success_rate*100:.1f}%")
                console.print(f"Breaking point: ~{num_workers} concurrent requests")
                break
            
            if avg_response_time > 5.0:
                console.print(f"\n[bold yellow]⚠️  High Latency Detected![/bold yellow]")
                console.print(f"Average response time: {avg_response_time*1000:.2f}ms")
            
            # Small delay between tests
            time.sleep(2)
        
        console.print("\n[bold green]✅ Stress test completed![/bold green]\n")


def main():
    """Main entry point"""
    console.print("[bold]Weather Proxy API - Stress Test[/bold]\n")
    
    # Check API is accessible
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            console.print(f"[green]✓[/green] API is accessible at {API_URL}")
        else:
            console.print(f"[red]✗[/red] API returned status {response.status_code}")
            return
    except Exception as e:
        console.print(f"[red]✗[/red] Cannot connect to API: {e}")
        console.print(f"\nMake sure the API is running: docker-compose up -d")
        return
    
    # Run stress test
    tester = StressTest(API_URL)
    tester.run_progressive_load_test()
    
    console.print("\n[dim]Tip: Check Grafana dashboard at http://localhost:3000 to see the impact[/dim]")


if __name__ == "__main__":
    main()
