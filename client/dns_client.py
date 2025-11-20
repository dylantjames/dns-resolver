#!/usr/bin/env python3
"""DNS client for querying local DNS server.

Provides command line interface for resolving domain names to IP addresses.
"""

import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dns_protocol import DNSMessage


class DNSClient:
    """DNS client that queries local server.

    Attributes:
        local_server: (host, port) tuple for local DNS server.
        query_id: Incrementing query identifier.
    """

    def __init__(self, local_server=('127.0.0.1', 53004)):
        self.local_server = local_server
        self.query_id = 0

    def resolve(self, domain):
        """Resolve domain name to IP address.

        Args:
            domain: Domain name to resolve.

        Returns:
            IP address string or error message prefixed with "ERROR:".
        """
        self.query_id += 1

        query = DNSMessage("QUERY", self.query_id, domain)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.local_server)

            sock.sendall(query.serialize())

            data = sock.recv(1024)
            sock.close()

            if data:
                response = DNSMessage.deserialize(data)

                if response.result_type == "IP":
                    return response.result_value
                else:
                    return f"ERROR: {response.result_value}"
        except Exception as e:
            return f"ERROR: {e}"

        return "ERROR: No response"

    def interactive_mode(self):
        """Run interactive command line interface."""
        print("DNS Client - Interactive Mode")
        print(f"Connected to Local Server: {self.local_server[0]}:{self.local_server[1]}")
        print("Enter domain names to resolve (or 'quit' to exit)")
        print()

        while True:
            try:
                domain = input("Enter domain: ").strip()

                if domain.lower() in ['quit', 'exit', 'q']:
                    break

                if not domain:
                    continue

                print(f"Resolving {domain}...")
                ip = self.resolve(domain)
                print(f"Result: {domain} -> {ip}")
                print()

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='DNS Client')
    parser.add_argument('--server-host', type=str, default='127.0.0.1',
                        help='Local DNS server host')
    parser.add_argument('--server-port', type=int, default=53004,
                        help='Local DNS server port')
    parser.add_argument('domain', nargs='?', help='Domain to resolve')

    args = parser.parse_args()

    client = DNSClient(local_server=(args.server_host, args.server_port))

    if args.domain:
        ip = client.resolve(args.domain)
        print(f"{args.domain} -> {ip}")
    else:
        client.interactive_mode()
