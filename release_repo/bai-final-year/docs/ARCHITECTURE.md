# BAI System Architecture

## Phase 1: Telemetry Collection & Ingestion

### Overview

The telemetry pipeline captures user interactions (clicks) from a frontend website and stores them in Supabase for later analysis.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      FRONTEND (Browser)                      │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         demo-website (index.html + styles.css)         │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  5 Semantic Sections (hero, features, etc.)     │  │  │
│  │  │  User scrolls and clicks                        │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                       ↓                                │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │        sensor.js (Telemetry Capture)            │  │  │
│  │  │  - Captures mousedown events                    │  │  │
│  │  │  - Buffers locally (localStorage)               │  │  │
│  │  │  - Batches every 5 seconds                      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                       ↓                                │  │
│  │                  [Network Request]                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                       ↓                                      │
└──────────────────────────────────────────────────────────────┘
              POST /api/ingest (JSON batch)
                        ↓
┌──────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                         │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  main.py - FastAPI Application                       │  │
│  │  - Receives POST /api/ingest                         │  │
│  │  - Validates with Pydantic models                    │  │
│  │  - Upserts sessions                                  │  │
│  │  - Inserts raw events                                │  │
│  │  - Returns success/error response                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                       ↓                                      │
│              [Supabase Client]                              │
│                       ↓                                      │
└──────────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│                   DATABASE (Supabase)                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   sessions   │  │  raw_events  │                        │
│  ├──────────────┤  ├──────────────┤                        │
│  │ session_id   │  │ id           │                        │
│  │ created_at   │  │ session_id   │ (FK)                   │
│  │ last_active  │  │ section_id   │ (Phase 2)              │
│  └──────────────┘  │ viewport_w   │                        │
│                    │ viewport_h   │                        │
│                    │ ema_weight   │ (Phase 3)              │
│                    │ created_at   │                        │
│                    └──────────────┘                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │user_clusters │  │   layouts    │ (Phase 5)              │
│  ├──────────────┤  ├──────────────┤                        │
│  │ session_id   │  │ id           │                        │
│  │ cluster_id   │  │ cluster_id   │                        │
│  │ assigned_at  │  │ layout_json  │                        │
│  └──────────────┘  │ generated_at │                        │
│                    └──────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Capture Phase** (Frontend)
   - User opens website at http://localhost:5000/demo-website/
   - sensor.js loads automatically
   - Clicks are captured and buffered locally

2. **Flush Phase** (Frontend)
   - Every 5 seconds, sensor.js sends buffered clicks to /api/ingest
   - If user closes tab, sendBeacon API ensures data is sent

3. **Validation Phase** (Backend)
   - FastAPI receives JSON payload
   - Pydantic validates schema and types
   - Bad payloads are rejected with 422 status

4. **Storage Phase** (Backend)
   - Session record is upserted (created if new)
   - Each interaction is inserted as a raw_event

5. **Analysis Phase** (Later phases)
   - Phase 2: Playwright extracts section bounding boxes, maps clicks to sections
   - Phase 3: K-Means clustering groups users
   - Phase 5: SLM generates personalized layouts

### Key Design Decisions

#### Why sensor.js vs Google Analytics?

- **Control**: You own the data, no third-party processing
- **Simplicity**: Only captures clicks, no tracking scripts
- **Privacy**: Minimal data collection
- **Cost**: Free (no API costs)
- **Education**: You understand every step

#### Why 5-second flush interval?

- **Batching**: Reduces 1000s of requests to 200 batches
- **Latency**: Still low-latency for real-time analysis
- **Reliability**: Sweet spot between data freshness and network efficiency

#### Why localStorage for session ID?

- **Persistence**: Same user across page reloads
- **Client-side**: No cookies or server-side session management
- **Clustering**: All clicks from one browsing session tagged together

#### Why Supabase?

- **PostgreSQL**: Industry-standard relational database
- **Free tier**: 500MB storage (plenty for prototype)
- **API**: Auto-generated REST/GraphQL endpoints
- **JSON support**: JSONB type for complex data
- **Indexes**: Performance optimization built-in

### Phase 1 Tables

#### sessions
```sql
session_id VARCHAR(255) PRIMARY KEY
created_at TIMESTAMP
last_active TIMESTAMP
```

#### raw_events
```sql
id UUID PRIMARY KEY
session_id VARCHAR(255) FOREIGN KEY
section_id VARCHAR(255) NULL  -- Filled in Phase 2
ema_weight FLOAT8
viewport_w INTEGER
viewport_h INTEGER
created_at TIMESTAMP
```

#### user_clusters
```sql
session_id VARCHAR(255) PRIMARY KEY FOREIGN KEY
cluster_id INTEGER
assigned_at TIMESTAMP
```

#### layouts
```sql
id UUID PRIMARY KEY
cluster_id INTEGER
layout_json JSONB
generated_at TIMESTAMP
```

### Running Phase 1

1. **Start Supabase**: Create project at supabase.com
2. **Configure .env**: Copy from .env.example with real credentials
3. **Install dependencies**: `pip install -r backend/requirements.txt`
4. **Start backend**: `python backend/main.py`
5. **Start frontend**: `python3 -m http.server 5000` in frontend/demo-website/
6. **Visit website**: http://localhost:5000
7. **Verify data**: Check Supabase dashboard → raw_events table

### API Endpoints (Phase 1)

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | /health | Health check | `{"status": "ok", "database": "connected"}` |
| GET | /docs | Swagger UI | Auto-generated docs |
| POST | /api/ingest | Receive telemetry | `{"status": "ok", "received": N}` |
| GET | /api/stats | Get statistics | `{"total_sessions": N, "total_events": N}` |

### Next: Phase 2

Phase 2 will add:
- Playwright browser automation
- Screenshot capture
- Section bounding box extraction
- Coordinate normalization
- Redis caching for extracted skeletons
