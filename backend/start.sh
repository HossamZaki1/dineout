#!/bin/bash

# Remedy Bot Backend Startup Script

echo "Starting Remedy Bot Multi-Agent System..."

# Check configuration first
echo "Checking configuration..."
python3 simple_config_check.py
if [ $? -ne 0 ]; then
    echo "❌ Configuration check failed. Please fix your .env file."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the server
echo "Starting FastAPI server..."
cd app
python main.py
