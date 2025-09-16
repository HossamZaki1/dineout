#!/bin/bash

echo "🍽️ Starting DineOut App..."

# Start backend
echo "Starting backend..."
cd backend
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install -q -r requirements-simple.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend  
echo "Starting frontend..."
cd ../frontend
flutter pub get
flutter run -d web-server --web-port=3000 &
FRONTEND_PID=$!

echo "✅ App running!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "Press Ctrl+C to stop"

# Cleanup on exit
cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Stopped."
}
trap cleanup EXIT

wait
