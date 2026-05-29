# Database Schema

## Overview

Supabase PostgreSQL database with 4 tables for telemetry, clustering, and layout management.

---

## Table: sessions

Tracks unique users/sessions.

```sql
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW()
);
```

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| session_id | VARCHAR(255) | PRIMARY KEY | UUID of user session (localStorage) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | When session first created |
| last_active | TIMESTAMP | NOT NULL, DEFAULT NOW() | When last interaction received |

**Indexes:**
- Primary key on session_id (automatic)

**Purpose:**
- One row per unique user
- Track first visit and last activity
- Foreign key for raw_events

**Example Data:**
```
session_id                           | created_at            | last_active
123e4567-e89b-12d3-a456-426614174000 | 2024-05-08 10:00:00  | 2024-05-08 10:30:45
223e4567-e89b-12d3-a456-426614174001 | 2024-05-08 10:05:00  | 2024-05-08 10:25:30
```

---

## Table: raw_events

Stores raw click telemetry.

```sql
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
```

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Auto-generated unique ID |
| session_id | VARCHAR(255) | FK → sessions | Which user made the click |
| section_id | VARCHAR(255) | NULLABLE | Which section clicked (filled Phase 2) |
| ema_weight | FLOAT8 | DEFAULT 1.0 | Exponential moving average weight (Phase 3) |
| viewport_w | INTEGER | NOT NULL | User's viewport width |
| viewport_h | INTEGER | NOT NULL | User's viewport height |
| created_at | TIMESTAMP | DEFAULT NOW() | When click occurred |

**Indexes:**
```sql
CREATE INDEX idx_raw_events_session ON raw_events(session_id);
CREATE INDEX idx_raw_events_created ON raw_events(created_at);
```

**Purpose:**
- One row per click
- Track click coordinates (x, y implicit in time series)
- Viewport dimensions for normalization
- EMA weight for temporal decay

**Example Data:**
```
id                                  | session_id                          | section_id | viewport_w | viewport_h | created_at
xxx-yyy-zzz-aaa                     | 123e4567-e89b-12d3-a456-426614174000 | NULL      | 1920       | 1080       | 2024-05-08 10:00:05
xxx-yyy-zzz-bbb                     | 123e4567-e89b-12d3-a456-426614174000 | NULL      | 1920       | 1080       | 2024-05-08 10:00:10
```

**Note:** section_id is NULL at Phase 1. Filled in Phase 2 by Playwright extraction.

---

## Table: user_clusters

Maps users to behavioral clusters.

```sql
CREATE TABLE user_clusters (
    session_id VARCHAR(255) PRIMARY KEY,
    cluster_id INTEGER,
    assigned_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_sessions FOREIGN KEY (session_id) 
        REFERENCES sessions(session_id) ON DELETE CASCADE
);
```

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| session_id | VARCHAR(255) | PRIMARY KEY, FK | Which user |
| cluster_id | INTEGER | NOT NULL | Which cluster (0, 1, 2, ...) |
| assigned_at | TIMESTAMP | DEFAULT NOW() | When clustering was run |

**Purpose:**
- Result of Phase 3 K-Means clustering
- Each user assigned to one cluster
- Used to fetch personalized layout in Phase 5

**Example Data:**
```
session_id                          | cluster_id | assigned_at
123e4567-e89b-12d3-a456-426614174000 | 0          | 2024-05-10 12:00:00
223e4567-e89b-12d3-a456-426614174001 | 1          | 2024-05-10 12:00:00
323e4567-e89b-12d3-a456-426614174002 | 2          | 2024-05-10 12:00:00
```

---

## Table: layouts

Stores personalized section ordering per cluster.

```sql
CREATE TABLE layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id INTEGER NOT NULL,
    layout_json JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW()
);
```

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique layout version ID |
| cluster_id | INTEGER | NOT NULL | Which cluster this layout is for |
| layout_json | JSONB | NOT NULL | Ordered array of section IDs |
| generated_at | TIMESTAMP | DEFAULT NOW() | When layout was generated |

**Purpose:**
- Result of Phase 5 SLM + K-Means
- Stores optimal section ordering per cluster
- Used by actuator.js (Phase 6) to reorder DOM

**Example Data:**
```
id                     | cluster_id | layout_json                              | generated_at
xxx-yyy-zzz-aaa       | 0          | ["hero", "pricing", "features", ...]    | 2024-05-10 12:00:00
xxx-yyy-zzz-bbb       | 1          | ["features", "testimonials", "hero",... | 2024-05-10 12:00:00
xxx-yyy-zzz-ccc       | 2          | ["cta", "hero", "pricing", ...]        | 2024-05-10 12:00:00
```

**Layout JSON Example:**
```json
["hero", "features", "pricing", "testimonials", "cta"]
```

This array determines the order actuator.js will apply via DOM reordering.

---

## Relationships

```
┌──────────────┐
│   sessions   │
└──────┬───────┘
       │ session_id (PK)
       │
       ├─────────────────────────────┐
       │                             │
       ↓                             ↓
┌──────────────────┐      ┌──────────────────┐
│   raw_events     │      │ user_clusters    │
│  (1:N relation)  │      │  (1:1 relation)  │
└──────────────────┘      └──────────────────┘
                                   │
                                   │ cluster_id
                                   │
                                   ↓
                          ┌──────────────────┐
                          │    layouts       │
                          │  (1:N relation)  │
                          └──────────────────┘
```

### Foreign Keys

1. **raw_events.session_id** → **sessions.session_id**
   - One session has many events
   - ON DELETE CASCADE: Delete all events when session deleted

2. **user_clusters.session_id** → **sessions.session_id**
   - One session belongs to one cluster
   - ON DELETE CASCADE

---

## Queries (Common Operations)

### Get all events for a user
```sql
SELECT * FROM raw_events 
WHERE session_id = '123e4567-...' 
ORDER BY created_at DESC;
```

### Get cluster assignment for user
```sql
SELECT cluster_id FROM user_clusters 
WHERE session_id = '123e4567-...';
```

### Get layout for cluster
```sql
SELECT layout_json FROM layouts 
WHERE cluster_id = 1 
ORDER BY generated_at DESC 
LIMIT 1;
```

### Get total sessions
```sql
SELECT COUNT(*) as total_sessions FROM sessions;
```

### Get events per session (for stats)
```sql
SELECT session_id, COUNT(*) as event_count 
FROM raw_events 
GROUP BY session_id 
ORDER BY event_count DESC;
```

---

## Data Retention Policy

### Phase 1-3 (Development)
- Keep all data indefinitely

### Phase 5+ (Production)
- Keep sessions: 1 year
- Keep raw_events: 90 days
- Keep layouts: 1 month (regenerated frequently)

```sql
-- Archive old events
DELETE FROM raw_events 
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## Backup Strategy

Supabase handles backups automatically on Free tier:
- Daily backups (7-day retention)
- Upgrade to Pro for 30-day retention

For critical data, export before running major operations:
```bash
# Export entire database
pg_dump "postgresql://..." > backup.sql

# Restore
psql "postgresql://..." < backup.sql
```
