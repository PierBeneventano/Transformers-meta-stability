#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None


def load_summaries(root: Path) -> pd.DataFrame:
    rows = []
    for p in root.glob("*/summary.json"):
        rows.append(json.loads(p.read_text()))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def load_metrics(root: Path, run_name: str) -> pd.DataFrame:
    p = root / run_name / "metrics.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()


def save_plot_or_data(fig_path: Path, x, y, title: str, xlabel: str, ylabel: str) -> str:
    if plt is None:
        data_path = fig_path.with_suffix(".csv")
        pd.DataFrame({"x": x, "y": y}).to_csv(data_path, index=False)
        txt = fig_path.with_suffix(".txt")
        txt.write_text(
            f"Plot backend unavailable (matplotlib missing).\n"
            f"title={title}\nxlabel={xlabel}\nylabel={ylabel}\n"
            f"data={data_path.name}\n",
            encoding="utf-8",
        )
        return data_path.name

    plt.figure(figsize=(5.2, 4))
    plt.scatter(x, y)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()
    return fig_path.name


def expected_h_from_schedule(schedule: str, default_h: float) -> float:
    if schedule == "const_small":
        return 0.2
    if schedule == "const_moderate":
        return 0.8
    if schedule == "const_large":
        return 1.6
    if schedule == "matched_S":
        return 0.7
    if schedule == "matched_C":
        return 0.4
    if schedule == "two_phase":
        return 0.55
    return float(default_h)


def write_theorem_specific_tables(df: pd.DataFrame, tabs: Path) -> list[str]:
    wrote = []

    # Exp4 barrier regime test
    e4 = df[df["experiment_id"] == "Exp4"].copy()
    if not e4.empty and "barrier_regime" in e4.columns:
        grp = e4.groupby("barrier_regime")["final_rho_min"].agg(["mean", "std", "count"]).reset_index()
        if set(grp["barrier_regime"].tolist()) >= {"valid", "invalid"}:
            v = float(grp.loc[grp["barrier_regime"] == "valid", "mean"].iloc[0])
            iv = float(grp.loc[grp["barrier_regime"] == "invalid", "mean"].iloc[0])
            verdict = "pass" if v > iv else "fail"
        else:
            verdict = "inconclusive"
        grp["verdict"] = verdict
        out = tabs / "exp4_barrier_test.csv"
        grp.to_csv(out, index=False)
        wrote.append(out.name)

    # Exp5 energetic vs direct proxy table
    e5 = df[df["experiment_id"] == "Exp5"].copy()
    if not e5.empty:
        e5 = e5.assign(
            energetic_window_proxy=(e5["steps"] - e5["k_ent_emp"].fillna(e5["steps"])).clip(lower=0),
            direct_window_proxy=e5["l_meta_emp"].fillna(0),
        )
        e5["window_gain_ratio"] = (e5["direct_window_proxy"] + 1.0) / (e5["energetic_window_proxy"] + 1.0)
        cols = ["run_name", "energetic_window_proxy", "direct_window_proxy", "window_gain_ratio"]
        out = tabs / "exp5_theorem_window_proxies.csv"
        e5[cols].to_csv(out, index=False)
        wrote.append(out.name)

    # Exp6 budget role correlation check
    e6 = df[df["experiment_id"] == "Exp6"].copy()
    if not e6.empty:
        e6["h_eff"] = [expected_h_from_schedule(s, h) for s, h in zip(e6["schedule"], e6["h"])]
        e6["S_budget"] = e6["steps"] * e6["h_eff"]
        e6["C_budget"] = e6["steps"] * e6["h_eff"] / ((1.0 + e6["h_eff"]) ** 2)

        def corr_safe(a: pd.Series, b: pd.Series) -> float:
            if len(a.dropna()) < 2 or len(b.dropna()) < 2:
                return float("nan")
            return float(a.corr(b))

        out_df = pd.DataFrame(
            [
                {
                    "corr_kesc_S": corr_safe(e6["k_esc_emp"], e6["S_budget"]),
                    "corr_kesc_C": corr_safe(e6["k_esc_emp"], e6["C_budget"]),
                    "corr_kent_S": corr_safe(e6["k_ent_emp"], e6["S_budget"]),
                    "corr_kent_C": corr_safe(e6["k_ent_emp"], e6["C_budget"]),
                }
            ]
        )
        out = tabs / "exp6_budget_role_correlations.csv"
        out_df.to_csv(out, index=False)
        wrote.append(out.name)

    # Stage-A/Stage-B tracking for Exp13-16
    e1316 = df[df["experiment_id"].isin(["Exp13", "Exp14", "Exp15", "Exp16"])].copy()
    if not e1316.empty:
        if "train_mode" not in e1316.columns:
            e1316["train_mode"] = "none"
        tier = (
            e1316.groupby(["experiment_id", "train_mode"])
            .size()
            .reset_index(name="n_runs")
            .sort_values(["experiment_id", "train_mode"])
        )
        out = tabs / "exp13_16_fidelity_tier_coverage.csv"
        tier.to_csv(out, index=False)
        wrote.append(out.name)

    return wrote


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("outputs/runs"))
    ap.add_argument("--out-dir", type=Path, default=Path("analysis"))
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    figs = args.out_dir / "figs"
    tabs = args.out_dir / "tables"
    figs.mkdir(exist_ok=True)
    tabs.mkdir(exist_ok=True)

    df = load_summaries(args.root)
    if df.empty:
        raise SystemExit("No summaries found")

    df = df.sort_values(["experiment_id", "run_name"]).reset_index(drop=True)
    df.to_csv(tabs / "table_all_runs.csv", index=False)

    summary_cols = [
        "k_ent_emp",
        "k_esc_emp",
        "l_meta_emp",
        "final_diam2_max",
        "final_rho_min",
        "final_eta_min",
        "final_rank_proxy",
        "probe_loss",
        "probe_acc",
    ]
    grouped = df.groupby("experiment_id")[summary_cols].mean(numeric_only=True).reset_index()
    grouped.to_csv(tabs / "table_experiment_summary.csv", index=False)

    figure_outputs = []

    exp1_runs = df[df["experiment_id"] == "Exp1"]
    if not exp1_runs.empty:
        m = load_metrics(args.root, exp1_runs.iloc[0]["run_name"])
        if not m.empty:
            m[["step", "diam2_max", "min_inter_gap", "escaped"]].to_csv(
                figs / "fig_exp1_metastability_panels.csv", index=False
            )
            (figs / "fig_exp1_metastability_panels.txt").write_text(
                "Saved panel source data: step,diam2_max,min_inter_gap,escaped\n",
                encoding="utf-8",
            )
            figure_outputs.append("fig_exp1_metastability_panels.csv")

    e2 = df[(df["experiment_id"] == "Exp2") & df["k_esc_emp"].notna()]
    if not e2.empty:
        x = (1.0 - e2["alpha_est"]) * e2["beta"] - np.log(e2["h"])
        y = np.log(e2["k_esc_emp"].astype(float))
        name = save_plot_or_data(
            figs / "fig_exp2_escape_scaling.png",
            x,
            y,
            "Exp2 escape scaling",
            "(1-alpha)beta-log h",
            "log K_esc",
        )
        figure_outputs.append(name)

    e3 = df[(df["experiment_id"] == "Exp3") & df["k_ent_emp"].notna()]
    if not e3.empty:
        x = np.exp(8.0 * e3["epsilon"] * e3["beta"])
        y = e3["k_ent_emp"].astype(float) * e3["h"]
        name = save_plot_or_data(
            figs / "fig_exp3_entrance_scaling.png",
            x,
            y,
            "Exp3 entrance scaling",
            "exp(8epsilon beta)",
            "K_ent*h",
        )
        figure_outputs.append(name)

    for exp_id, g in df.groupby("experiment_id"):
        d = pd.DataFrame({"K_ent_emp": g["k_ent_emp"], "K_esc_emp": g["k_esc_emp"]})
        d.to_csv(figs / f"fig_{exp_id}_endpoints.csv", index=False)
        figure_outputs.append(f"fig_{exp_id}_endpoints.csv")

    theorem_tables = write_theorem_specific_tables(df, tabs)

    report = {
        "n_runs": int(len(df)),
        "n_experiments": int(df["experiment_id"].nunique()),
        "plot_backend": "matplotlib" if plt is not None else "csv-fallback",
        "figures": sorted(figure_outputs),
        "tables": sorted([p.name for p in tabs.glob("*.csv")]),
        "theorem_specific_tables": sorted(theorem_tables),
    }
    (args.out_dir / "results_summary.md").write_text(
        "# Transformer Experiments Summary\n\n"
        f"- Runs analyzed: **{report['n_runs']}**\n"
        f"- Experiments represented: **{report['n_experiments']}**\n"
        f"- Plot backend: **{report['plot_backend']}**\n\n"
        "## Tables\n"
        + "\n".join(f"- {x}" for x in report["tables"])
        + "\n\n## Figures\n"
        + "\n".join(f"- {x}" for x in report["figures"])
        + "\n\n## Theorem-specific checks\n"
        + "\n".join(f"- {x}" for x in report["theorem_specific_tables"])
        + "\n",
        encoding="utf-8",
    )

    (args.out_dir / "artifact_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[analysis] wrote {tabs}")
    print(f"[analysis] wrote {figs}")


if __name__ == "__main__":
    main()
