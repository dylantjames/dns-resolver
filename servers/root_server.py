#!/usr/bin/env python3
"""
Root DNS Server

Responsibilities:
- Receives queries for any domain
- Returns the appropriate TLD server address based on domain extension
- Handles .com, .edu, .org, etc.
"""

import socket
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dns_protocol import DNSMessage


class RootServer:
    def __init__(self, host='127.0.0.1', port=53000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # TLD server mappings
        self.tld_servers = {
            'com': ('127.0.0.1', 53001),
            'edu': ('127.0.0.1', 53002),
            'org': ('127.0.0.1', 53001),  # Reuse .com TLD for .org
        }

        self.query_count = 0

    def get_tld(self, domain):
        """Extract TLD from domain name"""
        parts = domain.split('.')
        if len(parts) >= 2:
            return parts[-1]
        return None

    def handle_query(self, query_msg):
        """Process DNS query and return appropriate TLD server"""
        self.query_count += 1

        tld = self.get_tld(query_msg.domain)

        if tld and tld in self.tld_servers:
            tld_host, tld_port = self.tld_servers[tld]
            result = f"TLD:{tld_host}:{tld_port}"
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="NS",
                result_value=result
            )
            print(f"[ROOT] Query #{self.query_count}: {query_msg.domain} -> TLD server for .{tld} at {tld_host}:{tld_port}")
        else:
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="ERROR",
                result_value=f"No TLD server for .{tld}"
            )
            print(f"[ROOT] Query #{self.query_count}: {query_msg.domain} -> ERROR: Unknown TLD")

        return response

    def start(self):
        """Start the root server"""
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[ROOT] Server started on {self.host}:{self.port}")
        print(f"[ROOT] Handling TLDs: {', '.join(self.tld_servers.keys())}")

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
                print(f"\n[ROOT] Shutting down... Processed {self.query_count} queries")
                break
            except Exception as e:
                print(f"[ROOT] Error: {e}")

        self.sock.close()


if __name__ == "__main__":
    server = RootServer()
    server.start()
