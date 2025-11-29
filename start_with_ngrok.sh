#!/bin/bash

echo "========================================"
echo "  Bill Extraction API - ngrok Tunnel"
echo "========================================"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "[ERROR] ngrok is not installed or not in PATH"
    echo "Please install ngrok from: https://ngrok.com/download"
    echo ""
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $FASTAPI_PID 2>/dev/null
    kill $NGROK_PID 2>/dev/null
    echo "Servers stopped."
    exit
}

# Trap Ctrl+C
trap cleanup INT TERM

echo "[1/3] Starting FastAPI server on port 8000..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
FASTAPI_PID=$!

echo "[2/3] Waiting 5 seconds for server to start..."
sleep 5

echo "[3/3] Starting ngrok tunnel..."
echo ""
echo "========================================"
echo "  ngrok will display your public URL"
echo "  Look below for the forwarding URL"
echo "========================================"
echo ""

ngrok http 8000 &
NGROK_PID=$!

echo ""
echo "Local API: http://localhost:8000"
echo "ngrok Web UI: http://127.0.0.1:4040"
echo ""
echo "Press Ctrl+C to stop servers..."

# Wait for processes
wait

