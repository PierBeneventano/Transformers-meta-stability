# SHIP_IT.md — transformer-experiments operator runbook

## 0) Preconditions

- You are on a SLURM cluster node/login host.
- GPU partition/account details are known.
- Repo is up to date.

---

## 1) Bootstrap + environment

```bash
cd transformer-experiments
make bootstrap
conda activate ./transformers-meta-stability
```

---

## 2) Preflight checks

```bash
# strict local checks
make preflight

# strict cluster/GPU checks
make preflight-slurm
```

If this fails, do not launch jobs. Fix environment first.

---

## 3) Launch experiments

```bash
# full matrix
make launch-slurm

# optional controlled subset
make launch-slurm EXPERIMENT_IDS="Exp1 Exp2 Exp3 G1" MAX_VARIANTS_PER_EXP=1
```

Resource overrides example:

```bash
PARTITION=gpu ACCOUNT=<acct> QOS=<qos> GRES=gpu:1 CPUS=8 MEM=32G TIME_LIMIT=04:00:00 make launch-slurm
```

Optional OOM retry profile (across relaunches):

```bash
ENABLE_OOM_RETRY=1 OOM_RETRY_MAX=2 OOM_RETRY_MEM_PRESETS=16G,24G,32G OOM_RETRY_GRES_PRESETS=gpu:1,gpu:1,gpu:1 make launch-slurm
```

When a run exits with code 137, the job writes an OOM marker and increments retry attempt state in `outputs/slurm/retries/<run>.attempt`.
On the next launch, adjusted MEM/GRES preset for that attempt is used automatically.

---

## 4) Monitor progress

```bash
make status
make status-json
```

- human table: `make status`
- machine snapshot: `outputs/status/summary.json`

GPU smoke evidence validation (after real SLURM submissions):

```bash
make validate-jobs
make validate-gpu-smoke
```

Required per-job artifacts:
- `outputs/slurm/gpu_smoke/<run>-<job>-nvidia-smi.txt`
- `outputs/slurm/gpu_smoke/<run>-<job>-gpu.json`
- `outputs/slurm/gpu_smoke/<run>-<job>-smoke.json`

---

## 5) Finalize outputs

```bash
make analysis
make package
```

---

## 6) Release-grade gate (required)

```bash
make release-check
```

This is the required final gate before transfer.
It writes transcript + provenance to:
- `outputs/status/release-check.log`
- `outputs/status/release_check_provenance.json`

Optional live integration gate (real SLURM mini-run + GPU smoke evidence):

```bash
make release-check-live
```

---

## 7) Pull-back handoff

Pick latest bundle:

```bash
ls -1t outputs/bundles/transformer_results_*.tar.gz | head -n1
```

Copy these 3 files off cluster:
- `transformer_results_<STAMP>.tar.gz`
- `transformer_results_<STAMP>.tar.gz.sha256`
- `transformer_results_<STAMP>.tar.gz.manifest.json`

Example:

```bash
scp <user>@<cluster>:/path/to/transformer-experiments/outputs/bundles/transformer_results_<STAMP>.tar.gz .
scp <user>@<cluster>:/path/to/transformer-experiments/outputs/bundles/transformer_results_<STAMP>.tar.gz.sha256 .
scp <user>@<cluster>:/path/to/transformer-experiments/outputs/bundles/transformer_results_<STAMP>.tar.gz.manifest.json .
sha256sum -c transformer_results_<STAMP>.tar.gz.sha256
```

Then upload the 3 files here for interpretation.

---

## Troubleshooting quick list

- **`preflight-slurm` fails on GPU check**: verify `nvidia-smi` and cluster GPU allocation path.
- **SLURM submit errors**: verify `PARTITION/ACCOUNT/QOS/CONSTRAINT` values.
- **OOM exit code 137**: reduce run size or increase `MEM`/adjust job resources.
- **No space left on device**: clear stale `outputs/` artifacts and rerun.
- **release-check fails**: read the first failing validator; gate is intentionally fail-fast.
