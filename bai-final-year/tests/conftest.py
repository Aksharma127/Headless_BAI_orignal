"""
Pytest configuration and shared fixtures for BAI backend tests.

Sets environment variables BEFORE any backend module is imported,
ensuring the app boots in DEMO_MODE without requiring Supabase credentials.
"""

import os

# ── Environment must be set before backend imports ──────────────────────────
os.environ["DEMO_MODE"] = "true"
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest


@pytest.fixture(scope="module")
def client():
    """Create a FastAPI TestClient with the full app loaded in DEMO_MODE.

    Uses `scope="module"` so the app is only instantiated once per test file,
    avoiding repeated startup/shutdown overhead.
    """
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client
