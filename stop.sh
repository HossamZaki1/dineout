#!/bin/bash

echo "🛑 Stopping DineOut App..."

# Kill processes on ports
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :3000 | xargs kill -9 2>/dev/null || true

# Kill flutter and uvicorn processes
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
pkill -f "flutter.*run" 2>/dev/null || true

echo "✅ App stopped!"


