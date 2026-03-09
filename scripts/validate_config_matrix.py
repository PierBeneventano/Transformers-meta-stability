#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

REQUIRED_IDS = [
    *(f"Exp{i}" for i in range(1, 17)),
    "G1",
    "G2",
    "G3",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=Path("configs/experiments.yaml"))
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    exps = cfg.get("experiments", {})

    missing = [x for x in REQUIRED_IDS if x not in exps]
    extra = [x for x in exps.keys() if x not in REQUIRED_IDS]
    if missing:
        raise SystemExit(f"[config:FAIL] missing experiment ids: {missing}")

    for eid in REQUIRED_IDS:
        sweeps = exps[eid].get("sweeps", {})
        if not isinstance(sweeps, dict) or not sweeps:
            raise SystemExit(f"[config:FAIL] {eid} has empty/invalid sweeps")

    if extra:
        print(f"[config:WARN] extra experiment ids present: {extra}")

    print("[config:OK] experiments matrix contains Exp1..Exp16 + G1..G3")


if __name__ == "__main__":
    main()
