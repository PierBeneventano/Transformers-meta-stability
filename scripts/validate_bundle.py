#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, required=True)
    args = ap.parse_args()

    sha_file = Path(str(args.bundle) + ".sha256")
    manifest_file = Path(str(args.bundle) + ".manifest.json")
    if not args.bundle.exists() or not sha_file.exists() or not manifest_file.exists():
        raise SystemExit("[bundle:FAIL] bundle or sidecars missing")

    expected = sha_file.read_text().strip().split()[0]
    actual = sha256_file(args.bundle)
    if expected != actual:
        raise SystemExit("[bundle:FAIL] sha256 sidecar mismatch")

    manifest = json.loads(manifest_file.read_text())
    if manifest.get("bundle_sha256") != actual:
        raise SystemExit("[bundle:FAIL] manifest hash mismatch")
    if manifest.get("contract_version") != "transformer_handoff_v1":
        raise SystemExit("[bundle:FAIL] unexpected contract_version")

    if "release_check_provenance" not in manifest:
        raise SystemExit("[bundle:FAIL] release_check_provenance missing from manifest")
    prov = manifest.get("release_check_provenance")
    if prov is not None:
        required = ["git_commit", "command", "timestamp_utc", "stdout_stderr_sha256"]
        missing = [k for k in required if not prov.get(k)]
        if missing:
            raise SystemExit(f"[bundle:FAIL] release provenance missing fields: {missing}")

    print("[bundle:OK] bundle + sidecars + manifest consistent")


if __name__ == "__main__":
    main()
