#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def check_bin(name: str, required: bool = True) -> bool:
    ok = shutil.which(name) is not None
    if ok:
        print(f"[preflight:OK] binary found: {name}")
        return True
    if required:
        raise SystemExit(f"[preflight:FAIL] required binary missing from PATH: {name}")
    print(f"[preflight:WARN] optional binary missing: {name}")
    return False


def run_quiet(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out-root", type=Path, required=True)
    p.add_argument("--min-free-gb", type=float, default=2.0)
    p.add_argument("--mode", choices=["local", "slurm"], default="local")
    p.add_argument("--require-gpu", action="store_true")
    p.add_argument("--require-torch", action="store_true")
    args = p.parse_args()

    args.out_root.mkdir(parents=True, exist_ok=True)

    check_bin("python3", required=True)
    if args.mode == "slurm":
        check_bin("sbatch", required=True)
        check_bin("squeue", required=False)

    usage = shutil.disk_usage(args.out_root)
    free_gb = usage.free / (1024**3)
    print(f"[preflight] free disk: {free_gb:.2f} GB")
    if free_gb < args.min_free_gb:
        raise SystemExit(f"[preflight:FAIL] insufficient free disk: {free_gb:.2f} < {args.min_free_gb:.2f} GB")

    # GPU visibility checks
    has_nvidia_smi = check_bin("nvidia-smi", required=args.require_gpu)
    gpu_count = 0
    if has_nvidia_smi:
        rc, out, err = run_quiet(["nvidia-smi", "-L"])
        if rc != 0:
            msg = err or out or "unknown nvidia-smi error"
            if args.require_gpu:
                raise SystemExit(f"[preflight:FAIL] nvidia-smi failed: {msg}")
            print(f"[preflight:WARN] nvidia-smi not healthy: {msg}")
        else:
            gpu_count = sum(1 for ln in out.splitlines() if ln.strip())
            print(f"[preflight] detected GPUs: {gpu_count}")
            if args.require_gpu and gpu_count <= 0:
                raise SystemExit("[preflight:FAIL] require-gpu set but zero GPUs detected")

    # Torch/CUDA compatibility check
    rc, out, err = run_quiet(
        [
            "python3",
            "-c",
            (
                "import json\n"
                "try:\n"
                " import torch\n"
                " print(json.dumps({'ok':True,'torch':torch.__version__,"
                "'cuda_available':bool(torch.cuda.is_available()),"
                "'cuda_version':getattr(torch.version,'cuda',None),"
                "'gpu_count':torch.cuda.device_count()}))\n"
                "except Exception as e:\n"
                " print(json.dumps({'ok':False,'error':str(e)}))\n"
            ),
        ]
    )
    if rc == 0 and out:
        import json

        try:
            t = json.loads(out.splitlines()[-1])
        except Exception:
            t = {"ok": False, "error": out}

        if t.get("ok"):
            print(
                f"[preflight] torch={t.get('torch')} cuda_available={t.get('cuda_available')} "
                f"cuda_version={t.get('cuda_version')} gpu_count={t.get('gpu_count')}"
            )
            if args.require_gpu and not bool(t.get("cuda_available")):
                raise SystemExit("[preflight:FAIL] require-gpu set but torch.cuda.is_available() is false")
        else:
            if args.require_torch:
                raise SystemExit(f"[preflight:FAIL] torch check failed: {t.get('error')}")
            print(f"[preflight:WARN] torch unavailable: {t.get('error')}")
    elif args.require_torch:
        raise SystemExit(f"[preflight:FAIL] torch check command failed: {err or out}")

    print("[preflight:OK] all checks passed")


if __name__ == "__main__":
    main()
