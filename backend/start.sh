#!/bin/bash

# Simple start script for Google Cloud Run
echo "🚀 Starting DineOut backend on Google Cloud Run..."

# The environment variables are automatically set by Cloud Run
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8080}

echo "📡 Starting server on $HOST:$PORT"

# Start the FastAPI application
exec uvicorn app.main:app --host $HOST --port $PORT --workers 1
