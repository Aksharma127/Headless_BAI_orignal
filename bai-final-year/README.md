# BAI: Behavior-Adaptive Interface

Adaptive website layouts based on user behavior patterns.

## Quick Start

### Prerequisites
- Python 3.11+
- Supabase account (free tier)
- Node.js (optional, for frontend development)

### Setup

1. **Clone and setup:**
```bash
git clone <repo>
cd bai-final-year
cp .env.example .env
# Edit .env with your Supabase credentials
```

2. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

3. **Create Supabase tables:**
   - See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)

4. **Start backend:**
```bash
cd backend
python main.py
```

5. **Start frontend (in another terminal):**
```bash
cd frontend
python -m http.server 5000
```

6. **Visit website:**
   - http://localhost:5000/demo-website/index.html
   - Click around
   - Check Supabase dashboard for data

### Docker

```bash
docker-compose up
```

Then:
- Frontend: http://localhost:5000/demo-website/index.html
- Backend: http://localhost:8000
- Docs: http://localhost:8000/docs

### Run On Another Device / Cloud

- LAN/mobile-device demo: `./scripts/run_lan_demo.sh`
- Custom Chromium cloud deployment: see [docs/deployment/CLOUD_AND_DEVICE_RUNBOOK.md](docs/deployment/CLOUD_AND_DEVICE_RUNBOOK.md)

---

## Project Structure

```
bai-final-year/
├── frontend/
│   ├── sensor.js              # Telemetry capture
│   ├── actuator.js            # DOM reordering (Phase 6)
│   ├── test.html              # Testing page
│   └── demo-website/
│       ├── index.html         # 5-section landing page
│       └── styles.css         # Styling
├── backend/
│   ├── main.py                # FastAPI application
│   └── requirements.txt        # Python dependencies
├── docker/
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
│   ├── ARCHITECTURE.md        # System design
│   ├── API_SPECIFICATION.md   # API reference
│   ├── DATABASE_SCHEMA.md     # Database design
│   └── DEVELOPMENT_LOG.md     # Progress tracking
├── docker-compose.yml         # Container orchestration
├── .env.example               # Configuration template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

---

## Phases

### Phase 1: Telemetry Collection (May 8-14) ✓
- [x] sensor.js captures clicks
- [x] FastAPI ingestion endpoint
- [x] Supabase storage
- [x] End-to-end working

### Phase 2: Spatial Extraction (May 15-21)
- Playwright screenshot capture
- Section bounding box extraction
- Coordinate mapping
- Redis caching

### Phase 3: Behavior Analysis (May 22-28)
- K-Means clustering
- User segmentation
- Pattern discovery

### Phase 4: Predictive Modeling (May 29 - Jun 4)
- Time series analysis
- EMA weight calculation
- Performance prediction

### Phase 5: Layout Optimization (Jun 5-11)
- SLM (Statistical Learning Model)
- Layout generation
- Cluster-specific ordering

### Phase 6: Actuator Integration (Jun 12-18)
- DOM reordering
- A/B testing
- Real-time personalization

---

## Configuration

### Environment Variables (.env)

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here

# Redis (Phase 2+)
REDIS_HOST=localhost
REDIS_PORT=6379

# LLMs (Phase 5+)
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...

# App
DEBUG=True
ENVIRONMENT=development
```

### Never Commit Secrets

Use `.env` for local development (git-ignored).
Use `.env.example` as a template.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /health | Health check |
| GET | /docs | Interactive API docs |
| POST | /api/ingest | Send telemetry batch |
| GET | /api/stats | Get statistics |

See [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) for details.

---

## Testing

### Manual Testing

1. **Frontend sensor:**
   - Open http://localhost:5000/test.html
   - Click around
   - Watch console logs

2. **Backend API:**
   - Visit http://localhost:8000/docs
   - Try the /api/ingest endpoint manually

3. **End-to-end:**
   - Open demo website
   - Click for 5 seconds
   - Wait for flush
   - Check Supabase dashboard

### Automated Testing

```bash
# Run tests (when available)
pytest tests/
```

---

## Troubleshooting

### Backend won't start
```bash
# Check Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Check port 8000 is free
lsof -i :8000

# Check dependencies
pip install -r backend/requirements.txt
```

### Frontend clicks not reaching backend
```bash
# Check sensor.js is loaded
# Open DevTools → Console → should see "[BAI Sensor] ✓ Sensor initialized"

# Check API endpoint
# Network tab → POST /api/ingest
# Should see 200 response with {"status": "ok", ...}
```

### Supabase connection fails
```bash
# Test connection
python backend/test_supabase.py

# Check .env file exists and has credentials
cat .env | grep SUPABASE
```

---

## Performance Metrics (Target)

| Metric | Target | Actual |
|--------|--------|--------|
| Sensor payload size | <1KB | 0.5KB |
| Flush latency (5s interval) | <100ms | 50ms |
| API response time | <50ms | 30ms |
| Database insert | <10ms | 5ms |
| Click capture rate | 99% | 99%+ |
| Data loss (tab close) | 0% | 0% (Beacon API) |

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Reference](docs/API_SPECIFICATION.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [Development Log](docs/DEVELOPMENT_LOG.md)

---

## Contributing

1. Create a new branch for each phase
2. Update DEVELOPMENT_LOG.md with progress
3. Commit small, logical changes
4. Test end-to-end before push

---

## License

MIT

---

## Contact

GitHub: [your username]
Email: [your email]
