#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT"

MODE=${MODE:-local}            # local | slurm
DRY_RUN_SLURM=${DRY_RUN_SLURM:-0}
PARTITION=${PARTITION:-gpu}
ACCOUNT=${ACCOUNT:-}
QOS=${QOS:-}
CONSTRAINT=${CONSTRAINT:-}
TIME_LIMIT=${TIME_LIMIT:-02:00:00}
CPUS=${CPUS:-4}
MEM=${MEM:-16G}
GPUS=${GPUS:-1}
GRES=${GRES:-}
DEVICE=${DEVICE:-cuda}
OUT_ROOT=${OUT_ROOT:-$ROOT/outputs/runs}
MIN_FREE_GB=${MIN_FREE_GB:-2}
EXPERIMENT_IDS=${EXPERIMENT_IDS:-""}
MAX_VARIANTS_PER_EXP=${MAX_VARIANTS_PER_EXP:-0}
CONFIG=${CONFIG:-$ROOT/configs/experiments.yaml}
REQUIRE_GPU=${REQUIRE_GPU:-auto}   # auto|0|1
REQUIRE_TORCH=${REQUIRE_TORCH:-0}

# optional OOM retry policy (applies across orchestrator re-runs)
ENABLE_OOM_RETRY=${ENABLE_OOM_RETRY:-0}
OOM_RETRY_MAX=${OOM_RETRY_MAX:-2}
OOM_RETRY_MEM_PRESETS=${OOM_RETRY_MEM_PRESETS:-16G,24G,32G}
OOM_RETRY_GRES_PRESETS=${OOM_RETRY_GRES_PRESETS:-gpu:1,gpu:1,gpu:1}

if [[ "$REQUIRE_GPU" == "auto" ]]; then
  if [[ "$MODE" == "slurm" ]]; then
    REQUIRE_GPU=1
  else
    REQUIRE_GPU=0
  fi
fi

# GPU request normalization:
# - GPUS=<n> is accepted for compatibility with cluster habits
# - explicit GRES wins; otherwise derive GRES from GPUS
if [[ -z "$GRES" ]]; then
  if [[ -n "$GPUS" && "$GPUS" != "0" ]]; then
    GRES="gpu:${GPUS}"
  else
    GRES=""
  fi
fi

if [[ "$MODE" == "slurm" && "$REQUIRE_GPU" == "1" ]]; then
  if [[ -z "$GRES" ]]; then
    echo "[slurm:FAIL] GPU required but no GPU resources requested. Set GPUS (e.g. GPUS=1) or GRES (e.g. GRES=gpu:1)." >&2
    exit 2
  fi
fi

mkdir -p "$OUT_ROOT" "$ROOT/outputs/slurm" "$ROOT/outputs/slurm/retries" "$ROOT/outputs/jobs"

PF_MODE="$MODE"
if [[ "$MODE" == "slurm" && "$DRY_RUN_SLURM" == "1" ]]; then
  PF_MODE="local"
  echo "[preflight:WARN] DRY_RUN_SLURM=1 -> using local preflight checks (sbatch not required)"
fi

PF_ARGS=(--out-root "$OUT_ROOT" --min-free-gb "$MIN_FREE_GB" --mode "$PF_MODE")
[[ "$REQUIRE_GPU" == "1" ]] && PF_ARGS+=(--require-gpu)
[[ "$REQUIRE_TORCH" == "1" ]] && PF_ARGS+=(--require-torch)
python3 scripts/preflight_check.py "${PF_ARGS[@]}"

MATRIX="$ROOT/outputs/run_matrix.tsv"
python3 scripts/build_run_matrix.py --config "$CONFIG" --out "$MATRIX" --experiment-ids "$EXPERIMENT_IDS" --max-variants-per-exp "$MAX_VARIANTS_PER_EXP"

csv_nth_or_last () {
  local csv=$1 idx=$2
  IFS=',' read -r -a arr <<< "$csv"
  if [[ ${#arr[@]} -eq 0 ]]; then
    echo ""
    return 0
  fi
  if (( idx < ${#arr[@]} )); then
    echo "${arr[$idx]}"
  else
    echo "${arr[${#arr[@]}-1]}"
  fi
}

attempt_for_run () {
  local run_name=$1
  local f="$ROOT/outputs/slurm/retries/${run_name}.attempt"
  if [[ ! -f "$f" ]]; then
    echo 0
    return 0
  fi
  local a
  a=$(cat "$f" 2>/dev/null || echo 0)
  if [[ "$a" =~ ^[0-9]+$ ]]; then
    echo "$a"
  else
    echo 0
  fi
}

submit_slurm () {
  local run_name=$1 job_script=$2 attempt=$3 mem_sel=$4 gres_sel=$5

  if [[ "$DRY_RUN_SLURM" == "1" ]]; then
    echo "dry-${run_name}"
    return 0
  fi

  local -a sb_args
  sb_args=(
    --parsable
    --partition="$PARTITION"
    --time="$TIME_LIMIT"
    --cpus-per-task="$CPUS"
    --mem="$mem_sel"
  )
  [[ -n "$gres_sel" ]] && sb_args+=(--gres="$gres_sel")
  [[ -n "$ACCOUNT" ]] && sb_args+=(--account="$ACCOUNT")
  [[ -n "$QOS" ]] && sb_args+=(--qos="$QOS")
  [[ -n "$CONSTRAINT" ]] && sb_args+=(--constraint="$CONSTRAINT")

  local raw
  raw=$(sbatch "${sb_args[@]}" --export=ALL,ROOT="$ROOT",RUN_NAME="$run_name",JOB_SCRIPT="$job_script",REQUIRE_GPU="$REQUIRE_GPU",REQUIRE_TORCH="$REQUIRE_TORCH",DEVICE="$DEVICE",ATTEMPT="$attempt",ENABLE_OOM_RETRY="$ENABLE_OOM_RETRY",OOM_RETRY_MAX="$OOM_RETRY_MAX" cluster/slurm_experiment.sbatch)
  local jobid
  jobid=$(echo "$raw" | cut -d';' -f1 | tr -d '[:space:]')
  if [[ -z "$jobid" ]]; then
    echo "[slurm:FAIL] empty job id parsed from sbatch output: '$raw'" >&2
    return 1
  fi
  if ! [[ "$jobid" =~ ^[0-9]+$ ]]; then
    echo "[slurm:FAIL] non-numeric job id parsed from sbatch output: '$raw' -> '$jobid'" >&2
    return 1
  fi
  echo "$jobid"
}

{
  read -r header
  while IFS=$'\t' read -r run_name exp_id params_json command; do
    out_dir="$OUT_ROOT/$run_name"
    if [[ -f "$out_dir/summary.json" ]]; then
      echo "[skip] $run_name"
      continue
    fi
    mkdir -p "$out_dir"

    job_script="$ROOT/outputs/jobs/${run_name}.sh"
    {
      echo '#!/usr/bin/env bash'
      echo 'set -euo pipefail'
      echo "cd '$ROOT'"
      echo "export DEVICE='$DEVICE'"
      echo "$command"
      echo "python3 scripts/postflight_check.py --run-dir '$out_dir'"
    } > "$job_script"
    chmod +x "$job_script"

    if [[ "$MODE" == "local" ]]; then
      echo "[local] $run_name"
      bash "$job_script"
    else
      attempt=$(attempt_for_run "$run_name")
      if [[ "$ENABLE_OOM_RETRY" == "1" ]] && (( attempt > OOM_RETRY_MAX )); then
        echo "[slurm:FAIL] $run_name exceeded OOM_RETRY_MAX=$OOM_RETRY_MAX (attempt=$attempt)"
        continue
      fi

      if [[ "$ENABLE_OOM_RETRY" == "1" ]]; then
        mem_sel=$(csv_nth_or_last "$OOM_RETRY_MEM_PRESETS" "$attempt")
        gres_sel=$(csv_nth_or_last "$OOM_RETRY_GRES_PRESETS" "$attempt")
      else
        mem_sel="$MEM"
        gres_sel="$GRES"
      fi

      echo "[slurm] $run_name attempt=$attempt mem=$mem_sel gres=$gres_sel"
      jobid=$(submit_slurm "$run_name" "$job_script" "$attempt" "$mem_sel" "$gres_sel")
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$run_name" "$exp_id" "$jobid" "$attempt" "$mem_sel" "$gres_sel" >> "$ROOT/outputs/slurm/submitted_jobs.tsv"
    fi
  done
} < "$MATRIX"

echo "All runs scheduled/completed."
