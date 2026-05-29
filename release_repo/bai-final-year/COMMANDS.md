# BAI Phase 1 - Essential Commands

## Project Location
```bash
cd /home/zibo127/Downloads/Headless_BAI/bai-final-year
```

## Initial Setup (One-Time)

### 1. Create Supabase Account & Project
```bash
# Go to: https://app.supabase.com
# Sign up with GitHub (or email)
# Create new project named "bai-mvp"
# Choose region closest to you
# Set strong password and save it
```

### 2. Get Supabase Credentials
```bash
# Go to: https://app.supabase.com → Settings → API
# Copy SUPABASE_URL and SUPABASE_ANON_KEY
# Keep both safe!
```

### 3. Setup Environment
```bash
# Copy template
cp .env.example .env

# Edit with text editor (VS Code, nano, vim, etc)
nano .env
# Paste SUPABASE_URL and SUPABASE_ANON_KEY

# Verify (should NOT show actual keys in output)
cat .env
```

### 4. Create Database Tables
```bash
# Open Supabase SQL Editor:
# https://app.supabase.com → SQL Editor → New Query

# Copy entire contents of docs/DATABASE_SCHEMA.md
# Paste into Supabase SQL Editor
# Click "Run" button
# Verify tables created in Table Editor

# Or run helper script (shows SQL commands):
bash create-tables.sh
```

## Development Setup

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Or Use Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

### Terminal 1: Start Backend
```bash
cd backend
python main.py
# Output: Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2: Start Frontend
```bash
cd frontend/demo-website
python -m http.server 5000
# Output: Serving HTTP on 0.0.0.0 port 5000
```

### Terminal 3 (Optional): Monitor Logs
```bash
# Check what's happening in real-time
tail -f backend.log  # If logging is enabled
```

## Testing the Pipeline

### 1. Open Frontend
```bash
# Open browser and go to:
http://localhost:5000
```

### 2. Capture Click Data
```bash
# Click around the website for 5 seconds
# See console (F12) for debug output
# Notice: Interactions batched locally
```

### 3. Wait for Automatic Flush
```bash
# Every 5 seconds, data automatically sends to backend
# Watch console for: "Flushed X interactions"
# Backend console shows: "Received X interactions"
```

### 4. Verify Data in Supabase
```bash
# Go to: https://app.supabase.com
# Table Editor → raw_events
# Should see rows with your clicks!
# Fields: session_id, x, y, viewport_w, viewport_h, ema_weight, created_at
```

## Quick Verification Commands

### Check Backend Health
```bash
curl http://localhost:8000/health
# Response: {"status": "ok", "timestamp": "...", "database": "connected"}
```

### Get Statistics
```bash
curl http://localhost:8000/api/stats
# Response: {"status": "ok", "total_sessions": N, "total_events": N}
```

### View API Documentation
```bash
# Open browser and go to:
http://localhost:8000/docs
# Interactive Swagger UI for testing endpoints
```

### Check Logs
```bash
# In backend terminal, you should see:
# [INFO] - Session XXXX created
# [INFO] - Received X interactions
# [ERROR] - Any issues (if something goes wrong)
```

## Debugging Commands

### Test Frontend Sensor Directly
```bash
# Open browser console (F12) on http://localhost:5000
# Type: window.BAI_Sensor
# See configuration and stats
```

### Check Browser LocalStorage
```javascript
// In browser console (F12):
localStorage.getItem('bai_session_id')  // Should return UUID
localStorage.getItem('bai_events')      // Shows buffered events
```

### Manual Event Send
```javascript
// In browser console on test.html:
document.getElementById('simulateButton').click()  // Simulate clicks
document.getElementById('flushButton').click()    // Manually flush
```

### Query Supabase Directly
```sql
-- In Supabase SQL Editor:
SELECT * FROM raw_events ORDER BY created_at DESC LIMIT 10;
SELECT COUNT(*) FROM raw_events;
SELECT COUNT(DISTINCT session_id) FROM raw_events;
```

## Docker Commands (Alternative)

### Build and Run with Docker
```bash
# Build images
docker-compose build

# Start all services
docker-compose up

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

## Development Workflow

### Watch for Backend Changes (Hot Reload)
```bash
# Option 1: Use Uvicorn with reload flag
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Run script
bash start.sh  # Handles hot reload automatically
```

### Monitor Frontend Changes
```bash
# Frontend is served statically, no reload needed
# Just refresh browser (Ctrl+R or Cmd+R)
# Changes to sensor.js take effect immediately
```

### View Active Connections
```bash
# Check what's listening on ports 8000 and 5000:
lsof -i :8000    # Backend
lsof -i :5000    # Frontend
```

## Git Commands

### Initialize Repository
```bash
bash setup.sh  # Runs git init and creates initial commit
# Or manually:
git init
git add .
git commit -m "Initial commit: Phase 1 telemetry"
```

### Create Checkpoint Commit
```bash
git add .
git commit -m "Phase 1: Verified data collection with 500+ events"
```

### Track Progress
```bash
git log --oneline      # See all commits
git status             # See what changed
git diff frontend/     # See changes to frontend
```

## Troubleshooting Commands

### Port Already in Use
```bash
# Find and kill process using port 8000
sudo lsof -i :8000 | grep LISTEN
sudo kill -9 <PID>

# Or use different port:
cd backend
python main.py --port 9000
# Then update SENSOR_CONFIG.API_ENDPOINT in sensor.js
```

### Supabase Connection Failed
```bash
# Test connection:
python -c "from supabase import create_client; print(create_client('URL', 'KEY'))"

# Check credentials:
cat .env | grep SUPABASE

# Verify URL format (should be: https://xxxxx.supabase.co):
# Not: https://xxxxx.supabase.co/ (no trailing slash)
```

### Dependencies Installation Failed
```bash
# Update pip first
pip install --upgrade pip

# Try again
pip install -r requirements.txt

# Or be specific:
pip install fastapi==0.104.1 uvicorn==0.24.0 pydantic==2.4.2
```

### Data Not Appearing in Supabase
```bash
# 1. Check backend is running:
curl http://localhost:8000/health

# 2. Check browser console for errors (F12):
# Look for red messages

# 3. Check backend logs:
# Should show "Received X interactions"

# 4. Check database tables exist:
# Supabase → Table Editor → Should show raw_events table

# 5. Check database connection in .env:
cat .env
```

## Performance Monitoring

### Check Request Latency
```bash
# Backend will log response times:
# [INFO] - POST /api/ingest - Response time: 45ms

# Check in API docs:
http://localhost:8000/docs
# Execute requests and see timing
```

### Monitor Database Performance
```sql
-- In Supabase SQL Editor:
-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('sessions', 'raw_events', 'user_clusters', 'layouts');
```

## Stopping Services

### Stop Backend
```bash
# In backend terminal: Ctrl+C
# Or: kill -9 <process_id>
```

### Stop Frontend
```bash
# In frontend terminal: Ctrl+C
# Or: kill -9 <process_id>
```

### Stop All Docker Services
```bash
docker-compose down
```

## Next Steps (Phase 2)

### When Ready for Phase 2:
```bash
# 1. Capture data with current implementation
# 2. Verify 50+ events in Supabase
# 3. Take screenshots for documentation
# 4. Create git commit:
git add . && git commit -m "Phase 1 complete: 500+ events captured"

# 5. Start Phase 2 setup:
# - Create backend/playwright_extractor.py
# - Add section bounding box extraction
# - Implement click → section mapping
```

## Useful References

| Command | Purpose |
|---------|---------|
| `python main.py` | Start backend |
| `python -m http.server 5000` | Start frontend |
| `curl http://localhost:8000/health` | Check backend |
| `curl http://localhost:8000/api/stats` | Get stats |
| `cat .env` | View config |
| `tail -f backend.log` | Watch logs |
| `docker-compose up` | Start with Docker |
| `docker-compose down` | Stop all services |
| `git status` | Check git status |
| `git log --oneline` | See commits |

## Emergency: Reset Everything

```bash
# If something breaks completely:

# 1. Stop services (Ctrl+C)
# 2. Deactivate virtual environment
deactivate

# 3. Remove virtual environment
rm -rf venv

# 4. Create fresh environment
python3 -m venv venv
source venv/bin/activate

# 5. Install dependencies again
cd backend
pip install -r requirements.txt

# 6. Start fresh:
python main.py
# In new terminal:
cd frontend/demo-website && python -m http.server 5000
```

## Need Help?

- **Setup issues?** → See TESTING_GUIDE.md § Supabase Setup
- **Testing problems?** → See TESTING_GUIDE.md § Testing Scenarios
- **API questions?** → See docs/API_SPECIFICATION.md
- **Database help?** → See docs/DATABASE_SCHEMA.md
- **Architecture?** → See docs/ARCHITECTURE.md
- **Lost?** → See INDEX.md

---

**Quick Start Summary:**
```bash
# 1. Setup .env with Supabase credentials
cp .env.example .env && nano .env

# 2. Create database tables (copy from DATABASE_SCHEMA.md to Supabase)

# 3. Start backend
cd backend && python main.py

# 4. Start frontend (new terminal)
cd frontend/demo-website && python -m http.server 5000

# 5. Click at http://localhost:5000 and verify data in Supabase
```

**That's it! You're ready to collect telemetry data! 🚀**
