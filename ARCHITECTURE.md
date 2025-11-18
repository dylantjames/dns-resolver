# Architecture

## System Design

This DNS resolver implements a hierarchical distributed architecture with six components communicating via TCP sockets. The system demonstrates iterative query resolution with client-side caching.

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     ▼
┌──────────────────┐
│  Local Server    │ ◄── LRU Cache (TTL: 300s, Size: 1000)
│  (Resolver)      │
└────┬─────────────┘
     │
     ├─► Root Server ──────► TLD Server ──────► Authoritative Server
     │   (port 53000)        (.com: 53001)      (port 53003)
     │                       (.edu: 53002)               │
     │                                                   │
     └────────────────────── (Cached Result) ────────────┘
```

## Components

### Client (`client/dns_client.py`)
Command-line DNS client that sends queries to the Local Server and displays results.

### Local Server (`servers/local_server.py`)
Recursive resolver with LRU cache. Performs iterative resolution by querying Root → TLD → Authoritative servers in sequence.

**Key Features:**
- OrderedDict-based LRU cache with TTL expiration
- Query statistics tracking (hits, misses, latency)
- O(1) cache lookup complexity

### Root Server (`servers/root_server.py`)
Maps top-level domains (.com, .edu, .org) to their respective TLD server addresses.

### TLD Servers (`servers/tld_server.py`)
Handles domains under a specific TLD. Configurable via command-line arguments (`--tld`, `--port`).

### Authoritative Server (`servers/authoritative_server.py`)
Stores domain → IP mappings loaded from `data/dns_records.txt`. Returns final IP addresses for queried domains.

## Protocol

### Message Format
```
QUERY:    QUERY|<query_id>|<domain>
RESPONSE: RESPONSE|<query_id>|<domain>|<result_type>|<result_value>

Result Types:
  - IP:    Final IP address
  - NS:    Referral to another name server (format: "TLD:host:port" or "AUTH:host:port")
  - ERROR: Error message
```

### Query Flow

**Iterative Resolution (Cache Miss):**
```
1. Client → Local Server: QUERY|1|www.example.com
2. Local Server → Root:   QUERY|1|www.example.com
3. Root → Local Server:   RESPONSE|1|www.example.com|NS|TLD:127.0.0.1:53001
4. Local Server → TLD:    QUERY|1|www.example.com
5. TLD → Local Server:    RESPONSE|1|www.example.com|NS|AUTH:127.0.0.1:53003
6. Local Server → Auth:   QUERY|1|www.example.com
7. Auth → Local Server:   RESPONSE|1|www.example.com|IP|0.0.0.0
8. Local Server caches result
9. Local Server → Client: RESPONSE|1|www.example.com|IP|0.0.0.0
```

**Cached Resolution (Cache Hit):**
```
1. Client → Local Server: QUERY|2|www.example.com
2. Local Server checks cache → HIT
3. Local Server → Client: RESPONSE|2|www.example.com|IP|0.0.0.0
```

## Caching Strategy

### LRU Cache Implementation
- **Data Structure:** Python `OrderedDict` (hash table + doubly-linked list)
- **Eviction Policy:** Least Recently Used (LRU)
- **Time-to-Live:** 300 seconds (configurable)
- **Capacity:** 1,000 entries (configurable)

### Cache Operations
```python
# Lookup: O(1)
if domain in cache and not expired:
    cache.move_to_end(domain)  # Update LRU order
    return cached_ip

# Insertion: O(1)
if len(cache) >= max_size:
    cache.popitem(last=False)  # Evict oldest
cache[domain] = (ip, timestamp)
```

### Expiration
Entries expire after TTL seconds. Expiration is checked lazily on access (not via active background scanning).

## Performance Characteristics

### Measured Performance
- **Throughput:** 9,963 queries/second
- **Cache Hit Rate:** 85.7% (sustained workload)
- **Latency:**
  - Cache hit: 0.21ms average
  - Cache miss: 0.60ms average (3-hop resolution)
  - P95: 0.24ms
  - P99: 0.49ms

### Complexity Analysis
| Operation | Time Complexity | Space Complexity |
|-----------|----------------|------------------|
| Cache lookup | O(1) | O(n) where n = cache size |
| Cache insert | O(1) | O(n) |
| Domain lookup (Auth) | O(1) | O(m) where m = # of records |
| TLD lookup (Root) | O(1) | O(k) where k = # of TLDs |

## Network Communication

### TCP Socket Configuration
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, SO_REUSEADDR, 1)
sock.bind((host, port))
sock.listen(5)  # Backlog of 5 connections
```

### Connection Lifecycle
1. Accept connection: `conn, addr = sock.accept()`
2. Receive query: `data = conn.recv(1024)` (blocking)
3. Process and respond: `conn.sendall(response.serialize())`
4. Close connection: `conn.close()`

Each query uses a dedicated connection (no persistent connections or pipelining).

## Data Storage

### Zone File Format (`data/dns_records.txt`)
```
# Comments start with #
domain,ip_address
example.com,0.0.0.0
example.edu,0.0.0.0
```

**Loading:** Parsed on server startup. Changes require server restart.

## Configuration

### Server Ports
| Component | Default Port | Configurable |
|-----------|-------------|--------------|
| Root Server | 53000 | ✓ |
| TLD .com | 53001 | ✓ |
| TLD .edu | 53002 | ✓ |
| Authoritative | 53003 | ✓ |
| Local Server | 53004 | ✓ |

### Cache Parameters
```python
max_size = 1000  # Maximum cache entries
ttl = 300        # Time-to-live in seconds
```

## Benchmarking

The project includes automated benchmarking (`final_benchmark.py`) that measures:
- Sequential query throughput
- Concurrent query handling (20 threads)
- Cache effectiveness (hit rate, latency reduction)
- Latency distribution (P50/P95/P99)

Run with: `python3 final_benchmark.py`

## Design Decisions

### TCP vs UDP
Uses TCP for guaranteed delivery and simplified implementation. Production DNS primarily uses UDP with TCP fallback for large responses.

### Iterative vs Recursive Resolution
Implements iterative resolution where the Local Server (not upstream servers) performs multi-hop queries. This demonstrates the DNS hierarchy more explicitly than recursive resolution.

### Single-Threaded Servers
Each server processes one request at a time. Sufficient for localhost communication with microsecond latencies. Production systems would use async I/O or threading for concurrent request handling.

---

**Implementation:** Python 3.8+, standard library only (no external dependencies).
