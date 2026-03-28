#!/bin/bash
# Stops all running servers
echo "Stopping servers..."
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "  Backend stopped" || echo "  Backend was not running"
pkill -f "vite" 2>/dev/null && echo "  Frontend stopped" || echo "  Frontend was not running"
echo "Done."
