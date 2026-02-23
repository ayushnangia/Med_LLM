#!/usr/bin/env python3
"""Generate comprehensive DOCX evaluation report: Uro-Oncologist vs AI Judges.

Output: findings/evaluation_report_2026-02-17.docx
Usage: source venv/bin/activate && python scripts/generate_evaluation_report.py
"""

import json
import tempfile
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from scipy import stats as scipy_stats
from sklearn.metrics import cohen_kappa_score, confusion_matrix

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# ── Constants ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
# NOTE: These paths require the companion web app repo (medical-review-site/)
# to be cloned alongside this repository. See: github.com/ayushnangia/medical-review-site
ENV_FILE = BASE_DIR / "medical-review-site" / ".env.local"
CASES_FILE = BASE_DIR / "medical-review-site" / "src" / "data" / "cases.json"
OUTPUT_DIR = BASE_DIR / "findings"
OUTPUT_FILE = OUTPUT_DIR / f"evaluation_report_{pd.Timestamp.now().strftime('%Y-%m-%d')}.docx"
RUNS_DIR = BASE_DIR / "results" / "modal_treatment"

JUDGE_IDS = {
    "openai/gpt-5.2": "GPT-5.2",
    "google/medgemma-27b-text-it": "MedGemma 27B",
}

MODEL_DISPLAY = {
    "google/gemma-3-27b-it": "Gemma 3 27B",
    "google/gemma-3-4b-it": "Gemma 3 4B",
    "google/medgemma-27b-text-it": "MedGemma 27B",
    "OpenMeditron/Meditron3-Qwen2.5-7B": "Meditron3 7B",
    "allenai/Olmo-3.1-32B-Instruct": "OLMo 32B Instruct",
    "allenai/Olmo-3.1-32B-Think": "OLMo 32B Think",
}

MODEL_DESCRIPTIONS = {
    "google/gemma-3-27b-it": "Google's general-purpose 27B instruction-tuned model",
    "google/gemma-3-4b-it": "Google's compact 4B instruction-tuned model",
    "google/medgemma-27b-text-it": "Google's medical-specialized 27B model (also used as AI judge)",
    "OpenMeditron/Meditron3-Qwen2.5-7B": "Medical-specialized 7B model based on Qwen2.5",
    "allenai/Olmo-3.1-32B-Instruct": "Allen AI's open 32B instruction-tuned model",
    "allenai/Olmo-3.1-32B-Think": "Allen AI's 32B chain-of-thought reasoning model",
}

CLR_GPT = "#3B82F6"
CLR_MG = "#10B981"
CLR_AGREE = "#22C55E"
CLR_PARTIAL = "#F59E0B"
CLR_DISAGREE = "#EF4444"
CLR_HEADING = RGBColor(0x1E, 0x40, 0xAF)
CLR_TABLE_ALT = "F0F4FF"

# Normalize messy therapy categories into clean groups
THERAPY_CATEGORY_MAP = {
    "IO+TKI": "IO + TKI",
    "TKI+IO": "IO + TKI",
    "IO+TKI/TKI mono": "IO + TKI",
    "IO+TKI (bei Verf\u00fcgbarkeit) oder TKI mono": "IO + TKI",
    "Biopsie \u2192 IO+IO/TKI": "IO + TKI",
    "TKI mono": "TKI Mono",
    "TKI": "TKI Mono",
    "TKI mono (zweite Linie)": "TKI Mono",
    "TKI mono (zweite Linie nach ICI)": "TKI Mono",
    "TKI mono (Cabozantinib) / IO mono (Nivolumab)": "TKI Mono",
    "TKI mono / IO": "TKI Mono",
    "TKI mono / IO+TKI": "TKI Mono",
    "Surgery": "Surgery",
    "surgery": "Surgery",
    "Nierenchirurgie": "Surgery",
    "Surgery (after biopsy)": "Surgery",
    "Surgery (potentially preceded by biopsy)": "Surgery",
    "Surgery (if indicated after biopsy and staging)/Ablation/Biopsy": "Surgery",
    "Surgery/Surveillance": "Surgery",
    "Surgery/Ablation/Surveillance": "Surgery",
    "IO": "IO Mono",
    "IO mono": "IO Mono",
    "IO mono / Clinical trial": "IO Mono",
    "IO+IO": "IO + IO",
    "Surveillance": "Surveillance",
    "Surveillance/Ablation": "Surveillance",
    "Biopsie/Surveillance": "Surveillance",
    "Biopsie/Surgery/Surveillance/Ablation": "Surveillance",
    "TKI + mTOR-Inhibitor": "TKI + mTOR",
    "TKI + mTOR inhibitor": "TKI + mTOR",
    "TKI+mTOR-Inhibitor": "TKI + mTOR",
    "TKI + mTOR": "TKI + mTOR",
    "TKI+TKI": "TKI + mTOR",
}

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})


# ── Helpers ────────────────────────────────────────────────────────────────

def model_name(mid):
    return MODEL_DISPLAY.get(mid, mid.split("/")[-1])

def judge_name(jid):
    return JUDGE_IDS.get(jid, jid.split("/")[-1])

def save_chart(fig, name, chart_dir):
    path = chart_dir / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path

def kappa_interpretation(k):
    if k < 0.0: return "poor"
    if k < 0.2: return "slight"
    if k < 0.4: return "fair"
    if k < 0.6: return "moderate"
    if k < 0.8: return "substantial"
    return "almost perfect"

def normalize_category(cat):
    return THERAPY_CATEGORY_MAP.get(cat, "Other")


# ── Data Loading ───────────────────────────────────────────────────────────

def load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key] = val
    return env["NEXT_PUBLIC_SUPABASE_URL"], env["NEXT_PUBLIC_SUPABASE_ANON_KEY"]


def fetch_supabase(url, key, table, params=None):
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    resp = requests.get(f"{url}/rest/v1/{table}", params=params or {}, headers=headers)
    resp.raise_for_status()
    return resp.json()


def load_data():
    url, key = load_env()

    reviews_raw = fetch_supabase(url, key, "reviews", {
        "reviewer_name": "eq.Radu Alexa", "select": "*", "limit": "1000",
    })
    reviews_df = pd.DataFrame(reviews_raw)

    judge_reviews_raw = fetch_supabase(url, key, "judge_reviews", {
        "reviewer_name": "eq.Radu Alexa", "select": "*", "limit": "1000",
    })
    judge_reviews_df = pd.DataFrame(judge_reviews_raw)

    with open(CASES_FILE) as f:
        cases_data = json.load(f)

    # Flat judge evaluations
    judge_evals = []
    for case in cases_data["cases"]:
        cid = case["case_id"]
        for mid, pred in case["predictions"].items():
            for jid, jeval in pred.get("judge_evaluations", {}).items():
                judge_evals.append({
                    "case_id": cid, "model_id": mid, "judge_id": jid,
                    "is_correct": jeval["is_correct"],
                    "semantic_score": jeval["semantic_score"],
                    "clinical_score": jeval["clinical_score"],
                    "reasoning_quality": jeval["reasoning_quality"],
                    "overall_score": jeval["overall_score"],
                    "clinical_appropriate": jeval["clinical_appropriate"],
                })
    judge_evals_df = pd.DataFrame(judge_evals)

    # Flat predictions for full pipeline analysis
    predictions = []
    for case in cases_data["cases"]:
        cid = case["case_id"]
        for mid, pred in case["predictions"].items():
            predictions.append({
                "case_id": cid, "model_id": mid,
                "pred_metastatic": pred.get("pred_metastatic"),
                "pred_therapy": pred.get("pred_therapy", ""),
                "pred_category": pred.get("pred_category", "unknown"),
                "pred_category_clean": normalize_category(pred.get("pred_category", "unknown")),
                "pred_confidence": pred.get("pred_confidence"),
                "metastatic_correct": pred.get("metastatic_correct"),
                "therapy_exact_match": pred.get("therapy_exact_match"),
                "therapy_acceptable": pred.get("therapy_acceptable"),
            })
    predictions_df = pd.DataFrame(predictions)

    print(f"  Reviews: {len(reviews_df)} rows, {reviews_df['case_id'].nunique()} cases, "
          f"{reviews_df['model_id'].nunique()} models")
    print(f"  Judge reviews: {len(judge_reviews_df)} rows, "
          f"{judge_reviews_df['case_id'].nunique()} cases")
    print(f"  Judge evals: {len(judge_evals_df)} rows, "
          f"{judge_evals_df['case_id'].nunique()} cases")
    print(f"  Predictions: {len(predictions_df)} rows, "
          f"{predictions_df['case_id'].nunique()} cases")

    return reviews_df, judge_reviews_df, judge_evals_df, predictions_df, cases_data


def load_run_summaries():
    """Load summary.json and judge_evaluation metrics from all runs."""
    rows = []
    for model_dir in sorted(RUNS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        for run_dir in sorted(model_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_file = run_dir / "summary.json"
            if not summary_file.exists():
                continue
            with open(summary_file) as f:
                s = json.load(f)

            ts = s.get("timestamp", run_dir.name)
            run_label = "Jan 2026" if "2026-01" in ts else "Feb 2026"
            row = {
                "model_id": s["model"],
                "model_name": model_name(s["model"]),
                "timestamp": ts,
                "run_label": run_label,
                "total_cases": s.get("total_cases", 0),
                "metastatic_accuracy": s.get("metastatic_accuracy", 0) * 100,
                "therapy_exact_match_rate": s.get("therapy_exact_match_rate", 0) * 100,
                "therapy_acceptable_rate": s.get("therapy_acceptable_rate", 0) * 100,
                "errors": s.get("errors", 0),
            }

            # Load judge evaluation metrics from the same run directory
            for judge_file in sorted(run_dir.glob("judge_evaluation_*.json")):
                with open(judge_file) as f:
                    je = json.load(f)
                judge_short = je["judge_model"].split("/")[-1]
                m = je.get("metrics", {})
                row[f"judge_{judge_short}_accuracy"] = m.get("accuracy", 0) * 100
                row[f"judge_{judge_short}_avg_overall"] = m.get("avg_overall_score", 0)
                row[f"judge_{judge_short}_avg_clinical"] = m.get("avg_clinical_score", 0)
                row[f"judge_{judge_short}_avg_semantic"] = m.get("avg_therapy_semantic_score", 0)
                row[f"judge_{judge_short}_avg_reasoning"] = m.get("avg_reasoning_quality", 0)
                row[f"judge_{judge_short}_clinical_rate"] = m.get("clinical_appropriateness_rate", 0) * 100

            rows.append(row)

    df = pd.DataFrame(rows)
    print(f"  Run summaries: {len(df)} runs across {df['model_id'].nunique()} models")
    return df


# ── Analysis: Case Demographics ────────────────────────────────────────────

def compute_demographics(cases_data):
    cases = cases_data["cases"]
    ages = [c["patient"]["age"] for c in cases if c["patient"]["age"] is not None]
    ecogs = [c["patient"]["ecog"] for c in cases if c["patient"]["ecog"] is not None]
    metastatic = [c["ground_truth"]["metastatic"] for c in cases]
    histologies = [c["diagnosis"]["histologie_subtyp"] for c in cases]
    klarzellig = [c["diagnosis"]["klarzellig"] for c in cases]

    # Clean histology
    hist_clean = []
    for h in histologies:
        if not h or h == "":
            hist_clean.append("Not specified")
        elif "ccRCC" in h or "klarzellig" in h.lower():
            hist_clean.append("Clear cell (ccRCC)")
        elif "papill" in h.lower():
            hist_clean.append("Papillary")
        else:
            hist_clean.append(h)

    return {
        "n_cases": len(cases),
        "ages": ages,
        "age_mean": np.mean(ages) if ages else 0,
        "age_median": np.median(ages) if ages else 0,
        "age_min": min(ages) if ages else 0,
        "age_max": max(ages) if ages else 0,
        "ecog_counts": dict(sorted(Counter(ecogs).items())),
        "n_metastatic": sum(metastatic),
        "n_localized": len(metastatic) - sum(metastatic),
        "histology_counts": dict(Counter(hist_clean).most_common()),
        "n_clear_cell": sum(1 for k in klarzellig if k is True),
        "n_non_clear_cell": sum(1 for k in klarzellig if k is False),
        "n_histology_unknown": sum(1 for k in klarzellig if k is None),
    }


# ── Analysis: Full Pipeline (all 69 cases) ────────────────────────────────

def compute_full_pipeline(predictions_df, cases_data):
    model_summaries = {m["model_id"]: m for m in cases_data["models"]}

    # Per-model automated metrics
    model_rows = []
    for mid in sorted(MODEL_DISPLAY.keys()):
        ms = model_summaries.get(mid, {})
        g = predictions_df[predictions_df["model_id"] == mid]
        model_rows.append({
            "model_id": mid,
            "model_name": model_name(mid),
            "n_cases": ms.get("total_cases", len(g)),
            "met_accuracy": ms.get("metastatic_accuracy", 0),
            "therapy_exact": ms.get("therapy_exact_match_rate", 0),
            "judge_accuracy": ms.get("judge_accuracy", 0),
            "avg_overall": ms.get("avg_overall_score", 0),
            "avg_semantic": ms.get("avg_semantic_score", 0),
            "avg_clinical": ms.get("avg_clinical_score", 0),
            "avg_reasoning": ms.get("avg_reasoning_quality", 0),
        })

    # Therapy category distribution
    cat_counts = predictions_df.groupby(
        ["model_id", "pred_category_clean"]
    ).size().unstack(fill_value=0)

    # Overall automated stats
    met_correct = predictions_df["metastatic_correct"].sum()
    met_total = predictions_df["metastatic_correct"].notna().sum()
    therapy_exact = predictions_df["therapy_exact_match"].sum()
    therapy_total = predictions_df["therapy_exact_match"].notna().sum()
    therapy_accept = predictions_df["therapy_acceptable"].sum()
    therapy_accept_total = predictions_df["therapy_acceptable"].notna().sum()

    return {
        "model_rows": pd.DataFrame(model_rows).sort_values("avg_overall", ascending=False),
        "category_counts": cat_counts,
        "overall": {
            "met_accuracy": met_correct / met_total * 100 if met_total > 0 else 0,
            "therapy_exact_rate": therapy_exact / therapy_total * 100 if therapy_total > 0 else 0,
            "therapy_accept_rate": therapy_accept / therapy_accept_total * 100 if therapy_accept_total > 0 else 0,
            "total_predictions": len(predictions_df),
        },
    }


# ── Analysis: Uro-Oncologist Reviews ───────────────────────────────────────────────

def compute_model_performance(reviews_df):
    rows = []
    for mid, g in reviews_df.groupby("model_id"):
        rows.append({
            "model_id": mid,
            "model_name": model_name(mid),
            "n_cases": len(g),
            "acceptable_pct": g["therapy_acceptable_ra"].mean() * 100,
            "avg_exact_match": g["recommendation_exact_match"].mean(),
            "avg_patient_oriented": g["recommendation_patient_oriented"].mean(),
            "avg_quality": g["prediction_quality"].mean(),
        })
    return pd.DataFrame(rows).sort_values("avg_quality", ascending=False)


# ── Analysis: Agreement ────────────────────────────────────────────────────

def compute_agreement(reviews_df, judge_evals_df):
    results = {}
    for jid in JUDGE_IDS:
        je = judge_evals_df[judge_evals_df["judge_id"] == jid][
            ["case_id", "model_id", "is_correct"]]
        merged = reviews_df[["case_id", "model_id", "therapy_acceptable_ra"]].merge(
            je, on=["case_id", "model_id"], how="inner"
        )
        merged = merged.dropna(subset=["therapy_acceptable_ra", "is_correct"])
        if len(merged) < 5:
            continue

        doc_labels = merged["therapy_acceptable_ra"].astype(int).values
        judge_labels = merged["is_correct"].astype(int).values

        kappa = cohen_kappa_score(doc_labels, judge_labels)
        cm = confusion_matrix(doc_labels, judge_labels, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        sens = tp / (tp + fn) if (tp + fn) > 0 else 0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * prec * sens / (prec + sens) if (prec + sens) > 0 else 0

        results[jid] = {
            "n_pairs": len(merged), "n_cases": merged["case_id"].nunique(),
            "kappa": kappa, "cm": cm,
            "sensitivity": sens, "specificity": spec, "precision": prec, "f1": f1,
            "agreement_rate": (tp + tn) / len(merged),
        }
    return results


def compute_correlations(reviews_df, judge_evals_df):
    results = {}
    for jid in JUDGE_IDS:
        je = judge_evals_df[judge_evals_df["judge_id"] == jid][
            ["case_id", "model_id", "overall_score"]]
        merged = reviews_df[
            ["case_id", "model_id", "prediction_quality", "recommendation_exact_match"]
        ].merge(je, on=["case_id", "model_id"], how="inner")
        if len(merged) < 5:
            continue

        r_q, p_q = scipy_stats.spearmanr(
            merged["overall_score"], merged["prediction_quality"])
        r_e, p_e = scipy_stats.spearmanr(
            merged["overall_score"], merged["recommendation_exact_match"])

        results[jid] = {
            "n": len(merged),
            "quality_r": r_q, "quality_p": p_q,
            "exact_r": r_e, "exact_p": p_e,
            "data": merged,
        }
    return results


def compute_judge_ratings(judge_reviews_df):
    results = {}
    for jid in JUDGE_IDS:
        jr = judge_reviews_df[judge_reviews_df["judge_model"] == jid]
        if len(jr) == 0:
            continue
        counts = jr["judge_correct"].value_counts()
        total = len(jr)
        results[jid] = {
            "n": total,
            "agree": counts.get("agree", 0),
            "partial": counts.get("partial", 0),
            "disagree": counts.get("disagree", 0),
            "agree_pct": counts.get("agree", 0) / total * 100,
            "partial_pct": counts.get("partial", 0) / total * 100,
            "disagree_pct": counts.get("disagree", 0) / total * 100,
            "avg_reasoning_quality": jr["judge_reasoning_quality"].mean(),
        }
    return results


def compute_per_model_judge_accuracy(reviews_df, judge_evals_df):
    results = {}
    for jid in JUDGE_IDS:
        je = judge_evals_df[judge_evals_df["judge_id"] == jid][
            ["case_id", "model_id", "is_correct"]]
        merged = reviews_df[["case_id", "model_id", "therapy_acceptable_ra"]].merge(
            je, on=["case_id", "model_id"], how="inner"
        )
        merged = merged.dropna(subset=["therapy_acceptable_ra", "is_correct"])
        merged["therapy_acceptable_ra"] = merged["therapy_acceptable_ra"].astype(bool)
        merged["is_correct"] = merged["is_correct"].astype(bool)
        model_acc = {}
        for mid, g in merged.groupby("model_id"):
            model_acc[mid] = (
                g["therapy_acceptable_ra"] == g["is_correct"]).mean() * 100
        results[jid] = model_acc
    return results


def compute_inter_judge_agreement(judge_evals_df):
    jids = list(JUDGE_IDS.keys())
    j1 = judge_evals_df[judge_evals_df["judge_id"] == jids[0]][
        ["case_id", "model_id", "is_correct"]].rename(columns={"is_correct": "j1"})
    j2 = judge_evals_df[judge_evals_df["judge_id"] == jids[1]][
        ["case_id", "model_id", "is_correct"]].rename(columns={"is_correct": "j2"})
    merged = j1.merge(j2, on=["case_id", "model_id"], how="inner")
    if len(merged) < 5:
        return None

    kappa = cohen_kappa_score(merged["j1"].astype(int), merged["j2"].astype(int))
    cm = confusion_matrix(merged["j1"].astype(int), merged["j2"].astype(int), labels=[0, 1])
    return {
        "n_pairs": len(merged), "n_cases": merged["case_id"].nunique(),
        "kappa": kappa, "cm": cm,
        "agreement_rate": (merged["j1"] == merged["j2"]).mean(),
    }


def compute_medgemma_bias(judge_evals_df):
    mg_id = "google/medgemma-27b-text-it"
    mg_judge = judge_evals_df[judge_evals_df["judge_id"] == mg_id].copy()
    if len(mg_judge) == 0:
        return None

    self_scores = mg_judge[mg_judge["model_id"] == mg_id]["overall_score"]
    other_scores = mg_judge[mg_judge["model_id"] != mg_id]["overall_score"]
    if len(self_scores) < 3 or len(other_scores) < 3:
        return None

    u_stat, p_val = scipy_stats.mannwhitneyu(
        self_scores, other_scores, alternative="two-sided")
    return {
        "self_mean": self_scores.mean(), "self_median": self_scores.median(),
        "self_n": len(self_scores),
        "other_mean": other_scores.mean(), "other_median": other_scores.median(),
        "other_n": len(other_scores),
        "u_stat": u_stat, "p_val": p_val,
        "by_model": mg_judge.groupby("model_id")["overall_score"].mean().to_dict(),
    }


def compute_clinical_safety(reviews_df, judge_evals_df):
    results = {}
    for jid in JUDGE_IDS:
        je = judge_evals_df[judge_evals_df["judge_id"] == jid][
            ["case_id", "model_id", "is_correct"]]
        merged = reviews_df[["case_id", "model_id", "therapy_acceptable_ra"]].merge(
            je, on=["case_id", "model_id"], how="inner"
        )
        merged = merged.dropna(subset=["therapy_acceptable_ra", "is_correct"])
        if len(merged) == 0:
            continue
        doc_accept = merged["therapy_acceptable_ra"].astype(bool)
        judge_correct = merged["is_correct"].astype(bool)
        fp = (judge_correct & ~doc_accept).sum()
        fn = (~judge_correct & doc_accept).sum()
        n_pos = judge_correct.sum()
        n_neg = (~judge_correct).sum()
        results[jid] = {
            "n": len(merged), "fp": int(fp), "fn": int(fn),
            "fp_rate": fp / n_pos * 100 if n_pos > 0 else 0,
            "fn_rate": fn / n_neg * 100 if n_neg > 0 else 0,
            "n_judge_positive": int(n_pos), "n_judge_negative": int(n_neg),
        }
    return results


def select_case_studies(cases_data, reviews_df, judge_evals_df):
    """Pick 3 representative cases for the case study section."""
    cases = cases_data["cases"]
    studies = []

    # Build per-case prediction stats
    case_stats = {}
    for case in cases:
        cid = case["case_id"]
        preds = case["predictions"]
        acceptables = [p.get("therapy_acceptable", False) for p in preds.values()]
        exact_matches = [p.get("therapy_exact_match", False) for p in preds.values()]
        categories = [p.get("pred_category", "") for p in preds.values()]

        # Doctor reviews for this case
        doc_reviews = reviews_df[reviews_df["case_id"] == cid] if len(reviews_df) > 0 else pd.DataFrame()

        # Judge evals for this case
        je = judge_evals_df[judge_evals_df["case_id"] == cid] if len(judge_evals_df) > 0 else pd.DataFrame()

        case_stats[cid] = {
            "case": case,
            "n_acceptable": sum(bool(a) for a in acceptables),
            "n_exact": sum(bool(e) for e in exact_matches),
            "n_models": len(preds),
            "categories": categories,
            "category_unique": len(set(categories)),
            "has_doctor_review": len(doc_reviews) > 0,
            "doc_reviews": doc_reviews,
            "judge_evals": je,
        }

    # Case 1: High agreement — all/most models correct
    for cid, st in sorted(case_stats.items()):
        if st["n_exact"] >= 5 and st["n_models"] >= 6 and st["has_doctor_review"]:
            studies.append(("consensus_correct", cid, st))
            break

    # Case 2: Model disagreement — high category variance
    for cid, st in sorted(case_stats.items(), key=lambda x: -x[1]["category_unique"]):
        if cid in [s[1] for s in studies]:
            continue
        if st["category_unique"] >= 3 and st["has_doctor_review"]:
            studies.append(("model_disagreement", cid, st))
            break

    # Case 3: Doctor-judge divergence — doctor says acceptable but judges say incorrect
    for cid, st in sorted(case_stats.items()):
        if cid in [s[1] for s in studies]:
            continue
        if not st["has_doctor_review"] or len(st["judge_evals"]) == 0:
            continue
        doc = st["doc_reviews"]
        je = st["judge_evals"]
        # Find a model where doctor accepted but both judges rejected
        for _, dr in doc.iterrows():
            if not dr["therapy_acceptable_ra"]:
                continue
            mid = dr["model_id"]
            judge_rows = je[je["model_id"] == mid]
            if len(judge_rows) >= 2 and not judge_rows["is_correct"].any():
                studies.append(("doctor_judge_diverge", cid, st))
                break
        if len(studies) >= 3:
            break

    # Fallback: if fewer than 3, pick a high-disagreement case
    if len(studies) < 3:
        for cid, st in sorted(case_stats.items(), key=lambda x: x[1]["n_acceptable"]):
            if cid not in [s[1] for s in studies] and st["has_doctor_review"]:
                studies.append(("low_agreement", cid, st))
                break

    return studies


# ── Chart Generation ───────────────────────────────────────────────────────

def chart_demographics(demo, chart_dir):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # Age histogram
    ax = axes[0]
    ax.hist(demo["ages"], bins=10, color="#3B82F6", edgecolor="white", alpha=0.8)
    ax.axvline(demo["age_mean"], color="#EF4444", ls="--", lw=2,
               label=f"Mean: {demo['age_mean']:.0f}")
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Number of Patients")
    ax.set_title("Age Distribution", fontweight="bold")
    ax.legend()

    # ECOG bar
    ax = axes[1]
    ecog_vals = list(demo["ecog_counts"].keys())
    ecog_cnts = list(demo["ecog_counts"].values())
    colors = ["#22C55E", "#86EFAC", "#FDE047", "#EF4444"][:len(ecog_vals)]
    ax.bar([f"ECOG {e}" for e in ecog_vals], ecog_cnts, color=colors, edgecolor="white")
    for i, v in enumerate(ecog_cnts):
        ax.text(i, v + 0.5, str(v), ha="center", fontweight="bold")
    ax.set_ylabel("Number of Patients")
    ax.set_title("ECOG Performance Status", fontweight="bold")

    # Metastatic status
    ax = axes[2]
    sizes = [demo["n_metastatic"], demo["n_localized"]]
    labels = [f"Metastatic\n(n={sizes[0]})", f"Localized\n(n={sizes[1]})"]
    colors = ["#EF4444", "#3B82F6"]
    ax.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%",
           startangle=90, textprops={"fontsize": 10})
    ax.set_title("Metastatic Status", fontweight="bold")

    fig.suptitle("Patient Cohort Demographics (n=69 RCC Cases)", fontweight="bold", y=1.03)
    fig.tight_layout()
    return save_chart(fig, "demographics", chart_dir)


def chart_full_model_performance(pipeline, chart_dir):
    df = pipeline["model_rows"].sort_values("avg_overall", ascending=True)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Metastatic detection accuracy
    ax = axes[0]
    bars = ax.barh(df["model_name"], df["met_accuracy"],
                   color="#6366F1", edgecolor="white", height=0.6)
    for bar, val in zip(bars, df["met_accuracy"]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Metastatic Detection", fontweight="bold")
    ax.set_xlim(0, 105)

    # Therapy exact match
    ax = axes[1]
    bars = ax.barh(df["model_name"], df["therapy_exact"],
                   color="#F59E0B", edgecolor="white", height=0.6)
    for bar, val in zip(bars, df["therapy_exact"]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Exact Match (%)")
    ax.set_title("Therapy Exact Match", fontweight="bold")
    ax.set_xlim(0, 105)

    # Avg overall score
    ax = axes[2]
    bars = ax.barh(df["model_name"], df["avg_overall"],
                   color="#10B981", edgecolor="white", height=0.6)
    for bar, val in zip(bars, df["avg_overall"]):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Avg Judge Score (0\u20131)")
    ax.set_title("Avg Judge Overall Score", fontweight="bold")
    ax.set_xlim(0, 1.05)

    fig.suptitle("Model Performance \u2014 Automated Evaluation (All 69 Cases)",
                 fontweight="bold", y=1.03)
    fig.tight_layout()
    return save_chart(fig, "full_model_performance", chart_dir)


def chart_therapy_categories(pipeline, chart_dir):
    cat_df = pipeline["category_counts"]
    # Reindex with clean model names
    cat_df.index = [model_name(m) for m in cat_df.index]

    # Order categories by total count
    cat_order = cat_df.sum().sort_values(ascending=False).index.tolist()
    cat_df = cat_df[cat_order]

    # Use a good color palette
    colors = ["#3B82F6", "#10B981", "#6366F1", "#F59E0B",
              "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6"]

    fig, ax = plt.subplots(figsize=(12, 5))
    cat_df.plot(kind="barh", stacked=True, ax=ax, color=colors[:len(cat_order)],
                edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Number of Predictions")
    ax.set_title("Predicted Therapy Categories by Model (69 Cases)", fontweight="bold")
    ax.legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    fig.tight_layout()
    return save_chart(fig, "therapy_categories", chart_dir)


def chart_model_acceptability(perf_df, chart_dir):
    df = perf_df.sort_values("acceptable_pct")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#22C55E" if v >= 60 else "#F59E0B" if v >= 40
              else "#EF4444" for v in df["acceptable_pct"]]
    bars = ax.barh(df["model_name"], df["acceptable_pct"],
                   color=colors, edgecolor="white", height=0.6)
    for bar, val in zip(bars, df["acceptable_pct"]):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("Therapy Acceptable (%)")
    ax.set_title("Therapy Acceptability Rate by Model (Uro-Oncologist Review)", fontweight="bold")
    ax.set_xlim(0, 105)
    ax.axvline(50, color="gray", ls="--", alpha=0.4)
    fig.tight_layout()
    return save_chart(fig, "model_acceptability", chart_dir)


def chart_model_quality(perf_df, chart_dir):
    df = perf_df.sort_values("avg_quality")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(df["model_name"], df["avg_quality"],
                   color="#3B82F6", edgecolor="white", height=0.6)
    for bar, val in zip(bars, df["avg_quality"]):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("Average Prediction Quality (0\u20139)")
    ax.set_title("Average Prediction Quality by Model (Uro-Oncologist Review)", fontweight="bold")
    ax.set_xlim(0, 10)
    fig.tight_layout()
    return save_chart(fig, "model_quality", chart_dir)


def chart_confusion_matrices(agreement, chart_dir):
    jids = [jid for jid in JUDGE_IDS if jid in agreement]
    fig, axes = plt.subplots(1, len(jids), figsize=(5 * len(jids), 4))
    if len(jids) == 1:
        axes = [axes]
    labels = ["Reject", "Accept"]
    for ax, jid in zip(axes, jids):
        cm = agreement[jid]["cm"]
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels,
                    yticklabels=labels, ax=ax, cbar=False, annot_kws={"size": 14})
        ax.set_title(f"{judge_name(jid)}\n\u03ba = {agreement[jid]['kappa']:.3f}",
                     fontweight="bold")
        ax.set_xlabel("Judge Decision")
        ax.set_ylabel("Uro-Oncologist Decision")
    fig.suptitle("Confusion Matrices: Uro-Oncologist vs AI Judge",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return save_chart(fig, "confusion_matrices", chart_dir)



def chart_judge_ratings(ratings, chart_dir):
    jids = [jid for jid in JUDGE_IDS if jid in ratings]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    names = [judge_name(jid) for jid in jids]
    agree = [ratings[jid]["agree_pct"] for jid in jids]
    partial = [ratings[jid]["partial_pct"] for jid in jids]
    disagree = [ratings[jid]["disagree_pct"] for jid in jids]

    x = np.arange(len(names))
    w = 0.5
    ax1.bar(x, agree, w, label="Agree", color=CLR_AGREE)
    ax1.bar(x, partial, w, bottom=agree, label="Partial", color=CLR_PARTIAL)
    ax1.bar(x, disagree, w,
            bottom=[a + p for a, p in zip(agree, partial)],
            label="Disagree", color=CLR_DISAGREE)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    ax1.set_ylabel("Percentage (%)")
    ax1.set_title("Uro-Oncologist Agreement with Judge", fontweight="bold")
    ax1.legend()
    ax1.set_ylim(0, 105)

    qualities = [ratings[jid]["avg_reasoning_quality"] for jid in jids]
    bars = ax2.bar(names, qualities,
                   color=[CLR_GPT, CLR_MG][:len(jids)], width=0.5)
    for bar, val in zip(bars, qualities):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 f"{val:.1f}", ha="center", fontweight="bold")
    ax2.set_ylabel("Reasoning Quality (0\u201310)")
    ax2.set_title("Avg Judge Reasoning Quality\n(Rated by Uro-Oncologist)", fontweight="bold")
    ax2.set_ylim(0, 10)

    fig.tight_layout()
    return save_chart(fig, "judge_ratings", chart_dir)


def chart_per_model_accuracy(per_model_acc, chart_dir):
    jids = list(JUDGE_IDS.keys())
    models = sorted(set().union(
        *[set(per_model_acc[jid].keys()) for jid in jids if jid in per_model_acc]))
    data = [[per_model_acc.get(jid, {}).get(mid, np.nan)
             for jid in jids] for mid in models]
    df = pd.DataFrame(data, index=[model_name(m) for m in models],
                      columns=[judge_name(j) for j in jids])

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(df, annot=True, fmt=".0f", cmap="RdYlGn", vmin=30, vmax=100,
                ax=ax, cbar_kws={"label": "Agreement %"}, annot_kws={"size": 12})
    ax.set_title("Judge\u2013Uro-Oncologist Agreement (%) by Model", fontweight="bold")
    ax.set_ylabel("")
    fig.tight_layout()
    return save_chart(fig, "per_model_accuracy", chart_dir)


def chart_inter_judge(inter_judge, chart_dir):
    cm = inter_judge["cm"]
    fig, ax = plt.subplots(figsize=(4.5, 4))
    labels = ["Incorrect", "Correct"]
    sns.heatmap(cm, annot=True, fmt="d", cmap="Purples", xticklabels=labels,
                yticklabels=labels, ax=ax, cbar=False, annot_kws={"size": 14})
    ax.set_title(f"Inter-Judge Agreement\n\u03ba = {inter_judge['kappa']:.3f}",
                 fontweight="bold")
    jids = list(JUDGE_IDS.keys())
    ax.set_xlabel(judge_name(jids[1]))
    ax.set_ylabel(judge_name(jids[0]))
    fig.tight_layout()
    return save_chart(fig, "inter_judge", chart_dir)


def chart_medgemma_bias(bias, chart_dir):
    mg_id = "google/medgemma-27b-text-it"
    by_model = bias["by_model"]
    models = sorted(by_model.keys(), key=lambda m: by_model[m], reverse=True)
    names = [model_name(m) for m in models]
    scores = [by_model[m] for m in models]
    colors = [CLR_MG if m == mg_id else "#94A3B8" for m in models]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(names, scores, color=colors, edgecolor="white", height=0.6)
    for bar, val in zip(bars, scores):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", fontsize=10)
    ax.set_xlabel("MedGemma Judge: Average Overall Score")
    ax.set_title("MedGemma Self-Judging Bias Analysis", fontweight="bold")
    ax.axvline(bias["other_mean"], color="#EF4444", ls="--", alpha=0.7,
               label=f"Others avg: {bias['other_mean']:.2f}")
    ax.legend()
    ax.set_xlim(0, 1.05)
    fig.tight_layout()
    return save_chart(fig, "medgemma_bias", chart_dir)


def chart_score_distributions(judge_evals_df, chart_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    jids = list(JUDGE_IDS.keys())
    colors_list = [CLR_GPT, CLR_MG]

    for ax, jid, clr in zip(axes, jids, colors_list):
        data = judge_evals_df[judge_evals_df["judge_id"] == jid]
        models_sorted = sorted(data["model_id"].unique())
        plot_data = [data[data["model_id"] == m]["overall_score"].values
                     for m in models_sorted]
        bp = ax.boxplot(plot_data, patch_artist=True,
                        tick_labels=[model_name(m) for m in models_sorted])
        for patch in bp["boxes"]:
            patch.set_facecolor(clr)
            patch.set_alpha(0.6)
        ax.set_title(judge_name(jid), fontweight="bold")
        if ax == axes[0]:
            ax.set_ylabel("Overall Score (0\u20131)")
        ax.tick_params(axis="x", rotation=45)

    fig.suptitle("Score Distributions by Model and Judge (69 Cases)",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return save_chart(fig, "score_distributions", chart_dir)


def chart_score_types(judge_evals_df, chart_dir):
    score_cols = ["semantic_score", "clinical_score",
                  "reasoning_quality", "overall_score"]
    score_labels = ["Semantic", "Clinical", "Reasoning", "Overall"]
    jids = list(JUDGE_IDS.keys())

    fig, axes = plt.subplots(1, 4, figsize=(14, 4), sharey=True)
    for ax, col, label in zip(axes, score_cols, score_labels):
        data, labels_p, colors_p = [], [], []
        for jid, clr in zip(jids, [CLR_GPT, CLR_MG]):
            data.append(judge_evals_df[
                judge_evals_df["judge_id"] == jid][col].dropna().values)
            labels_p.append(judge_name(jid))
            colors_p.append(clr)
        bp = ax.boxplot(data, patch_artist=True, tick_labels=labels_p)
        for patch, clr in zip(bp["boxes"], colors_p):
            patch.set_facecolor(clr)
            patch.set_alpha(0.6)
        ax.set_title(label, fontweight="bold")
        ax.set_ylim(-0.05, 1.05)
    axes[0].set_ylabel("Score (0\u20131)")
    fig.suptitle("Score Type Distributions by Judge",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return save_chart(fig, "score_types", chart_dir)


# ── DOCX Building ──────────────────────────────────────────────────────────

def style_document(doc):
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)
    for level in range(1, 4):
        h = doc.styles[f"Heading {level}"]
        h.font.name = "Arial"
        h.font.color.rgb = CLR_HEADING
        h.font.bold = True
        h.font.size = Pt([0, 18, 14, 12][level])


def add_styled_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        cell._tc.get_or_add_tcPr().append(
            parse_xml(f'<w:shd {nsdecls("w")} w:fill="1E40AF"/>'))
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                run.font.bold = True
                run.font.size = Pt(9)
                run.font.name = "Arial"

    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.font.name = "Arial"
            if r_idx % 2 == 1:
                cell._tc.get_or_add_tcPr().append(
                    parse_xml(f'<w:shd {nsdecls("w")} w:fill="{CLR_TABLE_ALT}"/>'))

    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                if i < len(row.cells):
                    row.cells[i].width = Cm(w)
    return table


def add_chart(doc, chart_path, width=Inches(6)):
    doc.add_picture(str(chart_path), width=width)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def add_bullet(doc, text):
    p = doc.add_paragraph(text, style="List Bullet")
    for run in p.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10)


# ── Build the Report ───────────────────────────────────────────────────────

def build_report(reviews_df, judge_reviews_df, judge_evals_df,
                 predictions_df, cases_data, run_summaries_df, chart_dir):
    print("\nComputing analyses...")
    demo = compute_demographics(cases_data)
    pipeline = compute_full_pipeline(predictions_df, cases_data)
    perf = compute_model_performance(reviews_df)
    agreement = compute_agreement(reviews_df, judge_evals_df)
    correlations = compute_correlations(reviews_df, judge_evals_df)
    ratings = compute_judge_ratings(judge_reviews_df)
    per_model_acc = compute_per_model_judge_accuracy(reviews_df, judge_evals_df)
    inter_judge = compute_inter_judge_agreement(judge_evals_df)
    mg_bias = compute_medgemma_bias(judge_evals_df)
    safety = compute_clinical_safety(reviews_df, judge_evals_df)

    case_studies = select_case_studies(cases_data, reviews_df, judge_evals_df)

    print("Generating charts...")
    charts = {}
    charts["demographics"] = chart_demographics(demo, chart_dir)
    charts["full_perf"] = chart_full_model_performance(pipeline, chart_dir)
    charts["therapy_cats"] = chart_therapy_categories(pipeline, chart_dir)
    charts["acceptability"] = chart_model_acceptability(perf, chart_dir)
    charts["quality"] = chart_model_quality(perf, chart_dir)
    if agreement:
        charts["confusion"] = chart_confusion_matrices(agreement, chart_dir)
    if ratings:
        charts["ratings"] = chart_judge_ratings(ratings, chart_dir)
    if per_model_acc:
        charts["per_model"] = chart_per_model_accuracy(per_model_acc, chart_dir)
    if inter_judge:
        charts["inter_judge"] = chart_inter_judge(inter_judge, chart_dir)
    if mg_bias:
        charts["mg_bias"] = chart_medgemma_bias(mg_bias, chart_dir)
    charts["distributions"] = chart_score_distributions(judge_evals_df, chart_dir)
    charts["score_types"] = chart_score_types(judge_evals_df, chart_dir)
    print("Building DOCX...")
    doc = Document()
    style_document(doc)
    best_model = perf.iloc[0]
    best_auto = pipeline["model_rows"].iloc[0]
    ovr = pipeline["overall"]

    # ================================================================
    # TITLE PAGE
    # ================================================================
    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Evaluation Report")
    run.font.size = Pt(28)
    run.font.color.rgb = CLR_HEADING
    run.font.bold = True
    run.font.name = "Arial"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Uro-Oncologist vs AI Judges in Medical Oncology\n"
        "Therapy Recommendation Assessment")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    run.font.name = "Arial"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "\n\nFebruary 2026\n"
        "Renal Cell Carcinoma (RCC) \u2014 69 Cases from German Tumor Boards")
    run.font.size = Pt(12)
    run.font.name = "Arial"

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\nPrepared for Google AI Hackathon 2026")
    run.font.size = Pt(11)
    run.font.name = "Arial"
    run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    run.font.italic = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\nReviewer: Dr. Radu Alexa, Board-Certified Uro-Oncologist")
    run.font.size = Pt(11)
    run.font.name = "Arial"
    run.font.italic = True

    doc.add_page_break()

    # ================================================================
    # 1. EXECUTIVE SUMMARY
    # ================================================================
    doc.add_heading("1. Executive Summary", level=1)

    doc.add_paragraph(
        f"This report presents a novel three-tier evaluation pipeline for assessing "
        f"AI-generated therapy recommendations in clinical oncology. Across "
        f"{ovr['total_predictions']} predictions from 6 LLMs on {demo['n_cases']} "
        f"renal cell carcinoma (Nierenzellkarzinom, RCC) cases from German tumor boards "
        f"(Tumordiskussionen), the pipeline combines automated AI judging with expert "
        f"physician validation to establish a scalable, reproducible evaluation framework."
    )

    doc.add_heading("Key Findings", level=2)

    add_bullet(doc,
        f"Across all {ovr['total_predictions']} predictions: "
        f"{ovr['met_accuracy']:.1f}% metastatic detection accuracy, "
        f"{ovr['therapy_exact_rate']:.1f}% exact therapy match, "
        f"{ovr['therapy_accept_rate']:.1f}% clinically acceptable therapies.")
    add_bullet(doc,
        f"Best model by uro-oncologist review: {best_model['model_name']} "
        f"({best_model['avg_quality']:.1f}/9 quality, "
        f"{best_model['acceptable_pct']:.1f}% acceptable).")
    add_bullet(doc,
        f"Best model by automated judge score: {best_auto['model_name']} "
        f"(avg overall {best_auto['avg_overall']:.2f}/1.0).")

    for jid in agreement:
        k = agreement[jid]["kappa"]
        add_bullet(doc,
            f"{judge_name(jid)} shows {kappa_interpretation(k)} agreement "
            f"with the uro-oncologist (Cohen's \u03ba = {k:.3f}).")

    if inter_judge:
        add_bullet(doc,
            f"Inter-judge agreement: \u03ba = {inter_judge['kappa']:.3f}, "
            f"{inter_judge['agreement_rate'] * 100:.1f}% concordance "
            f"across {inter_judge['n_pairs']} evaluation pairs.")

    if mg_bias:
        direction = "higher" if mg_bias["self_mean"] > mg_bias["other_mean"] else "lower"
        sig = "significant" if mg_bias["p_val"] < 0.05 else "not significant"
        add_bullet(doc,
            f"MedGemma self-judging bias: {direction} scores for own predictions "
            f"({mg_bias['self_mean']:.2f} vs {mg_bias['other_mean']:.2f}), "
            f"{sig} (p={mg_bias['p_val']:.3f}).")

    if safety:
        safest = min(safety.items(), key=lambda x: x[1]["fp_rate"])
        add_bullet(doc,
            f"Clinical safety: {judge_name(safest[0])} has lowest dangerous error rate "
            f"({safest[1]['fp_rate']:.1f}% false positives).")

    doc.add_page_break()

    # ================================================================
    # 2. PROJECT OVERVIEW
    # ================================================================
    doc.add_heading("2. Project Overview", level=1)

    doc.add_paragraph(
        "This project investigates whether large language models (LLMs) can support "
        "clinical decision-making in oncology by generating appropriate therapy "
        "recommendations for renal cell carcinoma (RCC) patients presented at German "
        "tumor board discussions."
    )

    doc.add_heading("Clinical Context", level=2)
    doc.add_paragraph(
        "Tumor boards are multidisciplinary meetings where specialists review complex "
        "cancer cases and agree on treatment recommendations. Each case includes patient "
        "demographics, comorbidities, TNM staging, histological subtype, prior therapies, "
        "and imaging findings. The ground truth for this study is the consensus therapy "
        "recommendation from the tumor board."
    )

    doc.add_heading("Project Scope: Two Evaluation Pipelines", level=2)
    doc.add_paragraph(
        "This project comprises two complementary evaluation pipelines:"
    )
    add_styled_table(doc,
        ["Pipeline", "Task", "Models Tested", "Best Result", "Status"],
        [
            ["1. Classification", "7-class cancer type detection\n"
             "(NCC, PCA, HODEN, UCA, PENIS, COMBI, NON_URO)",
             "14 models (MiMo v2, GPT-5.2, Claude Opus 4.5, "
             "Gemini 3, DeepSeek v3.2, etc.)",
             "100% accuracy (MiMo v2 Flash)", "Complete"],
            ["2. Treatment Prediction", "RCC therapy recommendation\n"
             "following German oncology guidelines",
             "6 models (Gemma 3 27B/4B, MedGemma, "
             "Meditron3, OLMo 32B Instruct/Think)",
             "See detailed results below", "Complete + Validated"],
        ],
        col_widths=[2.5, 4, 4, 3, 2],
    )
    doc.add_paragraph(
        "Pipeline 1 established that modern LLMs can reliably classify German "
        "oncology cases by cancer type. This report focuses exclusively on "
        "Pipeline 2 (treatment prediction), which is the clinically more "
        "challenging task requiring guideline-aware therapeutic reasoning."
    )

    doc.add_heading("Evaluation Pipeline (Treatment Prediction)", level=2)
    doc.add_paragraph(
        "The treatment prediction study uses a three-tier evaluation pipeline:"
    )
    add_bullet(doc,
        "Tier 1 \u2014 LLM Prediction: Each model receives the full clinical case "
        "and generates a therapy recommendation with reasoning.")
    add_bullet(doc,
        "Tier 2 \u2014 AI Judge Evaluation: Two AI judges (GPT-5.2 and MedGemma 27B) "
        "independently score each prediction on semantic match, clinical appropriateness, "
        "reasoning quality, and overall correctness.")
    add_bullet(doc,
        "Tier 3 \u2014 Uro-Oncologist Validation: A board-certified uro-oncologist reviews "
        "model predictions (therapy acceptable? quality rating) and judge evaluations "
        "(agree/partial/disagree with judge verdict).")

    doc.add_heading("Models Evaluated", level=2)
    add_styled_table(doc,
        ["Model", "Size", "Type", "Description"],
        [
            [model_name(mid), mid.split("-")[-1].upper() if "B" in mid else "",
             "Medical" if "med" in mid.lower() or "meditron" in mid.lower()
             else "General",
             MODEL_DESCRIPTIONS.get(mid, "")]
            for mid in sorted(MODEL_DISPLAY.keys())
        ],
        col_widths=[3.5, 2, 2, 8],
    )

    # ================================================================
    # 3. TECHNICAL INNOVATION & IMPACT (NEW)
    # ================================================================
    doc.add_heading("3. Technical Innovation & Impact", level=1)

    doc.add_paragraph(
        "This project introduces a comprehensive, reproducible evaluation methodology "
        "for clinical AI that addresses key challenges in deploying LLMs for medical "
        "decision support."
    )

    doc.add_heading("Three-Tier Evaluation Pipeline", level=2)
    doc.add_paragraph(
        "Unlike single-layer evaluations (model vs. ground truth), this project "
        "implements a three-tier pipeline that separates automated scoring from "
        "expert validation:"
    )
    add_bullet(doc,
        "Tier 1 — LLM Prediction: Six models with diverse architectures (2B–32B "
        "parameters, general-purpose and medical-specialized) generate therapy "
        "recommendations from structured German clinical case data.")
    add_bullet(doc,
        "Tier 2 — AI Judge Evaluation: Two independent AI judges (GPT-5.2 and "
        "MedGemma 27B) score each prediction across four dimensions: semantic match, "
        "clinical appropriateness, reasoning quality, and overall correctness.")
    add_bullet(doc,
        "Tier 3 — Uro-Oncologist Validation: A board-certified uro-oncologist reviews "
        "both model predictions and judge evaluations, creating a ground truth for "
        "evaluating the evaluators themselves.")

    doc.add_heading("Clinical Data Format", level=2)
    doc.add_paragraph(
        "All 69 clinical cases are stored in structured JSON format. The inference "
        "pipeline automatically detects and normalizes schema variations across cases, "
        "extracting ECOG, TNM staging, histology, and therapy fields."
    )

    doc.add_heading("Medical Review Web Platform", level=2)
    doc.add_paragraph(
        "A web application enables structured physician review "
        "of AI predictions and judge evaluations. The platform supports structured review "
        "workflows, Likert-scale and binary ratings, and exports data for "
        "statistical analysis."
    )


    doc.add_page_break()

    # ================================================================
    # 4. METHODOLOGY (NEW)
    # ================================================================
    doc.add_heading("4. Methodology", level=1)

    doc.add_heading("Treatment Prediction Prompt", level=2)
    doc.add_paragraph(
        "Each model receives a structured German-language prompt with the role "
        "\"Du bist ein erfahrener Onkologe, spezialisiert auf Nierenzellkarzinom\" "
        "(You are an experienced oncologist specialized in RCC). The prompt contains:"
    )
    add_bullet(doc,
        "Patient demographics: name, age, ECOG, Karnofsky, comorbidity, life expectancy")
    add_bullet(doc,
        "Clinical data: diagnosis, TNM staging (clinical + pathological), "
        "histology subtype, grading")
    add_bullet(doc,
        "Medical history: anamnesis free text, secondary diagnoses, current medication, "
        "imaging findings, IMDC risk factors, ICI eligibility, prior systemic therapies")
    add_bullet(doc,
        "Embedded therapy guidelines: Complete IMDC-stratified treatment algorithm for "
        "metastatic clear-cell RCC (first-line ICI-eligible and non-eligible, second-line) "
        "and non-metastatic RCC (surveillance, ablation, partial/radical nephrectomy) "
        "with Grades of Recommendation (GoR A/B/0)")
    add_bullet(doc,
        "Structured output: JSON with is_metastatic, IMDC risk, therapy recommendation, "
        "category, reasoning, and confidence score")

    doc.add_heading("Inference Hyperparameters", level=2)
    add_styled_table(doc,
        ["Parameter", "Standard Models", "Thinking Models", "Rationale"],
        [
            ["Temperature", "0.3", "0.6",
             "Low for deterministic medical output; higher for thinking chains"],
            ["Top-p", "0.95", "0.95",
             "Nucleus sampling for balanced diversity"],
            ["Max tokens", "32,768", "65,536",
             "Headroom for reasoning; thinking models consume tokens before JSON"],
            ["Seed", "42 (Modal only)", "42",
             "Deterministic results for reproducibility"],
            ["Structured output", "Yes (Pydantic)", "No",
             "Thinking models produce <think> blocks before JSON"],
        ],
        col_widths=[3, 3, 3, 6],
    )

    doc.add_heading("LLM-as-Judge Evaluation", level=2)
    doc.add_paragraph(
        "Two AI judges independently evaluate each prediction using a structured "
        "German prompt. The judge receives the clinical case, ground truth therapy, "
        "and the model's full prediction including reasoning. The judge prompt uses "
        "the role \"Du bist ein erfahrener Uro-Onkologe, der als Gutachter f\u00fcr "
        "KI-generierte Therapieempfehlungen fungiert\" (You are an experienced "
        "uro-oncologist serving as expert reviewer for AI-generated therapy "
        "recommendations)."
    )
    doc.add_paragraph(
        "The judge scores each prediction on three dimensions, combined into an "
        "overall score using a fixed weighting formula:"
    )
    add_styled_table(doc,
        ["Dimension", "Weight", "Scale", "Criteria"],
        [
            ["Semantic Match", "40%", "0\u20131",
             "Does the therapy match the ground truth? Same drug = 1.0, "
             "same class = 0.5\u20130.7, different class = 0\u20130.3"],
            ["Clinical Appropriateness", "40%", "0\u20131",
             "Is the therapy guideline-concordant regardless of exact match? "
             "First-choice = 0.9\u20131.0, acceptable alternative = 0.6\u20130.8"],
            ["Reasoning Quality", "20%", "0\u20131",
             "Is the clinical reasoning complete, logical, and medically correct? "
             "Evaluated for IMDC calculation, staging, and hallucinations"],
        ],
        col_widths=[3.5, 1.5, 1.5, 8],
    )
    doc.add_paragraph(
        "Overall Score = (Semantic \u00d7 0.4) + (Clinical \u00d7 0.4) + "
        "(Reasoning \u00d7 0.2). The judge also provides a binary is_correct verdict "
        "and a free-text reasoning critique in German."
    )

    doc.add_heading("Uro-Oncologist Validation Protocol", level=2)
    doc.add_paragraph(
        "Dr. Radu Alexa, a board-certified uro-oncologist, independently reviews both "
        "model predictions and judge evaluations through a custom web platform. "
        "Two "
        "distinct review types are conducted:"
    )
    add_styled_table(doc,
        ["Review Type", "Target", "Metrics", "Scale"],
        [
            ["Model Review", "LLM prediction",
             "Therapy acceptable, exact match, patient-oriented, quality",
             "Boolean, 0\u2013100, 0\u2013100, 0\u20139"],
            ["Judge Review", "AI judge evaluation",
             "Judge correct, reasoning quality, comment",
             "Agree/Partial/Disagree, 0\u201310, free text"],
        ],
        col_widths=[3, 3, 5, 4],
    )

    doc.add_page_break()

    # ================================================================
    # 5. PATIENT COHORT
    # ================================================================
    doc.add_heading("5. Patient Cohort", level=1)

    doc.add_paragraph(
        f"The dataset comprises {demo['n_cases']} anonymized RCC cases from German "
        "tumor board discussions. All patient names are pseudonymized."
    )

    add_chart(doc, charts["demographics"])

    doc.add_heading("Demographics Summary", level=2)
    add_styled_table(doc,
        ["Characteristic", "Value"],
        [
            ["Total cases", str(demo["n_cases"])],
            ["Age range", f"{demo['age_min']}\u2013{demo['age_max']} years"],
            ["Age mean / median",
             f"{demo['age_mean']:.0f} / {demo['age_median']:.0f} years"],
            ["Metastatic", f"{demo['n_metastatic']} ({demo['n_metastatic']/demo['n_cases']*100:.1f}%)"],
            ["Localized", f"{demo['n_localized']} ({demo['n_localized']/demo['n_cases']*100:.1f}%)"],
            ["Clear cell (ccRCC)", str(demo["n_clear_cell"])],
            ["Non-clear cell", str(demo["n_non_clear_cell"])],
            ["Histology not specified", str(demo["n_histology_unknown"])],
        ],
        col_widths=[6, 6],
    )

    doc.add_heading("ECOG Performance Status", level=2)
    ecog_rows = []
    for ecog, cnt in demo["ecog_counts"].items():
        desc = {0: "Fully active", 1: "Restricted but ambulatory",
                2: "Ambulatory, limited self-care", 3: "Limited self-care",
                4: "Completely disabled"}.get(ecog, "")
        ecog_rows.append([f"ECOG {ecog}", str(cnt),
                          f"{cnt/sum(demo['ecog_counts'].values())*100:.1f}%", desc])
    add_styled_table(doc,
        ["Status", "Count", "Percentage", "Description"],
        ecog_rows,
        col_widths=[2.5, 2, 2.5, 8],
    )

    doc.add_page_break()

    # ================================================================
    # 6. STUDY DESIGN & DATA OVERVIEW
    # ================================================================
    doc.add_heading("6. Study Design & Data Overview", level=1)

    doc.add_heading("Evaluation Scope", level=2)
    add_styled_table(doc,
        ["Component", "Count", "Details"],
        [
            ["RCC Cases", str(demo["n_cases"]),
             "Anonymized from German tumor boards"],
            ["LLM Models", "6",
             ", ".join(sorted(MODEL_DISPLAY.values()))],
            ["AI Judges", "2", "GPT-5.2, MedGemma 27B"],
            ["Total Predictions", str(ovr["total_predictions"]),
             f"{demo['n_cases']} cases \u00d7 6 models"],
            ["Judge Evaluations", str(len(judge_evals_df)),
             f"{demo['n_cases']} cases \u00d7 6 models \u00d7 2 judges"],
            ["Uro-Oncologist Model Reviews", str(len(reviews_df)),
             f"{reviews_df['case_id'].nunique()} cases \u00d7 6 models"],
            ["Uro-Oncologist Judge Reviews", str(len(judge_reviews_df)),
             f"{judge_reviews_df['case_id'].nunique()} cases \u00d7 6 models \u00d7 2 judges"],
        ],
        col_widths=[5, 3, 9],
    )

    doc.add_heading("Uro-Oncologist Review Scales", level=2)
    add_styled_table(doc,
        ["Metric", "Scale", "Description"],
        [
            ["Therapy Acceptable", "Yes / No",
             "Would the uro-oncologist accept this therapy for the patient?"],
            ["Recommendation Exact Match", "0\u2013100",
             "How closely does the prediction match the tumor board recommendation?"],
            ["Recommendation Patient-Oriented", "0\u2013100",
             "How appropriate is the recommendation for this specific patient?"],
            ["Prediction Quality", "0\u20139",
             "Overall quality of the model's prediction and reasoning"],
        ],
        col_widths=[4.5, 2, 9],
    )

    doc.add_heading("Judge Scoring Dimensions", level=2)
    add_styled_table(doc,
        ["Dimension", "Scale", "Description"],
        [
            ["Semantic Match", "0\u20131",
             "Does the prediction match the ground truth semantically?"],
            ["Clinical Score", "0\u20131",
             "Is the therapy clinically appropriate regardless of exact match?"],
            ["Reasoning Quality", "0\u20131",
             "Quality and correctness of the model's clinical reasoning"],
            ["Overall Score", "0\u20131",
             "Weighted composite of all dimensions"],
            ["Is Correct", "True / False",
             "Binary verdict: does the prediction match ground truth?"],
        ],
        col_widths=[3.5, 2, 9],
    )

    doc.add_page_break()

    # ================================================================
    # 7. MODEL PERFORMANCE \u2014 AUTOMATED EVALUATION (69 CASES)
    # ================================================================
    doc.add_heading("7. Model Performance \u2014 Automated Evaluation", level=1)

    doc.add_paragraph(
        f"All {ovr['total_predictions']} predictions across {demo['n_cases']} cases "
        "were evaluated by both AI judges. This section shows the automated metrics "
        "before any uro-oncologist validation."
    )

    add_chart(doc, charts["full_perf"])

    doc.add_heading("Automated Metrics Summary", level=2)
    add_styled_table(doc,
        ["Model", "Cases", "Met. Detect.", "Exact Match",
         "Judge Acc.", "Avg Score"],
        [
            [row["model_name"], str(row["n_cases"]),
             f"{row['met_accuracy']:.1f}%", f"{row['therapy_exact']:.1f}%",
             f"{row['judge_accuracy']:.1f}%", f"{row['avg_overall']:.2f}"]
            for _, row in pipeline["model_rows"].iterrows()
        ],
        col_widths=[3.5, 1.8, 2.5, 2.5, 2.5, 2.2],
    )

    doc.add_paragraph(
        f"Overall: {ovr['met_accuracy']:.1f}% of predictions correctly identified "
        f"metastatic status. {ovr['therapy_exact_rate']:.1f}% matched the tumor board "
        f"therapy exactly, while {ovr['therapy_accept_rate']:.1f}% were classified as "
        "clinically acceptable (broader than exact match)."
    )

    doc.add_heading("Detailed Judge Scores", level=2)
    add_styled_table(doc,
        ["Model", "Semantic", "Clinical", "Reasoning", "Overall"],
        [
            [row["model_name"],
             f"{row['avg_semantic']:.2f}", f"{row['avg_clinical']:.2f}",
             f"{row['avg_reasoning']:.2f}", f"{row['avg_overall']:.2f}"]
            for _, row in pipeline["model_rows"].iterrows()
        ],
        col_widths=[4, 2.5, 2.5, 2.5, 2.5],
    )

    doc.add_page_break()

    # ================================================================
    # 8. THERAPY CATEGORY ANALYSIS
    # ================================================================
    doc.add_heading("8. Therapy Category Analysis", level=1)

    doc.add_paragraph(
        "Each model's therapy prediction was classified into standard categories. "
        "The distribution reveals which treatment approaches models favor and how "
        "this varies across models."
    )

    add_chart(doc, charts["therapy_cats"])

    # Aggregate category counts
    cat_totals = predictions_df["pred_category_clean"].value_counts()
    cat_rows = []
    for cat, cnt in cat_totals.items():
        cat_rows.append([cat, str(cnt),
                         f"{cnt / len(predictions_df) * 100:.1f}%"])
    add_styled_table(doc,
        ["Therapy Category", "Count", "% of Predictions"],
        cat_rows[:8],
        col_widths=[5, 3, 4],
    )

    doc.add_paragraph(
        "IO + TKI (immunotherapy combined with tyrosine kinase inhibitor) and TKI Mono "
        "are the dominant predicted categories, reflecting current RCC treatment "
        "guidelines for metastatic disease. Surgery dominates predictions for "
        "localized cases."
    )

    doc.add_page_break()

    # ================================================================
    # 9. MODEL PERFORMANCE \u2014 DOCTOR REVIEW (45 CASES)
    # ================================================================
    doc.add_heading("9. Model Performance \u2014 Uro-Oncologist Review", level=1)

    doc.add_paragraph(
        f"Dr. Alexa reviewed {len(reviews_df)} model predictions across "
        f"{reviews_df['case_id'].nunique()} cases, providing "
        "expert assessment on therapy acceptability, exact match, patient orientation, "
        "and overall quality."
    )

    doc.add_heading("Therapy Acceptability Rate", level=2)
    add_chart(doc, charts["acceptability"])

    doc.add_heading("Average Prediction Quality", level=2)
    add_chart(doc, charts["quality"])

    doc.add_heading("Uro-Oncologist Review Summary", level=2)
    add_styled_table(doc,
        ["Model", "Cases", "Acceptable %", "Avg Exact Match",
         "Avg Patient-Oriented", "Avg Quality (0\u20139)"],
        [
            [row["model_name"], str(row["n_cases"]),
             f"{row['acceptable_pct']:.1f}%",
             f"{row['avg_exact_match']:.1f}",
             f"{row['avg_patient_oriented']:.1f}",
             f"{row['avg_quality']:.1f}"]
            for _, row in perf.iterrows()
        ],
        col_widths=[3.5, 1.8, 2.5, 3, 3, 3],
    )

    doc.add_page_break()

    # ================================================================
    # 10. CASE STUDIES
    # ================================================================
    if case_studies:
        doc.add_heading("10. Case Studies", level=1)

        doc.add_paragraph(
            "The following cases illustrate key patterns observed in the evaluation. "
            "Each case shows the ground truth therapy recommendation from the tumor board "
            "(Tumordiskussion), predictions from all 6 models, and evaluation outcomes."
        )

        study_labels = {
            "consensus_correct": "Case Study A: Model Consensus — Correct Prediction",
            "model_disagreement": "Case Study B: Model Disagreement",
            "doctor_judge_diverge": "Case Study C: Uro-Oncologist–Judge Divergence",
            "low_agreement": "Case Study C: Low Model Agreement",
        }

        for study_type, cid, st in case_studies:
            case = st["case"]
            doc.add_heading(study_labels.get(study_type, f"Case: {cid}"), level=2)

            # Patient summary
            pt = case["patient"]
            dx = case["diagnosis"]
            gt = case["ground_truth"]
            doc.add_paragraph(
                f"Case {cid}: {pt['age']}-year-old patient, "
                f"ECOG {pt['ecog'] if pt['ecog'] is not None else 'N/A'}, "
                f"{'metastatic' if gt['metastatic'] else 'localized'} "
                f"{dx.get('histologie_subtyp', 'RCC')}. "
                f"Diagnosis: {dx.get('diagnose_kurz', 'RCC')}."
            )
            doc.add_paragraph(
                f"Tumor Board Recommendation (Ground Truth): {gt['therapy']}"
            )

            # Model predictions table
            pred_rows = []
            for mid in sorted(MODEL_DISPLAY.keys()):
                pred = case["predictions"].get(mid, {})
                if not pred:
                    continue
                cat = pred.get("pred_category", "—")
                exact = "Yes" if pred.get("therapy_exact_match") else "No"
                accept = "Yes" if pred.get("therapy_acceptable") else "No"
                pred_rows.append([model_name(mid), cat, exact, accept])

            add_styled_table(doc,
                ["Model", "Predicted Category", "Exact Match", "Acceptable"],
                pred_rows,
                col_widths=[4, 4, 2.5, 2.5],
            )

            # Interpretation
            if study_type == "consensus_correct":
                doc.add_paragraph(
                    f"All or most models agreed on the correct therapy category. "
                    f"This case demonstrates that for well-defined clinical scenarios, "
                    f"current LLMs can reliably identify appropriate treatment approaches."
                )
            elif study_type == "model_disagreement":
                cats = [p.get("pred_category", "") for p in case["predictions"].values()]
                unique_cats = sorted(set(cats))
                doc.add_paragraph(
                    f"Models predicted {len(unique_cats)} different therapy categories: "
                    f"{', '.join(unique_cats)}. This divergence highlights cases where "
                    f"clinical ambiguity leads to different model interpretations."
                )
            elif study_type == "doctor_judge_diverge":
                doc.add_paragraph(
                    "The physician rated the therapy as acceptable, but both AI judges "
                    "classified it as incorrect. This illustrates how strict semantic "
                    "matching by AI judges may reject clinically valid alternative "
                    "therapies that an experienced oncologist would accept."
                )
            else:
                doc.add_paragraph(
                    "This case shows low agreement across models, reflecting the "
                    "clinical complexity of certain tumor board presentations."
                )
            doc.add_paragraph()

        doc.add_page_break()

    # ================================================================
    # 11. JUDGE SCORE DISTRIBUTIONS (ALL 69 CASES)
    # ================================================================
    doc.add_heading("11. Judge Score Distributions", level=1)

    doc.add_paragraph(
        f"Distribution of AI judge scores across all {demo['n_cases']} cases and "
        "6 models. This shows how each judge rates different models and the spread "
        "of scores across different scoring dimensions."
    )

    doc.add_heading("Overall Score by Model and Judge", level=2)
    add_chart(doc, charts["distributions"])

    doc.add_heading("Score Types by Judge", level=2)
    add_chart(doc, charts["score_types"])

    doc.add_heading("Distribution Summary", level=2)
    score_cols = ["semantic_score", "clinical_score",
                  "reasoning_quality", "overall_score"]
    score_labels = ["Semantic", "Clinical", "Reasoning", "Overall"]
    dist_rows = []
    for jid in JUDGE_IDS:
        jdata = judge_evals_df[judge_evals_df["judge_id"] == jid]
        for col, label in zip(score_cols, score_labels):
            vals = jdata[col].dropna()
            dist_rows.append([
                judge_name(jid), label,
                f"{vals.mean():.3f}", f"{vals.median():.3f}",
                f"{vals.std():.3f}", f"{vals.min():.2f}", f"{vals.max():.2f}"])

    add_styled_table(doc,
        ["Judge", "Score Type", "Mean", "Median", "Std Dev", "Min", "Max"],
        dist_rows,
        col_widths=[3, 2.5, 2, 2, 2, 1.5, 1.5],
    )

    doc.add_page_break()

    # ================================================================
    # 12. AGREEMENT: DOCTOR VS AI JUDGE
    # ================================================================
    doc.add_heading("12. Agreement: Uro-Oncologist vs AI Judge", level=1)

    if agreement:
        a_first = list(agreement.values())[0]
        doc.add_paragraph(
            f"Agreement analysis based on {a_first['n_cases']} cases with complete "
            f"uro-oncologist reviews and judge evaluations ({a_first['n_pairs']} "
            "prediction\u2013evaluation pairs per judge). Cohen's Kappa measures "
            "agreement beyond chance between the uro-oncologist's therapy acceptability "
            "rating and the judge's correctness verdict."
        )

        doc.add_heading("Confusion Matrices", level=2)
        add_chart(doc, charts["confusion"])

        doc.add_heading("Agreement Metrics", level=2)
        jids_a = [jid for jid in JUDGE_IDS if jid in agreement]
        add_styled_table(doc,
            ["Metric", *[judge_name(jid) for jid in jids_a]],
            [
                ["N pairs",
                 *[str(agreement[jid]["n_pairs"]) for jid in jids_a]],
                ["Cohen's \u03ba",
                 *[f"{agreement[jid]['kappa']:.3f}" for jid in jids_a]],
                ["Agreement Rate",
                 *[f"{agreement[jid]['agreement_rate'] * 100:.1f}%" for jid in jids_a]],
                ["Sensitivity",
                 *[f"{agreement[jid]['sensitivity']:.3f}" for jid in jids_a]],
                ["Specificity",
                 *[f"{agreement[jid]['specificity']:.3f}" for jid in jids_a]],
                ["Precision",
                 *[f"{agreement[jid]['precision']:.3f}" for jid in jids_a]],
                ["F1 Score",
                 *[f"{agreement[jid]['f1']:.3f}" for jid in jids_a]],
            ],
            col_widths=[4, 4, 4],
        )

        doc.add_paragraph()
        for jid in jids_a:
            a = agreement[jid]
            doc.add_paragraph(
                f"{judge_name(jid)}: \u03ba = {a['kappa']:.3f} indicates "
                f"{kappa_interpretation(a['kappa'])} agreement. "
                f"Sensitivity = {a['sensitivity']:.1%}, "
                f"Specificity = {a['specificity']:.1%}.")

    doc.add_page_break()

    # ================================================================
    # 13. DOCTOR'S DIRECT RATING OF JUDGES

    # ================================================================
    doc.add_heading("13. Uro-Oncologist's Direct Rating of AI Judges", level=1)

    if ratings:
        doc.add_paragraph(
            f"Dr. Alexa directly reviewed {len(judge_reviews_df)} judge evaluations "
            f"across {judge_reviews_df['case_id'].nunique()} cases, rating whether "
            "the judge's assessment was correct (agree/partial/disagree) and the "
            "quality of the judge's reasoning."
        )
        add_chart(doc, charts["ratings"])

        jids_r = [jid for jid in JUDGE_IDS if jid in ratings]
        add_styled_table(doc,
            ["Metric", *[judge_name(jid) for jid in jids_r]],
            [
                ["Total Reviews",
                 *[str(ratings[jid]["n"]) for jid in jids_r]],
                ["Agree",
                 *[f"{ratings[jid]['agree']} ({ratings[jid]['agree_pct']:.1f}%)"
                   for jid in jids_r]],
                ["Partial",
                 *[f"{ratings[jid]['partial']} ({ratings[jid]['partial_pct']:.1f}%)"
                   for jid in jids_r]],
                ["Disagree",
                 *[f"{ratings[jid]['disagree']} ({ratings[jid]['disagree_pct']:.1f}%)"
                   for jid in jids_r]],
                ["Avg Reasoning Quality",
                 *[f"{ratings[jid]['avg_reasoning_quality']:.1f}/10"
                   for jid in jids_r]],
            ],
            col_widths=[5, 4.5, 4.5],
        )

    doc.add_page_break()

    # ================================================================
    # 14. PER-MODEL JUDGE ACCURACY
    # ================================================================
    doc.add_heading("14. Per-Model Judge Accuracy", level=1)

    if per_model_acc:
        doc.add_paragraph(
            "This heatmap shows the agreement rate (%) between each judge and the "
            "uro-oncologist, broken down by model."
        )
        add_chart(doc, charts["per_model"])

        jids_pm = list(JUDGE_IDS.keys())
        models = sorted(set().union(
            *[set(per_model_acc[jid].keys())
              for jid in jids_pm if jid in per_model_acc]))
        doc_acc = reviews_df.groupby("model_id")[
            "therapy_acceptable_ra"].mean() * 100

        add_styled_table(doc,
            ["Model", "Uro-Oncologist Acceptable %",
             *[f"{judge_name(jid)} Agr." for jid in jids_pm]],
            [
                [model_name(mid), f"{doc_acc.get(mid, 0):.1f}%",
                 *[f"{per_model_acc.get(jid, {}).get(mid, 0):.1f}%"
                   for jid in jids_pm]]
                for mid in models
            ],
            col_widths=[4, 3.5, 3.5, 3.5],
        )

    doc.add_page_break()

    # ================================================================
    # 15. INTER-JUDGE AGREEMENT
    # ================================================================
    doc.add_heading("15. Inter-Judge Agreement", level=1)

    if inter_judge:
        doc.add_paragraph(
            f"Agreement between GPT-5.2 and MedGemma 27B across "
            f"{inter_judge['n_pairs']} evaluation pairs "
            f"({inter_judge['n_cases']} cases \u00d7 6 models)."
        )
        add_chart(doc, charts["inter_judge"])

        k = inter_judge["kappa"]
        doc.add_paragraph(
            f"Cohen's \u03ba = {k:.3f} ({kappa_interpretation(k)} agreement). "
            f"Overall concordance: {inter_judge['agreement_rate'] * 100:.1f}%."
        )

    doc.add_page_break()

    # ================================================================
    # 16. MEDGEMMA SELF-JUDGING BIAS
    # ================================================================
    doc.add_heading("16. MedGemma Self-Judging Bias", level=1)

    if mg_bias:
        doc.add_paragraph(
            "MedGemma serves dual roles: both as a predictive model and as a judge. "
            "This analysis tests whether MedGemma shows bias when evaluating its "
            "own predictions compared to other models' predictions."
        )
        add_chart(doc, charts["mg_bias"])

        add_styled_table(doc,
            ["Metric", "Self-Judging", "Judging Others"],
            [
                ["N evaluations", str(mg_bias["self_n"]),
                 str(mg_bias["other_n"])],
                ["Mean Overall Score", f"{mg_bias['self_mean']:.3f}",
                 f"{mg_bias['other_mean']:.3f}"],
                ["Median Overall Score", f"{mg_bias['self_median']:.3f}",
                 f"{mg_bias['other_median']:.3f}"],
            ],
            col_widths=[5, 4, 4],
        )

        sig = ("statistically significant" if mg_bias["p_val"] < 0.05
               else "not statistically significant")
        direction = "higher" if mg_bias["self_mean"] > mg_bias["other_mean"] \
            else "lower"
        diff = abs(mg_bias["self_mean"] - mg_bias["other_mean"])
        doc.add_paragraph(
            f"Mann-Whitney U test: U = {mg_bias['u_stat']:.0f}, "
            f"p = {mg_bias['p_val']:.4f} ({sig}). "
            f"MedGemma gives {direction} scores to its own predictions by "
            f"{diff:.3f} points on average."
        )

    doc.add_page_break()

    # ================================================================
    # 17. CLINICAL SAFETY ANALYSIS
    # ================================================================
    doc.add_heading("17. Clinical Safety Analysis", level=1)

    if safety:
        doc.add_paragraph(
            "Clinical safety is assessed by examining two types of judge errors "
            "when compared to the uro-oncologist's assessment:"
        )
        add_bullet(doc,
            "False Positive (dangerous): Judge approves a prediction the uro-oncologist "
            "rejects. Could lead to inappropriate treatment.")
        add_bullet(doc,
            "False Negative (overly strict): Judge rejects a prediction the uro-oncologist "
            "approves. Could prevent appropriate treatment.")

        jids_s = [jid for jid in JUDGE_IDS if jid in safety]
        add_styled_table(doc,
            ["Safety Metric", *[judge_name(jid) for jid in jids_s]],
            [
                ["Total Pairs",
                 *[str(safety[jid]["n"]) for jid in jids_s]],
                ["Judge Approvals",
                 *[str(safety[jid]["n_judge_positive"]) for jid in jids_s]],
                ["Judge Rejections",
                 *[str(safety[jid]["n_judge_negative"]) for jid in jids_s]],
                ["False Positives (dangerous)",
                 *[f"{safety[jid]['fp']} ({safety[jid]['fp_rate']:.1f}%)"
                   for jid in jids_s]],
                ["False Negatives (overly strict)",
                 *[f"{safety[jid]['fn']} ({safety[jid]['fn_rate']:.1f}%)"
                   for jid in jids_s]],
            ],
            col_widths=[5, 4.5, 4.5],
        )

        doc.add_paragraph()
        for jid in jids_s:
            s = safety[jid]
            doc.add_paragraph(
                f"{judge_name(jid)}: {s['fp']} false positives out of "
                f"{s['n_judge_positive']} approvals "
                f"({s['fp_rate']:.1f}% dangerous error rate). "
                f"{s['fn']} false negatives out of "
                f"{s['n_judge_negative']} rejections "
                f"({s['fn_rate']:.1f}% overly strict rate)."
            )

    doc.add_page_break()

    # ================================================================
    # 18. SUMMARY COMPARISON: GPT-5.2 VS MEDGEMMA 27B
    # ================================================================
    doc.add_heading("18. Summary Comparison: GPT-5.2 vs MedGemma 27B", level=1)

    doc.add_paragraph(
        "Side-by-side comparison of all computed metrics for both AI judges."
    )

    jids_all = list(JUDGE_IDS.keys())
    metrics = []

    if agreement:
        jids_a = [jid for jid in jids_all if jid in agreement]
        metrics.append(("Cohen's \u03ba (vs Uro-Oncologist)",
                        *[f"{agreement[jid]['kappa']:.3f}" for jid in jids_a]))
        metrics.append(("Agreement Rate",
                        *[f"{agreement[jid]['agreement_rate'] * 100:.1f}%"
                          for jid in jids_a]))
        metrics.append(("Sensitivity",
                        *[f"{agreement[jid]['sensitivity']:.3f}" for jid in jids_a]))
        metrics.append(("Specificity",
                        *[f"{agreement[jid]['specificity']:.3f}" for jid in jids_a]))
        metrics.append(("F1 Score",
                        *[f"{agreement[jid]['f1']:.3f}" for jid in jids_a]))

    if correlations:
        jids_c = [jid for jid in jids_all if jid in correlations]
        metrics.append(("Corr: Quality (\u03c1)",
                        *[f"{correlations[jid]['quality_r']:.3f}" for jid in jids_c]))
        metrics.append(("Corr: Exact Match (\u03c1)",
                        *[f"{correlations[jid]['exact_r']:.3f}" for jid in jids_c]))

    if ratings:
        jids_r = [jid for jid in jids_all if jid in ratings]
        metrics.append(("Uro-Oncologist Agree %",
                        *[f"{ratings[jid]['agree_pct']:.1f}%"
                          for jid in jids_r]))
        metrics.append(("Avg Reasoning Quality",
                        *[f"{ratings[jid]['avg_reasoning_quality']:.1f}/10"
                          for jid in jids_r]))

    if safety:
        jids_s = [jid for jid in jids_all if jid in safety]
        metrics.append(("False Positive Rate",
                        *[f"{safety[jid]['fp_rate']:.1f}%"
                          for jid in jids_s]))
        metrics.append(("False Negative Rate",
                        *[f"{safety[jid]['fn_rate']:.1f}%"
                          for jid in jids_s]))

    for label, col in [("Avg Overall Score", "overall_score"),
                       ("Avg Clinical Score", "clinical_score"),
                       ("Avg Semantic Score", "semantic_score"),
                       ("Avg Reasoning Score", "reasoning_quality")]:
        vals = []
        for jid in jids_all:
            vals.append(
                f"{judge_evals_df[judge_evals_df['judge_id'] == jid][col].mean():.3f}")
        metrics.append((label, *vals))

    add_styled_table(doc,
        ["Metric", *[judge_name(jid) for jid in jids_all]],
        [list(m) for m in metrics],
        col_widths=[6, 4, 4],
    )

    doc.add_page_break()

    # ================================================================
    # 19. GERMAN-ENGLISH MEDICAL GLOSSARY
    # ================================================================
    doc.add_heading("19. German\u2013English Medical Glossary", level=1)

    doc.add_paragraph(
        "Key German medical terms used throughout this report and the clinical "
        "case data. Terms are preserved in their original German form to maintain "
        "clinical precision."
    )

    add_styled_table(doc,
        ["German Term", "English Translation", "Context"],
        [
            ["Nierenzellkarzinom (NCC/RCC)", "Renal Cell Carcinoma",
             "Primary cancer type in this study"],
            ["Tumordiskussion / Tumorboard", "Tumor Board Discussion",
             "Multidisciplinary case conference"],
            ["Systemtherapie", "Systemic Therapy",
             "Drug-based cancer treatment (chemo, IO, TKI)"],
            ["Klarzellig (ccRCC)", "Clear Cell",
             "Most common RCC histological subtype"],
            ["Metastasiert", "Metastatic",
             "Cancer spread beyond primary organ"],
            ["Lokalisiert", "Localized",
             "Cancer confined to primary organ"],
            ["Nephrektomie", "Nephrectomy",
             "Surgical removal of kidney"],
            ["Erstlinientherapie", "First-line Therapy",
             "Initial treatment regimen"],
            ["Zweitlinientherapie", "Second-line Therapy",
             "Treatment after first-line failure"],
            ["Lebenserwartung", "Life Expectancy",
             "Estimated patient survival time"],
            ["Nebendiagnosen", "Comorbidities",
             "Co-existing medical conditions"],
            ["Bildgebung", "Imaging",
             "Radiological examinations (CT, MRI, etc.)"],
            ["Histologie-Subtyp", "Histology Subtype",
             "Microscopic tissue classification"],
            ["Leitlinienkonform", "Guideline-Concordant",
             "Consistent with clinical practice guidelines"],
        ],
        col_widths=[4.5, 4, 5.5],
    )

    doc.add_page_break()

    # ================================================================
    # 20. CONCLUSIONS & RECOMMENDATIONS
    # ================================================================
    doc.add_heading("20. Conclusions & Recommendations", level=1)

    doc.add_heading("Key Findings", level=2)

    add_bullet(doc,
        f"Model Performance: {best_model['model_name']} achieved the highest "
        f"uro-oncologist-rated quality ({best_model['avg_quality']:.1f}/9) with "
        f"{best_model['acceptable_pct']:.1f}% therapy acceptability. "
        f"{best_auto['model_name']} scored highest on automated judge evaluation "
        f"({best_auto['avg_overall']:.2f}/1.0).")

    if agreement:
        best_j = max(agreement.items(), key=lambda x: x[1]["kappa"])
        add_bullet(doc,
            f"Best AI Judge: {judge_name(best_j[0])} showed the strongest agreement "
            f"with the uro-oncologist (\u03ba = {best_j[1]['kappa']:.3f}). Both judges show "
            "moderate agreement, indicating they are useful but not perfect proxies "
            "for expert clinical judgment.")

    add_bullet(doc,
        f"Therapy Categories: IO+TKI and TKI Mono dominate model predictions, "
        f"consistent with current RCC treatment guidelines for the "
        f"{demo['n_metastatic']}/{demo['n_cases']} metastatic cases in the cohort.")

    if safety:
        safest = min(safety.items(), key=lambda x: x[1]["fp_rate"])
        add_bullet(doc,
            f"Clinical Safety: {judge_name(safest[0])} has the lowest dangerous "
            f"error rate ({safest[1]['fp_rate']:.1f}%). Both judges tend to be "
            "overly strict (high false negative rates), which is safer than being "
            "too permissive in a clinical context.")

    if mg_bias and mg_bias["p_val"] < 0.05:
        add_bullet(doc,
            "Self-Judging Bias: MedGemma shows statistically significant "
            "self-judging bias. When MedGemma serves as both predictor and judge, "
            "its self-evaluations should be interpreted with caution.")

    doc.add_heading("Recommendations", level=2)

    for rec in [
        "AI judges should be used as screening tools, not final arbiters. Uro-oncologist "
        "review remains essential for clinical safety.",
        "Using both GPT-5.2 and MedGemma as judges and flagging disagreements "
        "could improve evaluation reliability \u2014 their complementary strengths "
        "(GPT-5.2 higher specificity, MedGemma higher sensitivity) create a more "
        "robust assessment.",
        "Models with high acceptability rates but lower exact match scores may "
        "still provide clinically valid alternative recommendations worthy of "
        "tumor board discussion.",
        "The strong Spearman correlations (\u03c1 > 0.64) between judge scores and "
        "uro-oncologist ratings suggest automated judge scores are useful proxies for "
        "prediction quality, enabling scalable evaluation.",
        "Future work should expand the dataset to include additional cancer types, "
        "test with multiple physician reviewers for inter-rater reliability, and "
        "evaluate medical-specialized models like Med-PaLM and BioMistral.",
    ]:
        add_bullet(doc, rec)

    doc.add_heading("Limitations", level=2)
    doc_cases_reviewed = reviews_df['case_id'].nunique()
    judge_cases_reviewed = judge_reviews_df['case_id'].nunique()
    if doc_cases_reviewed >= demo['n_cases'] and judge_cases_reviewed >= demo['n_cases']:
        coverage_text = (
            f"The uro-oncologist reviewed all {demo['n_cases']} cases for both model "
            "evaluation and judge evaluation, providing complete coverage."
        )
    else:
        coverage_text = (
            f"The uro-oncologist's reviews covered {doc_cases_reviewed} of "
            f"{demo['n_cases']} cases for model evaluation and "
            f"{judge_cases_reviewed} cases for judge evaluation, limiting "
            "the agreement analysis."
        )
    doc.add_paragraph(
        "This study relies on a single physician reviewer, which may introduce "
        "individual assessment bias. The case dataset is limited to RCC from a "
        f"single institution's tumor boards. {coverage_text} Ground truth "
        "represents the tumor board consensus, which is one valid approach but "
        "not necessarily the only correct therapy. All cases use German medical "
        "terminology, which may affect model performance compared to "
        "English-language clinical data."
    )

    doc.add_heading("Open Questions", level=2)
    doc.add_paragraph(
        "Several methodological questions remain open and may affect interpretation "
        "of the results:"
    )
    add_bullet(doc,
        "Ground Truth Definition: Is the ground_truth_therapy field the tumor board "
        "consensus recommendation or the actual treatment administered? The distinction "
        "matters when tumor board recommends X but the patient receives Y.")
    add_bullet(doc,
        "IMDC for Non-Clear-Cell RCC: IMDC risk stratification is only validated for "
        "clear-cell mRCC. Models sometimes calculate IMDC for papillary/chromophobe "
        "subtypes with a disclaimer. The preferred approach (skip vs. calculate with "
        "caveat) has not been standardized.")
    add_bullet(doc,
        "ICI Eligibility: Many cases have null ICI eligibility. The criteria for "
        "determining whether an ICI combination is feasible (autoimmune disease, "
        "prior transplant, active infection) are not explicitly coded in the data.")
    add_bullet(doc,
        "Therapy Guidelines Completeness: The embedded prompt guidelines cover "
        "first/second-line therapies but may not include adjuvant pembrolizumab, "
        "non-clear-cell-specific protocols, third-line options, oligometastatic "
        "management, or cytoreductive nephrectomy criteria.")
    add_bullet(doc,
        "Four JSON Schema Variants: The dataset uses four different JSON structures "
        "across 69 cases. While the pipeline handles all variants, edge cases in "
        "field mapping may introduce subtle data quality issues.")

    # ── Save ──
    OUTPUT_DIR.mkdir(exist_ok=True)
    doc.save(str(OUTPUT_FILE))
    print(f"\nReport saved to: {OUTPUT_FILE}")
    return OUTPUT_FILE


# ── Markdown Report ────────────────────────────────────────────────────────

def md_table(headers, rows):
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c).replace("\n", " ") for c in row) + " |")
    return "\n".join(lines)


def build_markdown_report(reviews_df, judge_reviews_df, judge_evals_df,
                          predictions_df, cases_data, run_summaries_df, chart_dir):
    print("\nGenerating Markdown report...")
    demo = compute_demographics(cases_data)
    pipeline = compute_full_pipeline(predictions_df, cases_data)
    perf = compute_model_performance(reviews_df)
    agreement = compute_agreement(reviews_df, judge_evals_df)
    correlations = compute_correlations(reviews_df, judge_evals_df)
    ratings = compute_judge_ratings(judge_reviews_df)
    per_model_acc = compute_per_model_judge_accuracy(reviews_df, judge_evals_df)
    inter_judge = compute_inter_judge_agreement(judge_evals_df)
    mg_bias = compute_medgemma_bias(judge_evals_df)
    safety = compute_clinical_safety(reviews_df, judge_evals_df)

    case_studies = select_case_studies(cases_data, reviews_df, judge_evals_df)

    best_model = perf.iloc[0]
    best_auto = pipeline["model_rows"].iloc[0]
    ovr = pipeline["overall"]
    img = "charts"  # relative to findings/ where the .md lives

    lines = []
    w = lines.append  # shorthand

    # ── TITLE ──
    w("# Evaluation Report")
    w("")
    w("**Uro-Oncologist vs AI Judges in Medical Oncology — Therapy Recommendation Assessment**")
    w("")
    w(f"> February 2026 | Renal Cell Carcinoma (RCC) — {demo['n_cases']} Cases from German Tumor Boards")
    w(">")
    w("> Prepared for Google AI Hackathon 2026")
    w(">")
    w("> Reviewer: Dr. Radu Alexa, Board-Certified Uro-Oncologist")
    w("")
    w("---")
    w("")

    # ── 1. EXECUTIVE SUMMARY ──
    w("## 1. Executive Summary")
    w("")
    w(f"This report presents a novel three-tier evaluation pipeline for assessing "
      f"AI-generated therapy recommendations in clinical oncology. Across "
      f"{ovr['total_predictions']} predictions from 6 LLMs on {demo['n_cases']} "
      f"renal cell carcinoma (Nierenzellkarzinom, RCC) cases from German tumor boards "
      f"(Tumordiskussionen), the pipeline combines automated AI judging with expert "
      f"physician validation to establish a scalable, reproducible evaluation framework.")
    w("")

    w("### Key Findings")
    w("")
    w(f"- Across all {ovr['total_predictions']} predictions: "
      f"**{ovr['met_accuracy']:.1f}%** metastatic detection accuracy, "
      f"**{ovr['therapy_exact_rate']:.1f}%** exact therapy match, "
      f"**{ovr['therapy_accept_rate']:.1f}%** clinically acceptable therapies.")
    w(f"- **Best model by uro-oncologist review:** {best_model['model_name']} "
      f"({best_model['avg_quality']:.1f}/9 quality, "
      f"{best_model['acceptable_pct']:.1f}% acceptable).")
    w(f"- **Best model by automated judge score:** {best_auto['model_name']} "
      f"(avg overall {best_auto['avg_overall']:.2f}/1.0).")

    for jid in agreement:
        k = agreement[jid]["kappa"]
        w(f"- {judge_name(jid)} shows **{kappa_interpretation(k)} agreement** "
          f"with the uro-oncologist (Cohen's κ = {k:.3f}).")

    if inter_judge:
        w(f"- **Inter-judge agreement:** κ = {inter_judge['kappa']:.3f}, "
          f"{inter_judge['agreement_rate'] * 100:.1f}% concordance "
          f"across {inter_judge['n_pairs']} evaluation pairs.")

    if mg_bias:
        direction = "higher" if mg_bias["self_mean"] > mg_bias["other_mean"] else "lower"
        sig = "significant" if mg_bias["p_val"] < 0.05 else "not significant"
        w(f"- **MedGemma self-judging bias:** {direction} scores for own predictions "
          f"({mg_bias['self_mean']:.2f} vs {mg_bias['other_mean']:.2f}), "
          f"{sig} (p={mg_bias['p_val']:.3f}).")

    if safety:
        safest = min(safety.items(), key=lambda x: x[1]["fp_rate"])
        w(f"- **Clinical safety:** {judge_name(safest[0])} has lowest dangerous error rate "
          f"({safest[1]['fp_rate']:.1f}% false positives).")
    w("")

    # ── 2. PROJECT OVERVIEW ──
    w("---")
    w("")
    w("## 2. Project Overview")
    w("")
    w("This project investigates whether large language models (LLMs) can support "
      "clinical decision-making in oncology by generating appropriate therapy "
      "recommendations for renal cell carcinoma (RCC) patients presented at German "
      "tumor board discussions.")
    w("")
    w("### Clinical Context")
    w("")
    w("Tumor boards (Tumordiskussionen) are multidisciplinary meetings where specialists "
      "review complex cancer cases and agree on treatment recommendations. Each case "
      "includes patient demographics, comorbidities, TNM staging, histological subtype, "
      "prior therapies, and imaging findings. The ground truth for this study is the "
      "consensus therapy recommendation from the tumor board.")
    w("")

    w("### Project Scope: Two Evaluation Pipelines")
    w("")
    w(md_table(
        ["Pipeline", "Task", "Models Tested", "Best Result", "Status"],
        [
            ["1. Classification", "7-class cancer type detection",
             "14 models", "100% accuracy (MiMo v2 Flash)", "Complete"],
            ["2. Treatment Prediction", "RCC therapy recommendation",
             "6 models", "See detailed results below", "Complete + Validated"],
        ],
    ))
    w("")
    w("Pipeline 1 established that modern LLMs can reliably classify German "
      "oncology cases by cancer type. **This report focuses exclusively on "
      "Pipeline 2** (treatment prediction), which is the clinically more "
      "challenging task requiring guideline-aware therapeutic reasoning.")
    w("")

    w("### Evaluation Pipeline (Treatment Prediction)")
    w("")
    w("The study uses a **three-tier evaluation pipeline:**")
    w("")
    w("1. **Tier 1 — LLM Prediction:** Each model receives the full clinical case "
      "and generates a therapy recommendation with reasoning.")
    w("2. **Tier 2 — AI Judge Evaluation:** Two AI judges (GPT-5.2 and MedGemma 27B) "
      "independently score each prediction on semantic match, clinical appropriateness, "
      "reasoning quality, and overall correctness.")
    w("3. **Tier 3 — Uro-Oncologist Validation:** A board-certified uro-oncologist reviews "
      "model predictions and judge evaluations.")
    w("")

    w("### Models Evaluated")
    w("")
    w(md_table(
        ["Model", "Type", "Description"],
        [
            [model_name(mid),
             "Medical" if "med" in mid.lower() or "meditron" in mid.lower()
             else "General",
             MODEL_DESCRIPTIONS.get(mid, "")]
            for mid in sorted(MODEL_DISPLAY.keys())
        ],
    ))
    w("")

    # ── 3. TECHNICAL INNOVATION ──
    w("---")
    w("")
    w("## 3. Technical Innovation & Impact")
    w("")
    w("This project introduces a comprehensive, reproducible evaluation methodology "
      "for clinical AI that addresses key challenges in deploying LLMs for medical "
      "decision support.")
    w("")

    w("### Three-Tier Evaluation Pipeline")
    w("")
    w("Unlike single-layer evaluations (model vs. ground truth), this project "
      "implements a three-tier pipeline that separates automated scoring from "
      "expert validation:")
    w("")
    w("- **Tier 1 — LLM Prediction:** Six models with diverse architectures (2B–32B "
      "parameters, general-purpose and medical-specialized) generate therapy "
      "recommendations from structured German clinical case data.")
    w("- **Tier 2 — AI Judge Evaluation:** Two independent AI judges score each "
      "prediction across four dimensions: semantic match, clinical appropriateness, "
      "reasoning quality, and overall correctness.")
    w("- **Tier 3 — Uro-Oncologist Validation:** A board-certified uro-oncologist "
      "reviews both model predictions and judge evaluations, creating a ground "
      "truth for evaluating the evaluators themselves.")
    w("")

    w("### Clinical Data Format")
    w("")
    w("All 69 clinical cases are stored in structured JSON format. The inference "
      "pipeline automatically detects and normalizes schema variations across cases, "
      "extracting ECOG, TNM staging, histology, and therapy fields.")
    w("")

    w("### Medical Review Web Platform")
    w("")
    w("A web application enables structured physician review "
      "of AI predictions and judge evaluations. The platform supports structured review "
      "workflows, Likert-scale and binary ratings, and exports data for "
      "statistical analysis.")
    w("")


    # ── 4. METHODOLOGY ──
    w("---")
    w("")
    w("## 4. Methodology")
    w("")

    w("### Treatment Prediction Prompt")
    w("")
    w("Each model receives a structured German-language prompt with the role "
      "\"Du bist ein erfahrener Onkologe, spezialisiert auf Nierenzellkarzinom\" "
      "(You are an experienced oncologist specialized in RCC). The prompt contains:")
    w("")
    w("- **Patient demographics:** name, age, ECOG, Karnofsky, comorbidity, life expectancy")
    w("- **Clinical data:** diagnosis, TNM staging (clinical + pathological), "
      "histology subtype, grading")
    w("- **Medical history:** anamnesis, secondary diagnoses, medication, imaging, "
      "IMDC risk factors, ICI eligibility, prior systemic therapies")
    w("- **Embedded therapy guidelines:** Complete IMDC-stratified treatment algorithm "
      "for metastatic clear-cell RCC and non-metastatic RCC with GoR A/B/0")
    w("- **Structured output:** JSON with is_metastatic, IMDC risk, therapy, category, "
      "reasoning, and confidence")
    w("")

    w("### Inference Hyperparameters")
    w("")
    w(md_table(
        ["Parameter", "Standard Models", "Thinking Models", "Rationale"],
        [
            ["Temperature", "0.3", "0.6",
             "Low for deterministic medical output; higher for thinking chains"],
            ["Top-p", "0.95", "0.95",
             "Nucleus sampling for balanced diversity"],
            ["Max tokens", "32,768", "65,536",
             "Headroom for reasoning; thinking models consume tokens before JSON"],
            ["Seed", "42 (Modal only)", "42",
             "Deterministic results for reproducibility"],
            ["Structured output", "Yes (Pydantic)", "No",
             "Thinking models produce `<think>` blocks before JSON"],
        ],
    ))
    w("")

    w("### LLM-as-Judge Evaluation")
    w("")
    w("Two AI judges independently evaluate each prediction using a structured "
      "German prompt with the role \"Du bist ein erfahrener Uro-Onkologe, der als "
      "Gutachter für KI-generierte Therapieempfehlungen fungiert.\"")
    w("")
    w("**Judge Scoring Formula:**")
    w("")
    w("```")
    w("overall_score = (semantic_score × 0.4) + (clinical_score × 0.4) + (reasoning_quality × 0.2)")
    w("```")
    w("")
    w(md_table(
        ["Dimension", "Weight", "Scale", "Criteria"],
        [
            ["Semantic Match", "40%", "0–1",
             "Same drug=1.0, same class=0.5–0.7, different=0–0.3"],
            ["Clinical Appropriateness", "40%", "0–1",
             "First-choice=0.9–1.0, acceptable alternative=0.6–0.8"],
            ["Reasoning Quality", "20%", "0–1",
             "Complete and correct=0.8–1.0, errors=0–0.4"],
        ],
    ))
    w("")

    w("### Uro-Oncologist Validation Protocol")
    w("")
    w(md_table(
        ["Review Type", "Target", "Metrics", "Scale"],
        [
            ["Model Review", "LLM prediction",
             "Therapy acceptable, exact match, patient-oriented, quality",
             "Boolean, 0–100, 0–100, 0–9"],
            ["Judge Review", "AI judge evaluation",
             "Judge correct, reasoning quality, comment",
             "Agree/Partial/Disagree, 0–10, free text"],
        ],
    ))
    w("")

    # ── 5. PATIENT COHORT ──
    w("---")
    w("")
    w("## 5. Patient Cohort")
    w("")
    w(f"The dataset comprises **{demo['n_cases']} anonymized RCC cases** from German "
      "tumor board discussions. All patient names are pseudonymized.")
    w("")
    w(f"![Patient Demographics]({img}/demographics.png)")
    w("")
    w(md_table(
        ["Characteristic", "Value"],
        [
            ["Total cases", str(demo["n_cases"])],
            ["Age range", f"{demo['age_min']}–{demo['age_max']} years"],
            ["Age mean / median", f"{demo['age_mean']:.0f} / {demo['age_median']:.0f} years"],
            ["Metastatic", f"{demo['n_metastatic']} ({demo['n_metastatic']/demo['n_cases']*100:.1f}%)"],
            ["Localized", f"{demo['n_localized']} ({demo['n_localized']/demo['n_cases']*100:.1f}%)"],
            ["Clear cell (ccRCC)", str(demo["n_clear_cell"])],
            ["Non-clear cell", str(demo["n_non_clear_cell"])],
            ["Histology not specified", str(demo["n_histology_unknown"])],
        ],
    ))
    w("")

    # ── 6. STUDY DESIGN ──
    w("---")
    w("")
    w("## 6. Study Design & Data Overview")
    w("")
    w(md_table(
        ["Component", "Count", "Details"],
        [
            ["RCC Cases", str(demo["n_cases"]),
             "Anonymized from German tumor boards"],
            ["LLM Models", "6",
             ", ".join(sorted(MODEL_DISPLAY.values()))],
            ["AI Judges", "2", "GPT-5.2, MedGemma 27B"],
            ["Total Predictions", str(ovr["total_predictions"]),
             f"{demo['n_cases']} cases × 6 models"],
            ["Judge Evaluations", str(len(judge_evals_df)),
             f"{demo['n_cases']} cases × 6 models × 2 judges"],
            ["Uro-Oncologist Model Reviews", str(len(reviews_df)),
             f"{reviews_df['case_id'].nunique()} cases × 6 models"],
            ["Uro-Oncologist Judge Reviews", str(len(judge_reviews_df)),
             f"{judge_reviews_df['case_id'].nunique()} cases × 6 models × 2 judges"],
        ],
    ))
    w("")

    # ── 7. AUTOMATED EVALUATION ──
    w("---")
    w("")
    w("## 7. Model Performance — Automated Evaluation")
    w("")
    w(f"All {ovr['total_predictions']} predictions across {demo['n_cases']} cases "
      "were evaluated by both AI judges.")
    w("")
    w(f"![Model Performance]({img}/full_model_performance.png)")
    w("")
    w(md_table(
        ["Model", "Cases", "Met. Detect.", "Exact Match", "Judge Acc.", "Avg Score"],
        [
            [row["model_name"], str(row["n_cases"]),
             f"{row['met_accuracy']:.1f}%", f"{row['therapy_exact']:.1f}%",
             f"{row['judge_accuracy']:.1f}%", f"{row['avg_overall']:.2f}"]
            for _, row in pipeline["model_rows"].iterrows()
        ],
    ))
    w("")
    w(f"Overall: **{ovr['met_accuracy']:.1f}%** metastatic detection accuracy, "
      f"**{ovr['therapy_exact_rate']:.1f}%** exact therapy match, "
      f"**{ovr['therapy_accept_rate']:.1f}%** clinically acceptable.")
    w("")

    w("### Detailed Judge Scores")
    w("")
    w(md_table(
        ["Model", "Semantic", "Clinical", "Reasoning", "Overall"],
        [
            [row["model_name"],
             f"{row['avg_semantic']:.2f}", f"{row['avg_clinical']:.2f}",
             f"{row['avg_reasoning']:.2f}", f"{row['avg_overall']:.2f}"]
            for _, row in pipeline["model_rows"].iterrows()
        ],
    ))
    w("")

    # ── 8. THERAPY CATEGORIES ──
    w("---")
    w("")
    w("## 8. Therapy Category Analysis")
    w("")
    w(f"![Therapy Categories]({img}/therapy_categories.png)")
    w("")
    cat_totals = predictions_df["pred_category_clean"].value_counts()
    w(md_table(
        ["Therapy Category", "Count", "% of Predictions"],
        [
            [cat, str(cnt), f"{cnt / len(predictions_df) * 100:.1f}%"]
            for cat, cnt in cat_totals.items()
        ][:8],
    ))
    w("")

    # ── 9. DOCTOR REVIEW ──
    w("---")
    w("")
    w("## 9. Model Performance — Uro-Oncologist Review")
    w("")
    w(f"Dr. Alexa reviewed **{len(reviews_df)} model predictions** across "
      f"{reviews_df['case_id'].nunique()} cases.")
    w("")
    w(f"![Acceptability]({img}/model_acceptability.png)")
    w("")
    w(f"![Quality]({img}/model_quality.png)")
    w("")
    w(md_table(
        ["Model", "Cases", "Acceptable %", "Avg Exact Match",
         "Avg Patient-Oriented", "Avg Quality (0–9)"],
        [
            [row["model_name"], str(row["n_cases"]),
             f"{row['acceptable_pct']:.1f}%",
             f"{row['avg_exact_match']:.1f}",
             f"{row['avg_patient_oriented']:.1f}",
             f"{row['avg_quality']:.1f}"]
            for _, row in perf.iterrows()
        ],
    ))
    w("")

    # ── 10. CASE STUDIES ──
    if case_studies:
        w("---")
        w("")
        w("## 10. Case Studies")
        w("")
        study_labels = {
            "consensus_correct": "Case Study A: Model Consensus — Correct Prediction",
            "model_disagreement": "Case Study B: Model Disagreement",
            "doctor_judge_diverge": "Case Study C: Uro-Oncologist–Judge Divergence",
            "low_agreement": "Case Study C: Low Model Agreement",
        }
        for study_type, cid, st in case_studies:
            case = st["case"]
            pt = case["patient"]
            dx = case["diagnosis"]
            gt = case["ground_truth"]
            w(f"### {study_labels.get(study_type, f'Case: {cid}')}")
            w("")
            w(f"**Case {cid}:** {pt['age']}-year-old patient, "
              f"ECOG {pt['ecog'] if pt['ecog'] is not None else 'N/A'}, "
              f"{'metastatic' if gt['metastatic'] else 'localized'} "
              f"{dx.get('histologie_subtyp', 'RCC')}. "
              f"Diagnosis: {dx.get('diagnose_kurz', 'RCC')}.")
            w("")
            w(f"**Tumor Board Recommendation:** {gt['therapy']}")
            w("")
            pred_rows = []
            for mid in sorted(MODEL_DISPLAY.keys()):
                pred = case["predictions"].get(mid, {})
                if not pred:
                    continue
                pred_rows.append([
                    model_name(mid),
                    pred.get("pred_category", "—"),
                    "Yes" if pred.get("therapy_exact_match") else "No",
                    "Yes" if pred.get("therapy_acceptable") else "No",
                ])
            w(md_table(
                ["Model", "Predicted Category", "Exact Match", "Acceptable"],
                pred_rows,
            ))
            w("")
            if study_type == "consensus_correct":
                w("All or most models agreed on the correct therapy category, "
                  "demonstrating reliable LLM performance for well-defined clinical scenarios.")
            elif study_type == "model_disagreement":
                cats = [p.get("pred_category", "") for p in case["predictions"].values()]
                w(f"Models predicted **{len(set(cats))} different therapy categories**, "
                  "highlighting clinical ambiguity.")
            elif study_type == "doctor_judge_diverge":
                w("The physician rated the therapy as acceptable, but both AI judges "
                  "classified it as incorrect — illustrating how strict semantic matching "
                  "may reject clinically valid alternatives.")
            else:
                w("Low agreement across models reflects the clinical complexity of "
                  "this case.")
            w("")

    # ── 11. JUDGE SCORE DISTRIBUTIONS ──
    w("---")
    w("")
    w("## 11. Judge Score Distributions")
    w("")
    w(f"![Score Distributions]({img}/score_distributions.png)")
    w("")
    w(f"![Score Types]({img}/score_types.png)")
    w("")

    score_cols = ["semantic_score", "clinical_score",
                  "reasoning_quality", "overall_score"]
    score_labels = ["Semantic", "Clinical", "Reasoning", "Overall"]
    dist_rows = []
    for jid in JUDGE_IDS:
        jdata = judge_evals_df[judge_evals_df["judge_id"] == jid]
        for col, label in zip(score_cols, score_labels):
            vals = jdata[col].dropna()
            dist_rows.append([
                judge_name(jid), label,
                f"{vals.mean():.3f}", f"{vals.median():.3f}",
                f"{vals.std():.3f}", f"{vals.min():.2f}", f"{vals.max():.2f}"])
    w(md_table(
        ["Judge", "Score Type", "Mean", "Median", "Std Dev", "Min", "Max"],
        dist_rows,
    ))
    w("")

    # ── 12. AGREEMENT ──
    if agreement:
        w("---")
        w("")
        w("## 12. Agreement: Uro-Oncologist vs AI Judge")
        w("")
        w(f"![Confusion Matrices]({img}/confusion_matrices.png)")
        w("")
        jids_a = [jid for jid in JUDGE_IDS if jid in agreement]
        w(md_table(
            ["Metric", *[judge_name(jid) for jid in jids_a]],
            [
                ["N pairs", *[str(agreement[jid]["n_pairs"]) for jid in jids_a]],
                ["Cohen's κ", *[f"{agreement[jid]['kappa']:.3f}" for jid in jids_a]],
                ["Agreement Rate",
                 *[f"{agreement[jid]['agreement_rate'] * 100:.1f}%" for jid in jids_a]],
                ["Sensitivity",
                 *[f"{agreement[jid]['sensitivity']:.3f}" for jid in jids_a]],
                ["Specificity",
                 *[f"{agreement[jid]['specificity']:.3f}" for jid in jids_a]],
                ["Precision",
                 *[f"{agreement[jid]['precision']:.3f}" for jid in jids_a]],
                ["F1 Score", *[f"{agreement[jid]['f1']:.3f}" for jid in jids_a]],
            ],
        ))
        w("")
        for jid in jids_a:
            a = agreement[jid]
            w(f"**{judge_name(jid)}:** κ = {a['kappa']:.3f} ({kappa_interpretation(a['kappa'])} "
              f"agreement), Sensitivity = {a['sensitivity']:.1%}, "
              f"Specificity = {a['specificity']:.1%}.")
        w("")

    # ── 13. DOCTOR RATINGS OF JUDGES ──
    if ratings:
        w("---")
        w("")
        w("## 13. Uro-Oncologist's Direct Rating of AI Judges")
        w("")
        w(f"![Judge Ratings]({img}/judge_ratings.png)")
        w("")
        jids_r = [jid for jid in JUDGE_IDS if jid in ratings]
        w(md_table(
            ["Metric", *[judge_name(jid) for jid in jids_r]],
            [
                ["Total Reviews", *[str(ratings[jid]["n"]) for jid in jids_r]],
                ["Agree",
                 *[f"{ratings[jid]['agree']} ({ratings[jid]['agree_pct']:.1f}%)"
                   for jid in jids_r]],
                ["Partial",
                 *[f"{ratings[jid]['partial']} ({ratings[jid]['partial_pct']:.1f}%)"
                   for jid in jids_r]],
                ["Disagree",
                 *[f"{ratings[jid]['disagree']} ({ratings[jid]['disagree_pct']:.1f}%)"
                   for jid in jids_r]],
                ["Avg Reasoning Quality",
                 *[f"{ratings[jid]['avg_reasoning_quality']:.1f}/10"
                   for jid in jids_r]],
            ],
        ))
        w("")

    # ── 14. PER-MODEL JUDGE ACCURACY ──
    if per_model_acc:
        w("---")
        w("")
        w("## 14. Per-Model Judge Accuracy")
        w("")
        w(f"![Per-Model Accuracy]({img}/per_model_accuracy.png)")
        w("")

    # ── 15. INTER-JUDGE ──
    if inter_judge:
        w("---")
        w("")
        w("## 15. Inter-Judge Agreement")
        w("")
        w(f"Agreement between GPT-5.2 and MedGemma 27B across "
          f"{inter_judge['n_pairs']} evaluation pairs "
          f"({inter_judge['n_cases']} cases × 6 models).")
        w("")
        w(f"![Inter-Judge]({img}/inter_judge.png)")
        w("")
        k = inter_judge["kappa"]
        w(f"**Cohen's κ = {k:.3f}** ({kappa_interpretation(k)} agreement). "
          f"Overall concordance: {inter_judge['agreement_rate'] * 100:.1f}%.")
        w("")

    # ── 16. MEDGEMMA BIAS ──
    if mg_bias:
        w("---")
        w("")
        w("## 16. MedGemma Self-Judging Bias")
        w("")
        w("MedGemma serves dual roles: both as a predictive model and as a judge.")
        w("")
        w(f"![MedGemma Bias]({img}/medgemma_bias.png)")
        w("")
        w(md_table(
            ["Metric", "Self-Judging", "Judging Others"],
            [
                ["N evaluations", str(mg_bias["self_n"]), str(mg_bias["other_n"])],
                ["Mean Overall Score", f"{mg_bias['self_mean']:.3f}",
                 f"{mg_bias['other_mean']:.3f}"],
                ["Median Overall Score", f"{mg_bias['self_median']:.3f}",
                 f"{mg_bias['other_median']:.3f}"],
            ],
        ))
        w("")
        sig = ("statistically significant" if mg_bias["p_val"] < 0.05
               else "not statistically significant")
        direction = "higher" if mg_bias["self_mean"] > mg_bias["other_mean"] else "lower"
        diff = abs(mg_bias["self_mean"] - mg_bias["other_mean"])
        w(f"**Mann-Whitney U test:** U = {mg_bias['u_stat']:.0f}, "
          f"p = {mg_bias['p_val']:.4f} ({sig}). "
          f"MedGemma gives {direction} scores to its own predictions by "
          f"{diff:.3f} points on average.")
        w("")

    # ── 17. CLINICAL SAFETY ──
    if safety:
        w("---")
        w("")
        w("## 17. Clinical Safety Analysis")
        w("")
        w("- **False Positive (dangerous):** Judge approves a prediction the uro-oncologist "
          "rejects → could lead to inappropriate treatment.")
        w("- **False Negative (overly strict):** Judge rejects a prediction the uro-oncologist "
          "approves → could prevent appropriate treatment.")
        w("")
        jids_s = [jid for jid in JUDGE_IDS if jid in safety]
        w(md_table(
            ["Safety Metric", *[judge_name(jid) for jid in jids_s]],
            [
                ["Total Pairs", *[str(safety[jid]["n"]) for jid in jids_s]],
                ["Judge Approvals",
                 *[str(safety[jid]["n_judge_positive"]) for jid in jids_s]],
                ["Judge Rejections",
                 *[str(safety[jid]["n_judge_negative"]) for jid in jids_s]],
                ["False Positives (dangerous)",
                 *[f"{safety[jid]['fp']} ({safety[jid]['fp_rate']:.1f}%)"
                   for jid in jids_s]],
                ["False Negatives (overly strict)",
                 *[f"{safety[jid]['fn']} ({safety[jid]['fn_rate']:.1f}%)"
                   for jid in jids_s]],
            ],
        ))
        w("")

    # ── 18. SUMMARY COMPARISON ──
    w("---")
    w("")
    w("## 18. Summary Comparison: GPT-5.2 vs MedGemma 27B")
    w("")
    jids_all = list(JUDGE_IDS.keys())
    metrics_rows = []

    if agreement:
        jids_a = [jid for jid in jids_all if jid in agreement]
        metrics_rows.append(("Cohen's κ (vs Uro-Oncologist)",
                             *[f"{agreement[jid]['kappa']:.3f}" for jid in jids_a]))
        metrics_rows.append(("Agreement Rate",
                             *[f"{agreement[jid]['agreement_rate'] * 100:.1f}%"
                               for jid in jids_a]))
        metrics_rows.append(("F1 Score",
                             *[f"{agreement[jid]['f1']:.3f}" for jid in jids_a]))

    if ratings:
        jids_r = [jid for jid in jids_all if jid in ratings]
        metrics_rows.append(("Uro-Oncologist Agree %",
                             *[f"{ratings[jid]['agree_pct']:.1f}%"
                               for jid in jids_r]))
        metrics_rows.append(("Avg Reasoning Quality",
                             *[f"{ratings[jid]['avg_reasoning_quality']:.1f}/10"
                               for jid in jids_r]))

    if safety:
        jids_s = [jid for jid in jids_all if jid in safety]
        metrics_rows.append(("False Positive Rate",
                             *[f"{safety[jid]['fp_rate']:.1f}%"
                               for jid in jids_s]))

    for label, col in [("Avg Overall Score", "overall_score"),
                       ("Avg Clinical Score", "clinical_score")]:
        vals = []
        for jid in jids_all:
            vals.append(
                f"{judge_evals_df[judge_evals_df['judge_id'] == jid][col].mean():.3f}")
        metrics_rows.append((label, *vals))

    w(md_table(
        ["Metric", *[judge_name(jid) for jid in jids_all]],
        [list(m) for m in metrics_rows],
    ))
    w("")

    # ── 19. GLOSSARY ──
    w("---")
    w("")
    w("## 19. German–English Medical Glossary")
    w("")
    w(md_table(
        ["German Term", "English Translation", "Context"],
        [
            ["Nierenzellkarzinom (NCC/RCC)", "Renal Cell Carcinoma",
             "Primary cancer type in this study"],
            ["Tumordiskussion / Tumorboard", "Tumor Board Discussion",
             "Multidisciplinary case conference"],
            ["Systemtherapie", "Systemic Therapy",
             "Drug-based treatment (chemo, IO, TKI)"],
            ["Klarzellig (ccRCC)", "Clear Cell",
             "Most common RCC histological subtype"],
            ["Metastasiert", "Metastatic", "Cancer spread beyond primary organ"],
            ["Lokalisiert", "Localized", "Cancer confined to primary organ"],
            ["Nephrektomie", "Nephrectomy", "Surgical removal of kidney"],
            ["Erstlinientherapie", "First-line Therapy", "Initial treatment regimen"],
            ["Zweitlinientherapie", "Second-line Therapy",
             "Treatment after first-line failure"],
            ["Lebenserwartung", "Life Expectancy", "Estimated patient survival"],
            ["Nebendiagnosen", "Comorbidities", "Co-existing medical conditions"],
            ["Bildgebung", "Imaging", "Radiological examinations (CT, MRI)"],
            ["Histologie-Subtyp", "Histology Subtype",
             "Microscopic tissue classification"],
            ["Leitlinienkonform", "Guideline-Concordant",
             "Consistent with clinical practice guidelines"],
        ],
    ))
    w("")

    # ── 20. CONCLUSIONS ──
    w("---")
    w("")
    w("## 20. Conclusions & Recommendations")
    w("")

    w("### Key Findings")
    w("")
    w(f"- **Model Performance:** {best_model['model_name']} achieved the highest "
      f"uro-oncologist-rated quality ({best_model['avg_quality']:.1f}/9) with "
      f"{best_model['acceptable_pct']:.1f}% therapy acceptability. "
      f"{best_auto['model_name']} scored highest on automated judge evaluation "
      f"({best_auto['avg_overall']:.2f}/1.0).")

    if agreement:
        best_j = max(agreement.items(), key=lambda x: x[1]["kappa"])
        w(f"- **Best AI Judge:** {judge_name(best_j[0])} showed the strongest agreement "
          f"with the uro-oncologist (κ = {best_j[1]['kappa']:.3f}).")

    w(f"- **Therapy Categories:** IO+TKI and TKI Mono dominate model predictions, "
      f"consistent with current RCC guidelines for the "
      f"{demo['n_metastatic']}/{demo['n_cases']} metastatic cases.")

    if safety:
        safest = min(safety.items(), key=lambda x: x[1]["fp_rate"])
        w(f"- **Clinical Safety:** {judge_name(safest[0])} has the lowest dangerous "
          f"error rate ({safest[1]['fp_rate']:.1f}%). Both judges tend to be "
          "overly strict, which is safer in a clinical context.")

    if mg_bias and mg_bias["p_val"] < 0.05:
        w("- **Self-Judging Bias:** MedGemma shows statistically significant "
          "self-judging bias. Self-evaluations should be interpreted with caution.")
    w("")

    w("### Recommendations")
    w("")
    w("1. AI judges should be used as **screening tools**, not final arbiters. "
      "Uro-oncologist review remains essential for clinical safety.")
    w("2. Using **both GPT-5.2 and MedGemma** as judges and flagging disagreements "
      "could improve evaluation reliability.")
    w("3. Models with high acceptability but lower exact match may still provide "
      "clinically valid alternative recommendations.")
    w("4. Strong Spearman correlations (ρ > 0.64) suggest automated judge scores are "
      "useful proxies for prediction quality, enabling scalable evaluation.")
    w("5. Future work should expand to additional cancer types, test with multiple "
      "physician reviewers, and evaluate newer medical-specialized models.")
    w("")

    w("### Limitations")
    w("")
    w(f"- Single physician reviewer (potential individual assessment bias)")
    w(f"- Dataset limited to RCC from a single institution's tumor boards")
    md_doc_cases = reviews_df['case_id'].nunique()
    md_judge_cases = judge_reviews_df['case_id'].nunique()
    if md_doc_cases >= demo['n_cases'] and md_judge_cases >= demo['n_cases']:
        w(f"- Uro-oncologist reviewed all {demo['n_cases']} cases for both model and judge evaluation (complete coverage)")
    else:
        w(f"- Uro-oncologist reviews covered {md_doc_cases} of "
          f"{demo['n_cases']} cases for model evaluation and "
          f"{md_judge_cases} cases for judge evaluation")
    w(f"- Ground truth = tumor board consensus (not necessarily the only correct therapy)")
    w(f"- All cases use German medical terminology, which may affect model performance")
    w("")

    w("### Open Questions")
    w("")
    w("- **Ground Truth Definition:** Is `ground_truth_therapy` the tumor board "
      "consensus or the actual treatment administered?")
    w("- **IMDC for Non-Clear-Cell RCC:** Should IMDC be skipped entirely or "
      "calculated with disclaimer for papillary/chromophobe subtypes?")
    w("- **ICI Eligibility:** Criteria for determining ICI combination feasibility "
      "(autoimmune disease, prior transplant) are not explicitly coded.")
    w("- **Therapy Guidelines Completeness:** Embedded guidelines may not include "
      "adjuvant pembrolizumab, non-clear-cell protocols, third-line options, "
      "oligometastatic management, or cytoreductive nephrectomy criteria.")
    w("- **Four JSON Schema Variants:** Edge cases in field mapping across four "
      "schema variants may introduce subtle data quality issues.")
    w("")

    # ── Write ──
    md_path = OUTPUT_DIR / f"evaluation_report_{pd.Timestamp.now().strftime('%Y-%m-%d')}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Markdown report saved to: {md_path}")
    return md_path


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    reviews_df, judge_reviews_df, judge_evals_df, predictions_df, cases_data = \
        load_data()
    run_summaries_df = load_run_summaries()

    chart_dir = OUTPUT_DIR / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    build_report(reviews_df, judge_reviews_df, judge_evals_df,
                 predictions_df, cases_data, run_summaries_df, chart_dir)

    build_markdown_report(reviews_df, judge_reviews_df, judge_evals_df,
                          predictions_df, cases_data, run_summaries_df, chart_dir)


if __name__ == "__main__":
    main()
