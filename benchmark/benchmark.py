#!/usr/bin/env python3
"""DNS system benchmark suite.

Measures query throughput, cache hit rate, latency, and concurrent performance.
"""

import sys
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.dns_client import DNSClient


class DNSBenchmark:
    """Benchmark suite for DNS system performance.

    Attributes:
        client: DNSClient instance for queries.
        results: Dictionary tracking query metrics.
    """

    def __init__(self):
        self.client = DNSClient()
        self.results = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_time': 0.0,
            'query_times': [],
        }

    def load_test_domains(self, filename='data/dns_records.txt'):
        """Load domain names from DNS records file.

        Returns:
            List of domain name strings.
        """
        domains = []
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, filename)

        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                parts = line.split(',')
                if len(parts) == 2:
                    domains.append(parts[0].strip())

        return domains

    def single_query(self, domain):
        """Perform single query and measure time.

        Args:
            domain: Domain name to resolve.

        Returns:
            Dictionary with domain, result, time_ms, and success status.
        """
        start = time.time()
        result = self.client.resolve(domain)
        elapsed = (time.time() - start) * 1000

        success = not result.startswith('ERROR')

        return {
            'domain': domain,
            'result': result,
            'time_ms': elapsed,
            'success': success
        }

    def sequential_benchmark(self, domains, num_queries):
        """Run sequential queries."""
        print(f"\n=== Sequential Benchmark ({num_queries} queries) ===")

        start_time = time.time()

        for i in range(num_queries):
            domain = random.choice(domains)
            result = self.single_query(domain)

            self.results['total_queries'] += 1
            self.results['query_times'].append(result['time_ms'])

            if result['success']:
                self.results['successful_queries'] += 1
            else:
                self.results['failed_queries'] += 1

            if (i + 1) % 100 == 0:
                print(f"Completed {i + 1}/{num_queries} queries...")

        total_time = time.time() - start_time
        self.results['total_time'] = total_time

        print(f"Completed in {total_time:.2f} seconds")

    def concurrent_benchmark(self, domains, num_queries, max_workers=10):
        """Run concurrent queries."""
        print(f"\n=== Concurrent Benchmark ({num_queries} queries, {max_workers} threads) ===")

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(num_queries):
                domain = random.choice(domains)
                future = executor.submit(self.single_query, domain)
                futures.append(future)

            completed = 0
            for future in as_completed(futures):
                result = future.result()

                self.results['total_queries'] += 1
                self.results['query_times'].append(result['time_ms'])

                if result['success']:
                    self.results['successful_queries'] += 1
                else:
                    self.results['failed_queries'] += 1

                completed += 1
                if completed % 100 == 0:
                    print(f"Completed {completed}/{num_queries} queries...")

        total_time = time.time() - start_time
        self.results['total_time'] = total_time

        print(f"Completed in {total_time:.2f} seconds")

    def cache_effectiveness_test(self, domains, iterations=5):
        """Test cache effectiveness by querying same domains multiple times.

        Args:
            domains: List of domains to query.
            iterations: Number of times to query each domain.
        """
        print(f"\n=== Cache Effectiveness Test ===")
        print(f"Querying {len(domains)} unique domains {iterations} times each")

        first_pass_times = []
        cached_times = []

        print("First pass (populating cache)...")
        for domain in domains:
            result = self.single_query(domain)
            first_pass_times.append(result['time_ms'])
            self.results['total_queries'] += 1
            if result['success']:
                self.results['successful_queries'] += 1

        for iteration in range(1, iterations):
            print(f"Pass {iteration + 1} (cached queries)...")
            for domain in domains:
                result = self.single_query(domain)
                cached_times.append(result['time_ms'])
                self.results['total_queries'] += 1
                if result['success']:
                    self.results['successful_queries'] += 1

        avg_first = sum(first_pass_times) / len(first_pass_times)
        avg_cached = sum(cached_times) / len(cached_times)
        improvement = ((avg_first - avg_cached) / avg_first) * 100

        print(f"\nCache Performance:")
        print(f"  Avg first query time:  {avg_first:.2f} ms")
        print(f"  Avg cached query time: {avg_cached:.2f} ms")
        print(f"  Performance improvement: {improvement:.1f}%")

        self.results['query_times'].extend(first_pass_times)
        self.results['query_times'].extend(cached_times)

    def print_results(self):
        """Print benchmark results."""
        print(f"\n{'='*60}")
        print(f"BENCHMARK RESULTS")
        print(f"{'='*60}")

        print(f"\nTotal Queries: {self.results['total_queries']}")
        print(f"Successful: {self.results['successful_queries']}")
        print(f"Failed: {self.results['failed_queries']}")
        print(f"Success Rate: {(self.results['successful_queries'] / self.results['total_queries'] * 100):.2f}%")

        if self.results['total_time'] > 0:
            qps = self.results['total_queries'] / self.results['total_time']
            print(f"\nTotal Time: {self.results['total_time']:.2f} seconds")
            print(f"Queries Per Second: {qps:.2f}")

        if self.results['query_times']:
            avg_time = sum(self.results['query_times']) / len(self.results['query_times'])
            min_time = min(self.results['query_times'])
            max_time = max(self.results['query_times'])
            sorted_times = sorted(self.results['query_times'])
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]

            print(f"\nLatency Statistics:")
            print(f"  Average: {avg_time:.2f} ms")
            print(f"  Min: {min_time:.2f} ms")
            print(f"  Max: {max_time:.2f} ms")
            print(f"  P50 (median): {p50:.2f} ms")
            print(f"  P95: {p95:.2f} ms")
            print(f"  P99: {p99:.2f} ms")

        print(f"{'='*60}\n")


def main():
    print("DNS System Benchmark")
    print("=" * 60)

    benchmark = DNSBenchmark()

    print("Loading test domains...")
    domains = benchmark.load_test_domains()
    print(f"Loaded {len(domains)} domains")

    test_domains = random.sample(domains, min(20, len(domains)))
    benchmark.cache_effectiveness_test(test_domains, iterations=5)

    benchmark.sequential_benchmark(domains, num_queries=200)

    benchmark.concurrent_benchmark(domains, num_queries=500, max_workers=20)

    benchmark.print_results()

    print("\nNote: Check servers/local_server.py output for cache hit rate statistics")


if __name__ == "__main__":
    main()
