#!/bin/bash
# =============================================================
# DataCenter Submittal Review Platform - One-Click Startup
# =============================================================
# This script installs everything and starts both the backend
# and frontend servers. Just run: ./start.sh
# =============================================================

set -e

echo "============================================"
echo "  DC Submittal Review Platform - Starting"
echo "============================================"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    echo "Install it from: https://www.python.org/downloads/"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is required but not installed."
    echo "Install it from: https://nodejs.org/"
    exit 1
fi

echo "[1/4] Installing Python dependencies..."
cd backend
python3 -m pip install -r requirements.txt --quiet 2>&1 | tail -1
cd ..

echo "[2/4] Installing frontend dependencies..."
cd frontend
npm install --silent 2>&1 | tail -1
cd ..

echo "[3/4] Starting backend server (API)..."
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "     Waiting for backend to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "     Backend is ready!"
        break
    fi
    sleep 1
done

echo "[4/4] Starting frontend (UI)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo "  ALL RUNNING!"
echo "============================================"
echo ""
echo "  Open your browser to:"
echo ""
echo "    http://localhost:5173"
echo ""
echo "  (Backend API at http://localhost:8000)"
echo ""
echo "  To stop: press Ctrl+C"
echo "============================================"
echo ""

# Handle Ctrl+C gracefully
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Keep running
wait
