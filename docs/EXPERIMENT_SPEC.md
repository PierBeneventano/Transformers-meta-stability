# Frozen Experiment Spec (I1)

This file is the immutable experiment-spec anchor used by the coverage matrix.

Source basis:
- `Transformers.tex` experiment section supplied by user context in this session
- Additional controls proposed and accepted: `G1`, `G2`, `G3`

Canonical required IDs:
- `Exp1` ... `Exp16`
- `G1`, `G2`, `G3`

## Canonical list

1. Exp1 — visualization of discrete metastability
2. Exp2 — escape-depth scaling
3. Exp3 — entrance-depth scaling
4. Exp4 — propagation of smallness barrier test
5. Exp5 — energetic theorem vs direct theorem
6. Exp6 — raw budget vs contraction budget (`S_K` vs `C_K`)
7. Exp7 — optimal constant step near `h=1`
8. Exp8 — two-phase schedules
9. Exp9 — deformed query-key geometry
10. Exp10 — value-output contraction vs shear/rotation
11. Exp11 — mask ablations
12. Exp12 — normalization ablations (none/spherical/LayerNorm/RMSNorm)
13. Exp13 — trained tiny-transformer clustered task probe
14. Exp14 — residual-scale depth-efficiency tradeoff (trained models)
15. Exp15 — attention sinks and perturbation controls
16. Exp16 — skip/gating ablation
17. G1 — random/non-separated baseline
18. G2 — initialization spread sensitivity
19. G3 — finite-size `n` effects

## Contract notes

- Coverage decisions must reference this file + checksum.
- Any change to experiment definitions requires updating this file and re-running I1 coverage generation.
