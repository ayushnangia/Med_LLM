"""Generate inter-rater agreement figures and statistics for Hendrik vs Radu.

Reads data/paired_reviews.csv (60 paired reviews across 10 NCC cases x 6 baseline models)
and emits PNG figures into figures/ plus JSON stats into data/stats.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.metrics import cohen_kappa_score, confusion_matrix

HERE = Path(__file__).parent
DATA = HERE / "data"
FIGS = HERE / "figures"
FIGS.mkdir(exist_ok=True)

# Consistent palette
H_COLOR = "#1f77b4"   # Hendrik — blue
R_COLOR = "#ff7f0e"   # Radu    — orange
AGREE = "#2ca02c"
DISAGREE = "#d62728"

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 160
plt.rcParams["savefig.bbox"] = "tight"

MODEL_SHORT = {
    "google/medgemma-27b-text-it": "MedGemma 27B",
    "google/gemma-3-27b-it": "Gemma-3 27B",
    "google/gemma-3-4b-it": "Gemma-3 4B",
    "allenai/Olmo-3.1-32B-Instruct": "Olmo-3.1 32B Inst",
    "allenai/Olmo-3.1-32B-Think": "Olmo-3.1 32B Think",
    "OpenMeditron/Meditron3-Qwen2.5-7B": "Meditron3 7B",
}


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA / "paired_reviews.csv")
    df["model_short"] = df["model_id"].map(MODEL_SHORT)
    df["agree"] = df["h_accept"] == df["r_accept"]
    return df


# ── stats ────────────────────────────────────────────────────────────────────

def compute_stats(df: pd.DataFrame) -> dict:
    s: dict = {"n_paired": len(df)}

    # Acceptable agreement
    s["acceptable"] = {
        "hendrik_yes": int(df["h_accept"].sum()),
        "radu_yes": int(df["r_accept"].sum()),
        "agreements": int(df["agree"].sum()),
        "disagreements": int((~df["agree"]).sum()),
        "raw_agreement_pct": round(100 * df["agree"].mean(), 1),
        "cohens_kappa": round(cohen_kappa_score(df["h_accept"], df["r_accept"]), 3),
    }
    # McNemar's test for systematic bias on acceptability
    b = int(((df["h_accept"]) & (~df["r_accept"])).sum())  # H yes, R no
    c = int(((~df["h_accept"]) & (df["r_accept"])).sum())  # H no, R yes
    if b + c > 0:
        mcnemar_stat = (abs(b - c) - 1) ** 2 / (b + c)
        s["acceptable"]["mcnemar_b_h_yes_r_no"] = b
        s["acceptable"]["mcnemar_c_h_no_r_yes"] = c
        s["acceptable"]["mcnemar_chi2"] = round(mcnemar_stat, 3)
        s["acceptable"]["mcnemar_p"] = round(1 - stats.chi2.cdf(mcnemar_stat, df=1), 4)

    # Correlations + Bland-Altman for each numeric metric
    for label, h, r in [
        ("quality (0-9)", "h_quality", "r_quality"),
        ("exact_match (0-100)", "h_exact", "r_exact"),
        ("patient_oriented (0-100)", "h_patient", "r_patient"),
    ]:
        x, y = df[h].to_numpy(), df[r].to_numpy()
        diff = x - y
        s[label] = {
            "hendrik_mean": round(float(x.mean()), 2),
            "radu_mean": round(float(y.mean()), 2),
            "mean_abs_diff": round(float(np.mean(np.abs(diff))), 2),
            "pearson_r": round(float(stats.pearsonr(x, y).statistic), 3),
            "spearman_r": round(float(stats.spearmanr(x, y).statistic), 3),
            "bland_altman_bias": round(float(diff.mean()), 2),
            "bland_altman_sd": round(float(diff.std(ddof=1)), 2),
            "bland_altman_loa_low": round(float(diff.mean() - 1.96 * diff.std(ddof=1)), 2),
            "bland_altman_loa_high": round(float(diff.mean() + 1.96 * diff.std(ddof=1)), 2),
        }

    return s


# ── figures ──────────────────────────────────────────────────────────────────

def fig_overall(df: pd.DataFrame, s: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    metrics = [
        ("Acceptable (% Yes)", df["h_accept"].mean() * 100, df["r_accept"].mean() * 100, "%"),
        ("Avg Quality (0-9)", df["h_quality"].mean(), df["r_quality"].mean(), ""),
        ("Avg Exact-Match (0-100)", df["h_exact"].mean(), df["r_exact"].mean(), ""),
    ]
    for ax, (title, hv, rv, unit) in zip(axes, metrics):
        bars = ax.bar(["Hendrik", "Radu"], [hv, rv], color=[H_COLOR, R_COLOR], width=0.55)
        ax.set_title(title, fontsize=14, pad=10)
        ax.set_ylim(0, max(hv, rv) * 1.25 if unit != "%" else 100)
        for bar, v in zip(bars, [hv, rv]):
            ax.text(bar.get_x() + bar.get_width() / 2, v + (max(hv, rv) * 0.03),
                    f"{v:.1f}{unit}", ha="center", fontsize=13, weight="bold")
        ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle(
        f"Overall Agreement on 60 Paired Reviews — Raw agreement {s['acceptable']['raw_agreement_pct']}%  ·  "
        f"Cohen's κ = {s['acceptable']['cohens_kappa']}",
        fontsize=14, y=1.05,
    )
    fig.savefig(FIGS / "01_overall_agreement.png")
    plt.close(fig)


def fig_per_model(df: pd.DataFrame) -> None:
    agg = df.groupby("model_short").agg(
        h_quality=("h_quality", "mean"),
        r_quality=("r_quality", "mean"),
        h_accept_pct=("h_accept", lambda s_: s_.mean() * 100),
        r_accept_pct=("r_accept", lambda s_: s_.mean() * 100),
    ).sort_values("h_quality", ascending=False).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    x = np.arange(len(agg))
    w = 0.38

    # Quality
    ax = axes[0]
    ax.bar(x - w / 2, agg["h_quality"], w, label="Hendrik", color=H_COLOR)
    ax.bar(x + w / 2, agg["r_quality"], w, label="Radu", color=R_COLOR)
    ax.set_xticks(x)
    ax.set_xticklabels(agg["model_short"], rotation=25, ha="right")
    ax.set_ylabel("Avg Quality (0-9)")
    ax.set_title("Quality Score by Model")
    ax.legend(frameon=False)
    ax.set_ylim(0, 9)
    ax.spines[["top", "right"]].set_visible(False)

    # Acceptable %
    ax = axes[1]
    ax.bar(x - w / 2, agg["h_accept_pct"], w, label="Hendrik", color=H_COLOR)
    ax.bar(x + w / 2, agg["r_accept_pct"], w, label="Radu", color=R_COLOR)
    ax.set_xticks(x)
    ax.set_xticklabels(agg["model_short"], rotation=25, ha="right")
    ax.set_ylabel("% Therapy Acceptable")
    ax.set_title("Acceptability by Model")
    ax.legend(frameon=False)
    ax.set_ylim(0, 110)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("Hendrik vs Radu — Per-Model Comparison (n=10 cases per model)", fontsize=14, y=1.02)
    fig.savefig(FIGS / "02_per_model_quality.png")
    plt.close(fig)


def fig_scatter(df: pd.DataFrame, s: dict) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))
    # Jitter slightly to avoid overlap on identical integer scores
    rng = np.random.default_rng(7)
    jx = df["h_quality"] + rng.uniform(-0.12, 0.12, len(df))
    jy = df["r_quality"] + rng.uniform(-0.12, 0.12, len(df))
    colors = [AGREE if a else DISAGREE for a in df["agree"]]
    ax.scatter(jx, jy, c=colors, alpha=0.7, s=90, edgecolor="white", linewidth=1.2)
    ax.plot([-0.3, 9.3], [-0.3, 9.3], "k--", alpha=0.4, label="Perfect agreement (y = x)")
    ax.set_xlim(-0.3, 9.3)
    ax.set_ylim(-0.3, 9.3)
    ax.set_xlabel("Hendrik — Quality Score")
    ax.set_ylabel("Radu — Quality Score")
    ax.set_title(
        f"Paired Quality Scores — Pearson r = {s['quality (0-9)']['pearson_r']}, "
        f"Spearman ρ = {s['quality (0-9)']['spearman_r']}"
    )
    # Legend
    from matplotlib.patches import Patch
    ax.legend(
        handles=[
            Patch(facecolor=AGREE, label="Acceptable: agree"),
            Patch(facecolor=DISAGREE, label="Acceptable: disagree"),
        ],
        loc="lower right", frameon=False,
    )
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(FIGS / "03_quality_scatter.png")
    plt.close(fig)


def fig_bland_altman(df: pd.DataFrame, s: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    mean = (df["h_quality"] + df["r_quality"]) / 2
    diff = df["h_quality"] - df["r_quality"]

    rng = np.random.default_rng(11)
    jx = mean + rng.uniform(-0.08, 0.08, len(df))
    jy = diff + rng.uniform(-0.08, 0.08, len(df))

    ax.scatter(jx, jy, c=H_COLOR, alpha=0.65, s=80, edgecolor="white", linewidth=1)

    bias = s["quality (0-9)"]["bland_altman_bias"]
    loa_lo = s["quality (0-9)"]["bland_altman_loa_low"]
    loa_hi = s["quality (0-9)"]["bland_altman_loa_high"]
    ax.axhline(bias, color="black", linewidth=2, label=f"Mean bias = {bias:+.2f}")
    ax.axhline(loa_hi, color="gray", linestyle="--", linewidth=1.5, label=f"+1.96 SD = {loa_hi:+.2f}")
    ax.axhline(loa_lo, color="gray", linestyle="--", linewidth=1.5, label=f"−1.96 SD = {loa_lo:+.2f}")
    ax.axhline(0, color="green", alpha=0.3, linewidth=1)

    ax.set_xlabel("Mean Quality Score — (Hendrik + Radu) / 2")
    ax.set_ylabel("Difference — Hendrik − Radu")
    ax.set_title("Bland–Altman: Systematic Bias on Quality Score")
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(FIGS / "04_bland_altman.png")
    plt.close(fig)


def fig_per_case(df: pd.DataFrame) -> None:
    agg = df.groupby("case_id").agg(
        h_quality=("h_quality", "mean"),
        r_quality=("r_quality", "mean"),
        agreements=("agree", "sum"),
    ).reset_index()
    # Natural sort by case number
    agg["sortkey"] = agg["case_id"].str.replace("ncc_", "").astype(int)
    agg = agg.sort_values("sortkey").drop(columns="sortkey")

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(agg))
    w = 0.38
    ax.bar(x - w / 2, agg["h_quality"], w, label="Hendrik", color=H_COLOR)
    ax.bar(x + w / 2, agg["r_quality"], w, label="Radu", color=R_COLOR)

    # Annotate agreement count above each pair
    ymax = max(agg["h_quality"].max(), agg["r_quality"].max())
    for i, row in agg.reset_index(drop=True).iterrows():
        ax.text(i, ymax + 0.4, f"{int(row['agreements'])}/6",
                ha="center", fontsize=11,
                color=AGREE if row["agreements"] >= 5 else DISAGREE,
                weight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(agg["case_id"], rotation=0)
    ax.set_ylabel("Avg Quality (0-9, across 6 models)")
    ax.set_ylim(0, ymax + 1.2)
    ax.set_title("Per-Case Quality + Acceptability Agreement Count (out of 6 models)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(FIGS / "05_per_case_quality.png")
    plt.close(fig)


def fig_heatmap(df: pd.DataFrame) -> None:
    # Encode: +1 = both yes, -1 = both no, 0.5 = H yes only, -0.5 = R yes only
    def encode(row):
        if row["h_accept"] and row["r_accept"]:
            return 2  # both yes — strong green
        if (not row["h_accept"]) and (not row["r_accept"]):
            return 1  # both no — light green
        if row["h_accept"] and not row["r_accept"]:
            return -1  # H yes / R no
        return -2  # R yes / H no

    df = df.copy()
    df["code"] = df.apply(encode, axis=1)

    # natural-sort cases by numeric suffix
    case_order = sorted(df["case_id"].unique(), key=lambda c: int(c.split("_")[1]))
    model_order = list(MODEL_SHORT.values())

    pivot = df.pivot_table(index="case_id", columns="model_short", values="code", aggfunc="first")
    pivot = pivot.reindex(index=case_order, columns=model_order)

    fig, ax = plt.subplots(figsize=(12, 7))
    # Custom colormap
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap([
        "#67000d",  # -2 R yes only (deep red)
        "#fc9272",  # -1 H yes only (light red)
        "#c7e9c0",  # +1 both no (light green)
        "#41ab5d",  # +2 both yes (strong green)
    ])
    sns.heatmap(pivot, cmap=cmap, vmin=-2, vmax=2, center=0,
                cbar=False, linewidths=1, linecolor="white",
                annot=False, ax=ax)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Acceptability Agreement Grid — Case × Model")

    # Manual legend
    from matplotlib.patches import Patch
    handles = [
        Patch(color="#41ab5d", label="Both Yes (agree)"),
        Patch(color="#c7e9c0", label="Both No (agree)"),
        Patch(color="#fc9272", label="Hendrik Yes / Radu No"),
        Patch(color="#67000d", label="Radu Yes / Hendrik No"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.15),
              ncol=2, frameon=False)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    fig.savefig(FIGS / "06_acceptability_heatmap.png")
    plt.close(fig)


def fig_confusion(df: pd.DataFrame, s: dict) -> None:
    cm = confusion_matrix(df["h_accept"], df["r_accept"], labels=[True, False])
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Radu: Yes", "Radu: No"],
                yticklabels=["Hendrik: Yes", "Hendrik: No"],
                annot_kws={"size": 22, "weight": "bold"}, ax=ax)
    ax.set_title(
        f"Confusion Matrix — Therapy Acceptable\n"
        f"Cohen's κ = {s['acceptable']['cohens_kappa']}  ·  "
        f"raw agreement = {s['acceptable']['raw_agreement_pct']}%"
    )
    fig.savefig(FIGS / "07_confusion_matrix.png")
    plt.close(fig)


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    df = load()
    s = compute_stats(df)
    (DATA / "stats.json").write_text(json.dumps(s, indent=2))

    fig_overall(df, s)
    fig_per_model(df)
    fig_scatter(df, s)
    fig_bland_altman(df, s)
    fig_per_case(df)
    fig_heatmap(df)
    fig_confusion(df, s)
    print(json.dumps(s, indent=2))
    print(f"\nFigures written to {FIGS}")


if __name__ == "__main__":
    main()
