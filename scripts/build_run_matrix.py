#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import shlex
from pathlib import Path

import yaml


FULL_FIDELITY_EXPERIMENTS = {"Exp13", "Exp14", "Exp15", "Exp16"}


def cartesian_product(d: dict) -> list[dict]:
    if not d:
        return [{}]
    keys = list(d.keys())
    vals = []
    for k in keys:
        v = d[k]
        vals.append(v if isinstance(v, list) else [v])
    out = []
    for combo in itertools.product(*vals):
        out.append(dict(zip(keys, combo)))
    return out


def select_runner_script(exp_id: str, params: dict) -> str:
    train_mode = str(params.get("train_mode", "none")).lower()
    if exp_id in FULL_FIDELITY_EXPERIMENTS and train_mode == "full":
        return "scripts/run_tiny_transformer_experiment.py"
    return "scripts/run_experiment.py"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=Path("configs/experiments.yaml"))
    ap.add_argument("--out", type=Path, default=Path("outputs/run_matrix.tsv"))
    ap.add_argument("--experiment-ids", type=str, default="", help="space/comma separated subset")
    ap.add_argument("--max-variants-per-exp", type=int, default=0)
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    defaults = cfg.get("defaults", {})
    experiments = cfg.get("experiments", {})

    wanted = None
    if args.experiment_ids.strip():
        parts = [p.strip() for p in args.experiment_ids.replace(",", " ").split() if p.strip()]
        wanted = set(parts)

    rows = []
    for exp_id, spec in experiments.items():
        if wanted and exp_id not in wanted:
            continue
        sweeps = spec.get("sweeps", {})
        variants = cartesian_product(sweeps)
        if args.max_variants_per_exp and args.max_variants_per_exp > 0:
            variants = variants[: args.max_variants_per_exp]

        for vidx, v in enumerate(variants):
            merged = dict(defaults)
            merged.update(v)
            seeds = merged.pop("seeds", [11])
            if not isinstance(seeds, list):
                seeds = [seeds]
            runner_script = select_runner_script(exp_id, merged)

            for seed in seeds:
                run_name = f"{exp_id}_v{vidx:03d}_s{seed}"
                out_dir = f"outputs/runs/{run_name}"
                cmd = [
                    "python3",
                    runner_script,
                    "--experiment-id", exp_id,
                    "--run-name", run_name,
                    "--out-dir", out_dir,
                    "--seed", str(seed),
                ]
                for k, val in sorted(merged.items()):
                    flag = "--" + k.replace("_", "-")
                    cmd.extend([flag, str(val)])
                rows.append((run_name, exp_id, json.dumps(merged, sort_keys=True), shlex.join(cmd)))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        f.write("run_name\texperiment_id\tparams_json\tcommand\n")
        for r in rows:
            f.write("\t".join(r) + "\n")

    print(f"[matrix] wrote {len(rows)} runs -> {args.out}")


if __name__ == "__main__":
    main()
