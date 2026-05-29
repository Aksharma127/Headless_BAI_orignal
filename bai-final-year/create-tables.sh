#!/usr/bin/env bash
set -euo pipefail

# Applies/updates schema directly using psql.
# Usage:
#   ./create-tables.sh "postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres"
# Or set env var SUPABASE_DB_URL and run ./create-tables.sh

DB_URL="${1:-${SUPABASE_DB_URL:-}}"

if [[ -z "$DB_URL" ]]; then
  echo "Usage: ./create-tables.sh <postgres-connection-url>"
  echo "Or set SUPABASE_DB_URL env var."
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required but not found in PATH."
  exit 1
fi

echo "Applying schema to database..."

psql "$DB_URL" <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    is_bot BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS raw_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    t BIGINT NOT NULL,
    section_id VARCHAR(255),
    ema_weight FLOAT8 DEFAULT 1.0,
    viewport_w INTEGER NOT NULL,
    viewport_h INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_sessions FOREIGN KEY (session_id)
        REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_clusters (
    session_id VARCHAR(255) PRIMARY KEY,
    cluster_id INTEGER,
    assigned_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_user_cluster_sessions FOREIGN KEY (session_id)
        REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id INTEGER NOT NULL,
    layout_json JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS x INTEGER;
ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS y INTEGER;
ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS t BIGINT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS is_bot BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_raw_events_session ON raw_events(session_id);
CREATE INDEX IF NOT EXISTS idx_raw_events_domain ON raw_events(domain);
CREATE INDEX IF NOT EXISTS idx_raw_events_session_domain ON raw_events(session_id, domain);
CREATE INDEX IF NOT EXISTS idx_raw_events_created ON raw_events(created_at);
CREATE INDEX IF NOT EXISTS idx_raw_events_t ON raw_events(t);

SQL

echo "Schema apply complete."
