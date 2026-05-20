#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt pyinstaller

rm -rf build dist

PYINSTALLER_ARGS=(
  --noconfirm \
  --clean \
  --windowed \
  --name "CCSD Board Personnel Watch" \
  --paths src \
  --add-data "src/ccsd_board_watch/templates:ccsd_board_watch/templates" \
  --add-data "src/ccsd_board_watch/static:ccsd_board_watch/static" \
  --add-data "data/schools.csv:data"
)

if [ -f "data/runs/latest.txt" ]; then
  LATEST_RUN="$(cat data/runs/latest.txt)"
  if [ -d "$LATEST_RUN" ]; then
    PYINSTALLER_ARGS+=(--add-data "data/runs/latest.txt:data/runs")
    PYINSTALLER_ARGS+=(--add-data "$LATEST_RUN:data/runs/$(basename "$LATEST_RUN")")
  fi
fi

.venv/bin/pyinstaller "${PYINSTALLER_ARGS[@]}" src/ccsd_board_watch/desktop.py

echo "Built dist/CCSD Board Personnel Watch.app"
