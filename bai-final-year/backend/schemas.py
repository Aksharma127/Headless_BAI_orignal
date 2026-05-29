from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator


MAX_INTERACTIONS_PER_BATCH = 500


class Interaction(BaseModel):
    """Single mouse click captured by sensor"""
    x: int = Field(..., description="Horizontal position in viewport (pixels)")
    y: int = Field(..., description="Vertical position in viewport (pixels)")
    t: int = Field(..., description="Timestamp in milliseconds since epoch")

    @field_validator("x", "y")
    @classmethod
    def validate_coordinate(cls, value: int) -> int:
        if value < 0:
            raise ValueError("coordinates must be non-negative viewport pixels")
        return value

    @field_validator("t")
    @classmethod
    def validate_timestamp_ms(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("t must be a positive unix timestamp in milliseconds")
        return value


class IngestPayload(BaseModel):
    """Telemetry batch received from sensor.js"""
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    domain: str = Field(default="unknown", description="Hostname of the page where clicks occurred")
    viewport: Dict[str, Any] = Field(..., description="User's viewport dimensions (width/height)")
    interactions: List[Interaction] = Field(..., description="List of captured clicks")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("session_id is required")
        if len(normalized) > 128:
            raise ValueError("session_id is too long")
        return normalized

    @field_validator("interactions")
    @classmethod
    def validate_batch_size(cls, value: List[Interaction]) -> List[Interaction]:
        if len(value) > MAX_INTERACTIONS_PER_BATCH:
            raise ValueError(f"interactions cannot exceed {MAX_INTERACTIONS_PER_BATCH} events")
        return value

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_domain(cls, value):
        if value is None:
            return "unknown"

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or "unknown"

        return str(value)


class IngestResponse(BaseModel):
    """Response from ingest endpoint"""
    status: str = Field(..., description="'success' or 'error'")
    received: int = Field(..., description="Number of interactions received")
    message: str = Field("", description="Optional message")
