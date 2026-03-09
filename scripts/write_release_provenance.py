#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
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


def git_head(cwd: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, text=True).strip()
        return out
    except Exception:
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--command", type=str, default="make release-check")
    ap.add_argument("--out", type=Path, default=Path("outputs/status/release_check_provenance.json"))
    args = ap.parse_args()

    if not args.log.exists():
        raise SystemExit(f"[provenance:FAIL] log not found: {args.log}")

    out = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": git_head(Path.cwd()),
        "command": args.command,
        "log_path": str(args.log),
        "stdout_stderr_sha256": sha256_file(args.log),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[provenance:OK] wrote {args.out}")


if __name__ == "__main__":
    main()
