#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("outputs/runs"))
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    runs = sorted([p for p in args.root.glob("*") if p.is_dir()])
    if not runs:
        print("No runs found")
        return

    rows = []
    print(f"{'run':28} {'exp':6} {'model':5} {'beta':>5} {'h':>5} {'seed':>5} {'K_ent':>8} {'K_esc':>8} {'L_meta':>8} {'rank':>8}")
    print("-" * 112)
    for r in runs:
        sfile = r / "summary.json"
        if not sfile.exists():
            continue
        s = json.loads(sfile.read_text())
        rows.append(s)
        print(
            f"{s['run_name'][:28]:28} {s.get('experiment_id','-')[:6]:6} {s['model']:5} {s['beta']:5.1f} {s['h']:5.2f} {s['seed']:5d} "
            f"{str(s['k_ent_emp']):>8} {str(s['k_esc_emp']):>8} {str(s.get('l_meta_emp')):>8} {s.get('final_rank_proxy',0.0):8.3f}"
        )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "count": len(rows),
            "runs": rows,
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
