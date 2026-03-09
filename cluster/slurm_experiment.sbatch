#!/usr/bin/env bash
#SBATCH -J trf-exp
#SBATCH -o outputs/slurm/%x-%j.out
#SBATCH -e outputs/slurm/%x-%j.err

set -euo pipefail

ROOT=${ROOT:?ROOT not set}
JOB_SCRIPT=${JOB_SCRIPT:?JOB_SCRIPT not set}
RUN_NAME=${RUN_NAME:-run}
REQUIRE_GPU=${REQUIRE_GPU:-1}
REQUIRE_TORCH=${REQUIRE_TORCH:-0}
DEVICE=${DEVICE:-cuda}
ATTEMPT=${ATTEMPT:-0}
ENABLE_OOM_RETRY=${ENABLE_OOM_RETRY:-0}
OOM_RETRY_MAX=${OOM_RETRY_MAX:-2}

cd "$ROOT"
mkdir -p outputs/slurm outputs/slurm/retries outputs/slurm/gpu_smoke

JOB_ID=${SLURM_JOB_ID:-nojob}
SMOKE_DIR="outputs/slurm/gpu_smoke"
GPU_JSON="$SMOKE_DIR/${RUN_NAME}-${JOB_ID}-gpu.json"
NVIDIA_LOG="$SMOKE_DIR/${RUN_NAME}-${JOB_ID}-nvidia-smi.txt"
SMOKE_SUMMARY="$SMOKE_DIR/${RUN_NAME}-${JOB_ID}-smoke.json"
RUN_SUMMARY="outputs/runs/${RUN_NAME}/summary.json"


echo "[slurm] host=$(hostname) job_id=${JOB_ID} run=${RUN_NAME} attempt=${ATTEMPT}"
echo "[slurm] device=${DEVICE} cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"

if command -v nvidia-smi >/dev/null 2>&1; then
  {
    echo "[nvidia-smi -L]"
    nvidia-smi -L || true
    echo
    echo "[nvidia-smi]"
    nvidia-smi || true
  } > "$NVIDIA_LOG"
else
  echo "[slurm:WARN] nvidia-smi not found" > "$NVIDIA_LOG"
fi

GPU_ARGS=()
[[ "$REQUIRE_GPU" == "1" ]] && GPU_ARGS+=(--require-cuda)
[[ "$REQUIRE_TORCH" == "1" ]] && GPU_ARGS+=(--mixed-precision-smoke)
python3 scripts/gpu_sanity.py "${GPU_ARGS[@]}" > "$GPU_JSON" || {
  echo "[slurm:FAIL] gpu_sanity failed"
  exit 1
}

set +e
bash "$JOB_SCRIPT"
rc=$?
set -e

if [[ $rc -eq 137 ]]; then
  echo "[slurm:FAIL] run exited with code 137 (possible OOM)"
  python3 - <<PY
import json, pathlib
p = pathlib.Path("outputs/slurm/${RUN_NAME}-${JOB_ID}.oom.json")
p.write_text(json.dumps({
  "run_name": "${RUN_NAME}",
  "job_id": "${JOB_ID}",
  "attempt": int("${ATTEMPT}"),
  "exit_code": 137,
  "status": "oom"
}, indent=2), encoding="utf-8")
PY
  if [[ "$ENABLE_OOM_RETRY" == "1" ]]; then
    next_attempt=$((ATTEMPT + 1))
    if (( next_attempt <= OOM_RETRY_MAX )); then
      echo "$next_attempt" > "outputs/slurm/retries/${RUN_NAME}.attempt"
      echo "[slurm:RETRY] marked ${RUN_NAME} for retry attempt ${next_attempt}/${OOM_RETRY_MAX}"
    else
      echo "[slurm:RETRY] max retries exhausted for ${RUN_NAME}"
    fi
  fi
fi

if [[ $rc -eq 0 ]]; then
  echo "0" > "outputs/slurm/retries/${RUN_NAME}.attempt"
fi

python3 - <<PY
import json, pathlib
summary = {
  "run_name": "${RUN_NAME}",
  "job_id": "${JOB_ID}",
  "attempt": int("${ATTEMPT}"),
  "success": bool(${rc} == 0),
  "exit_code": int(${rc}),
  "nvidia_smi_log": "${NVIDIA_LOG}",
  "gpu_sanity_json": "${GPU_JSON}",
  "run_summary_path": "${RUN_SUMMARY}",
  "run_summary_exists": pathlib.Path("${RUN_SUMMARY}").exists()
}
pathlib.Path("${SMOKE_SUMMARY}").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY

exit $rc
