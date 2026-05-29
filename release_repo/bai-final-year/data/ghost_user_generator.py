#!/usr/bin/env python3
"""Generate synthetic telemetry sessions and post to BAI ingest API.

Phase 3 scaffold goals:
- 3 behavioral personas
- ~50 sessions per persona
- 20-40 clicks per session
- x/y/t fields matching backend IngestPayload schema
- graceful handling of network failures and non-2xx responses
"""

from __future__ import annotations

import argparse
import time
import uuid
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import requests


VIEWPORT_W = 1920
VIEWPORT_H = 1080


@dataclass(frozen=True)
class Persona:
    name: str
    center: Tuple[float, float]
    sigma: Tuple[float, float]
    exploratory_click_ratio: float


PERSONAS: List[Persona] = [
    Persona(
        name="Pricing Seeker",
        center=(980.0, 720.0),
        sigma=(190.0, 120.0),
        exploratory_click_ratio=0.10,
    ),
    Persona(
        name="Feature Reader",
        center=(920.0, 430.0),
        sigma=(260.0, 110.0),
        exploratory_click_ratio=0.14,
    ),
    Persona(
        name="Social Proof Buyer",
        center=(960.0, 860.0),
        sigma=(220.0, 130.0),
        exploratory_click_ratio=0.12,
    ),
]


def _clamp(v: float, low: int, high: int) -> int:
    return int(max(low, min(high, round(v))))


def _sample_click_xy(persona: Persona) -> Tuple[int, int]:
    if random.random() < persona.exploratory_click_ratio:
        x = random.randint(0, VIEWPORT_W - 1)
        y = random.randint(0, VIEWPORT_H - 1)
        return x, y

    x = np.random.normal(persona.center[0], persona.sigma[0])
    y = np.random.normal(persona.center[1], persona.sigma[1])
    return _clamp(x, 0, VIEWPORT_W - 1), _clamp(y, 0, VIEWPORT_H - 1)


def _generate_interactions(persona: Persona, clicks_count: int, start_ts_ms: int) -> List[Dict[str, int]]:
    interactions: List[Dict[str, int]] = []
    ts = start_ts_ms

    for _ in range(clicks_count):
        x, y = _sample_click_xy(persona)
        # Positive inter-click delays, centered around ~850ms.
        delta_ms = max(80, int(abs(np.random.normal(850, 280))))
        ts += delta_ms
        interactions.append({"x": x, "y": y, "t": ts})

    return interactions


def _build_payload(session_id: str, domain: str, interactions: List[Dict[str, int]]) -> Dict:
    # Must match backend IngestPayload schema exactly:
    # session_id (str), domain (str), viewport (dict), interactions (list of x/y/t)
    return {
        "session_id": session_id,
        "domain": domain,
        "viewport": {
            "width": VIEWPORT_W,
            "height": VIEWPORT_H,
        },
        "interactions": interactions,
    }


def _post_payload(base_url: str, payload: Dict, timeout_s: float, retries: int) -> bool:
    # Prefer /api/sync, fallback to /api/ingest for compatibility.
    endpoints = [f"{base_url}/api/sync", f"{base_url}/api/ingest"]

    for endpoint in endpoints:
        for attempt in range(retries + 1):
            try:
                resp = requests.post(endpoint, json=payload, timeout=timeout_s)
                if 200 <= resp.status_code < 300:
                    return True

                # 404 on /api/sync means try /api/ingest next.
                if resp.status_code == 404:
                    break

                # Retry transient server-side failures on same endpoint.
                if resp.status_code >= 500 and attempt < retries:
                    time.sleep(0.2 * (attempt + 1))
                    continue

                print(
                    f"[WARN] request failed endpoint={endpoint} "
                    f"status={resp.status_code} body={resp.text[:140]}"
                )
                break
            except requests.RequestException as exc:
                # Graceful handling: log and continue retrying/next payload.
                if attempt < retries:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                print(f"[WARN] connection error endpoint={endpoint}: {exc}")

    return False


def generate_and_send(
    base_url: str,
    domain: str,
    sessions_per_persona: int,
    min_clicks: int,
    max_clicks: int,
    timeout_s: float,
    retries: int,
) -> None:
    generated = 0
    posted_ok = 0
    posted_failed = 0

    print("Generating synthetic ghost users...")

    for persona in PERSONAS:
        for _ in range(sessions_per_persona):
            session_id = str(uuid.uuid4())
            clicks_count = random.randint(min_clicks, max_clicks)
            start_ts_ms = int(time.time() * 1000) - random.randint(60_000, 600_000)

            interactions = _generate_interactions(persona, clicks_count, start_ts_ms)
            payload = _build_payload(session_id=session_id, domain=domain, interactions=interactions)

            ok = _post_payload(base_url=base_url, payload=payload, timeout_s=timeout_s, retries=retries)

            generated += 1
            if ok:
                posted_ok += 1
            else:
                posted_failed += 1

        print(
            f"Persona complete: {persona.name} "
            f"sessions={sessions_per_persona}"
        )

    print("Done.")
    print(
        f"Summary: generated_sessions={generated} posted_ok={posted_ok} posted_failed={posted_failed}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ghost user synthetic telemetry generator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--domain", default="localhost", help="Domain field for IngestPayload")
    parser.add_argument("--sessions-per-persona", type=int, default=50)
    parser.add_argument("--min-clicks", type=int, default=20)
    parser.add_argument("--max-clicks", type=int, default=40)
    parser.add_argument("--timeout", type=float, default=4.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.min_clicks <= 0 or args.max_clicks < args.min_clicks:
        raise ValueError("Invalid click range")

    np.random.seed(args.seed)
    random.seed(args.seed)

    generate_and_send(
        base_url=args.base_url.rstrip("/"),
        domain=args.domain,
        sessions_per_persona=args.sessions_per_persona,
        min_clicks=args.min_clicks,
        max_clicks=args.max_clicks,
        timeout_s=args.timeout,
        retries=args.retries,
    )


if __name__ == "__main__":
    main()
