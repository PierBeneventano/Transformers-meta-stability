# Acceptance Checklist — transformer-experiments

Use this checklist before declaring the repo ready for push/run/pull workflow.

## A. Coverage + scope (I1/I2)

- [x] `docs/EXPERIMENT_COVERAGE.json` exists.
- [x] Coverage matrix includes canonical IDs: `Exp1..Exp16`, `G1..G3`.
- [x] `configs/experiments.yaml` contains runnable entries for all canonical IDs.
- [x] `scripts/build_run_matrix.py` deterministically expands matrix to run commands.

## B. GPU + SLURM hardening (I3)

- [x] `scripts/preflight_check.py` supports `--mode slurm` and GPU checks.
- [x] `scripts/gpu_sanity.py` exists and validates CUDA runtime in jobs.
- [x] `cluster/slurm_experiment.sbatch` emits GPU diagnostics + per-job smoke artifact set (`nvidia-smi.txt`, `gpu.json`, `smoke.json`).
- [x] `run_all_experiments.sh` supports scheduler resource knobs, strict job-id parsing, and optional OOM retry policy with MEM/GRES presets.
- [x] `scripts/validate_gpu_smoke_artifacts.py` validates required real-cluster GPU smoke evidence.

## C. End-to-end validation gates (I4)

- [x] `make release-check` exists and is documented.
- [x] Gate includes syntax + config + mini-run + slurm-dry-run + status + analysis + package + handoff checks.
- [x] `make release-check-live` exists for real-SLURM integration validation.
- [x] `release-check` writes transcript provenance (`outputs/status/release_check_provenance.json`) used in bundle manifest.
- [x] `scripts/test_jobid_parsing.py` regression exists.
- [x] `scripts/validate_submitted_jobs.py` validates job manifest format (supports retry metadata columns).
- [x] `scripts/validate_bundle.py` verifies bundle + sidecars + contract.
- [x] `scripts/validate_handoff_bundle.py` verifies required tar members.

## D. Operator docs + handoff (I5)

- [x] `README.md` includes exact cluster flow and release-check.
- [x] `SHIP_IT.md` includes unambiguous runbook + troubleshooting.
- [x] Pull-back triplet documented (`tar.gz`, `.sha256`, `.manifest.json`).

## E. Evidence artifacts (latest local validation snapshot)

- [x] `outputs/status/summary.json`
- [x] `analysis/results_summary.md`
- [x] `analysis/artifact_manifest.json`
- [x] `analysis/tables/table_all_runs.csv`
- [x] `analysis/tables/table_experiment_summary.csv`
- [x] At least one bundle in `outputs/bundles/transformer_results_*.tar.gz` with sidecars
- [ ] (Cluster run) `make validate-gpu-smoke` passes against real SLURM job artifacts

## F. Lineage reconciliation (signoff integrity)

- [x] `docs/READINESS_REPORT.md` includes a commit-lineage reconciliation note (including scope boundaries and any known cross-repo ambiguities).
- [x] Readiness report includes immutable evidence block: HEAD commit SHA, bundle SHA256, status JSON hash, analysis manifest hash.

## Exit criteria

Declare ready only when all boxes above are checked and `make release-check` passes on the intended branch.
