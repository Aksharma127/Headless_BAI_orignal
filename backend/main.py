#!/usr/bin/env python3
"""Compatibility entry point for the BAI FastAPI application."""

from pathlib import Path
import importlib.util
import sys


def _load_application():
    app_path = Path(__file__).resolve().parents[1] / "bai-final-year" / "backend" / "main.py"
    sys.path.insert(0, str(app_path.parent))
    spec = importlib.util.spec_from_file_location("bai_final_year_backend", app_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load backend application from {app_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


app = _load_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
