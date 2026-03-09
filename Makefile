SHELL := /usr/bin/env bash
PY ?= python3
OUT_ROOT ?= $(CURDIR)/outputs/runs
ANALYSIS_DIR ?= $(CURDIR)/analysis
EXPERIMENT_IDS ?=
MAX_VARIANTS_PER_EXP ?= 0
REQUIRE_TORCH ?= 0

# MIT cluster convenience defaults (override at invocation if needed)
MIT_PARTITION ?= mit_normal_gpu
MIT_GPUS ?= 1
MIT_CPUS ?= 8
MIT_MEM ?= 32G
MIT_TIME_LIMIT ?= 06:00:00
MIT_REQUIRE_GPU ?= 0

.PHONY: bootstrap preflight preflight-slurm build-matrix launch-local launch-slurm launch-mit-gpu slurm-dry-run release-check-live status status-json analysis package validate-syntax validate-config validate-status validate-analysis validate-bundle validate-handoff validate-jobs validate-gpu-smoke test-jobid mini-run release-check sample-proof

bootstrap:
	bash scripts/bootstrap_env.sh

preflight:
	$(PY) scripts/preflight_check.py --out-root "$(OUT_ROOT)" --min-free-gb 2 --mode local

preflight-slurm:
	$(PY) scripts/preflight_check.py --out-root "$(OUT_ROOT)" --min-free-gb 2 --mode slurm --require-gpu

build-matrix:
	$(PY) scripts/build_run_matrix.py --config configs/experiments.yaml --out outputs/run_matrix.tsv --experiment-ids "$(EXPERIMENT_IDS)" --max-variants-per-exp "$(MAX_VARIANTS_PER_EXP)"

launch-local:
	MODE=local REQUIRE_GPU=0 OUT_ROOT="$(OUT_ROOT)" EXPERIMENT_IDS="$(EXPERIMENT_IDS)" MAX_VARIANTS_PER_EXP="$(MAX_VARIANTS_PER_EXP)" REQUIRE_TORCH="$(REQUIRE_TORCH)" ./run_all_experiments.sh

launch-slurm:
	MODE=slurm REQUIRE_GPU=1 OUT_ROOT="$(OUT_ROOT)" EXPERIMENT_IDS="$(EXPERIMENT_IDS)" MAX_VARIANTS_PER_EXP="$(MAX_VARIANTS_PER_EXP)" REQUIRE_TORCH="$(REQUIRE_TORCH)" ./run_all_experiments.sh

# Convenience target for MIT GPU partition from login nodes (no local GPU required)
launch-mit-gpu:
	MODE=slurm REQUIRE_GPU="$(MIT_REQUIRE_GPU)" DEVICE=cuda PARTITION="$(MIT_PARTITION)" GPUS="$(MIT_GPUS)" CPUS="$(MIT_CPUS)" MEM="$(MIT_MEM)" TIME_LIMIT="$(MIT_TIME_LIMIT)" OUT_ROOT="$(OUT_ROOT)" EXPERIMENT_IDS="$(EXPERIMENT_IDS)" MAX_VARIANTS_PER_EXP="$(MAX_VARIANTS_PER_EXP)" REQUIRE_TORCH="$(REQUIRE_TORCH)" ./run_all_experiments.sh

slurm-dry-run:
	rm -f outputs/slurm/submitted_jobs.tsv
	MODE=slurm DRY_RUN_SLURM=1 REQUIRE_GPU=0 MIN_FREE_GB=0.10 OUT_ROOT="$(CURDIR)/outputs/runs_dryslurm" EXPERIMENT_IDS="Exp1 Exp2" MAX_VARIANTS_PER_EXP=1 ./run_all_experiments.sh

status:
	$(PY) scripts/print_status.py --root "$(OUT_ROOT)"

status-json:
	mkdir -p outputs/status
	$(PY) scripts/print_status.py --root "$(OUT_ROOT)" --json outputs/status/summary.json

analysis:
	$(PY) scripts/run_analysis_pipeline.py --root "$(OUT_ROOT)" --out-dir "$(ANALYSIS_DIR)"

package:
	bash scripts/package_results.sh

validate-syntax:
	$(PY) -m py_compile scripts/*.py
	bash -n run_all_experiments.sh
	bash -n cluster/slurm_experiment.sbatch

validate-config:
	$(PY) scripts/validate_config_matrix.py --config configs/experiments.yaml

validate-status:
	$(PY) scripts/validate_status_json.py --status-json outputs/status/summary.json

validate-analysis:
	$(PY) scripts/validate_analysis_outputs.py --analysis-dir analysis

validate-bundle:
	@B=$$(ls -1t outputs/bundles/transformer_results_*.tar.gz 2>/dev/null | head -n1); \
	if [ -z "$$B" ]; then echo "[bundle:FAIL] no bundle found"; exit 2; fi; \
	$(PY) scripts/validate_bundle.py --bundle "$$B"

validate-handoff:
	@B=$$(ls -1t outputs/bundles/transformer_results_*.tar.gz 2>/dev/null | head -n1); \
	if [ -z "$$B" ]; then echo "[handoff:FAIL] no bundle found"; exit 2; fi; \
	$(PY) scripts/validate_handoff_bundle.py --bundle "$$B"

validate-jobs:
	@if [ -f outputs/slurm/submitted_jobs.tsv ]; then \
		$(PY) scripts/validate_submitted_jobs.py --file outputs/slurm/submitted_jobs.tsv --allow-dry; \
	else \
		echo "[jobs:WARN] outputs/slurm/submitted_jobs.tsv not found (skip)"; \
	fi

validate-gpu-smoke:
	$(PY) scripts/validate_gpu_smoke_artifacts.py --submitted outputs/slurm/submitted_jobs.tsv --smoke-dir outputs/slurm/gpu_smoke

test-jobid:
	$(PY) scripts/test_jobid_parsing.py

mini-run:
	MODE=local REQUIRE_GPU=0 MIN_FREE_GB=0.10 OUT_ROOT="$(OUT_ROOT)" EXPERIMENT_IDS="Exp1 Exp2 Exp3 Exp4 Exp5 Exp6 Exp7 Exp8 Exp9 Exp10 Exp11 Exp12 Exp13 Exp14 Exp15 Exp16 G1 G2 G3" MAX_VARIANTS_PER_EXP=1 ./run_all_experiments.sh
	$(MAKE) status-json
	$(MAKE) analysis

release-check:
	@set -euo pipefail; \
	mkdir -p outputs/status; \
	LOG=outputs/status/release-check.log; \
	: > "$$LOG"; \
	{ \
		echo "[release-check] start"; \
		$(MAKE) validate-syntax; \
		$(MAKE) validate-config; \
		$(MAKE) mini-run; \
		$(MAKE) slurm-dry-run; \
		$(MAKE) validate-jobs; \
		$(MAKE) test-jobid; \
		$(MAKE) validate-status; \
		$(MAKE) validate-analysis; \
		$(MAKE) package; \
		$(MAKE) validate-bundle; \
		$(MAKE) validate-handoff; \
		echo "[release-check:OK] all validation gates passed"; \
	} 2>&1 | tee -a "$$LOG"; \
	$(PY) scripts/write_release_provenance.py --log "$$LOG" --command "make release-check"

release-check-live:
	@set -euo pipefail; \
	mkdir -p outputs/status; \
	LOG=outputs/status/release-check-live.log; \
	: > "$$LOG"; \
	{ \
		echo "[release-check-live] start"; \
		MODE=slurm REQUIRE_GPU=1 MIN_FREE_GB=0.10 OUT_ROOT="$(CURDIR)/outputs/runs_livecheck" EXPERIMENT_IDS="Exp1" MAX_VARIANTS_PER_EXP=1 ./run_all_experiments.sh; \
		$(PY) scripts/validate_submitted_jobs.py --file outputs/slurm/submitted_jobs.tsv; \
		$(PY) scripts/validate_gpu_smoke_artifacts.py --submitted outputs/slurm/submitted_jobs.tsv --smoke-dir outputs/slurm/gpu_smoke --require-success; \
		echo "[release-check-live:OK] submitted real slurm mini-run with gpu smoke evidence"; \
	} 2>&1 | tee -a "$$LOG"

sample-proof:
	$(MAKE) mini-run
