#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_IDS = set([*(f"Exp{i}" for i in range(1, 17)), "G1", "G2", "G3"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status-json", type=Path, default=Path("outputs/status/summary.json"))
    args = ap.parse_args()

    obj = json.loads(args.status_json.read_text())
    runs = obj.get("runs", [])
    if not runs:
        raise SystemExit("[status:FAIL] summary contains no runs")

    ids = {r.get("experiment_id") for r in runs if r.get("experiment_id")}
    missing = sorted(REQUIRED_IDS - ids)
    if missing:
        raise SystemExit(f"[status:FAIL] missing experiment ids in status summary: {missing}")

    print(f"[status:OK] {len(runs)} runs; all required experiment ids present")


if __name__ == "__main__":
    main()
