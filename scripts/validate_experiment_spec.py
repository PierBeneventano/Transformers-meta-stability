#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', type=Path, default=Path('docs/EXPERIMENT_SPEC.md'))
    ap.add_argument('--coverage', type=Path, default=Path('docs/EXPERIMENT_COVERAGE.json'))
    ap.add_argument('--sha-file', type=Path, default=Path('docs/EXPERIMENT_SPEC.sha256'))
    args = ap.parse_args()

    if not args.spec.exists() or not args.coverage.exists() or not args.sha_file.exists():
        raise SystemExit('[spec:FAIL] required spec/coverage/hash file missing')

    actual = sha256_path(args.spec)
    from_sidecar = args.sha_file.read_text().split()[0].strip()
    if actual != from_sidecar:
        raise SystemExit('[spec:FAIL] spec sha mismatch against sidecar')

    cov = json.loads(args.coverage.read_text())
    src = cov.get('source', {})
    if src.get('spec_path') != 'docs/EXPERIMENT_SPEC.md':
        raise SystemExit('[spec:FAIL] coverage source.spec_path mismatch')
    if src.get('spec_sha256') != actual:
        raise SystemExit('[spec:FAIL] coverage source.spec_sha256 mismatch')

    print('[spec:OK] frozen experiment spec hash matches coverage + sidecar')


if __name__ == '__main__':
    main()
