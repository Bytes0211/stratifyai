#!/usr/bin/env python3
"""
Performance Benchmarking Tool

Profile and measure performance of StratifyAI across different scenarios:
- Cold start latency
- Request latency
- Throughput
- Memory usage
- Cache performance
- Concurrent load profiles

Usage:
    python examples/performance_benchmark.py --output benchmark_results.json
    python examples/performance_benchmark.py --profile concurrent-heavy
"""

import argparse
import asyncio
import json
import sys
import time
import tracemalloc
from enum import Enum
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

# noqa: E402
from stratifyai import LLMClient, Router, RoutingStrategy  # noqa: E402
from stratifyai.caching import ResponseCache  # noqa: E402
from stratifyai.models import Message  # noqa: E402

console = Console()


class LoadProfile(str, Enum):
    """Load profile types for benchmarking."""

    BASELINE = "baseline"  # 1 concurrent user
    CONCURRENT_LIGHT = "concurrent-light"  # 3 concurrent users
    CONCURRENT_HEAVY = "concurrent-heavy"  # 10 concurrent users
    MIXED_COMPLEXITY = "mixed-complexity"  # Varying message complexity


class PerformanceBenchmark:
    """Benchmark StratifyAI performance."""

    def __init__(self):
        """Initialize the benchmark."""
        self.results = {}

    def measure_cold_start(self) -> dict[str, float]:
        """Measure cold start latency.

        Returns:
            Dictionary with timing measurements
        """
        console.print("\n[cyan]Measuring cold start latency...[/cyan]")

        # Measure client initialization
        start = time.time()
        _client = LLMClient()  # noqa: F841
        client_init_time = time.time() - start

        # Measure router initialization
        start = time.time()
        _router = Router()  # noqa: F841
        router_init_time = time.time() - start

        # Measure cache initialization
        start = time.time()
        _cache = ResponseCache(max_size=1000)  # noqa: F841
        cache_init_time = time.time() - start

        return {
            "client_init_ms": client_init_time * 1000,
            "router_init_ms": router_init_time * 1000,
            "cache_init_ms": cache_init_time * 1000,
            "total_cold_start_ms": (
                client_init_time + router_init_time + cache_init_time
            )
            * 1000,
        }

    def measure_request_latency(
        self, model: str = "gpt-4o-mini", num_requests: int = 5
    ) -> dict[str, Any]:
        """Measure request latency for different scenarios.

        Args:
            model: Model to test
            num_requests: Number of requests to average

        Returns:
            Dictionary with latency measurements
        """
        console.print(
            f"\n[cyan]Measuring request latency ({num_requests} requests)...[/cyan]"
        )

        client = LLMClient()
        latencies = []

        simple_message = [Message(role="user", content="Say hello")]

        for i in range(num_requests):
            start = time.time()
            try:
                _response = client.chat(model=model, messages=simple_message)  # noqa: F841
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                console.print(f"  Request {i + 1}: {latency:.1f}ms")
            except Exception as e:
                console.print(f"  [red]Request {i + 1} failed: {e}[/red]")

        if latencies:
            return {
                "model": model,
                "num_requests": len(latencies),
                "mean_latency_ms": mean(latencies),
                "median_latency_ms": median(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "stdev_latency_ms": stdev(latencies) if len(latencies) > 1 else 0,
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)]
                if latencies
                else 0,
            }
        else:
            return {"error": "All requests failed"}

    def measure_router_overhead(self, num_iterations: int = 100) -> dict[str, float]:
        """Measure router overhead vs direct client calls.

        Args:
            num_iterations: Number of routing decisions to measure

        Returns:
            Dictionary with overhead measurements
        """
        console.print(
            f"\n[cyan]Measuring router overhead ({num_iterations} iterations)...[/cyan]"
        )

        router = Router(strategy=RoutingStrategy.HYBRID)
        messages = [Message(role="user", content="Test message for routing")]

        # Measure routing decision overhead (no API calls)
        routing_times = []
        for _ in range(num_iterations):
            start = time.time()
            # route() performs complexity analysis and model selection
            provider, model = router.route(messages)
            routing_times.append((time.time() - start) * 1000)

        return {
            "num_iterations": num_iterations,
            "mean_routing_overhead_ms": mean(routing_times),
            "median_routing_overhead_ms": median(routing_times),
            "min_routing_overhead_ms": min(routing_times),
            "max_routing_overhead_ms": max(routing_times),
        }

    def measure_cache_performance(
        self, cache_size: int = 1000, num_operations: int = 1000
    ) -> dict[str, Any]:
        """Measure cache performance.

        Args:
            cache_size: Cache size
            num_operations: Number of cache operations

        Returns:
            Dictionary with cache performance metrics
        """
        console.print(
            f"\n[cyan]Measuring cache performance ({num_operations} operations)...[/cyan]"
        )

        cache = ResponseCache(max_size=cache_size, ttl=3600)

        # Measure write performance
        write_times = []
        for i in range(num_operations // 2):
            key = f"test_key_{i}"
            value = {"content": f"test_value_{i}" * 100}  # Simulate response

            start = time.time()
            cache.set(key, value)
            write_times.append((time.time() - start) * 1000)

        # Measure read performance (hits)
        read_times = []
        for i in range(num_operations // 2):
            key = f"test_key_{i}"

            start = time.time()
            cache.get(key)
            read_times.append((time.time() - start) * 1000)

        # Measure miss performance
        miss_times = []
        for i in range(100):
            key = f"missing_key_{i}"

            start = time.time()
            cache.get(key)
            miss_times.append((time.time() - start) * 1000)

        return {
            "cache_size": cache_size,
            "num_operations": num_operations,
            "write_mean_ms": mean(write_times),
            "write_p95_ms": sorted(write_times)[int(len(write_times) * 0.95)],
            "read_mean_ms": mean(read_times),
            "read_p95_ms": sorted(read_times)[int(len(read_times) * 0.95)],
            "miss_mean_ms": mean(miss_times),
            "miss_p95_ms": sorted(miss_times)[int(len(miss_times) * 0.95)],
        }

    def measure_memory_usage(self) -> dict[str, float]:
        """Measure memory usage of key components.

        Returns:
            Dictionary with memory measurements in MB
        """
        console.print("\n[cyan]Measuring memory usage...[/cyan]")

        tracemalloc.start()

        # Baseline
        baseline = tracemalloc.get_traced_memory()[0]

        # Client
        _client = LLMClient()  # noqa: F841
        client_mem = tracemalloc.get_traced_memory()[0] - baseline

        # Router
        _router = Router()  # noqa: F841
        router_mem = tracemalloc.get_traced_memory()[0] - baseline - client_mem

        # Cache with 1000 entries
        cache = ResponseCache(max_size=1000)
        for i in range(1000):
            cache.set(f"key_{i}", {"content": "x" * 1000})
        cache_mem = (
            tracemalloc.get_traced_memory()[0] - baseline - client_mem - router_mem
        )

        total_mem = tracemalloc.get_traced_memory()[0] - baseline
        tracemalloc.stop()

        return {
            "client_mb": client_mem / (1024 * 1024),
            "router_mb": router_mem / (1024 * 1024),
            "cache_1000_entries_mb": cache_mem / (1024 * 1024),
            "total_mb": total_mem / (1024 * 1024),
        }

    async def measure_concurrent_load(
        self,
        profile: LoadProfile = LoadProfile.BASELINE,
        model: str = "gpt-4o-mini",
        duration: int = 10,
    ) -> dict[str, Any]:
        """Measure concurrent load performance.

        Args:
            profile: Load profile type
            model: Model to use
            duration: Duration in seconds

        Returns:
            Dictionary with concurrency metrics
        """
        # Determine concurrency level based on profile
        profile_config = {
            LoadProfile.BASELINE: {"users": 1, "delays": [0]},
            LoadProfile.CONCURRENT_LIGHT: {"users": 3, "delays": [0, 0.05, 0.1]},
            LoadProfile.CONCURRENT_HEAVY: {
                "users": 10,
                "delays": [i * 0.02 for i in range(10)],
            },
            LoadProfile.MIXED_COMPLEXITY: {
                "users": 5,
                "delays": [0, 0.1, 0, 0.05, 0.15],
                "complexity": ["simple", "simple", "complex", "complex", "simple"],
            },
        }

        config = profile_config[profile]
        num_users = config["users"]
        delays = config["delays"]

        console.print(
            f"\n[cyan]Measuring {profile.value} load ({num_users} concurrent users, {duration}s)...[/cyan]"
        )

        client = LLMClient()
        latencies = []
        errors = 0
        start_time = time.time()

        async def user_task(user_id: int, delay: float):
            """Simulate a user making requests."""
            nonlocal errors
            await asyncio.sleep(delay)  # Stagger start times

            complexity = config.get("complexity", ["simple"] * num_users)[user_id]
            if complexity == "complex":
                content = (
                    "Explain machine learning in detail with equations and examples. "
                    * 3
                )
            else:
                content = "Say hello"

            message = [Message(role="user", content=content)]

            while time.time() - start_time < duration:
                try:
                    req_start = time.time()
                    _response = await client.chat(model=model, messages=message)  # noqa: F841
                    latency = (time.time() - req_start) * 1000
                    latencies.append(latency)
                except Exception:
                    errors += 1
                await asyncio.sleep(0.1)  # 100ms between requests per user

        # Create user tasks
        tasks = [user_task(user_id, delays[user_id]) for user_id in range(num_users)]

        # Run concurrent tasks
        await asyncio.gather(*tasks)

        if latencies:
            return {
                "profile": profile.value,
                "num_users": num_users,
                "duration_seconds": duration,
                "total_requests": len(latencies),
                "errors": errors,
                "throughput_rps": len(latencies) / duration,
                "mean_latency_ms": mean(latencies),
                "median_latency_ms": median(latencies),
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)]
                if latencies
                else 0,
                "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)]
                if latencies
                else 0,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
            }
        else:
            return {"error": "All requests failed", "profile": profile.value}

    def run_all_benchmarks(
        self, model: str = "gpt-4o-mini", num_requests: int = 3
    ) -> dict[str, Any]:
        """Run all benchmarks.

        Args:
            model: Model to use for API benchmarks
            num_requests: Number of requests for latency tests

        Returns:
            Complete benchmark results
        """
        console.print("[bold]Performance Benchmarking[/bold]\n")

        # Cold start
        self.results["cold_start"] = self.measure_cold_start()

        # Request latency
        self.results["request_latency"] = self.measure_request_latency(
            model=model, num_requests=num_requests
        )

        # Router overhead
        self.results["router_overhead"] = self.measure_router_overhead(
            num_iterations=100
        )

        # Cache performance
        self.results["cache_performance"] = self.measure_cache_performance(
            cache_size=1000, num_operations=1000
        )

        # Memory usage
        self.results["memory_usage"] = self.measure_memory_usage()

        return self.results

    async def run_load_profile_benchmark(
        self, profile: LoadProfile = LoadProfile.BASELINE, model: str = "gpt-4o-mini"
    ) -> dict[str, Any]:
        """Run concurrent load profile benchmark.

        Args:
            profile: Load profile to test
            model: Model to use

        Returns:
            Benchmark results with load profile metrics
        """
        console.print("[bold]Load Profile Benchmarking[/bold]\n")

        # Run the specified load profile
        self.results["load_profile"] = await self.measure_concurrent_load(
            profile=profile, model=model, duration=10
        )

        return self.results

    def display_results(self):
        """Display benchmark results as Rich tables."""

        # Cold start table
        console.print("\n[bold cyan]Cold Start Performance[/bold cyan]")
        table1 = Table()
        table1.add_column("Component", style="cyan")
        table1.add_column("Time (ms)", justify="right", style="yellow")

        cs = self.results.get("cold_start", {})
        table1.add_row("Client Init", f"{cs.get('client_init_ms', 0):.2f}")
        table1.add_row("Router Init", f"{cs.get('router_init_ms', 0):.2f}")
        table1.add_row("Cache Init", f"{cs.get('cache_init_ms', 0):.2f}")
        table1.add_row(
            "[bold]Total[/bold]", f"[bold]{cs.get('total_cold_start_ms', 0):.2f}[/bold]"
        )
        console.print(table1)

        # Request latency table
        console.print("\n[bold cyan]Request Latency[/bold cyan]")
        table2 = Table()
        table2.add_column("Metric", style="cyan")
        table2.add_column("Value (ms)", justify="right", style="yellow")

        rl = self.results.get("request_latency", {})
        table2.add_row("Model", rl.get("model", "N/A"))
        table2.add_row("Mean", f"{rl.get('mean_latency_ms', 0):.1f}")
        table2.add_row("Median", f"{rl.get('median_latency_ms', 0):.1f}")
        table2.add_row("P95", f"{rl.get('p95_latency_ms', 0):.1f}")
        table2.add_row("Min", f"{rl.get('min_latency_ms', 0):.1f}")
        table2.add_row("Max", f"{rl.get('max_latency_ms', 0):.1f}")
        console.print(table2)

        # Router overhead table
        console.print("\n[bold cyan]Router Overhead[/bold cyan]")
        table3 = Table()
        table3.add_column("Metric", style="cyan")
        table3.add_column("Time (ms)", justify="right", style="yellow")

        ro = self.results.get("router_overhead", {})
        table3.add_row("Mean", f"{ro.get('mean_routing_overhead_ms', 0):.3f}")
        table3.add_row("Median", f"{ro.get('median_routing_overhead_ms', 0):.3f}")
        table3.add_row("Min", f"{ro.get('min_routing_overhead_ms', 0):.3f}")
        table3.add_row("Max", f"{ro.get('max_routing_overhead_ms', 0):.3f}")
        console.print(table3)

        # Cache performance table
        console.print("\n[bold cyan]Cache Performance[/bold cyan]")
        table4 = Table()
        table4.add_column("Operation", style="cyan")
        table4.add_column("Mean (ms)", justify="right", style="yellow")
        table4.add_column("P95 (ms)", justify="right", style="green")

        cp = self.results.get("cache_performance", {})
        table4.add_row(
            "Write",
            f"{cp.get('write_mean_ms', 0):.4f}",
            f"{cp.get('write_p95_ms', 0):.4f}",
        )
        table4.add_row(
            "Read (Hit)",
            f"{cp.get('read_mean_ms', 0):.4f}",
            f"{cp.get('read_p95_ms', 0):.4f}",
        )
        table4.add_row(
            "Read (Miss)",
            f"{cp.get('miss_mean_ms', 0):.4f}",
            f"{cp.get('miss_p95_ms', 0):.4f}",
        )
        console.print(table4)

        # Memory usage table
        console.print("\n[bold cyan]Memory Usage[/bold cyan]")
        table5 = Table()
        table5.add_column("Component", style="cyan")
        table5.add_column("Memory (MB)", justify="right", style="yellow")

        mu = self.results.get("memory_usage", {})
        table5.add_row("Client", f"{mu.get('client_mb', 0):.2f}")
        table5.add_row("Router", f"{mu.get('router_mb', 0):.2f}")
        table5.add_row(
            "Cache (1000 entries)", f"{mu.get('cache_1000_entries_mb', 0):.2f}"
        )
        table5.add_row(
            "[bold]Total[/bold]", f"[bold]{mu.get('total_mb', 0):.2f}[/bold]"
        )
        console.print(table5)

        # Performance targets
        console.print("\n[bold cyan]Performance Targets[/bold cyan]")
        table6 = Table()
        table6.add_column("Metric", style="cyan")
        table6.add_column("Target", style="green")
        table6.add_column("Actual", style="yellow")
        table6.add_column("Status", justify="center")

        # Cold start < 1s
        cold_start_ms = cs.get("total_cold_start_ms", 0)
        table6.add_row(
            "Cold Start",
            "< 1000ms",
            f"{cold_start_ms:.1f}ms",
            "✅" if cold_start_ms < 1000 else "❌",
        )

        # Response time < 2s (P95)
        p95_latency = rl.get("p95_latency_ms", 0)
        table6.add_row(
            "Response Time (P95)",
            "< 2000ms",
            f"{p95_latency:.1f}ms",
            "✅" if p95_latency < 2000 else "❌",
        )

        # Cache hit < 1ms
        cache_read_ms = cp.get("read_mean_ms", 0)
        table6.add_row(
            "Cache Read",
            "< 1ms",
            f"{cache_read_ms:.4f}ms",
            "✅" if cache_read_ms < 1 else "❌",
        )

        # Memory < 100MB
        total_mem = mu.get("total_mb", 0)
        table6.add_row(
            "Memory Usage",
            "< 100MB",
            f"{total_mem:.2f}MB",
            "✅" if total_mem < 100 else "❌",
        )

        console.print(table6)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Benchmark StratifyAI performance")
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o-mini",
        help="Model to use for API benchmarks (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--requests",
        "-r",
        type=int,
        default=3,
        help="Number of API requests for latency tests (default: 3)",
    )
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        choices=[profile.value for profile in LoadProfile],
        help="Run specific load profile benchmark (concurrent mode)",
    )
    parser.add_argument("--output", "-o", type=Path, help="Save results to JSON file")

    args = parser.parse_args()

    # Run benchmarks
    benchmark = PerformanceBenchmark()

    if args.profile:
        # Run load profile benchmark (async)
        profile = LoadProfile(args.profile)
        results = asyncio.run(
            benchmark.run_load_profile_benchmark(profile=profile, model=args.model)
        )
    else:
        # Run standard benchmarks
        results = benchmark.run_all_benchmarks(
            model=args.model, num_requests=args.requests
        )

    # Display results
    benchmark.display_results()

    # Save to file
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]✓ Results saved to {args.output}[/green]")

    console.print("\n[bold]Benchmark complete![/bold]\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
