# Phase 1 Implementation Checklist

## Pre-Execution (Setup)

- [ ] Create Supabase account (supabase.com)
- [ ] Create new project named "bai-mvp" in Supabase
- [ ] Get SUPABASE_URL from Supabase Settings → API
- [ ] Get SUPABASE_ANON_KEY from Supabase Settings → API
- [ ] Copy .env.example to .env
- [ ] Edit .env with actual Supabase credentials
- [ ] Verify .env is NOT committed (check .gitignore)

## Database Setup

- [ ] Create database tables (copy DATABASE_SCHEMA.md to Supabase SQL Editor)
- [ ] Verify 4 tables exist in Supabase Table Editor:
  - [ ] sessions table
  - [ ] raw_events table
  - [ ] user_clusters table
  - [ ] layouts table
- [ ] Verify indexes created on raw_events

## Backend Setup

- [ ] Install Python 3.11+ (check: `python3 --version`)
- [ ] Create virtual environment: `python3 -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify FastAPI installed: `python -c "import fastapi; print(fastapi.__version__)"`
- [ ] Verify Supabase client installed: `python -c "import supabase; print(supabase.__version__)"`

## Backend Verification

- [ ] Start backend: `python main.py`
- [ ] Verify output shows: "Uvicorn running on http://127.0.0.1:8000"
- [ ] Test health endpoint: `curl http://localhost:8000/health`
- [ ] Verify response: `{"status": "ok", ...}`
- [ ] Open http://localhost:8000/docs (Swagger UI)
- [ ] Verify 4 endpoints visible in Swagger

## Frontend Verification

- [ ] Open new terminal
- [ ] Navigate to: `cd frontend/demo-website`
- [ ] Start server: `python -m http.server 5000`
- [ ] Verify output shows: "Serving HTTP on 0.0.0.0 port 5000"
- [ ] Open http://localhost:5000 in browser
- [ ] Verify page loads (5 semantic sections visible)

## Functional Testing

- [ ] Open browser console (F12)
- [ ] Look for BAI sensor logs
- [ ] Click on website elements (hero, features, pricing, testimonials, CTA)
- [ ] Observe console: "Interaction buffered" messages
- [ ] Wait 5 seconds for automatic flush
- [ ] Observe console: "Flushed X interactions" message
- [ ] Check backend logs: "Received X interactions" message
- [ ] Go to Supabase → Table Editor → raw_events
- [ ] Verify rows appear with session_id, x, y, viewport_w, viewport_h
- [ ] Repeat clicks (generate 50+ events total)

## Data Validation

- [ ] Check raw_events table has 50+ rows
- [ ] Verify each row has:
  - [ ] Valid session_id (UUID format)
  - [ ] Valid x coordinate (number)
  - [ ] Valid y coordinate (number)
  - [ ] Valid viewport_w (number)
  - [ ] Valid viewport_h (number)
  - [ ] Valid created_at (timestamp)
  - [ ] Valid ema_weight (number)
- [ ] Verify sessions table has 1+ rows
- [ ] Check session has correct created_at timestamp

## API Endpoint Testing

- [ ] Test GET /health
  ```bash
  curl http://localhost:8000/health
  ```
  - [ ] Response status: 200
  - [ ] Response has: status, timestamp, database

- [ ] Test GET /api/stats
  ```bash
  curl http://localhost:8000/api/stats
  ```
  - [ ] Response has: total_sessions, total_events

- [ ] Test POST /api/ingest (manual test in Swagger UI)
  - [ ] Go to http://localhost:8000/docs
  - [ ] Expand /api/ingest endpoint
  - [ ] Click "Try it out"
  - [ ] Modify example payload with test data
  - [ ] Click "Execute"
  - [ ] Verify response status: 200
  - [ ] Verify response shows: interactions_stored > 0

- [ ] Test GET /docs (Swagger UI)
  - [ ] Should load at http://localhost:8000/docs
  - [ ] Should show all 4 endpoints

## Frontend Sensor Testing

- [ ] Open http://localhost:5000 in clean browser window
- [ ] F12 to open DevTools
- [ ] Check Application → LocalStorage
  - [ ] Verify bai_session_id exists (UUID format)
  - [ ] Note the session ID for database verification
- [ ] Click around website multiple times
- [ ] Watch Network tab for POST requests to localhost:8000/api/ingest
- [ ] Verify requests every 5 seconds (or after manual flush)
- [ ] Check request payload has correct format:
  ```json
  {
    "session_id": "...",
    "interactions": [...],
    "viewport_w": number,
    "viewport_h": number
  }
  ```

## Tab Close Testing

- [ ] Generate some events (5-10 clicks)
- [ ] Don't wait for 5-second flush
- [ ] Immediately close the browser tab
- [ ] Wait 5 seconds
- [ ] Check Supabase raw_events table
- [ ] Verify events were saved (Beacon API worked)

## Cross-Browser Testing (Optional)

- [ ] Test in Chrome: Works? [ ]
- [ ] Test in Firefox: Works? [ ]
- [ ] Test in Safari: Works? [ ]
- [ ] Test in Edge: Works? [ ]

## Documentation Verification

- [ ] README.md exists and is readable
- [ ] TESTING_GUIDE.md exists and is comprehensive
- [ ] ARCHITECTURE.md exists with diagrams
- [ ] API_SPECIFICATION.md exists with examples
- [ ] DATABASE_SCHEMA.md exists with SQL
- [ ] DEVELOPMENT_LOG.md exists as template
- [ ] QUICK_START.txt exists with commands
- [ ] INDEX.md exists as master index
- [ ] PHASE1_SUMMARY.md exists
- [ ] COMMANDS.md exists
- [ ] FILES.txt exists

## Configuration Files Verification

- [ ] .env exists (user-created from template)
- [ ] .env.example exists (template preserved)
- [ ] .gitignore exists with correct excludes
- [ ] docker-compose.yml exists and valid YAML
- [ ] docker/Dockerfile exists
- [ ] .projectrc exists with metadata

## Helper Scripts Verification

- [ ] setup.sh exists and is executable
- [ ] start.sh exists and is executable
- [ ] create-tables.sh exists and shows SQL

## Code Quality Checks

- [ ] frontend/sensor.js: No syntax errors
- [ ] frontend/sensor.js: IIFE pattern used correctly
- [ ] frontend/sensor.js: 5-second flush working
- [ ] frontend/sensor.js: Beacon API fallback present
- [ ] frontend/test.html: Loads and renders correctly
- [ ] frontend/demo-website/index.html: 5 sections present
- [ ] frontend/demo-website/styles.css: Valid CSS (no errors in console)
- [ ] backend/main.py: Starts without errors
- [ ] backend/main.py: Pydantic models validate correctly
- [ ] backend/main.py: CORS enabled
- [ ] backend/requirements.txt: All dependencies correct versions

## Performance Checks

- [ ] Backend response time < 100ms for /api/ingest
- [ ] Frontend batching reduces requests (should be ~12/min, not 1000s/min)
- [ ] Memory usage stable (no memory leaks)
- [ ] Database queries complete in < 1s

## Security Checks

- [ ] No secrets in .git (check: `git secrets`)
- [ ] .env not committed
- [ ] .env.example has no real credentials
- [ ] CORS only allows needed origins
- [ ] API validates all input (Pydantic)
- [ ] Database uses appropriate access levels

## Final Documentation

- [ ] Create final git commit:
  ```bash
  git add .
  git commit -m "Phase 1 complete: Telemetry pipeline working with 500+ events"
  ```
- [ ] Write summary of what was accomplished
- [ ] Document any issues encountered and solutions
- [ ] Note what went well
- [ ] Note what to improve for Phase 2

## Success Criteria - ALL MET?

- [ ] ✅ sensor.js captures clicks from website
- [ ] ✅ Clicks batched and sent every 5 seconds
- [ ] ✅ FastAPI receives and validates data
- [ ] ✅ Supabase stores events reliably
- [ ] ✅ Tab-close doesn't lose data
- [ ] ✅ Session persisted across reloads
- [ ] ✅ Error handling is graceful
- [ ] ✅ Complete end-to-end working
- [ ] ✅ Fully documented
- [ ] ✅ Ready for Phase 2

## Phase 1 Completion

- [ ] All code implemented
- [ ] All tests passing
- [ ] All documentation written
- [ ] Data successfully captured (50+ events)
- [ ] Supabase table populated
- [ ] Git repository initialized
- [ ] Ready to proceed to Phase 2

## Next Steps After Phase 1

1. [ ] Review implementation and document lessons learned
2. [ ] Take screenshots of working system for portfolio
3. [ ] Create Phase 2 plan (Playwright + section extraction)
4. [ ] Schedule Phase 2 start (May 15)
5. [ ] Create backend/playwright_extractor.py
6. [ ] Implement section bounding box extraction
7. [ ] Add click → section mapping

---

**Checklist Completed?** 

If all items are checked, Phase 1 is COMPLETE and WORKING! 🎉

Ready for Phase 2? Start May 15!
