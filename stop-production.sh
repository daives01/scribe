#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="logs/scribe.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ PID file not found: $PID_FILE"
    echo "   Server may not be running or was started differently"
    exit 1
fi

PID=$(cat "$PID_FILE")

if [ -z "$PID" ]; then
    echo "❌ PID file is empty"
    rm -f "$PID_FILE"
    exit 1
fi

# Check if process is actually running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process $PID is not running"
    echo "   Cleaning up PID file..."
    rm -f "$PID_FILE"
    exit 1
fi

echo "🛑 Stopping Scribe server (PID: $PID)..."

# Kill the process
kill "$PID"

# Wait a bit for graceful shutdown
sleep 2

# Check if it's still running (force kill if needed)
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process still running, force killing..."
    kill -9 "$PID"
    sleep 1
fi

# Clean up PID file
rm -f "$PID_FILE"

if ps -p "$PID" > /dev/null 2>&1; then
    echo "❌ Failed to stop server"
    exit 1
else
    echo "✓ Server stopped successfully"
fi

