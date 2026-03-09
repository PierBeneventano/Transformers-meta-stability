# Experiment Coverage Audit (Transformers.tex -> transformer-experiments)

## Frozen spec reference

- Spec file: `docs/EXPERIMENT_SPEC.md`
- Spec checksum: `docs/EXPERIMENT_SPEC.sha256`
- Machine coverage source of truth: `docs/EXPERIMENT_COVERAGE.json`

## Summary (current)

- Total required items: **19** (`Exp1..Exp16`, `G1..G3`)
- Complete: **15**
- Partial: **4** (`Exp13..Exp16` implemented via surrogate train/probe path)
- Missing: **0**

## Machine-testable contract additions

Each coverage item now includes:

- `required_outputs.run_level`
  - `outputs/runs/<run>/config.json`
  - `outputs/runs/<run>/metrics.csv`
  - `outputs/runs/<run>/summary.json`
- `required_outputs.analysis_common`
  - `analysis/tables/table_all_runs.csv`
  - `analysis/tables/table_experiment_summary.csv`
  - `analysis/results_summary.md`
  - `analysis/artifact_manifest.json`
- `required_outputs.analysis_specific_any_of`
  - experiment-specific figure artifact(s), with PNG/CSV fallback where applicable.
- `validator_checks`
  - references to validation scripts + `make release-check` and status-summary experiment-id presence.

## Interpretation note for partial items

`Exp13..Exp16` are runnable and emitted via current surrogate train/probe implementation, but remain marked partial relative to full tiny-transformer training fidelity.
