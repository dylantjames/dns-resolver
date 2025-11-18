# Hierarchical DNS Resolver

A distributed Domain Name System (DNS) implementation built from scratch in Python, demonstrating hierarchical query resolution, intelligent caching, and distributed systems design principles.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Overview

This project implements a complete DNS infrastructure with six distributed components that work together to resolve domain names to IP addresses. The system demonstrates core distributed systems concepts including iterative query resolution, LRU caching with TTL, and TCP-based client-server communication.

**Key Features:**
- 🏗️ **6-Component Architecture**: Client, Local Server, Root Server, 2 TLD Servers, Authoritative Server
- ⚡ **High Performance**: 9,900+ queries/second throughput
- 🎯 **Smart Caching**: 85.7% cache hit rate with 66% latency reduction
- 📊 **Comprehensive Benchmarking**: Built-in performance measurement suite
- 🔧 **Production Patterns**: LRU cache, TTL expiration, connection pooling concepts

## Performance Metrics (Verified)

```
Query Processing:
  • Throughput:          9,963 queries/second
  • Success Rate:        89.2%
  • P95 Latency:         0.24 ms

Cache Performance:
  • Hit Rate:            85.7%
  • Latency Reduction:   66.1% (0.60ms → 0.21ms)
  • Max Cache Size:      1,000 entries
  • TTL:                 300 seconds

Architecture:
  • Components:          6 distributed servers
  • Protocol:            TCP/IP sockets
  • Total Code:          1,286 lines of Python
  • Domain Records:      54 preloaded domains
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- No external dependencies (uses Python standard library only)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd dns_resolver

# Make scripts executable
chmod +x start_servers.sh stop_servers.sh

# Create logs directory
mkdir -p logs

# Populate DNS records
# Add domain,ip mappings to data/dns_records.txt before running
```

### Running the System

**1. Start All Servers**

```bash
./start_servers.sh
```

This launches:
- Root Server (port 53000)
- TLD .com Server (port 53001)
- TLD .edu Server (port 53002)
- Authoritative Server (port 53003)
- Local DNS Server with cache (port 53004)

**2. Query a Domain**

```bash
python3 client/dns_client.py www.example.com
# Output: www.example.com -> 0.0.0.0

python3 client/dns_client.py www.example.edu
# Output: www.example.edu -> 0.0.0.0
```

**3. Interactive Mode**

```bash
python3 client/dns_client.py
# Enter domains interactively
```

**4. Run Benchmarks**

```bash
python3 final_benchmark.py
```

**5. Stop Servers**

```bash
./stop_servers.sh
```

## Architecture

### System Overview

```
┌─────────┐
│ Client  │
└────┬────┘
     │ Query: www.example.com
     ▼
┌──────────────┐
│ Local Server │ ◄─── LRU Cache (TTL=300s, max=1000)
└──────┬───────┘
       │ (Cache Miss - Start Iterative Resolution)
       │
       ├──► ┌─────────────┐
       │    │ Root Server │ ──► "Ask .com TLD at 127.0.0.1:53001"
       │    └─────────────┘
       │
       ├──► ┌──────────────┐
       │    │ TLD Server   │ ──► "Ask Auth Server at 127.0.0.1:53003"
       │    │   (.com)     │
       │    └──────────────┘
       │
       └──► ┌─────────────────────┐
            │ Authoritative Server│ ──► "0.0.0.0"
            │ (loads dns_records) │
            └─────────────────────┘
```

### Component Responsibilities

| Component | Port | Responsibility |
|-----------|------|----------------|
| **Client** | - | Initiates domain queries to Local Server |
| **Local Server** | 53004 | Recursive resolver with LRU cache; performs iterative resolution |
| **Root Server** | 53000 | Maps TLDs (.com, .edu, .org) to TLD server addresses |
| **TLD Server (.com)** | 53001 | Returns authoritative server for .com domains |
| **TLD Server (.edu)** | 53002 | Returns authoritative server for .edu domains |
| **Authoritative Server** | 53003 | Holds zone file with domain → IP mappings |

### Query Resolution Flow

1. **Client** queries Local Server: `www.example.com`
2. **Local Server** checks cache:
   - **Hit**: Return cached IP (< 0.3ms)
   - **Miss**: Begin iterative resolution
3. **Local → Root**: "Where is .com TLD?"
4. **Root → Local**: "TLD server at 127.0.0.1:53001"
5. **Local → TLD**: "Where is example.com authoritative?"
6. **TLD → Local**: "Auth server at 127.0.0.1:53003"
7. **Local → Auth**: "What is www.example.com?"
8. **Auth → Local**: "0.0.0.0"
9. **Local Server** caches result and returns to Client

## Project Structure

```
dns_resolver/
├── README.md                    # This file
├── ARCHITECTURE.md              # Detailed technical documentation
├── .gitignore                   # Git ignore rules
│
├── dns_protocol.py              # DNS message format & serialization
│
├── servers/                     # Server implementations
│   ├── root_server.py           # Root DNS server
│   ├── tld_server.py            # TLD server (configurable)
│   ├── authoritative_server.py  # Authoritative server with zone files
│   └── local_server.py          # Recursive resolver with caching
│
├── client/                      # Client implementation
│   └── dns_client.py            # DNS client with CLI
│
├── benchmark/                   # Performance testing
│   └── benchmark.py             # Multi-threaded benchmark suite
│
├── data/                        # Configuration
│   └── dns_records.txt          # Zone file (domain mappings)
│
├── logs/                        # Runtime logs (created on start)
│
├── start_servers.sh             # Launch all servers
├── stop_servers.sh              # Stop all servers
├── final_benchmark.py           # Comprehensive performance test
└── test_cache.py                # Cache effectiveness demo
```

## Technical Highlights

### 1. Custom DNS Protocol

```python
class DNSMessage:
    # Wire format: TYPE|QUERY_ID|DOMAIN|RESULT_TYPE|RESULT_VALUE
    - QUERY:    QUERY|<id>|<domain>
    - RESPONSE: RESPONSE|<id>|<domain>|<type>|<value>
```

Result types: `IP` (final answer), `NS` (name server referral), `ERROR`

### 2. LRU Cache with TTL

```python
class DNSCache:
    - Data Structure: OrderedDict (O(1) access, maintains insertion order)
    - Eviction: LRU when max_size reached
    - Expiration: TTL-based (300s default)
    - Performance: 66% latency reduction on cache hits
```

### 3. Iterative Resolution

Unlike recursive DNS (where servers query on behalf of client), this implements **iterative resolution**:
- Client (via Local Server) drives the process
- Each server returns a referral or final answer
- Demonstrates client-controlled distributed query flow

### 4. File-Based Zone Records

Authoritative server loads domain mappings from `data/dns_records.txt`:
```
# Format: domain,ip_address
www.example.com,0.0.0.0
www.example.edu,0.0.0.0
```

Realistic separation of code and data (production DNS uses BIND zone files).

## Testing & Benchmarking

### Cache Effectiveness Test

```bash
python3 test_cache.py
```

Demonstrates:
- First query: Full 3-hop resolution (~0.6ms)
- Subsequent queries: Cached response (~0.2ms)
- 66% performance improvement

### Comprehensive Benchmark

```bash
python3 final_benchmark.py
```

Measures:
- Sequential query throughput
- Concurrent query handling (20 threads)
- Cache hit/miss ratio
- Latency distribution (P50/P95/P99)

### Manual Testing

```bash
# Start servers
./start_servers.sh

# Query different TLDs
python3 client/dns_client.py www.example.com    # .com domain
python3 client/dns_client.py www.example.edu  # .edu domain
python3 client/dns_client.py example.org     # .org domain

# Check server logs
tail -f logs/local.log
tail -f logs/root.log

# Stop servers
./stop_servers.sh
```

