#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=Path("outputs/slurm/submitted_jobs.tsv"))
    ap.add_argument("--allow-dry", action="store_true")
    args = ap.parse_args()

    if not args.file.exists():
        raise SystemExit(f"[jobs:FAIL] file not found: {args.file}")

    bad = []
    for i, ln in enumerate(args.file.read_text().splitlines(), start=1):
        if not ln.strip():
            continue
        cols = ln.split("\t")
        if len(cols) not in (3, 6):
            bad.append((i, "column_count", ln))
            continue

        if len(cols) == 3:
            run, exp, job = cols
            attempt = None
        else:
            run, exp, job, attempt, mem_sel, gres_sel = cols
            if not attempt.isdigit():
                bad.append((i, "invalid_attempt", ln))
                continue
            if not mem_sel or not gres_sel:
                bad.append((i, "empty_mem_or_gres", ln))
                continue

        if not run or not exp:
            bad.append((i, "empty_run_or_exp", ln))
            continue
        if args.allow_dry and job.startswith("dry-"):
            continue
        if not job.isdigit():
            bad.append((i, "invalid_job_id", ln))

    if bad:
        raise SystemExit(f"[jobs:FAIL] invalid rows: {bad[:5]}{' ...' if len(bad)>5 else ''}")

    print("[jobs:OK] submitted jobs manifest format valid")


if __name__ == "__main__":
    main()
