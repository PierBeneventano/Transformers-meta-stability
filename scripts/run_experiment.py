#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


def normalize(v: np.ndarray, axis: int = -1, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.clip(n, eps, None)


def layernorm(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    m = x.mean(axis=-1, keepdims=True)
    v = ((x - m) ** 2).mean(axis=-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps)


def rmsnorm(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    v = (x**2).mean(axis=-1, keepdims=True)
    return x / np.sqrt(v + eps)


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    z = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=axis, keepdims=True)


def random_unit(rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
    return normalize(rng.normal(size=shape))


def init_points(
    rng: np.random.Generator,
    n: int,
    d: int,
    m: int,
    epsilon: float,
    init_mode: str = "separated",
    alpha_target: float | None = None,
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], np.ndarray, float]:
    if init_mode == "random":
        centers = random_unit(rng, (m, d))
        block_ids = np.arange(n) % m
        X = random_unit(rng, (n, d))
    else:
        centers = random_unit(rng, (m, d))
        if alpha_target is not None:
            for _ in range(200):
                cand = random_unit(rng, (m, d))
                alpha = max(float(np.dot(cand[i], cand[j])) for i in range(m) for j in range(m) if i != j)
                if alpha <= alpha_target:
                    centers = cand
                    break
        block_ids = np.arange(n) % m
        X = np.zeros((n, d))
        for q in range(m):
            idx = np.where(block_ids == q)[0]
            noise = random_unit(rng, (len(idx), d))
            X[idx] = normalize((1.0 - epsilon) * centers[q] + epsilon * noise)

    blocks = [np.where(block_ids == q)[0] for q in range(m)]
    alpha_est = max(float(np.dot(centers[i], centers[j])) for i in range(m) for j in range(m) if i != j)
    return X, centers, blocks, block_ids, alpha_est


def make_mask(n: int, mask_kind: str, window: int = 8) -> np.ndarray:
    M = np.ones((n, n), dtype=bool)
    if mask_kind == "causal":
        M = np.tril(np.ones((n, n), dtype=bool))
    elif mask_kind == "window":
        M = np.zeros((n, n), dtype=bool)
        for i in range(n):
            lo, hi = max(0, i - window), min(n, i + window + 1)
            M[i, lo:hi] = True
    elif mask_kind == "block_sparse_center":
        M = np.zeros((n, n), dtype=bool)
        center = 0
        for i in range(n):
            M[i, i] = True
            M[i, center] = True
            M[center, i] = True
    return M


def make_transforms(d: int, geometry: str, g_scale: float, value_map: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    WQ = np.eye(d)
    WK = np.eye(d)
    if geometry == "gmetric":
        G = np.eye(d)
        G[0, 0] = g_scale
        G[1, 1] = max(1.0, g_scale / 2.0)
        WQ = np.linalg.cholesky(G)
        WK = np.linalg.cholesky(G)

    R = np.eye(d)
    if value_map == "contractive":
        R = 0.8 * np.eye(d)
    elif value_map == "shear":
        R = np.eye(d)
        if d >= 2:
            R[0, 1] = 0.35
    elif value_map == "rotation":
        R = np.eye(d)
        if d >= 2:
            th = np.pi / 10
            R[:2, :2] = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    return WQ, WK, R


def apply_norm(x: np.ndarray, kind: str) -> np.ndarray:
    if kind == "none":
        return x
    if kind == "layernorm":
        return layernorm(x)
    if kind == "rmsnorm":
        return rmsnorm(x)
    return normalize(x)


def make_schedule(schedule: str, steps: int, h: float, h_fast: float, h_slow: float, switch_step: int) -> np.ndarray:
    if schedule in {"const", "const_small", "const_moderate", "const_large", "matched_S", "matched_C"}:
        if schedule == "const_small":
            h = 0.2
        elif schedule == "const_moderate":
            h = 0.8
        elif schedule == "const_large":
            h = 1.6
        elif schedule == "matched_S":
            h = 0.7
        elif schedule == "matched_C":
            h = 0.4
        return np.full(steps, h, dtype=float)
    if schedule == "two_phase":
        hs = np.full(steps, h_slow, dtype=float)
        hs[: max(1, min(steps, switch_step))] = h_fast
        return hs
    return np.full(steps, h, dtype=float)


def first_with_hold(mask: np.ndarray, hold: int) -> int | None:
    c = 0
    for i, v in enumerate(mask):
        c = c + 1 if bool(v) else 0
        if c >= hold:
            return i - hold + 1
    return None


def train_linear_probe(features: np.ndarray, labels: np.ndarray, epochs: int = 40, lr: float = 0.2) -> tuple[float, float]:
    n, d = features.shape
    m = int(labels.max()) + 1
    W = np.zeros((d, m))
    Y = np.eye(m)[labels]
    for _ in range(epochs):
        logits = features @ W
        probs = softmax(logits, axis=1)
        grad = features.T @ (probs - Y) / n
        W -= lr * grad
    logits = features @ W
    probs = softmax(logits, axis=1)
    loss = float(-np.mean(np.log(np.clip(probs[np.arange(n), labels], 1e-12, None))))
    acc = float((np.argmax(probs, axis=1) == labels).mean())
    return loss, acc


def stable_rank(x: np.ndarray) -> float:
    s = np.linalg.svd(x, compute_uv=False)
    if np.max(s) <= 1e-12:
        return 0.0
    return float((s**2).sum() / (np.max(s) ** 2))


@dataclass
class Summary:
    run_name: str
    experiment_id: str
    model: str
    beta: float
    h: float
    schedule: str
    n: int
    d: int
    m: int
    epsilon: float
    lambda_val: float
    seed: int
    alpha_est: float
    steps: int
    k_ent_emp: int | None
    k_esc_emp: int | None
    l_meta_emp: int | None
    final_eta_min: float
    final_rho_min: float
    final_diam2_max: float
    final_rank_proxy: float
    probe_loss: float | None
    probe_acc: float | None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--model", choices=["SA", "USA"], default="USA")
    ap.add_argument("--beta", type=float, default=8.0)
    ap.add_argument("--h", type=float, default=0.5)
    ap.add_argument("--schedule", default="const")
    ap.add_argument("--h-fast", type=float, default=1.0)
    ap.add_argument("--h-slow", type=float, default=0.1)
    ap.add_argument("--switch-step", type=int, default=40)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--d", type=int, default=8)
    ap.add_argument("--m", type=int, default=3)
    ap.add_argument("--epsilon", type=float, default=0.05)
    ap.add_argument("--lambda-val", type=float, default=0.6)
    ap.add_argument("--steps", type=int, default=240)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--w-hold", type=int, default=3)
    ap.add_argument("--init-mode", choices=["separated", "random"], default="separated")
    ap.add_argument("--alpha-target", type=float, default=None)
    ap.add_argument("--mask", choices=["full", "causal", "window", "block_sparse_center"], default="full")
    ap.add_argument("--window", type=int, default=8)
    ap.add_argument("--geometry", choices=["euclidean", "gmetric"], default="euclidean")
    ap.add_argument("--g-scale", type=float, default=1.0)
    ap.add_argument("--value-map", choices=["identity", "contractive", "shear", "rotation"], default="identity")
    ap.add_argument("--normalization", choices=["none", "spherical", "layernorm", "rmsnorm"], default="spherical")
    ap.add_argument("--barrier-regime", choices=["valid", "invalid"], default=None)
    ap.add_argument("--compare-mode", default=None)
    ap.add_argument("--train-mode", choices=["none", "surrogate"], default="none")
    ap.add_argument("--probe-depth", type=int, default=8)
    ap.add_argument("--residual-mode", choices=["standard", "scalar", "gated"], default="standard")
    ap.add_argument("--residual-scale", type=float, default=1.0)
    ap.add_argument("--sink-mode", choices=["on", "off"], default="off")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cfg = vars(args).copy()
    cfg["out_dir"] = str(cfg["out_dir"])
    (args.out_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    rng = np.random.default_rng(args.seed)
    X, centers, blocks, labels, alpha_est = init_points(
        rng, args.n, args.d, args.m, args.epsilon, args.init_mode, args.alpha_target
    )
    if args.barrier_regime == "invalid":
        X += 0.25 * rng.normal(size=X.shape)
        X = normalize(X)

    WQ, WK, R = make_transforms(args.d, args.geometry, args.g_scale, args.value_map)
    mask = make_mask(args.n, args.mask, args.window)
    hs = make_schedule(args.schedule, args.steps, args.h, args.h_fast, args.h_slow, args.switch_step)

    rows = []
    hidden_snap = None
    for k in range(args.steps + 1):
        # metrics
        eta_vals, rho_vals, diam2_vals = [], [], []
        escaped = 0
        for q, idx in enumerate(blocks):
            Xi = X[idx]
            dots_c = Xi @ centers[q]
            eta = float(np.min(dots_c))
            eta_vals.append(eta)
            if eta < 1.0 - 2.0 * args.epsilon:
                escaped = 1
            S = Xi @ Xi.T
            rho_vals.append(float(np.min(S)))
            diam2_vals.append(float(np.max(2.0 * (1.0 - S))))

        inter = []
        for i, idx_i in enumerate(blocks):
            for j, idx_j in enumerate(blocks):
                if j <= i:
                    continue
                inter.append(float(np.min(1.0 - (X[idx_i] @ X[idx_j].T))))
        min_inter_gap = float(min(inter)) if inter else float("nan")

        rows.append(
            {
                "step": k,
                "eta_min": float(min(eta_vals)),
                "rho_min": float(min(rho_vals)),
                "diam2_max": float(max(diam2_vals)),
                "min_inter_gap": min_inter_gap,
                "escaped": int(escaped),
                "rank_proxy": stable_rank(X),
            }
        )

        if k == min(args.probe_depth, args.steps):
            hidden_snap = X.copy()

        if k == args.steps:
            break

        # attention update
        XQ = X @ WQ
        XK = X @ WK
        S = XQ @ XK.T
        if args.sink_mode == "on":
            S[:, 0] += 0.3
        if args.mask != "full":
            S_masked = S.copy()
            S_masked[~mask] = -1e9
            S = S_masked

        if args.model == "SA":
            A = softmax(args.beta * S, axis=1)
        else:
            A = np.exp(args.beta * (S - np.max(S, axis=1, keepdims=True)))
            A *= mask.astype(float)
            A /= np.clip(A.sum(axis=1, keepdims=True), 1e-12, None)

        mixed = A @ (X @ R)
        h_k = hs[k]

        gate = 1.0
        if args.residual_mode == "scalar":
            gate = args.residual_scale
        elif args.residual_mode == "gated":
            t = (k + 1) / max(1, args.steps)
            gate = 1.0 / (1.0 + np.exp(-args.residual_scale * (t - 0.5)))

        X = X + gate * h_k * mixed
        X = apply_norm(X, args.normalization)

    df = pd.DataFrame(rows)
    df.to_csv(args.out_dir / "metrics.csv", index=False)

    thr = 2.0 * np.exp(-args.lambda_val * args.beta)
    ent_mask = df["diam2_max"].to_numpy() <= thr
    esc_mask = df["escaped"].to_numpy().astype(bool)

    k_ent = first_with_hold(ent_mask, args.w_hold)
    k_esc = first_with_hold(esc_mask, args.w_hold)
    l_meta = None
    if k_ent is not None:
        end = k_esc if k_esc is not None else args.steps
        l_meta = int(max(0, end - k_ent))

    probe_loss = None
    probe_acc = None
    if args.train_mode == "surrogate":
        feats = hidden_snap if hidden_snap is not None else X
        probe_loss, probe_acc = train_linear_probe(feats, labels)

    summary = Summary(
        run_name=args.run_name,
        experiment_id=args.experiment_id,
        model=args.model,
        beta=args.beta,
        h=args.h,
        schedule=args.schedule,
        n=args.n,
        d=args.d,
        m=args.m,
        epsilon=args.epsilon,
        lambda_val=args.lambda_val,
        seed=args.seed,
        alpha_est=alpha_est,
        steps=args.steps,
        k_ent_emp=k_ent,
        k_esc_emp=k_esc,
        l_meta_emp=l_meta,
        final_eta_min=float(df["eta_min"].iloc[-1]),
        final_rho_min=float(df["rho_min"].iloc[-1]),
        final_diam2_max=float(df["diam2_max"].iloc[-1]),
        final_rank_proxy=float(df["rank_proxy"].iloc[-1]),
        probe_loss=probe_loss,
        probe_acc=probe_acc,
    )

    (args.out_dir / "summary.json").write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    print(f"[done] {args.run_name}")


if __name__ == "__main__":
    main()
