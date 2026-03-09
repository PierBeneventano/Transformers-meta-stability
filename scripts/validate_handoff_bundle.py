#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

REQUIRED_MEMBERS = [
    "analysis/results_summary.md",
    "analysis/artifact_manifest.json",
    "analysis/tables/table_all_runs.csv",
    "analysis/tables/table_experiment_summary.csv",
    "outputs/status/summary.json",
    "outputs/run_matrix.tsv",
    "configs/experiments.yaml",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, required=True)
    args = ap.parse_args()

    if not args.bundle.exists():
        raise SystemExit(f"[handoff:FAIL] bundle not found: {args.bundle}")

    with tarfile.open(args.bundle, "r:gz") as tf:
        names = set(tf.getnames())

    missing = [m for m in REQUIRED_MEMBERS if m not in names]
    if missing:
        raise SystemExit(f"[handoff:FAIL] required members missing: {missing}")

    print("[handoff:OK] required handoff members present")


if __name__ == "__main__":
    main()
