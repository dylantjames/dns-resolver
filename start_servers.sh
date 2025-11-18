#!/bin/bash

# Start all DNS servers in the background

echo "Starting DNS Infrastructure..."
echo ""

# Start Root Server
echo "Starting Root Server (port 53000)..."
python3 servers/root_server.py > logs/root.log 2>&1 &
ROOT_PID=$!
sleep 0.5

# Start .com TLD Server
echo "Starting .com TLD Server (port 53001)..."
python3 servers/tld_server.py --tld com --port 53001 > logs/tld_com.log 2>&1 &
TLD_COM_PID=$!
sleep 0.5

# Start .edu TLD Server
echo "Starting .edu TLD Server (port 53002)..."
python3 servers/tld_server.py --tld edu --port 53002 > logs/tld_edu.log 2>&1 &
TLD_EDU_PID=$!
sleep 0.5

# Start Authoritative Server
echo "Starting Authoritative Server (port 53003)..."
python3 servers/authoritative_server.py > logs/auth.log 2>&1 &
AUTH_PID=$!
sleep 0.5

# Start Local Server
echo "Starting Local Server (port 53004)..."
python3 servers/local_server.py > logs/local.log 2>&1 &
LOCAL_PID=$!
sleep 0.5

echo ""
echo "All servers started!"
echo ""
echo "Process IDs:"
echo "  Root Server:    $ROOT_PID"
echo "  TLD .com:       $TLD_COM_PID"
echo "  TLD .edu:       $TLD_EDU_PID"
echo "  Auth Server:    $AUTH_PID"
echo "  Local Server:   $LOCAL_PID"
echo ""
echo "Logs are in the logs/ directory"
echo ""
echo "To stop all servers, run: ./stop_servers.sh"
echo "To test: python3 client/dns_client.py www.google.com"
echo ""

# Save PIDs to file for stop script
echo "$ROOT_PID $TLD_COM_PID $TLD_EDU_PID $AUTH_PID $LOCAL_PID" > .server_pids
