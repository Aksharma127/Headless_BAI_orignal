#!/bin/bash
# Quick start script for Phase 1 testing
# Run: bash start.sh

set -e

echo "🎯 BAI Phase 1 - Quick Start"
echo "============================="
echo ""

PROJECT_ROOT="$(dirname "$0")"
cd "$PROJECT_ROOT"

# Check for .env file
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env from .env.example with your Supabase credentials:"
    echo ""
    echo "  cp .env.example .env"
    echo "  # Edit .env with your SUPABASE_URL and keys"
    echo ""
    exit 1
fi

echo "✓ .env file found"
echo ""

# Terminal 1: Start Backend
echo "📡 Starting Backend API on http://localhost:8000..."
echo "   Logs will appear below"
echo "   Press Ctrl+C to stop"
echo ""

cd backend

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip install -q -r requirements.txt
fi

# Run backend
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    exit 1
fi

echo "✓ Backend running (PID: $BACKEND_PID)"
echo ""

# Terminal 2: Start Frontend
echo "🌐 Starting Frontend on http://localhost:5000..."
echo "   Open http://localhost:5000 in your browser"
echo ""

cd ../frontend/demo-website
python -m http.server 5000 2>&1 | grep -v "GET" &
FRONTEND_PID=$!

sleep 2

echo "✓ Frontend running (PID: $FRONTEND_PID)"
echo ""

# Instructions
echo "═══════════════════════════════════════════════════"
echo "✨ BAI Phase 1 is ready!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "📍 Open your browser:"
echo "   Frontend: http://localhost:5000"
echo "   Backend:  http://localhost:8000/docs"
echo ""
echo "🔍 Test the pipeline:"
echo "   1. Visit http://localhost:5000"
echo "   2. Click around the website"
echo "   3. Wait 5 seconds for flush"
echo "   4. Check Supabase dashboard for data in raw_events"
echo ""
echo "⚠️  To stop both services, press Ctrl+C"
echo ""

# Trap Ctrl+C to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo 'Stopped.'" EXIT

# Wait for both processes
wait
