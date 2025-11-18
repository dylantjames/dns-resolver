#!/usr/bin/env python3
"""
Local DNS Server (Recursive Resolver with Caching)

Responsibilities:
- Receives queries from clients
- Checks local cache first (cache hit = fast response)
- On cache miss, performs iterative resolution:
  1. Query Root Server for TLD server
  2. Query TLD Server for Authoritative server
  3. Query Authoritative Server for IP
- Caches results with TTL
- Returns final IP to client
"""

import socket
import sys
import os
import time
from collections import OrderedDict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dns_protocol import DNSMessage


class DNSCache:
    """LRU Cache with TTL for DNS records"""
    def __init__(self, max_size=1000, ttl=300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl  # Time-to-live in seconds
        self.hits = 0
        self.misses = 0

    def get(self, domain):
        """Retrieve from cache if exists and not expired"""
        if domain in self.cache:
            ip, timestamp = self.cache[domain]
            if time.time() - timestamp < self.ttl:
                # Move to end (most recently used)
                self.cache.move_to_end(domain)
                self.hits += 1
                return ip
            else:
                # Expired entry
                del self.cache[domain]

        self.misses += 1
        return None

    def put(self, domain, ip):
        """Add to cache with current timestamp"""
        if domain in self.cache:
            # Update existing entry
            self.cache.move_to_end(domain)
        elif len(self.cache) >= self.max_size:
            # Remove oldest entry (LRU)
            self.cache.popitem(last=False)

        self.cache[domain] = (ip, time.time())

    def get_hit_rate(self):
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100


class LocalServer:
    def __init__(self, host='127.0.0.1', port=53004,
                 root_server=('127.0.0.1', 53000)):
        self.host = host
        self.port = port
        self.root_server = root_server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # DNS Cache
        self.cache = DNSCache(max_size=1000, ttl=300)

        # Statistics
        self.query_count = 0
        self.total_resolution_time = 0.0

    def query_server(self, server_addr, query_msg):
        """Send query to a DNS server and get response"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(server_addr)
            sock.sendall(query_msg.serialize())
            data = sock.recv(1024)
            sock.close()

            if data:
                return DNSMessage.deserialize(data)
        except Exception as e:
            print(f"[LOCAL] Error querying {server_addr}: {e}")

        return None

    def iterative_resolve(self, domain, query_id):
        """Perform iterative DNS resolution"""
        print(f"[LOCAL] Starting iterative resolution for {domain}")

        # Step 1: Query Root Server
        query = DNSMessage("QUERY", query_id, domain)
        response = self.query_server(self.root_server, query)

        if not response or response.result_type == "ERROR":
            print(f"[LOCAL] Root server error")
            return None

        # Step 2: Parse TLD server address
        if response.result_type != "NS":
            print(f"[LOCAL] Unexpected response from root: {response.result_type}")
            return None

        # Format: "TLD:host:port"
        parts = response.result_value.split(':')
        tld_server = (parts[1], int(parts[2]))
        print(f"[LOCAL] Root -> TLD server at {tld_server[0]}:{tld_server[1]}")

        # Step 3: Query TLD Server
        response = self.query_server(tld_server, query)

        if not response or response.result_type == "ERROR":
            print(f"[LOCAL] TLD server error")
            return None

        # Step 4: Parse Authoritative server address
        if response.result_type != "NS":
            # Might have gotten IP directly (shouldn't happen in our design)
            if response.result_type == "IP":
                return response.result_value
            print(f"[LOCAL] Unexpected response from TLD: {response.result_type}")
            return None

        # Format: "AUTH:host:port"
        parts = response.result_value.split(':')
        auth_server = (parts[1], int(parts[2]))
        print(f"[LOCAL] TLD -> Auth server at {auth_server[0]}:{auth_server[1]}")

        # Step 5: Query Authoritative Server
        response = self.query_server(auth_server, query)

        if not response:
            print(f"[LOCAL] Auth server error")
            return None

        if response.result_type == "IP":
            print(f"[LOCAL] Auth -> IP: {response.result_value}")
            return response.result_value
        else:
            print(f"[LOCAL] Auth server returned: {response.result_type}")
            return None

    def handle_query(self, query_msg):
        """Process DNS query with caching"""
        self.query_count += 1
        start_time = time.time()

        domain = query_msg.domain.lower()

        # Check cache first
        cached_ip = self.cache.get(domain)
        if cached_ip:
            resolution_time = (time.time() - start_time) * 1000  # Convert to ms
            self.total_resolution_time += resolution_time
            print(f"[LOCAL] Query #{self.query_count}: {domain} -> {cached_ip} (CACHED, {resolution_time:.2f}ms)")

            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="IP",
                result_value=cached_ip
            )
            return response

        # Cache miss - perform iterative resolution
        print(f"[LOCAL] Query #{self.query_count}: {domain} (CACHE MISS)")
        ip_address = self.iterative_resolve(domain, query_msg.query_id)

        resolution_time = (time.time() - start_time) * 1000  # Convert to ms
        self.total_resolution_time += resolution_time

        if ip_address:
            # Cache the result
            self.cache.put(domain, ip_address)
            print(f"[LOCAL] Resolved {domain} -> {ip_address} ({resolution_time:.2f}ms)")

            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="IP",
                result_value=ip_address
            )
        else:
            print(f"[LOCAL] Failed to resolve {domain}")
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="ERROR",
                result_value="Resolution failed"
            )

        return response

    def print_statistics(self):
        """Print server statistics"""
        print(f"\n[LOCAL] ===== STATISTICS =====")
        print(f"[LOCAL] Total Queries: {self.query_count}")
        print(f"[LOCAL] Cache Hits: {self.cache.hits}")
        print(f"[LOCAL] Cache Misses: {self.cache.misses}")
        print(f"[LOCAL] Cache Hit Rate: {self.cache.get_hit_rate():.2f}%")
        if self.query_count > 0:
            avg_time = self.total_resolution_time / self.query_count
            print(f"[LOCAL] Average Resolution Time: {avg_time:.2f}ms")
        print(f"[LOCAL] Cache Size: {len(self.cache.cache)}/{self.cache.max_size}")
        print(f"[LOCAL] ========================\n")

    def start(self):
        """Start the local server"""
        self.sock.bind((self.host, self.port))
        self.sock.listen(10)
        print(f"[LOCAL] Server started on {self.host}:{self.port}")
        print(f"[LOCAL] Root server: {self.root_server[0]}:{self.root_server[1]}")
        print(f"[LOCAL] Cache: max_size={self.cache.max_size}, TTL={self.cache.ttl}s")

        while True:
            try:
                conn, addr = self.sock.accept()
                data = conn.recv(1024)

                if data:
                    query = DNSMessage.deserialize(data)
                    response = self.handle_query(query)
                    conn.sendall(response.serialize())

                conn.close()
            except KeyboardInterrupt:
                self.print_statistics()
                print(f"[LOCAL] Shutting down...")
                break
            except Exception as e:
                print(f"[LOCAL] Error: {e}")

        self.sock.close()


if __name__ == "__main__":
    server = LocalServer()
    server.start()
