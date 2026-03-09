#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--require-cuda", action="store_true")
    p.add_argument("--mixed-precision-smoke", action="store_true")
    args = p.parse_args()

    report = {
        "timestamp": time.time(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }

    try:
        import torch  # type: ignore

        report["torch"] = torch.__version__
        report["cuda_available"] = bool(torch.cuda.is_available())
        report["cuda_version"] = getattr(torch.version, "cuda", None)
        report["gpu_count"] = int(torch.cuda.device_count())

        if report["cuda_available"]:
            report["current_device"] = int(torch.cuda.current_device())
            report["device_name"] = torch.cuda.get_device_name(report["current_device"])

            # simple tensor smoke
            x = torch.randn(512, 512, device="cuda")
            y = torch.randn(512, 512, device="cuda")
            z = x @ y
            report["cuda_smoke_norm"] = float(z.norm().item())

            if args.mixed_precision_smoke:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    z2 = x @ y
                report["amp_smoke_norm"] = float(z2.float().norm().item())

    except Exception as e:  # noqa: BLE001
        report["torch_error"] = str(e)

    print(json.dumps(report, indent=2))

    if args.require_cuda and not bool(report.get("cuda_available", False)):
        raise SystemExit("gpu_sanity: CUDA required but unavailable")


if __name__ == "__main__":
    main()
