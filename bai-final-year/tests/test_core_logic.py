"""
Real unit tests for BAI core logic functions.

Tests actual importable functions from the backend package — no mocks.
Each test class targets a specific module and uses deterministic input data
with pre-calculated expected outputs.

Tested modules:
  - backend.filters.bot_detector  (spatial/temporal variance, frequency, is_bot)
  - backend.schemas               (Pydantic model validation: valid + invalid)
  - backend.main                  (/health endpoint response shape via TestClient)
"""

import math
import pytest
from pydantic import ValidationError

from backend.filters.bot_detector import (
    calculate_spatial_variance,
    calculate_temporal_variance,
    calculate_frequency,
    is_bot,
    SPATIAL_VARIANCE_THRESHOLD,
    TEMPORAL_VARIANCE_THRESHOLD,
    FREQUENCY_THRESHOLD,
)
from backend.schemas import (
    Interaction,
    IngestPayload,
    IngestResponse,
    MAX_INTERACTIONS_PER_BATCH,
)


# ============================================================
# BOT DETECTOR — Scoring Functions
# ============================================================

class TestSpatialVariance:
    """Test calculate_spatial_variance with known coordinate distributions."""

    def test_identical_points_returns_zero(self):
        """All clicks at the same pixel → zero spatial variance."""
        xs = [500.0] * 10
        ys = [300.0] * 10
        assert calculate_spatial_variance(xs, ys) == 0.0

    def test_known_variance(self):
        """Hand-calculated variance for a small set of points.

        x = [0, 10]  → mean=5, pvariance = ((5^2 + 5^2)/2) = 25
        y = [0, 20]  → mean=10, pvariance = ((10^2 + 10^2)/2) = 100
        total = 25 + 100 = 125
        """
        result = calculate_spatial_variance([0.0, 10.0], [0.0, 20.0])
        assert result == pytest.approx(125.0, abs=0.01)

    def test_high_spread_exceeds_threshold(self):
        """Clicks spread across viewport should produce variance >> threshold."""
        xs = [100.0, 800.0, 300.0, 1500.0, 200.0]
        ys = [200.0, 400.0, 900.0, 100.0, 750.0]
        result = calculate_spatial_variance(xs, ys)
        assert result > SPATIAL_VARIANCE_THRESHOLD

    def test_tight_cluster_below_threshold(self):
        """Clicks in a 2px square → variance well below bot threshold."""
        xs = [500.0, 501.0, 500.0, 501.0, 500.0, 501.0, 500.0, 501.0]
        ys = [300.0, 300.0, 301.0, 301.0, 300.0, 300.0, 301.0, 301.0]
        result = calculate_spatial_variance(xs, ys)
        assert result < SPATIAL_VARIANCE_THRESHOLD

    def test_empty_input_returns_inf(self):
        """Edge case: empty lists should return inf (not enough data)."""
        assert math.isinf(calculate_spatial_variance([], []))

    def test_single_point_returns_inf(self):
        """Edge case: single point can't compute variance."""
        assert math.isinf(calculate_spatial_variance([100.0], [200.0]))


class TestTemporalVariance:
    """Test calculate_temporal_variance with known timestamp sequences."""

    def test_perfectly_regular_intervals_returns_zero(self):
        """Exactly 50ms between every click → interval variance = 0."""
        timestamps = [1000.0, 1050.0, 1100.0, 1150.0, 1200.0]
        result = calculate_temporal_variance(timestamps)
        assert result == pytest.approx(0.0, abs=0.001)

    def test_irregular_intervals_has_positive_variance(self):
        """Human-like irregular timing should produce nonzero variance."""
        timestamps = [1000.0, 2500.0, 4200.0, 6800.0, 8100.0, 11000.0]
        result = calculate_temporal_variance(timestamps)
        assert result > 0.0

    def test_known_interval_variance(self):
        """Intervals [100, 200, 300] → mean=200, pvariance = (10000+0+10000)/3 ≈ 6666.67."""
        timestamps = [0.0, 100.0, 300.0, 600.0]
        result = calculate_temporal_variance(timestamps)
        assert result == pytest.approx(6666.67, abs=1.0)

    def test_too_few_timestamps_returns_inf(self):
        """Need >= 3 timestamps to compute interval variance."""
        assert math.isinf(calculate_temporal_variance([1000.0, 2000.0]))
        assert math.isinf(calculate_temporal_variance([1000.0]))
        assert math.isinf(calculate_temporal_variance([]))


class TestFrequency:
    """Test calculate_frequency (clicks per second)."""

    def test_known_frequency(self):
        """10 clicks over 1 second (1000ms span) → 10 clicks/sec."""
        # span = 900ms, count = 10 → rate = 10 / 0.9 ≈ 11.11
        timestamps = [float(i * 100) for i in range(10)]
        result = calculate_frequency(timestamps)
        assert result == pytest.approx(10.0 / 0.9, abs=0.1)

    def test_low_frequency_human(self):
        """~1 click per 2 seconds → frequency well below bot threshold."""
        timestamps = [0.0, 2000.0, 4000.0, 6000.0, 8000.0]
        result = calculate_frequency(timestamps)
        expected = 5.0 / 8.0  # 0.625 clicks/sec
        assert result == pytest.approx(expected, abs=0.01)
        assert result < FREQUENCY_THRESHOLD

    def test_high_frequency_bot(self):
        """20 clicks in 500ms → 40 clicks/sec, way above threshold."""
        timestamps = [float(i * 25) for i in range(20)]
        result = calculate_frequency(timestamps)
        assert result > FREQUENCY_THRESHOLD

    def test_single_timestamp_returns_zero(self):
        """Can't compute frequency from a single click."""
        assert calculate_frequency([1000.0]) == 0.0

    def test_empty_returns_zero(self):
        assert calculate_frequency([]) == 0.0


class TestIsBot:
    """End-to-end bot detection with realistic click patterns."""

    def _make_clicks(self, xs, ys, ts):
        """Helper: zip coordinates and timestamps into click dicts."""
        return [{"x": x, "y": y, "t": t} for x, y, t in zip(xs, ys, ts)]

    def test_bot_pattern_detected(self):
        """Tight spatial cluster + perfectly regular 50ms intervals + high frequency.

        This is the classic autoclicker pattern: clicks at nearly the same
        pixel at machine-speed intervals.
        """
        n = 20
        xs = [500 + (i % 2) for i in range(n)]
        ys = [300 + (i % 2) for i in range(n)]
        ts = [1000 + i * 50 for i in range(n)]
        clicks = self._make_clicks(xs, ys, ts)
        assert is_bot("bot-session-001", clicks) is True

    def test_human_pattern_not_flagged(self):
        """Wide spatial spread + irregular timing + low frequency.

        Simulates a real user browsing different sections of a page.
        """
        xs = [100, 800, 300, 1500, 200, 950, 400, 1200, 600, 50]
        ys = [200, 400, 900, 100, 750, 300, 600, 800, 150, 500]
        ts = [1000, 2500, 4200, 6800, 8100, 11000, 13500, 16200, 19000, 22000]
        clicks = self._make_clicks(xs, ys, ts)
        assert is_bot("human-session-001", clicks) is False

    def test_too_few_clicks_returns_false(self):
        """Less than 3 clicks → insufficient data, never flag as bot."""
        clicks = [{"x": 500, "y": 300, "t": 1000}, {"x": 500, "y": 300, "t": 1050}]
        assert is_bot("short-session", clicks) is False

    def test_empty_clicks_returns_false(self):
        assert is_bot("empty-session", []) is False

    def test_high_freq_but_high_spatial_variance_is_human(self):
        """Fast clicks spread across the viewport → not a bot (spatial variance too high)."""
        n = 15
        xs = [100 * (i + 1) for i in range(n)]    # 100, 200, ... 1500
        ys = [80 * (i + 1) for i in range(n)]      # 80, 160, ... 1200
        ts = [1000 + i * 60 for i in range(n)]      # 60ms intervals (fast)
        clicks = self._make_clicks(xs, ys, ts)
        assert is_bot("fast-but-spread", clicks) is False


# ============================================================
# SCHEMA VALIDATION — Pydantic Models
# ============================================================

class TestInteractionSchema:
    """Test the Interaction Pydantic model."""

    def test_valid_interaction(self):
        inter = Interaction(x=500, y=300, t=1719200000000)
        assert inter.x == 500
        assert inter.y == 300
        assert inter.t == 1719200000000

    def test_negative_x_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            Interaction(x=-1, y=300, t=1719200000000)
        assert "coordinates must be non-negative" in str(exc_info.value)

    def test_negative_y_rejected(self):
        with pytest.raises(ValidationError):
            Interaction(x=500, y=-10, t=1719200000000)

    def test_zero_timestamp_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            Interaction(x=500, y=300, t=0)
        assert "positive unix timestamp" in str(exc_info.value)

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValidationError):
            Interaction(x=500, y=300, t=-1)

    def test_zero_coordinates_accepted(self):
        """Coordinates at origin (0,0) are valid viewport positions."""
        inter = Interaction(x=0, y=0, t=1719200000000)
        assert inter.x == 0
        assert inter.y == 0


class TestIngestPayloadSchema:
    """Test the IngestPayload Pydantic model with valid and invalid inputs."""

    VALID_PAYLOAD = {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "domain": "example.com",
        "viewport": {"width": 1920, "height": 1080},
        "interactions": [
            {"x": 500, "y": 300, "t": 1719200000000},
            {"x": 600, "y": 400, "t": 1719200001000},
        ],
    }

    def test_valid_payload_accepted(self):
        payload = IngestPayload(**self.VALID_PAYLOAD)
        assert payload.session_id == "550e8400-e29b-41d4-a716-446655440000"
        assert payload.domain == "example.com"
        assert len(payload.interactions) == 2

    def test_empty_session_id_rejected(self):
        data = {**self.VALID_PAYLOAD, "session_id": "   "}
        with pytest.raises(ValidationError) as exc_info:
            IngestPayload(**data)
        assert "session_id is required" in str(exc_info.value)

    def test_oversized_session_id_rejected(self):
        data = {**self.VALID_PAYLOAD, "session_id": "x" * 200}
        with pytest.raises(ValidationError) as exc_info:
            IngestPayload(**data)
        assert "too long" in str(exc_info.value)

    def test_none_domain_defaults_to_unknown(self):
        data = {**self.VALID_PAYLOAD, "domain": None}
        payload = IngestPayload(**data)
        assert payload.domain == "unknown"

    def test_empty_domain_defaults_to_unknown(self):
        data = {**self.VALID_PAYLOAD, "domain": "  "}
        payload = IngestPayload(**data)
        assert payload.domain == "unknown"

    def test_batch_size_limit_enforced(self):
        """Payloads exceeding MAX_INTERACTIONS_PER_BATCH must be rejected."""
        interactions = [
            {"x": i, "y": i, "t": 1719200000000 + i}
            for i in range(MAX_INTERACTIONS_PER_BATCH + 1)
        ]
        data = {**self.VALID_PAYLOAD, "interactions": interactions}
        with pytest.raises(ValidationError) as exc_info:
            IngestPayload(**data)
        assert "cannot exceed" in str(exc_info.value)

    def test_exactly_max_batch_size_accepted(self):
        """Exactly MAX_INTERACTIONS_PER_BATCH interactions should be valid."""
        interactions = [
            {"x": i % 1920, "y": i % 1080, "t": 1719200000000 + i}
            for i in range(MAX_INTERACTIONS_PER_BATCH)
        ]
        data = {**self.VALID_PAYLOAD, "interactions": interactions}
        payload = IngestPayload(**data)
        assert len(payload.interactions) == MAX_INTERACTIONS_PER_BATCH

    def test_invalid_interaction_in_batch_rejected(self):
        """A single bad interaction should invalidate the whole payload."""
        data = {
            **self.VALID_PAYLOAD,
            "interactions": [
                {"x": 500, "y": 300, "t": 1719200000000},
                {"x": -1, "y": 300, "t": 1719200001000},  # negative x
            ],
        }
        with pytest.raises(ValidationError):
            IngestPayload(**data)


class TestIngestResponseSchema:
    """Test the IngestResponse Pydantic model."""

    def test_valid_response(self):
        resp = IngestResponse(status="success", received=42)
        assert resp.status == "success"
        assert resp.received == 42
        assert resp.message == ""

    def test_response_with_message(self):
        resp = IngestResponse(status="error", received=0, message="Something failed")
        assert resp.message == "Something failed"


# ============================================================
# /health ENDPOINT — Response Shape
# ============================================================

class TestHealthEndpoint:
    """Test the /health API endpoint via FastAPI TestClient.

    The `client` fixture is provided by conftest.py and runs the app in DEMO_MODE.
    """

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get("/health").json()
        required_fields = {"status", "timestamp", "redis", "database", "demo_mode", "cache_loaded"}
        missing = required_fields - set(data.keys())
        assert not missing, f"Missing fields in /health response: {missing}"

    def test_health_status_is_ok_or_degraded(self, client):
        data = client.get("/health").json()
        assert data["status"] in ("ok", "degraded")

    def test_health_demo_mode_is_boolean(self, client):
        data = client.get("/health").json()
        assert isinstance(data["demo_mode"], bool)

    def test_health_redis_field_is_valid_state(self, client):
        data = client.get("/health").json()
        assert data["redis"] in ("connected", "disconnected", "not_configured")

    def test_health_cache_loaded_is_boolean(self, client):
        data = client.get("/health").json()
        assert isinstance(data["cache_loaded"], bool)


# ============================================================
# /api/layout ENDPOINT — Response Schema
# ============================================================

class TestLayoutEndpoint:
    """Test the /api/layout endpoint response schema via TestClient."""

    def test_layout_returns_200(self, client):
        response = client.get("/api/layout")
        assert response.status_code == 200

    def test_layout_has_required_fields(self, client):
        data = client.get("/api/layout").json()
        required = {"layout_order", "source", "timestamp"}
        missing = required - set(data.keys())
        assert not missing, f"Missing fields: {missing}"

    def test_layout_order_is_nonempty_list(self, client):
        data = client.get("/api/layout").json()
        assert isinstance(data["layout_order"], list)
        assert len(data["layout_order"]) > 0

    def test_layout_source_is_valid(self, client):
        data = client.get("/api/layout").json()
        assert data["source"] in ("cache", "live_ml", "cache_fallback")

    def test_section_layout_has_geometry(self, client):
        data = client.get("/api/layout").json()
        if "section_layout" in data and data["section_layout"]:
            for section_id, geom in data["section_layout"].items():
                for field in ("id", "x", "y", "width", "height"):
                    assert field in geom, f"Section '{section_id}' missing geometry field '{field}'"
