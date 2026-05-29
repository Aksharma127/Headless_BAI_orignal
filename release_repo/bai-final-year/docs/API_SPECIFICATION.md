# API Specification

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required (development mode).

## Content-Type

All endpoints expect and return `application/json`.

---

## Endpoints

### 1. GET /health

Health check endpoint to verify API is running.

**Request:**
```http
GET /health
```

**Response (200 OK):**
```json
{
    "status": "ok",
    "timestamp": "2024-05-08T10:30:45.123456",
    "database": "connected"
}
```

**Use Case:**
- Before sending telemetry, client can verify backend is running
- Monitoring and alerting

---

### 2. GET /docs

Auto-generated Swagger UI documentation.

**Request:**
```http
GET /docs
```

**Response:**
- HTML page with interactive API documentation
- Try-it-out functionality for testing endpoints

**URL:** http://localhost:8000/docs

---

### 3. POST /api/ingest

Main telemetry ingestion endpoint.

**Request:**
```http
POST /api/ingest
Content-Type: application/json

{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "viewport": {
        "width": 1920,
        "height": 1080
    },
    "interactions": [
        {
            "x": 500,
            "y": 300,
            "t": 1714000000000
        },
        {
            "x": 502,
            "y": 301,
            "t": 1714000000050
        }
    ]
}
```

**Request Body Schema:**

```
IngestPayload {
    session_id: string (UUID, required)
        - Unique identifier for user session
        - Persisted in localStorage
        - Used to group clicks from same user
    
    viewport: object (required)
        - width: integer (pixels, 800-4096)
        - height: integer (pixels, 600-2160)
    
    interactions: array (required, min 1 item)
        - x: integer (0 to viewport.width)
        - y: integer (0 to viewport.height)
        - t: integer (milliseconds since epoch)
}
```

**Response (200 OK):**
```json
{
    "status": "ok",
    "received": 2,
    "message": "Stored 2 interactions"
}
```

**Response (422 Unprocessable Entity):**
```json
{
    "detail": [
        {
            "loc": ["body", "session_id"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

**Response (500 Internal Server Error):**
```json
{
    "status": "error",
    "message": "Failed to ingest telemetry: [error details]"
}
```

**Database Operations:**
1. Upsert session record:
   ```sql
   INSERT INTO sessions (session_id, last_active)
   VALUES (?, now())
   ON CONFLICT (session_id) DO UPDATE
   SET last_active = now()
   ```

2. Insert raw events:
   ```sql
   INSERT INTO raw_events 
   (session_id, section_id, viewport_w, viewport_h, ema_weight, created_at)
   VALUES (?, NULL, ?, ?, 1.0, ?)
   ```

**Use Case:**
- Called by sensor.js every 5 seconds
- Called by actuator.js before page close (Beacon API)

---

### 4. GET /api/stats

Get statistics about collected telemetry.

**Request:**
```http
GET /api/stats
```

**Response (200 OK):**
```json
{
    "status": "ok",
    "total_sessions": 42,
    "total_events": 1250
}
```

**Use Case:**
- Dashboard
- Monitoring progress during testing

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Ingest successful |
| 400 | Bad Request | Missing required field |
| 422 | Validation Error | Invalid data type |
| 500 | Server Error | Database connection failed |

### Error Response Format

```json
{
    "status": "error",
    "message": "Human-readable error description"
}
```

### Validation Rules

**session_id:**
- Must be a valid UUID string
- Example: `123e4567-e89b-12d3-a456-426614174000`

**viewport:**
- width: 800-4096 pixels
- height: 600-2160 pixels

**interactions[].x:**
- 0 ≤ x ≤ viewport.width
- Must be integer

**interactions[].y:**
- 0 ≤ y ≤ viewport.height
- Must be integer

**interactions[].t:**
- Milliseconds since epoch
- Must be positive integer
- Should be recent (within last 24 hours)

---

## Request/Response Examples

### Example 1: Single Click

**Request:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "viewport": {"width": 1920, "height": 1080},
    "interactions": [
        {"x": 960, "y": 540, "t": 1714000000000}
    ]
}
```

**Response:**
```json
{
    "status": "ok",
    "received": 1,
    "message": "Stored 1 interactions"
}
```

### Example 2: Batch of Clicks (5-second flush)

**Request:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "viewport": {"width": 1366, "height": 768},
    "interactions": [
        {"x": 683, "y": 384, "t": 1714000000000},
        {"x": 700, "y": 350, "t": 1714000000050},
        {"x": 725, "y": 380, "t": 1714000000100},
        {"x": 750, "y": 400, "t": 1714000000150},
        {"x": 680, "y": 420, "t": 1714000000200}
    ]
}
```

**Response:**
```json
{
    "status": "ok",
    "received": 5,
    "message": "Stored 5 interactions"
}
```

### Example 3: Invalid Payload (Missing field)

**Request:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "interactions": [
        {"x": 960, "y": 540, "t": 1714000000000}
    ]
}
```

**Response (422):**
```json
{
    "detail": [
        {
            "loc": ["body", "viewport"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. Production deployment will add:
- Per-session rate limit: 1000 events/minute
- Per-IP rate limit: 10000 events/minute

---

## CORS

CORS is enabled for all origins (development mode).

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

For production, restrict to specific domains:
```
Access-Control-Allow-Origin: https://yourdomain.com
```
