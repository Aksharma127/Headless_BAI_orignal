#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

if [[ -z "${LAN_IP:-}" ]]; then
  LAN_IP="YOUR_PC_IP"
fi

export ENABLE_PHASE2_SCHEDULER="${ENABLE_PHASE2_SCHEDULER:-false}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://$LAN_IP:5000,http://localhost:5000,http://127.0.0.1:5000}"
export MIN_DESKTOP_VIEWPORT_WIDTH="${MIN_DESKTOP_VIEWPORT_WIDTH:-0}"

cd "$PROJECT_DIR"

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

python -m http.server 5000 --directory frontend &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo
echo "BAI LAN demo is running."
echo "Open this from your other device on the same Wi-Fi:"
echo "  http://$LAN_IP:5000/demo-website/index.html"
echo
echo "Backend health:"
echo "  http://$LAN_IP:8000/health"
echo
wait
