#!/bin/bash
# Stop both development servers

echo "🛑 Stopping AutoUGC Development Servers..."

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Stop backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID 2>/dev/null
        echo "✓ Stopped FastAPI backend (PID: $BACKEND_PID)"
    fi
    rm .backend.pid
fi

# Stop frontend
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✓ Stopped Next.js frontend (PID: $FRONTEND_PID)"
    fi
    rm .frontend.pid
fi

# Fallback: kill any remaining processes
pkill -f "uvicorn api.server:app" 2>/dev/null
pkill -f "next dev" 2>/dev/null

echo "✅ All servers stopped"
