# Readiness Report — transformer-experiments

**Report time (UTC):** 2026-03-09T04:10:00Z

## Scope

This report signs off operator readiness for:
- push to cluster
- run via `run_all_experiments.sh` / Make targets
- monitor via status tools
- produce analysis + bundle handoff for downstream interpretation

## Implementation milestones (commits)

- I1 coverage audit baseline: `2fa12a3`
- I1 round-2 spec freeze + hash lock: `323a3c8`
- I2 full matrix implementation: `435c6a7`
- I2 round-2 theorem-specific analysis + Stage-B full-fidelity path: `aae202d`
- I3 GPU/SLURM hardening baseline: `662c419`
- I3 round-2 GPU smoke contract + OOM retry presets: `9b9ffc6`
- I4 validation gates baseline: `9bad156`
- I4 round-2 live gate + provenance hashing: `b86be86`
- I5 operator docs/checklists/report: this report + checklist updates

## Immutable evidence block

- Branch HEAD commit SHA: `b86be86abb7bb12e2feaa3d7ef974ebcab174a9a`
- Latest validated bundle:
  - `outputs/bundles/transformer_results_20260309T040800Z.tar.gz`
  - sha256: `0f4b1039082b9ae9209fc093b5101109fcfae4b3bedc1e7914ed0dd22e9eef22`
- `outputs/status/summary.json`
  - sha256: `f178fea398b2bfcf5df6f7dfdb849bf5b0b60af837c754eafa04a9e45c95b2c7`
- `analysis/artifact_manifest.json`
  - sha256: `30dae9f973e2aeb61500d716e11857fdcac0622cb14bd411afb02c508bad0b15`
- Release-check provenance artifact:
  - `outputs/status/release_check_provenance.json`
  - includes: commit, command, timestamp, transcript digest

## Commit-lineage reconciliation note (required)

- Transformer repo lineage above is internally consistent and pinned by commit SHA.
- Previously noted commit ambiguity (`4eebf7c` vs `1b8b4ba`) belongs to the **calibration** repo history, not `transformer-experiments`.
- This signoff only covers `transformer-experiments` artifacts and commit lineage listed here.

## Acceptance result

Using checklist: `docs/ACCEPTANCE_CHECKLIST.md`

- Coverage/config matrix: **PASS**
- GPU/SLURM hardening: **PASS**
- End-to-end validation gate (`make release-check`): **PASS**
- Live integration gate (`make release-check-live`): **available** (cluster-run evidence required on target cluster)
- Operator runbook clarity: **PASS**

## Operational caveats

- Site-specific SLURM policy values (`ACCOUNT/QOS/CONSTRAINT/PARTITION`) must be set correctly.
- GPU availability and CUDA health remain cluster-environment dependent at execution time.
- Cluster-executed `make release-check-live` + `make validate-gpu-smoke` must be archived for final production signoff.

## Signed readiness statement

I certify that `transformer-experiments` is operator-ready for the defined push/run/pull workflow, with deterministic validation gates, provenance-linked packaging, and documented troubleshooting.

**Signed:** CyberTommy (ct)
