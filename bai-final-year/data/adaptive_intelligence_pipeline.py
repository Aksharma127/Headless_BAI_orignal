#!/usr/bin/env python3
"""Synthetic telemetry, unsupervised cohorts, and friction proof for BAI.

This script implements the local, reproducible path for:
- Phase 1: Gaussian ghost-user click generation from clean_layout.json.
- Phase 2: EMA weighted K-Means clustering.
- Phase 5: 1D kinematic friction comparison for a chosen optimized order.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "bai-final-year"
FRONTEND = PROJECT / "frontend"
DEFAULT_LAYOUT = ROOT / "clean_layout.json"
DEFAULT_CACHE = FRONTEND / "cache"

SECTION_ORDER = ["hero", "features", "pricing", "testimonials", "cta", "footer"]
FALLBACK_SECTION_HEIGHTS = {
    "hero": 420.0,
    "features": 520.0,
    "pricing": 620.0,
    "testimonials": 500.0,
    "cta": 340.0,
    "footer": 160.0,
}


@dataclass(frozen=True)
class Persona:
    key: str
    label: str
    section_weights: dict[str, float]
    sigma_ratio: float = 0.18


PERSONAS = [
    Persona(
        key="pricing_seeker",
        label="The Pricing Seeker",
        section_weights={"pricing": 0.68, "cta": 0.14, "features": 0.10, "testimonials": 0.06, "hero": 0.02},
    ),
    Persona(
        key="social_proof_scanner",
        label="The Social Proof Scanner",
        section_weights={"testimonials": 0.64, "pricing": 0.16, "features": 0.10, "hero": 0.07, "cta": 0.03},
    ),
    Persona(
        key="feature_evaluator",
        label="The Feature Evaluator",
        section_weights={"features": 0.65, "hero": 0.15, "pricing": 0.10, "testimonials": 0.07, "cta": 0.03},
    ),
]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _node_section_id(node: dict[str, Any]) -> str | None:
    candidates = [
        node.get("id"),
        node.get("section_id"),
        node.get("semantic_id"),
        node.get("semantic"),
        node.get("label"),
        node.get("name"),
    ]
    text = " ".join(str(value).lower() for value in candidates if value)
    for section_id in SECTION_ORDER:
        if section_id in text:
            return section_id
    return None


def read_section_layout(layout_path: Path) -> dict[str, dict[str, float]]:
    """Read clean_layout.json and return section bounding boxes.

    The current extractor may emit low-level DOM nodes without semantic section
    labels. In that case, keep the pipeline runnable by using the demo website's
    canonical section order and stable section-height estimates.
    """
    raw = json.loads(layout_path.read_text(encoding="utf-8"))
    nodes = raw.get("sections") or raw.get("nodes") or []
    sections: dict[str, dict[str, float]] = {}

    for node in nodes:
        section_id = _node_section_id(node)
        if not section_id:
            continue

        x = float(node.get("x", node.get("x_min", 0.0)))
        y = float(node.get("y", node.get("y_min", 0.0)))
        width = float(node.get("width", node.get("x_max", x) - x))
        height = float(node.get("height", node.get("y_max", y) - y))
        if width <= 0 or height <= 0:
            continue

        if section_id not in sections or height > sections[section_id]["height"]:
            sections[section_id] = {
                "id": section_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "center_y": y + height / 2.0,
            }

    if sections:
        return dict(sorted(sections.items(), key=lambda item: item[1]["y"]))

    y_cursor = 0.0
    for section_id in SECTION_ORDER:
        height = FALLBACK_SECTION_HEIGHTS[section_id]
        sections[section_id] = {
            "id": section_id,
            "x": 0.0,
            "y": y_cursor,
            "width": 1920.0,
            "height": height,
            "center_y": y_cursor + height / 2.0,
        }
        y_cursor += height
    return sections


def generate_synthetic_events(
    sections: dict[str, dict[str, float]],
    sessions_per_persona: int,
    clicks_per_session: int,
    seed: int,
) -> list[dict[str, Any]]:
    np.random.seed(seed)
    random.seed(seed)

    rows: list[dict[str, Any]] = []
    now_ms = int(time.time() * 1000)
    known_sections = [section for section in SECTION_ORDER if section in sections]

    for persona in PERSONAS:
        persona_sections = [section for section in persona.section_weights if section in sections]
        probabilities = np.array([persona.section_weights[section] for section in persona_sections], dtype=float)
        probabilities = probabilities / probabilities.sum()

        for _ in range(sessions_per_persona):
            session_id = str(uuid.uuid4())
            ts = now_ms - random.randint(60_000, 3_600_000)

            for index in range(clicks_per_session):
                if random.random() < 0.08:
                    target = random.choice(known_sections)
                else:
                    target = str(np.random.choice(persona_sections, p=probabilities))

                box = sections[target]
                sigma = max(24.0, box["height"] * persona.sigma_ratio)
                y = _clamp(float(np.random.normal(box["center_y"], sigma)), box["y"], box["y"] + box["height"])
                x_center = box["x"] + box["width"] / 2.0
                x_sigma = max(80.0, box["width"] * 0.15)
                x = _clamp(float(np.random.normal(x_center, x_sigma)), box["x"], box["x"] + box["width"])
                ts += max(80, int(abs(np.random.normal(850, 260))))

                rows.append(
                    {
                        "event_id": len(rows) + 1,
                        "session_id": session_id,
                        "persona": persona.key,
                        "persona_label": persona.label,
                        "event_index": index,
                        "timestamp_ms": ts,
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "target_section": target,
                    }
                )

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def ema_session_features(rows: list[dict[str, Any]], section_ids: list[str], alpha: float) -> tuple[list[str], np.ndarray]:
    by_session: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_session.setdefault(str(row["session_id"]), []).append(row)

    session_ids: list[str] = []
    features: list[np.ndarray] = []

    for session_id, events in by_session.items():
        weights = np.zeros(len(section_ids), dtype=float)
        for event in sorted(events, key=lambda item: int(item["timestamp_ms"])):
            observation = np.zeros(len(section_ids), dtype=float)
            observation[section_ids.index(str(event["target_section"]))] = 1.0
            weights = alpha * observation + (1.0 - alpha) * weights
        session_ids.append(session_id)
        features.append(weights)

    return session_ids, np.vstack(features)


def cluster_preferences(
    rows: list[dict[str, Any]],
    section_ids: list[str],
    alpha: float,
    k: int,
    seed: int,
) -> dict[str, Any]:
    session_ids, features = ema_session_features(rows, section_ids, alpha)
    model = KMeans(n_clusters=k, random_state=seed, n_init=20)
    labels = model.fit_predict(features)

    cohorts: list[dict[str, Any]] = []
    for cluster_id, center in enumerate(model.cluster_centers_):
        normalized = center / center.sum() if center.sum() > 0 else center
        top_section = section_ids[int(np.argmax(normalized))]
        cohorts.append(
            {
                "cluster_id": int(cluster_id),
                "sessions": int(np.sum(labels == cluster_id)),
                "top_section": top_section,
                "preference_weights": {
                    section: round(float(weight), 6)
                    for section, weight in zip(section_ids, normalized, strict=True)
                },
            }
        )

    assignments = [
        {"session_id": session_id, "cluster_id": int(cluster_id)}
        for session_id, cluster_id in zip(session_ids, labels.tolist(), strict=True)
    ]

    return {
        "alpha": alpha,
        "k": k,
        "wcss": round(float(model.inertia_), 6),
        "section_ids": section_ids,
        "session_assignments": assignments,
        "cohorts": cohorts,
    }


def centers_for_order(
    order: list[str],
    sections: dict[str, dict[str, float]],
) -> dict[str, float]:
    centers: dict[str, float] = {}
    y_cursor = 0.0
    for section_id in order:
        if section_id not in sections:
            continue
        height = sections[section_id]["height"]
        centers[section_id] = y_cursor + height / 2.0
        y_cursor += height
    return centers


def friction_report(
    sections: dict[str, dict[str, float]],
    preference_matrix: dict[str, Any],
    optimized_order: list[str],
    y_start: float,
) -> dict[str, Any]:
    default_order = [section for section in SECTION_ORDER if section in sections]
    default_centers = centers_for_order(default_order, sections)
    optimized_centers = centers_for_order(optimized_order, sections)

    rows: list[dict[str, Any]] = []
    for cohort in preference_matrix["cohorts"]:
        target = cohort["top_section"]
        default_friction = abs(default_centers[target] - y_start)
        optimized_friction = abs(optimized_centers[target] - y_start)
        reduction = 0.0
        if default_friction > 0:
            reduction = ((default_friction - optimized_friction) / default_friction) * 100.0
        rows.append(
            {
                "cluster_id": cohort["cluster_id"],
                "primary_target": target,
                "default_friction_px": round(default_friction, 2),
                "optimized_friction_px": round(optimized_friction, 2),
                "reduction_percent": round(reduction, 2),
            }
        )

    average_reduction = float(np.mean([row["reduction_percent"] for row in rows])) if rows else 0.0
    weighted_default = 0.0
    weighted_optimized = 0.0
    total_sessions = 0
    for row, cohort in zip(rows, preference_matrix["cohorts"], strict=True):
        sessions = int(cohort["sessions"])
        weighted_default += row["default_friction_px"] * sessions
        weighted_optimized += row["optimized_friction_px"] * sessions
        total_sessions += sessions
    weighted_reduction = 0.0
    if weighted_default > 0:
        weighted_reduction = ((weighted_default - weighted_optimized) / weighted_default) * 100.0

    return {
        "metric": "1D Kinematic Friction",
        "formula": "F = |Y_target_center - Y_start_position|",
        "y_start_position": y_start,
        "default_order": default_order,
        "optimized_order": optimized_order,
        "average_reduction_percent": round(average_reduction, 2),
        "session_weighted_reduction_percent": round(weighted_reduction, 2) if total_sessions else 0.0,
        "cohort_results": rows,
    }


def load_optimized_order(path: Path, sections: dict[str, dict[str, float]], matrix: dict[str, Any]) -> list[str]:
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        order = raw if isinstance(raw, list) else raw.get("order", [])
        order = [str(section) for section in order if str(section) in sections]
        if order:
            return order

    ranked = sorted(
        sections,
        key=lambda section: sum(cohort["preference_weights"].get(section, 0.0) for cohort in matrix["cohorts"]),
        reverse=True,
    )
    if "footer" in ranked:
        ranked = [section for section in ranked if section != "footer"] + ["footer"]
    return ranked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BAI synthetic intelligence pipeline")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--sessions-per-persona", type=int, default=120)
    parser.add_argument("--clicks-per-session", type=int, default=30)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--optimized-order", type=Path, default=DEFAULT_CACHE / "layout_order.json")
    parser.add_argument("--y-start", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.layout.exists():
        raise FileNotFoundError(f"Layout file not found: {args.layout}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    sections = read_section_layout(args.layout)
    section_ids = [section for section in SECTION_ORDER if section in sections]
    if len(section_ids) < 3:
        raise ValueError("Need at least three semantic sections for k=3 clustering")

    events = generate_synthetic_events(
        sections=sections,
        sessions_per_persona=args.sessions_per_persona,
        clicks_per_session=args.clicks_per_session,
        seed=args.seed,
    )
    telemetry_path = args.out_dir / "synthetic_telemetry.csv"
    write_csv(telemetry_path, events)

    layout_path = args.out_dir / "section_layout.json"
    layout_path.write_text(json.dumps(sections, indent=2), encoding="utf-8")

    matrix = cluster_preferences(events, section_ids, alpha=args.alpha, k=args.k, seed=args.seed)
    assignments = matrix.pop("session_assignments")
    matrix_path = args.out_dir / "preference_weight_matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    assignments_path = args.out_dir / "cluster_session_assignments.csv"
    write_csv(assignments_path, assignments)

    optimized_order = load_optimized_order(args.optimized_order, sections, matrix)
    friction = friction_report(sections, matrix, optimized_order, args.y_start)
    friction_path = args.out_dir / "friction_report.json"
    friction_path.write_text(json.dumps(friction, indent=2), encoding="utf-8")

    print(f"Generated events: {len(events)} -> {telemetry_path}")
    print(f"Preference matrix: WCSS={matrix['wcss']} -> {matrix_path}")
    print(f"Friction proof -> {friction_path}")


if __name__ == "__main__":
    main()
