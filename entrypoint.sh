#!/bin/bash
set -e

echo "Starting Applied Time Series Production Engine..."

# Start FastAPI backend in background
uvicorn api:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!
echo "FastAPI backend started with PID $FASTAPI_PID on port 8000."

# Start Streamlit dashboard in foreground
echo "Starting Streamlit UI on port 8501..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
