# Experiments Explained from the Paper

This document explains, in human-readable but technically precise terms, what `Exp1..Exp16` and `G1..G3` are trying to validate in the discrete-time metastability program.

Primary references:
- `Slow Motions of Gradient-Based Optimization Algorithms` (attached PDF)
- `Transformers` manuscript (attached LaTeX)
- frozen experiment contract in `docs/EXPERIMENT_SPEC.md`

---

## 1) Core idea of the paper (why this experiment suite exists)

The paper proves a **discrete-time metastability mechanism**:

1. Iterates quickly approach a low-dimensional slow set/manifold (`N`) because there is strong descent in directions transverse to it (PL-type control).
2. Once near `N`, motion becomes slow because the objective restricted to `N` varies weakly (small Lipschitz constant `δ`).
3. In self-attention dynamics, this appears as: tokens become tightly clustered **within** initial groups for a long depth range before eventual full collapse.

So the experiments are not generic benchmarks: they are stress tests for this specific two-phase geometry
(**fast entrance** + **slow drift/late escape**).

---

## 2) Transformer-specific quantities from the paper

In the discrete transformer analysis, the key objects are:

- `K_esc`: first depth where any token leaves its original safety cap.
- `η_q^k`: worst in-cap alignment with cluster center `w_q` at depth `k`.
- `ρ_q^k`: worst pairwise similarity inside cluster `q` at depth `k`.
- `K1#`: entrance depth into a tight metastable tube.
- `K2#`: lower bound on escape depth (typically much larger).
- `h`: residual step size (depth/time conversion in discrete layers).
- `β`: attention temperature/sharpness parameter.

The direct theorem gives (informally):
- tokens remain in caps up to at least `K2#`;
- after depth `K1#`, in-cluster pairwise distance stays exponentially small;
- metastable window length is approximately controlled by `K2# - K1#`, with explicit `h` dependence.

---

## 3) How to read the experiment IDs

Each experiment isolates one structural claim from the theorem stack.

### Exp1 — visualization of discrete metastability
- **Question:** Do we see a two-phase depth profile (quick entrance, long plateau)?
- **What to inspect:** endpoint maps and trajectories vs depth.
- **Paper link:** qualitative theorem picture (`K1#` entrance then metastable window).

### Exp2 — escape-depth scaling
- **Question:** Does escape depth increase as theory predicts in low-temperature/separated regimes?
- **What to inspect:** scaling of estimated `K_esc` vs control parameters (especially `β`, separation).
- **Paper link:** escape-depth lower bound and `K2#` scaling.

### Exp3 — entrance-depth scaling
- **Question:** Is the onset of tight clustering early and predictable?
- **What to inspect:** depth to hit high in-cluster similarity threshold (proxy for `K1#`).
- **Paper link:** entrance proposition (`K1#`) and its parameter dependence.

### Exp4 — propagation of smallness barrier test
- **Question:** Once contraction starts, does it propagate stably across layers?
- **What to inspect:** monotonicity/stability of in-cluster contraction proxies after entrance.
- **Paper link:** propagation lemma used after first hit of tight regime.

### Exp5 — energetic theorem vs direct theorem
- **Question:** Do both proof viewpoints describe the same metastable window in practice?
- **What to inspect:** consistency between energy-based and direct discrete proxies.
- **Paper link:** abstract slow-manifold theorem vs direct discrete transformer theorem.

### Exp6 — raw budget vs contraction budget (`S_K` vs `C_K`)
- **Question:** Which cumulative quantity better predicts metastable persistence?
- **What to inspect:** correlation of plateau length with raw accumulation vs effective contraction accumulation.
- **Paper link:** discrete-time budget accounting in theorem inequalities.

### Exp7 — optimal constant step near `h=1`
- **Question:** Is there a practical step-size regime maximizing useful depth before instability?
- **What to inspect:** stability/plateau tradeoff as constant residual step varies.
- **Paper link:** explicit `h` dependence of `K1#`, `K2#`, and window width.

### Exp8 — two-phase schedules
- **Question:** Can schedule design improve entrance + preservation jointly?
- **What to inspect:** early fast contraction with later gentle drift under piecewise schedules.
- **Paper link:** theorem allows general step sequence effects; tests constructive schedule design.

### Exp9 — deformed query-key geometry
- **Question:** Does metastability survive non-ideal geometry?
- **What to inspect:** robustness of entrance/plateau metrics under geometric deformation.
- **Paper link:** conjectural extension to deformed QK geometry in manuscript discussion.

### Exp10 — value-output contraction vs shear/rotation
- **Question:** Are contractions the true driver, versus neutral geometric transforms?
- **What to inspect:** metastability metrics under controlled contraction vs shear/rotation perturbations.
- **Paper link:** separates theorem-relevant contraction mechanism from confounders.

### Exp11 — mask ablations
- **Question:** How much does masking contribute to the metastable mechanism?
- **What to inspect:** change in entrance/escape proxies with mask removed or altered.
- **Paper link:** sensitivity of effective interaction graph and induced coefficient bounds.

### Exp12 — normalization ablations (none/spherical/LayerNorm/RMSNorm)
- **Question:** Which normalization preserves the geometric assumptions best?
- **What to inspect:** regime where cap separation and in-cap contraction remain valid longest.
- **Paper link:** assumptions depend on controlled norms/similarities; normalization alters these invariants.

### Exp13 — trained tiny-transformer clustered task probe
- **Question:** Do theorem-style signatures remain visible after training on a real task?
- **What to inspect:** same metastability observables on learned representations.
- **Paper link:** bridge from stylized dynamics to finite-depth practical transformers.

### Exp14 — residual-scale depth-efficiency tradeoff (trained models)
- **Question:** In trained systems, how does residual scaling trade quality vs metastable depth window?
- **What to inspect:** performance metrics jointly with `K1#`/`K2#` proxies.
- **Paper link:** practical manifestation of depth scaling with residual step.

### Exp15 — attention sinks and perturbation controls
- **Question:** Can sink dynamics prematurely break metastability, and can interventions delay it?
- **What to inspect:** sink indicators, collapse acceleration, and control efficacy.
- **Paper link:** late-phase destabilization/escape mechanisms beyond entrance phase.

### Exp16 — skip/gating ablation
- **Question:** Are skip/gating mechanisms necessary to realize a useful metastable window?
- **What to inspect:** window shrinkage/expansion when skip/gate are altered.
- **Paper link:** effective discrete step geometry and contraction budget modulation.

### G1 — random/non-separated baseline
- **Question:** Does metastability disappear when separation assumptions are broken?
- **Expected:** weak or absent clean entrance/plateau behavior.
- **Paper link:** violates separated initialization geometry.

### G2 — initialization spread sensitivity
- **Question:** How sensitive is metastability to initial spread around cluster centers?
- **Expected:** window degrades as spread grows past theorem-friendly range.
- **Paper link:** enters directly via cap parameters (e.g., `ε`, effective `α`).

### G3 — finite-size `n` effects
- **Question:** Are finite-width/token-count corrections significant at practical scales?
- **Expected:** asymptotic predictions hold with finite-size deviations.
- **Paper link:** many bounds include explicit factors in `n`.

---

## 4) Practical interpretation of endpoint plots

The endpoint plots in `analysis/figs/rendered/*_endpoints.png` are best read as a **phase portrait of theorem validity**:

- regions where trajectories remain clustered and stable correspond to the metastable tube;
- boundaries where trajectories rapidly de-cluster correspond to escape-threshold crossing;
- smooth scaling trends across Exp2/Exp3 indicate the predicted separation of timescales (`K1# << K2#`).

So these figures are not just visual diagnostics: they empirically map where theorem assumptions are approximately true in finite depth.

---

## 5) What counts as strong empirical support

A strong validation pattern is:

1. **Early entrance:** fast approach to high in-cluster similarity (small pairwise distances).
2. **Long plateau:** extended depth interval with stable in-cap clustering.
3. **Late escape:** eventual breakdown only at much larger depth.
4. **Correct parameter trends:** larger separation / lower effective cross-cluster interaction -> longer plateau.
5. **Control failure modes:** G1/G2/G3 degrade exactly where assumptions are intentionally broken.

If all five appear, the experiment suite is behaving as a faithful finite-depth empirical counterpart of the discrete metastability theory.

---

## 6) Scope note

This document explains the experiments at the level of theorem mechanism and observable interpretation. It does not replace the formal proofs in the manuscript; rather, it provides a practical map from equations/assumptions to plots and run outputs.
