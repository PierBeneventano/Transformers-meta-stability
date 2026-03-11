# transformer-experiments

Runnable cluster pipeline for the **discrete-time transformer metastability** program.

This repo is organized to support:
- full experiment IDs `Exp1..Exp16`
- controls `G1,G2,G3`
- local execution + SLURM execution
- deterministic status/analysis/package/handoff artifacts

Canonical matrix:
- `configs/experiments.yaml`

Coverage audit:
- `docs/EXPERIMENT_COVERAGE.json`
- `docs/EXPERIMENT_COVERAGE.md`

Spec lock:
- `docs/EXPERIMENT_SPEC.md`
- `docs/EXPERIMENT_SPEC.sha256`

Paper-aligned experiment guide:
- `docs/EXPERIMENTS_FROM_PAPER_EXPLAINED.md`

---

## Quick start (cluster)

```bash
cd transformer-experiments
make bootstrap
# default bootstrap creates a conda env at ./transformers-meta-stability
conda activate ./transformers-meta-stability

# validates slurm-mode prerequisites + GPU visibility
make preflight-slurm

# launches all configured runs through SLURM
make launch-slurm

# MIT convenience target (partition=mit_normal_gpu, GPUS=1, CPUS=8)
# designed for login-node submission where local GPU checks may fail
make launch-mit-gpu

# observability
make status
make status-json

# post-run analysis + packaging
make analysis
make package

# full safety gate before handoff
make release-check
```

## Quick start (local smoke)

```bash
cd transformer-experiments
make bootstrap
conda activate ./transformers-meta-stability

make preflight
make sample-proof
```

`sample-proof` runs one variant per `Exp1..Exp16,G1..G3`, then writes status + analysis artifacts.

---

## Runtime knobs

`run_all_experiments.sh` supports:

- Scheduler/resources:
  - `PARTITION` (default `gpu`)
  - `ACCOUNT` (optional)
  - `QOS` (optional)
  - `CONSTRAINT` (optional)
  - `GPUS` (default `1`; translated to `GRES=gpu:<GPUS>` if `GRES` not set)
  - `GRES` (optional explicit override)
  - `CPUS`, `MEM`, `TIME_LIMIT`
  - `DEVICE` (default `cuda`, exported into jobs)
- Selection:
  - `EXPERIMENT_IDS` (subset)
  - `MAX_VARIANTS_PER_EXP` (cap for smoke runs)
- Safety:
  - `REQUIRE_GPU` (`auto|0|1`, default `auto`)
  - `REQUIRE_TORCH` (`0|1`, default `0`)
  - `MIN_FREE_GB`
  - `DRY_RUN_SLURM` (`0|1`)
  - `ENABLE_OOM_RETRY` (`0|1`, default `0`)
  - `OOM_RETRY_MAX` (default `2`)
  - `OOM_RETRY_MEM_PRESETS` (default `16G,24G,32G`)
  - `OOM_RETRY_GRES_PRESETS` (default `gpu:1,gpu:1,gpu:1`)

Example subset run:

```bash
make launch-slurm EXPERIMENT_IDS="Exp1 Exp2 Exp3 G1" MAX_VARIANTS_PER_EXP=1
```

MIT convenience target (equivalent to partition=`mit_normal_gpu`, `GPUS=1`, `CPUS=8`, `MEM=32G`, `TIME_LIMIT=06:00:00`, `REQUIRE_GPU=0`):

```bash
make launch-mit-gpu
```

Optional overrides:

```bash
MIT_TIME_LIMIT=08:00:00 MIT_MEM=48G make launch-mit-gpu
```

### Exp13–Exp16 fidelity tiers

- **Stage-A (default):** surrogate train/probe path from `configs/experiments.yaml`
- **Stage-B (full-fidelity):** tiny-transformer training/probing path from `configs/experiments_full_fidelity.yaml`

Run Stage-B example:

```bash
make bootstrap INSTALL_TORCH=1
conda activate ./transformers-meta-stability
MODE=local CONFIG=configs/experiments_full_fidelity.yaml ./run_all_experiments.sh
make analysis
```

---

## Validation gates

Single gate:

```bash
make release-check
```

Live-cluster integration gate (real SLURM mini-run + GPU smoke validation):

```bash
make release-check-live
```

This runs:
- syntax/static checks
- config schema/coverage checks
- local mini-run
- SLURM dry-run submission path
- job-id parser regression test
- status/analysis validation
- package + bundle integrity validation
- handoff bundle member validation
- release-check provenance capture (`outputs/status/release_check_provenance.json`)

For **real cluster GPU evidence** after a SLURM run:

```bash
make validate-jobs
make validate-gpu-smoke
```

Required GPU smoke artifacts per job:
- `outputs/slurm/gpu_smoke/<run>-<job>-nvidia-smi.txt`
- `outputs/slurm/gpu_smoke/<run>-<job>-gpu.json`
- `outputs/slurm/gpu_smoke/<run>-<job>-smoke.json`

---

## Outputs

- Runs: `outputs/runs/`
- Status JSON: `outputs/status/summary.json`
- SLURM logs/meta: `outputs/slurm/`
- Analysis tables/figs: `analysis/`
- Bundles: `outputs/bundles/transformer_results_<STAMP>.tar.gz`

---

## Pull-back handoff (send me these 3 files)

- `outputs/bundles/transformer_results_<STAMP>.tar.gz`
- `outputs/bundles/transformer_results_<STAMP>.tar.gz.sha256`
- `outputs/bundles/transformer_results_<STAMP>.tar.gz.manifest.json`

Once uploaded back here, I’ll validate integrity and do full plot-by-plot interpretation.

---

## Acceptance/signoff docs

- `docs/ACCEPTANCE_CHECKLIST.md`
- `docs/READINESS_REPORT.md`
