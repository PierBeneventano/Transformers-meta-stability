#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submitted", type=Path, default=Path("outputs/slurm/submitted_jobs.tsv"))
    ap.add_argument("--smoke-dir", type=Path, default=Path("outputs/slurm/gpu_smoke"))
    ap.add_argument("--require-success", action="store_true")
    args = ap.parse_args()

    if not args.submitted.exists():
        raise SystemExit(f"[gpu-smoke:FAIL] submitted file not found: {args.submitted}")
    if not args.smoke_dir.exists():
        raise SystemExit(f"[gpu-smoke:FAIL] smoke dir not found: {args.smoke_dir}")

    rows = []
    for ln in args.submitted.read_text().splitlines():
        if not ln.strip():
            continue
        c = ln.split("\t")
        if len(c) < 3:
            continue
        run, _exp, job = c[:3]
        if job.startswith("dry-"):
            continue
        rows.append((run, job))

    if not rows:
        raise SystemExit("[gpu-smoke:FAIL] no real slurm jobs found in submitted manifest")

    missing = []
    successes = 0
    for run, job in rows:
        nvidia = args.smoke_dir / f"{run}-{job}-nvidia-smi.txt"
        gpu = args.smoke_dir / f"{run}-{job}-gpu.json"
        smoke = args.smoke_dir / f"{run}-{job}-smoke.json"
        for p in (nvidia, gpu, smoke):
            if not p.exists():
                missing.append(str(p))
        if smoke.exists():
            try:
                obj = json.loads(smoke.read_text())
                if bool(obj.get("success", False)):
                    successes += 1
            except Exception:
                pass

    if missing:
        raise SystemExit(f"[gpu-smoke:FAIL] missing required artifacts: {missing[:5]}{' ...' if len(missing)>5 else ''}")
    if args.require_success and successes <= 0:
        raise SystemExit("[gpu-smoke:FAIL] no successful GPU smoke summary found")

    print(f"[gpu-smoke:OK] verified {len(rows)} job artifact sets; successful_jobs={successes}")


if __name__ == "__main__":
    main()
