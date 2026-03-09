#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_TABLES = [
    "tables/table_all_runs.csv",
    "tables/table_experiment_summary.csv",
    "results_summary.md",
    "artifact_manifest.json",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis-dir", type=Path, default=Path("analysis"))
    args = ap.parse_args()

    missing = [p for p in REQUIRED_TABLES if not (args.analysis_dir / p).exists()]
    if missing:
        raise SystemExit(f"[analysis:FAIL] missing required artifacts: {missing}")

    manifest = json.loads((args.analysis_dir / "artifact_manifest.json").read_text())
    figs = manifest.get("figures", [])
    if not figs:
        raise SystemExit("[analysis:FAIL] artifact_manifest has no figures")

    print("[analysis:OK] required analysis artifacts present")


if __name__ == "__main__":
    main()
