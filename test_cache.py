#!/usr/bin/env python3
"""Simple test to demonstrate cache effectiveness"""

import time
import sys
from client.dns_client import DNSClient

def load_domains_from_file():
    """Load domains from dns_records.txt"""
    domains = []
    try:
        with open('data/dns_records.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                parts = line.split(',')
                if len(parts) == 2:
                    domains.append(parts[0].strip())
    except FileNotFoundError:
        print("ERROR: data/dns_records.txt not found!")
        sys.exit(1)

    return domains

def main():
    client = DNSClient()

    # Load domains from dns_records.txt
    domains = load_domains_from_file()

    if not domains:
        print("ERROR: No domains found in data/dns_records.txt")
        print("Please add domain,ip pairs to the file before running this test.")
        print("\nExample format:")
        print("  example.com,0.0.0.0")
        print("  example.edu,0.0.0.0")
        sys.exit(1)

    print(f"Loaded {len(domains)} domains from dns_records.txt")

    # Use first 8 domains (or all if less than 8)
    test_domains = domains[:8] if len(domains) >= 8 else domains

    print("Testing DNS Resolution with Caching")
    print("=" * 60)

    # First pass - all cache misses
    print("\nFirst pass (cache misses - full resolution):")
    for domain in test_domains:
        start = time.time()
        ip = client.resolve(domain)
        elapsed = (time.time() - start) * 1000
        print(f"  {domain:25s} -> {ip:20s} ({elapsed:6.2f} ms)")

    time.sleep(0.5)

    # Second pass - all cache hits
    print("\nSecond pass (cache hits - instant):")
    for domain in test_domains:
        start = time.time()
        ip = client.resolve(domain)
        elapsed = (time.time() - start) * 1000
        print(f"  {domain:25s} -> {ip:20s} ({elapsed:6.2f} ms)")

    time.sleep(0.5)

    # Mixed workload
    print("\nMixed workload (repeat queries):")
    test_sequence = test_domains * 3  # Query each domain 3 more times
    for domain in test_sequence:
        client.resolve(domain)

    print(f"\nTotal queries sent: {client.query_id}")
    print("\nCheck local server output for cache statistics!")

if __name__ == "__main__":
    main()
