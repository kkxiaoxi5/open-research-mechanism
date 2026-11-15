#!/usr/bin/env bash
# One-click local deployment for mechanism-agent (Linux / macOS).
#
#   ./deploy.sh            init (if needed) + seed demo + start console
#   PORT=9000 ./deploy.sh  custom port
#   ./deploy.sh stop       stop the background console
#
# Zero dependencies: Python >= 3.11 standard library only.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8765}"
HOME_DIR="${MECH_HOME:-$PWD/mech-state}"
PID_FILE="$PWD/.mech-agent.pid"
LOG_FILE="$PWD/mech-agent.log"

if [ "${1:-}" = "stop" ]; then
  if [ -f "$PID_FILE" ]; then kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"; echo "stopped"; else echo "not running"; fi
  exit 0
fi

command -v python3 >/dev/null || { echo "python3 not found (need >= 3.11)"; exit 1; }
python3 - <<'EOF'
import sys
if sys.version_info < (3, 11):
    sys.exit("Python >= 3.11 required, found " + sys.version.split()[0])
EOF

export PYTHONPATH="$PWD/src"
if [ ! -f "$HOME_DIR/board.jsonl" ]; then
  python3 -m mechanism_agent --home "$HOME_DIR" init
  python3 -m mechanism_agent --home "$HOME_DIR" seed-demo
  echo "seeded demo data (leaves D1-D3, two tickets)"
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "already running (pid $(cat "$PID_FILE")): http://127.0.0.1:$PORT"
  exit 0
fi
nohup python3 -m mechanism_agent --home "$HOME_DIR" serve --port "$PORT" \
  > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
sleep 1
echo "mechanism-agent console: http://127.0.0.1:$PORT"
echo "state dir: $HOME_DIR   log: $LOG_FILE   stop: ./deploy.sh stop"
