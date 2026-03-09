#!/usr/bin/env python3
from __future__ import annotations


def parse_jobid(raw: str) -> str:
    return raw.split(";")[0].strip()


def main() -> None:
    cases = {
        "12345": "12345",
        "12345;gpu": "12345",
        "12345 ; gpu": "12345",
        " 98765\n": "98765",
    }
    for raw, want in cases.items():
        got = parse_jobid(raw)
        if got != want:
            raise SystemExit(f"[jobid-test:FAIL] {raw!r} -> {got!r}, want {want!r}")

    bad = ["", "abc", "abc;gpu"]
    for raw in bad:
        got = parse_jobid(raw)
        if got.isdigit():
            raise SystemExit(f"[jobid-test:FAIL] expected non-digit parse for bad case {raw!r}")

    print("[jobid-test:OK] parser behavior matches expectations")


if __name__ == "__main__":
    main()
