# Headless BAI - Behavioral AI Pipeline

A production-grade system for capturing user behavior, filtering bots, and optimizing UI layouts through intelligent clustering.

## Architecture

- **Frontend**: Zero-dependency vanilla JS tracking sensor
- **Backend**: FastAPI ingestion gateway with Redis caching
- **Intelligence**: Nightly ML batch jobs for clustering and layout optimization
- **Evaluation**: Academic benchmarks and bot filter validation

## Setup

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Redis
- Supabase account

### Environment Variables

Create `bai-final-year/.env` from `bai-final-year/.env.example`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
REDIS_HOST=localhost
REDIS_PORT=6379
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
ENABLE_PHASE2_SCHEDULER=true
```

### Running the Pipeline

```bash
# Start infrastructure
docker-compose up -d

# Install dependencies
pip install -r bai-final-year/backend/requirements.txt

# Run backend
python -m uvicorn backend.main:app --reload --app-dir bai-final-year

# Open the test sensor page
python -m http.server 8080 --directory bai-final-year/frontend
```

## Components

See individual README files in each subdirectory for detailed documentation.
