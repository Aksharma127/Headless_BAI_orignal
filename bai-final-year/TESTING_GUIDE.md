# Phase 1 Testing Guide

Complete walkthrough for testing the telemetry pipeline end-to-end.

## Prerequisites Checklist

- [ ] Python 3.11 or higher installed
- [ ] Git installed
- [ ] Supabase account created (free tier is fine)
- [ ] Text editor or IDE
- [ ] Modern web browser

## Step-by-Step Testing

### Step 1: Supabase Setup (5 minutes)

1. **Create Supabase Project**
   - Go to https://supabase.com
   - Sign up with GitHub
   - Click "New Project"
   - Name: `bai-mvp`
   - Password: Generate strong one (save it!)
   - Region: Choose your closest
   - Click "Create new project"

2. **Get API Credentials**
   - Wait 2 minutes for initialization
   - In Supabase dashboard, go to **Settings** → **API**
   - Copy **Project URL** (SUPABASE_URL)
   - Copy **anon public key** (SUPABASE_ANON_KEY)

3. **Create Environment File**
   ```bash
   cd bai-final-year
   cp .env.example .env
   ```

4. **Fill in .env**
   - Open `.env` in text editor
   - Paste your Supabase URL and keys
   - Save

   **Example .env:**
   ```
   SUPABASE_URL=https://abcdefgh.supabase.co
   SUPABASE_ANON_KEY=your_anon_key_here
   SUPABASE_SERVICE_KEY=your_service_key_here
   DEBUG=True
   ENVIRONMENT=development
   ```

5. **Create Database Tables**
   
   **Option A: Using SQL Editor (Easiest)**
   - Go to Supabase → SQL Editor
   - Click "New Query"
   - Copy-paste this SQL and run:

   ```sql
   -- Create sessions table
   CREATE TABLE sessions (
       session_id VARCHAR(255) PRIMARY KEY,
       created_at TIMESTAMP DEFAULT NOW(),
       last_active TIMESTAMP DEFAULT NOW()
   );

   -- Create raw_events table
   CREATE TABLE raw_events (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       session_id VARCHAR(255) NOT NULL,
       section_id VARCHAR(255),
       ema_weight FLOAT8 DEFAULT 1.0,
       viewport_w INTEGER NOT NULL,
       viewport_h INTEGER NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       CONSTRAINT fk_sessions FOREIGN KEY (session_id) 
           REFERENCES sessions(session_id) ON DELETE CASCADE
   );

   -- Create user_clusters table
   CREATE TABLE user_clusters (
       session_id VARCHAR(255) PRIMARY KEY,
       cluster_id INTEGER,
       assigned_at TIMESTAMP DEFAULT NOW(),
       CONSTRAINT fk_sessions FOREIGN KEY (session_id) 
           REFERENCES sessions(session_id) ON DELETE CASCADE
   );

   -- Create layouts table
   CREATE TABLE layouts (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       cluster_id INTEGER NOT NULL,
       layout_json JSONB NOT NULL,
       generated_at TIMESTAMP DEFAULT NOW()
   );

   -- Create indexes
   CREATE INDEX idx_raw_events_session ON raw_events(session_id);
   CREATE INDEX idx_raw_events_created ON raw_events(created_at);
   ```

   - Click "Run" button
   - Wait for success message

6. **Verify Tables Created**
   - Click "Table Editor" in Supabase
   - You should see 4 tables: sessions, raw_events, user_clusters, layouts
   - Each table should have columns matching the schema

---

### Step 2: Backend Setup (5 minutes)

1. **Install Dependencies**
   ```bash
   cd bai-final-year/backend
   pip install -r requirements.txt
   ```

2. **Test Backend Connection**
   ```bash
   python main.py
   ```

   **Expected output:**
   ```
   ✓ Connected to Supabase: https://abcdefgh.supabase.co
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```

3. **Test Health Endpoint**
   - Open browser: http://localhost:8000/health
   - Should see:
   ```json
   {
     "status": "ok",
     "timestamp": "2024-05-08T10:30:45.123456",
     "database": "connected"
   }
   ```

4. **View API Documentation**
   - Go to: http://localhost:8000/docs
   - See interactive Swagger UI with all endpoints

✓ **Backend working!**

Keep this terminal running. Open a new terminal for the next step.

---

### Step 3: Frontend Setup (5 minutes)

In a **new terminal window**:

1. **Start Frontend Server**
   ```bash
   cd bai-final-year/frontend/demo-website
   python -m http.server 5000
   ```

   **Expected output:**
   ```
   Serving HTTP on 0.0.0.0 port 5000 (http://0.0.0.0:5000/) ...
   ```

2. **Visit Website**
   - Open browser: http://localhost:5000
   - You should see the demo website with 5 sections:
     1. Hero (purple gradient)
     2. Features (white background)
     3. Pricing (light gradient)
     4. Testimonials (light gray)
     5. CTA (purple gradient)

✓ **Frontend loaded!**

---

### Step 4: Test sensor.js (5 minutes)

1. **Open Browser DevTools**
   - Press F12 or right-click → "Inspect"
   - Go to "Console" tab

2. **Check Sensor Initialization**
   - You should see logs like:
   ```
   [BAI Sensor] ✓ New session created: abc123-uuid-string
   [BAI Sensor] ✓ Viewport: 1920×1080
   [BAI Sensor] ✓ Sensor initialized and ready
   ```

3. **Test Clicking**
   - Click anywhere on the webpage
   - You should see console logs:
   ```
   [BAI Sensor] Click captured: {"x": 500, "y": 300, "t": 1621000000000}
   [BAI Sensor] Click captured: {"x": 502, "y": 301, "t": 1621000000050}
   ```

4. **Wait for Flush**
   - Wait 5 seconds without clicking
   - You should see:
   ```
   [BAI Sensor] ✓ Sent via fetch: 2 interactions
   ```

✓ **sensor.js working!**

---

### Step 5: Verify Data in Supabase (5 minutes)

1. **Go to Supabase Dashboard**
   - https://app.supabase.com
   - Select your project

2. **Check Sessions Table**
   - Click "Table Editor" → "sessions"
   - You should see 1 row with:
     - session_id: (your UUID)
     - created_at: (timestamp)
     - last_active: (recent timestamp)

3. **Check Raw Events Table**
   - Click "Table Editor" → "raw_events"
   - You should see multiple rows (one per click)
   - Each row has:
     - session_id: (matching sessions table)
     - viewport_w: 1920
     - viewport_h: 1080
     - created_at: (timestamp of when clicked)
     - ema_weight: 1.0
     - section_id: NULL (will be filled in Phase 2)

**Example raw_events data:**
```
id: xxx-yyy-zzz-aaa
session_id: abc123-uuid
section_id: NULL
viewport_w: 1920
viewport_h: 1080
ema_weight: 1.0
created_at: 2024-05-08 10:30:45
```

✓ **End-to-end pipeline working!**

---

### Step 6: Stress Test (10 minutes)

1. **Generate Many Clicks**
   - Visit the test page: http://localhost:5000/test.html
   - Click the "Simulate 10 Clicks" button several times
   - Watch console output
   - Wait for flush

2. **Verify Large Batch**
   - Go to Supabase raw_events table
   - Refresh (F5)
   - Should see many new rows added

3. **Check Stats**
   - Visit: http://localhost:8000/api/stats
   - Should show:
   ```json
   {
     "status": "ok",
     "total_sessions": N,
     "total_events": N
   }
   ```

✓ **Handles batch traffic!**

---

## Troubleshooting

### Issue: "SUPABASE_URL not set"

**Solution:**
- Check .env file exists in bai-final-year/
- Verify Supabase credentials are correct
- No quotes around values:
  ```
  ✓ SUPABASE_URL=https://...
  ✗ SUPABASE_URL="https://..."
  ```

### Issue: Frontend can't reach backend

**Check:**
- Backend is running on port 8000
- Frontend is on port 5000
- Check browser DevTools → Network tab
- POST /api/ingest should show 200 status

**Solution:**
- Check CORS is enabled (should be in backend/main.py)
- Check firewall isn't blocking ports

### Issue: Data not appearing in Supabase

**Check:**
- Are you using the ANON_KEY (not SERVICE_KEY)?
- Did you create the tables?
- Check backend logs for errors (should show "Stored X interactions")

**Solution:**
- Run the SQL statements again
- Verify table names exactly: sessions, raw_events, etc.

### Issue: "port already in use"

**Solution:**
```bash
# Find process on port 8000
lsof -i :8000
# Kill it
kill -9 <PID>

# Or use different port
python main.py --port 8001
```

---

## Success Criteria

You'll know Phase 1 is complete when:

- [ ] sensor.js logs show "Sensor initialized"
- [ ] Clicks are captured and logged in console
- [ ] Data is flushed every 5 seconds
- [ ] Supabase shows sessions table with 1+ rows
- [ ] Supabase shows raw_events table with 50+ rows
- [ ] Each row has correct session_id, viewport dimensions, timestamps
- [ ] /api/stats shows non-zero total_events
- [ ] /health endpoint returns "ok"

---

## Next: Phase 2

Phase 2 (coming May 15) will add:
- Playwright for screenshot capture
- Section bounding box extraction
- Mapping clicks to sections
- Redis caching

But first, enjoy your working telemetry pipeline! 🎉

---

## Quick Reference

### URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5000 | Demo website |
| Backend | http://localhost:8000 | API server |
| Docs | http://localhost:8000/docs | API documentation |
| Health | http://localhost:8000/health | Health check |
| Stats | http://localhost:8000/api/stats | Stats endpoint |
| Supabase | https://app.supabase.com | Database dashboard |

### Commands

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start backend
cd backend && python main.py

# Start frontend
cd frontend/demo-website && python -m http.server 5000

# Test sensor.js
open http://localhost:5000/test.html

# View Supabase data
open https://app.supabase.com
```

---

## Support

If you get stuck:
1. Check DEVELOPMENT_LOG.md for progress tracking
2. Read ARCHITECTURE.md for system overview
3. Check API_SPECIFICATION.md for endpoint details
4. Review DATABASE_SCHEMA.md for table structures
