#!/bin/bash

# Mock API request to test the chat endpoint
# This simulates the exact request your Flutter app makes

echo "🚀 Testing DineQuest Chat API..."
echo "Backend URL: http://127.0.0.1:8080"
echo ""

# Test 1: Basic chat request
echo "📤 Test 1: Basic restaurant search request"
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "I want to find Italian restaurants in San Francisco",
    "session_id": "test-session-123",
    "history": []
  }' \
  | python3 -m json.tool

echo ""
echo "----------------------------------------"
echo ""

# Test 2: Follow-up request with history
echo "📤 Test 2: Follow-up request with conversation history"
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "What about something more upscale?",
    "session_id": "test-session-123",
    "history": [
      {
        "role": "user",
        "content": "I want to find Italian restaurants in San Francisco"
      },
      {
        "role": "assistant",
        "content": "I found some great Italian restaurants in San Francisco for you!"
      }
    ]
  }' \
  | python3 -m json.tool

echo ""
echo "----------------------------------------"
echo ""

# Test 3: Health check endpoint
echo "📤 Test 3: Health check endpoint"
curl -X GET http://127.0.0.1:8080/health \
  -H "Content-Type: application/json" \
  | python3 -m json.tool

echo ""
echo "✅ API testing complete!"
