#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_OUT = Path("clean_layout.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract BAI skeleton JSON from Chromium output")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="File containing Chromium stdout/stderr. If omitted, stdin is used.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.input:
        if not args.input.exists():
            print(f"Error: {args.input} not found", file=sys.stderr)
            return 2
        text = args.input.read_text(encoding="utf-8", errors="replace")
    else:
        text = sys.stdin.read()
        if not text.strip():
            print("Error: no input received on stdin", file=sys.stderr)
            return 2

    pattern = r"=== BAI_SKELETON_START ===\s*(\{.*?\})\s*=== BAI_SKELETON_END ==="
    matches = re.findall(pattern, text, flags=re.DOTALL)
    if not matches:
        print("No BAI skeleton markers found", file=sys.stderr)
        return 1

    payload = matches[-1].strip()
    try:
        obj = json.loads(payload)
    except Exception as exc:
        print("Invalid JSON payload:", exc, file=sys.stderr)
        return 3

    args.out.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
