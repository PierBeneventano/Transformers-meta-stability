#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PYTHON=${PYTHON:-python3}
VENV=${VENV:-.venv}

if [[ ! -d "$VENV" ]]; then
  "$PYTHON" -m venv "$VENV"
fi
source "$VENV/bin/activate"
python -m pip install -U pip setuptools wheel
python -m pip install --no-cache-dir -r requirements.txt

if [[ "${INSTALL_TORCH:-0}" == "1" ]]; then
  echo "[info] installing torch for full-fidelity Exp13-Exp16"
  python -m pip install --no-cache-dir torch
fi

echo "[ok] environment ready"
