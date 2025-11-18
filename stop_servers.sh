#!/bin/bash

# Stop all DNS servers

if [ ! -f .server_pids ]; then
    echo "No server PIDs found. Are the servers running?"
    echo "You can manually find and kill processes with: ps aux | grep server.py"
    exit 1
fi

PIDS=$(cat .server_pids)

echo "Stopping DNS servers..."

for PID in $PIDS; do
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping process $PID..."
        kill $PID
    fi
done

sleep 1

# Force kill if still running
for PID in $PIDS; do
    if kill -0 $PID 2>/dev/null; then
        echo "Force stopping process $PID..."
        kill -9 $PID
    fi
done

rm -f .server_pids

echo "All servers stopped."
