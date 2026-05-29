#!/bin/bash
# BAI Phase 1 Setup Script
# Initializes Git repository and project structure

set -e

echo "🚀 BAI Phase 1 Project Setup"
echo "=============================="
echo ""

# Navigate to project root
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

echo "📁 Project Root: $PROJECT_ROOT"
echo ""

# Initialize Git
if [ ! -d .git ]; then
    echo "🔧 Initializing Git repository..."
    git init
    git config user.name "BAI Developer"
    git config user.email "dev@bai.local"
else
    echo "✓ Git repository already initialized"
fi

echo ""
echo "📝 Adding files to Git..."
git add .

echo ""
echo "💾 Creating initial commit..."
git commit -m "Phase 1 Project Structure - Telemetry Collection Pipeline

- Frontend: sensor.js for click capture
- Backend: FastAPI for telemetry ingestion
- Database: Supabase PostgreSQL schema
- Demo: 5-section landing page for testing
- Docs: Complete architecture and API docs

Ready for Phase 1 testing" || echo "Nothing to commit (files already tracked)"

echo ""
echo "✓ Project initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Create Supabase account: https://supabase.com"
echo "2. Copy .env.example → .env and fill in credentials"
echo "3. Create database tables (see docs/DATABASE_SCHEMA.md)"
echo "4. Start backend: cd backend && python main.py"
echo "5. Start frontend: cd frontend/demo-website && python -m http.server 5000"
echo "6. Visit http://localhost:5000"
echo ""
