#!/usr/bin/env python3
"""
Authoritative DNS Server

Responsibilities:
- Loads domain name to IP address mappings from dns_records.txt
- Returns final IP address for domain queries
- Authoritative source of truth for domain records
"""

import socket
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dns_protocol import DNSMessage


class AuthoritativeServer:
    def __init__(self, host='127.0.0.1', port=53003, records_file='data/dns_records.txt'):
        self.host = host
        self.port = port
        self.records_file = records_file
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # DNS records: domain -> IP mapping
        self.dns_records = {}
        self.load_dns_records()

        self.query_count = 0

    def load_dns_records(self):
        """Load DNS records from text file"""
        # Construct absolute path to records file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        records_path = os.path.join(base_dir, self.records_file)

        try:
            with open(records_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line.startswith('#') or not line:
                        continue

                    parts = line.split(',')
                    if len(parts) == 2:
                        domain = parts[0].strip().lower()
                        ip = parts[1].strip()
                        self.dns_records[domain] = ip

            print(f"[AUTH] Loaded {len(self.dns_records)} DNS records from {records_path}")
        except FileNotFoundError:
            print(f"[AUTH] ERROR: Records file not found: {records_path}")
            print(f"[AUTH] Starting with empty records database")
        except Exception as e:
            print(f"[AUTH] ERROR loading records: {e}")
            print(f"[AUTH] Starting with empty records database")

    def handle_query(self, query_msg):
        """Process DNS query and return IP address"""
        self.query_count += 1

        domain = query_msg.domain.lower()

        if domain in self.dns_records:
            ip_address = self.dns_records[domain]
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="IP",
                result_value=ip_address
            )
            print(f"[AUTH] Query #{self.query_count}: {query_msg.domain} -> {ip_address}")
        else:
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="ERROR",
                result_value="Domain not found"
            )
            print(f"[AUTH] Query #{self.query_count}: {query_msg.domain} -> NOT FOUND")

        return response

    def start(self):
        """Start the authoritative server"""
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[AUTH] Server started on {self.host}:{self.port}")

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
                print(f"\n[AUTH] Shutting down... Processed {self.query_count} queries")
                break
            except Exception as e:
                print(f"[AUTH] Error: {e}")

        self.sock.close()


if __name__ == "__main__":
    server = AuthoritativeServer()
    server.start()
