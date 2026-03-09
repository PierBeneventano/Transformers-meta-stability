#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--run-dir", type=Path, required=True)
args = p.parse_args()

required = ["config.json", "metrics.csv", "summary.json"]
missing = [f for f in required if not (args.run_dir / f).exists()]
if missing:
    raise SystemExit(f"Missing artifacts in {args.run_dir}: {missing}")
print("[postflight] ok")
