#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PYTHON=${PYTHON:-python3}
VENV=${VENV:-.venv}
CONDA_ENV_PREFIX=${CONDA_ENV_PREFIX:-$ROOT/transformers-meta-stability}
PYTHON_VERSION=${PYTHON_VERSION:-3.11}

if command -v conda >/dev/null 2>&1; then
  if [[ ! -d "$CONDA_ENV_PREFIX" ]]; then
    conda create -y -p "$CONDA_ENV_PREFIX" "python=${PYTHON_VERSION}"
  fi

  conda run -p "$CONDA_ENV_PREFIX" python -m pip install -U pip setuptools wheel
  conda run -p "$CONDA_ENV_PREFIX" python -m pip install --no-cache-dir -r requirements.txt

  if [[ "${INSTALL_TORCH:-0}" == "1" ]]; then
    echo "[info] installing torch for full-fidelity Exp13-Exp16"
    conda run -p "$CONDA_ENV_PREFIX" python -m pip install --no-cache-dir torch
  fi

  echo "[ok] conda environment ready: $CONDA_ENV_PREFIX"
  echo "[next] run: conda activate $CONDA_ENV_PREFIX"
else
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

  echo "[ok] venv environment ready: $VENV"
  echo "[next] run: source $VENV/bin/activate"
fi
