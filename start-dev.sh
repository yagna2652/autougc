#!/bin/bash
# Start both FastAPI backend and Next.js frontend

echo "🚀 Starting AutoUGC Development Servers..."
echo ""

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -r requirements-api.txt"
    exit 1
fi

# Start FastAPI backend
echo "🔵 Starting FastAPI backend on http://localhost:8000..."
source venv/bin/activate
python -m uvicorn api.server:app --reload --port 8000 > fastapi.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 2

# Start Next.js frontend
echo "🟢 Starting Next.js frontend on http://localhost:3000..."
cd web
npm run dev > ../nextjs.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Both servers started!"
echo ""
echo "📊 Access your application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo ""
echo "📝 View logs:"
echo "   Backend:  tail -f fastapi.log"
echo "   Frontend: tail -f nextjs.log"
echo ""
echo "🛑 To stop servers:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   Or run: ./stop-dev.sh"
echo ""

# Save PIDs for stop script
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

# Wait for both processes
wait
