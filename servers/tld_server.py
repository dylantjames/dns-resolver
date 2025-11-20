#!/usr/bin/env python3
"""TLD (Top Level Domain) server implementation.

Receives queries for domains under its TLD and returns authoritative server address.
"""

import socket
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dns_protocol import DNSMessage


class TLDServer:
    """TLD server that delegates to authoritative servers.

    Attributes:
        tld_name: TLD this server handles (e.g., "com", "edu").
        host: Server bind address.
        port: Server bind port.
        auth_server: (host, port) tuple for authoritative server.
        sock: TCP socket for accepting connections.
        query_count: Total queries processed.
    """

    def __init__(self, tld_name, host='127.0.0.1', port=53001, auth_server=('127.0.0.1', 53003)):
        self.tld_name = tld_name
        self.host = host
        self.port = port
        self.auth_server = auth_server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.query_count = 0

    def get_domain_name(self, full_domain):
        """Extract domain name from full domain (e.g., 'example' from 'www.example.com')."""
        parts = full_domain.split('.')
        if len(parts) >= 2:
            return parts[-2]
        return full_domain

    def handle_query(self, query_msg):
        """Process DNS query and return authoritative server reference.

        Args:
            query_msg: DNSMessage query object.

        Returns:
            DNSMessage response with NS or ERROR type.
        """
        self.query_count += 1

        domain_name = self.get_domain_name(query_msg.domain)

        if query_msg.domain.endswith(f'.{self.tld_name}'):
            auth_host, auth_port = self.auth_server
            result = f"AUTH:{auth_host}:{auth_port}"
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="NS",
                result_value=result
            )
            print(f"[TLD-{self.tld_name.upper()}] Query #{self.query_count}: {query_msg.domain} -> AUTH server at {auth_host}:{auth_port}")
        else:
            response = DNSMessage(
                msg_type="RESPONSE",
                query_id=query_msg.query_id,
                domain=query_msg.domain,
                result_type="ERROR",
                result_value=f"Domain not under .{self.tld_name} TLD"
            )
            print(f"[TLD-{self.tld_name.upper()}] Query #{self.query_count}: {query_msg.domain} -> ERROR: Wrong TLD")

        return response

    def start(self):
        """Start the TLD server and handle incoming connections."""
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[TLD-{self.tld_name.upper()}] Server started on {self.host}:{self.port}")
        print(f"[TLD-{self.tld_name.upper()}] Authoritative server: {self.auth_server[0]}:{self.auth_server[1]}")

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
                print(f"\n[TLD-{self.tld_name.upper()}] Shutting down... Processed {self.query_count} queries")
                break
            except Exception as e:
                print(f"[TLD-{self.tld_name.upper()}] Error: {e}")

        self.sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TLD DNS Server')
    parser.add_argument('--tld', type=str, required=True, help='TLD name (e.g., com, edu)')
    parser.add_argument('--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('--auth-host', type=str, default='127.0.0.1', help='Authoritative server host')
    parser.add_argument('--auth-port', type=int, default=53003, help='Authoritative server port')

    args = parser.parse_args()

    server = TLDServer(
        tld_name=args.tld,
        port=args.port,
        auth_server=(args.auth_host, args.auth_port)
    )
    server.start()
