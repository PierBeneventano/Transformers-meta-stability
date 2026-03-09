#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
STAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUT="$ROOT/outputs/bundles/transformer_results_${STAMP}.tar.gz"
mkdir -p "$ROOT/outputs/bundles"

cd "$ROOT"
items=(outputs/runs analysis outputs/status outputs/slurm outputs/run_matrix.tsv configs/experiments.yaml)
existing=()
for p in "${items[@]}"; do
  [[ -e "$p" ]] && existing+=("$p")
done

if [[ ${#existing[@]} -eq 0 ]]; then
  echo "No outputs to package" >&2
  exit 2
fi

tar -czf "$OUT" "${existing[@]}"
sha256sum "$OUT" > "$OUT.sha256"

python3 - <<PY
import hashlib, json, tarfile
from pathlib import Path

out=Path(r"$OUT")
h=hashlib.sha256(out.read_bytes()).hexdigest()
entries=[]
with tarfile.open(out, 'r:gz') as tf:
    for m in tf.getmembers():
        e={"path":m.name,"size":int(m.size),"type":"file" if m.isfile() else "dir" if m.isdir() else "other"}
        entries.append(e)

prov_path=Path("outputs/status/release_check_provenance.json")
release_provenance=None
if prov_path.exists():
    try:
        p=json.loads(prov_path.read_text())
        release_provenance={
            "git_commit": p.get("git_commit"),
            "command": p.get("command"),
            "timestamp_utc": p.get("timestamp_utc"),
            "stdout_stderr_sha256": p.get("stdout_stderr_sha256"),
            "log_path": p.get("log_path"),
        }
    except Exception:
        release_provenance={"error":"failed_to_parse_release_check_provenance"}

manifest={
  "contract_version":"transformer_handoff_v1",
  "bundle":str(out),
  "bundle_sha256":h,
  "bundle_bytes":out.stat().st_size,
  "created_utc":"$STAMP",
  "included_paths":$(printf '%s\n' "${existing[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))'),
  "members":entries,
  "release_check_provenance": release_provenance,
}
Path(str(out)+'.manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
PY

echo "Packaged: $OUT"
echo "Checksum: $OUT.sha256"
echo "Manifest: $OUT.manifest.json"
