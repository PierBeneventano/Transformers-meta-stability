#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


def stable_rank(x: np.ndarray) -> float:
    s = np.linalg.svd(x, compute_uv=False)
    if np.max(s) <= 1e-12:
        return 0.0
    return float((s**2).sum() / (np.max(s) ** 2))


def pairwise_diam2(x: np.ndarray) -> float:
    x = x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12, None)
    sims = x @ x.T
    return float(np.max(2.0 * (1.0 - sims)))


def first_with_hold(mask: np.ndarray, hold: int) -> int | None:
    c = 0
    for i, v in enumerate(mask):
        c = c + 1 if bool(v) else 0
        if c >= hold:
            return i - hold + 1
    return None


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
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--steps", type=int, default=240)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--d", type=int, default=8)
    ap.add_argument("--m", type=int, default=3)
    ap.add_argument("--epsilon", type=float, default=0.05)
    ap.add_argument("--lambda-val", type=float, default=0.6)
    ap.add_argument("--w-hold", type=int, default=3)
    ap.add_argument("--beta", type=float, default=8.0)
    ap.add_argument("--h", type=float, default=0.5)
    ap.add_argument("--schedule", type=str, default="const")
    ap.add_argument("--residual-mode", choices=["standard", "scalar", "gated"], default="standard")
    ap.add_argument("--residual-scale", type=float, default=1.0)
    ap.add_argument("--sink-mode", choices=["on", "off"], default="off")
    ap.add_argument("--seq-len", type=int, default=24)
    ap.add_argument("--batch-size", type=int, default=24)
    ap.add_argument("--train-steps", type=int, default=120)
    ap.add_argument("--lr", type=float, default=2e-3)
    args, _unknown = ap.parse_known_args()

    try:
        import torch
        import torch.nn as nn
    except Exception as e:
        raise SystemExit(f"[train:FAIL] torch required for train_mode=full: {e}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cfg = vars(args).copy()
    cfg["out_dir"] = str(cfg["out_dir"])
    cfg["train_mode"] = "full"
    (args.out_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    vocab_size = max(32, args.m * 8)
    d_model = max(16, args.d * 4)
    nhead = 4 if d_model % 4 == 0 else 2
    ff_dim = d_model * 2
    n_layers = 2

    class TinyDecoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(vocab_size, d_model)
            layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=ff_dim,
                dropout=0.0,
                batch_first=True,
                activation="gelu",
            )
            self.blocks = nn.ModuleList([layer for _ in range(n_layers)])
            self.ln = nn.LayerNorm(d_model)
            self.out = nn.Linear(d_model, args.m)

        def forward_hidden(self, x):
            h = self.emb(x)
            hidden = [h]
            T = x.size(1)
            causal_mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
            for b in self.blocks:
                h = b(h, src_mask=causal_mask)
                hidden.append(h)
            h = self.ln(h)
            hidden.append(h)
            logits = self.out(h)
            return logits, hidden

        def forward(self, x):
            logits, _ = self.forward_hidden(x)
            return logits

    model = TinyDecoder().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    ce = nn.CrossEntropyLoss()

    def sample_batch(batch: int):
        groups = torch.randint(low=0, high=args.m, size=(batch, args.seq_len), device=device)
        base = groups + torch.randint(low=0, high=vocab_size // args.m, size=groups.shape, device=device) * args.m
        noise = torch.rand_like(base.float()) < args.epsilon
        random_tok = torch.randint(0, vocab_size, size=base.shape, device=device)
        x = torch.where(noise, random_tok, base).long()
        y = groups.long()
        return x, y

    for _ in range(args.train_steps):
        x, y = sample_batch(args.batch_size)
        logits = model(x)
        loss = ce(logits.reshape(-1, args.m), y.reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        x, y = sample_batch(args.batch_size)
        logits, hidden = model.forward_hidden(x)
        pred = logits.argmax(dim=-1)
        probe_acc = float((pred == y).float().mean().item())
        probe_loss = float(ce(logits.reshape(-1, args.m), y.reshape(-1)).item())

    rows = []
    for layer_idx, h in enumerate(hidden):
        arr = h.detach().cpu().numpy().reshape(-1, h.shape[-1])
        diam2 = pairwise_diam2(arr)
        rank = stable_rank(arr)
        rho = 1.0 - 0.5 * diam2
        eta = float(np.clip(rho, -1.0, 1.0))
        escaped = int(eta < 1.0 - 2.0 * args.epsilon)
        rows.append(
            {
                "step": layer_idx,
                "eta_min": eta,
                "rho_min": rho,
                "diam2_max": diam2,
                "min_inter_gap": float(1.0 - rho),
                "escaped": escaped,
                "rank_proxy": rank,
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(args.out_dir / "metrics.csv", index=False)

    thr = 2.0 * np.exp(-args.lambda_val * args.beta)
    ent_mask = df["diam2_max"].to_numpy() <= thr
    esc_mask = df["escaped"].to_numpy().astype(bool)
    k_ent = first_with_hold(ent_mask, args.w_hold)
    k_esc = first_with_hold(esc_mask, args.w_hold)
    l_meta = None
    if k_ent is not None:
        end = k_esc if k_esc is not None else int(df["step"].iloc[-1])
        l_meta = int(max(0, end - k_ent))

    summary = Summary(
        run_name=args.run_name,
        experiment_id=args.experiment_id,
        model="tiny_transformer",
        beta=args.beta,
        h=args.h,
        schedule=args.schedule,
        n=args.n,
        d=args.d,
        m=args.m,
        epsilon=args.epsilon,
        lambda_val=args.lambda_val,
        seed=args.seed,
        alpha_est=0.0,
        steps=int(df["step"].iloc[-1]),
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
    print(f"[done] {args.run_name} [full-fidelity tiny transformer]")


if __name__ == "__main__":
    main()
