#!/bin/bash

set -e

echo "Starting Recovery Validation Backend..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start demo app in background
echo "Starting demo app on port 8001..."
python -m src.demo_app.main &
DEMO_PID=$!

# Wait for demo app to start
sleep 2

# Start orchestrator in background
echo "Starting orchestrator on port 8000..."
python -m src.orchestrator.main &
ORCH_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $DEMO_PID $ORCH_PID 2>/dev/null || true
    wait
    echo "Services stopped."
}

# Set trap to cleanup on script exit
trap cleanup EXIT

echo "Backend services started!"
echo "Demo app: http://localhost:8001"
echo "Orchestrator: http://localhost:8000"
echo "WebSocket: ws://localhost:8000/ws"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for both processes
wait