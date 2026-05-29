#!/usr/bin/env python3
"""Route semantic sections with Groq Llama 3 at low temperature.

The script sends extracted bounding boxes and the K-Means preference matrix to
Groq, asking for a strict JSON array that the browser actuator can consume.
If GROQ_API_KEY is not configured or the API fails, it writes a deterministic
local fallback so the rest of the demo pipeline remains runnable.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "bai-final-year"
DEFAULT_CACHE = PROJECT / "frontend" / "cache"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-8b-8192"


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def deterministic_order(layout: dict[str, Any], matrix: dict[str, Any]) -> list[str]:
    section_ids = list(layout.keys())
    scores = {
        section: sum(cohort["preference_weights"].get(section, 0.0) for cohort in matrix["cohorts"])
        for section in section_ids
    }
    order = sorted(section_ids, key=lambda section: scores.get(section, 0.0), reverse=True)
    if "footer" in order:
        order = [section for section in order if section != "footer"] + ["footer"]
    return order


def extract_json_array(text: str) -> list[str]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response did not contain a JSON array")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("Model response JSON must be an array of strings")
    return parsed


def call_groq(layout: dict[str, Any], matrix: dict[str, Any], api_key: str) -> list[str]:
    allowed = list(layout.keys())
    prompt = {
        "role": "user",
        "content": (
            "You are a deterministic spatial logic router for a web page. "
            "Return only a strict JSON array of section IDs, with no prose. "
            "Use the preference weight matrix to move the most valuable sections earlier. "
            "Obey these constraints: include every allowed section exactly once; "
            "do not invent section IDs; footer must always remain last if present; "
            "preserve a coherent landing-page flow when weights are tied.\n\n"
            f"Allowed section IDs: {allowed}\n\n"
            f"Bounding boxes from clean_layout.json:\n{json.dumps(layout, indent=2)}\n\n"
            f"Preference Weight Matrix:\n{json.dumps(matrix['cohorts'], indent=2)}"
        ),
    }
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": "Output valid JSON only."},
            prompt,
        ],
    }
    response = requests.post(
        GROQ_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    proposed = extract_json_array(content)
    proposed = _ordered_unique([section for section in proposed if section in allowed])

    missing = [section for section in allowed if section not in proposed]
    proposed.extend(missing)
    if "footer" in proposed:
        proposed = [section for section in proposed if section != "footer"] + ["footer"]
    return proposed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Groq SLM spatial router")
    parser.add_argument("--layout", type=Path, default=DEFAULT_CACHE / "section_layout.json")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_CACHE / "preference_weight_matrix.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_CACHE / "layout_order.json")
    parser.add_argument("--allow-fallback", action="store_true", default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    source = "groq"
    try:
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        order = call_groq(layout, matrix, api_key)
    except Exception as exc:
        if not args.allow_fallback:
            raise
        source = f"deterministic_fallback: {exc}"
        order = deterministic_order(layout, matrix)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(order, indent=2), encoding="utf-8")
    print(f"Layout order source={source}")
    print(json.dumps(order))


if __name__ == "__main__":
    main()
