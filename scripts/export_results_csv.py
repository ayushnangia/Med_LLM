#!/usr/bin/env python3
"""
Export Modal/OpenRouter treatment prediction results to CSV for medical review.

Usage:
    python scripts/export_results_csv.py --all --latest   # Latest run per model (recommended)
    python scripts/export_results_csv.py --all            # All runs
    python scripts/export_results_csv.py --results-dir PATH

Output: to_be_reviewed_results/{model}_treatment_{dd-mm-yy}.csv
"""

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Output folder for all review CSVs
REVIEWED_RESULTS_DIR = Path("to_be_reviewed_results")


# CSV column order (for readability in Excel)
CSV_COLUMNS = [
    # Case identification
    "case_id",
    "patient_name",
    "age",

    # Patient status
    "ecog",
    "karnofsky",
    "comorbidity",

    # Clinical data
    "diagnose_kurz",
    "stadium",
    "histologie_subtyp",
    "klarzellig",
    "tnm_cM",

    # Ground truth
    "gt_metastatic",
    "gt_therapy",

    # Model prediction
    "pred_metastatic",
    "pred_imdc_risk",
    "pred_therapy",
    "pred_category",
    "pred_confidence",

    # Basic evaluation
    "metastatic_correct",
    "therapy_exact_match",
    "therapy_acceptable",

    # Judge evaluation - ALL fields
    "judge_is_correct",
    "judge_correctness_reason",
    "judge_semantic_match",
    "judge_semantic_score",
    "judge_clinical_appropriate",
    "judge_clinical_score",
    "judge_reasoning_quality",
    "judge_reasoning_critique",
    "judge_overall_score",
    "judge_reasoning",
    "judge_inference_time_s",

    # Model reasoning (full)
    "pred_reasoning",

    # Metadata
    "model",
    "timestamp",
    "inference_time_s",
    "success",
]


def truncate_text(text: Optional[str], max_len: int = 200) -> str:
    """Truncate text to max_len characters, adding ... if truncated."""
    if text is None:
        return ""
    text = str(text).replace("\n", " ").replace("\r", " ")
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def safe_get(d: dict, *keys, default=None):
    """Safely get nested dict values."""
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d if d is not None else default


def load_case_results(results_dir: Path) -> List[dict]:
    """Load all ncc_*.json case files from a results directory."""
    cases = []

    # Find all ncc_*.json files
    case_files = sorted(results_dir.glob("ncc_*.json"),
                        key=lambda x: int(re.search(r'ncc_(\d+)', x.name).group(1)))

    for case_file in case_files:
        with open(case_file, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        # Extract fields into flat structure
        input_case = case_data.get("input_case", {})
        prediction = case_data.get("prediction", {}) or {}

        row = {
            # Case identification
            "case_id": case_data.get("case_id", ""),
            "patient_name": safe_get(input_case, "patient_name", default=""),
            "age": safe_get(input_case, "age", default=""),

            # Patient status
            "ecog": safe_get(input_case, "ecog", default=""),
            "karnofsky": safe_get(input_case, "karnofsky", default=""),
            "comorbidity": safe_get(input_case, "comorbidity", default=""),

            # Clinical data
            "diagnose_kurz": safe_get(input_case, "diagnose_kurz", default=""),
            "stadium": safe_get(input_case, "stadium", default=""),
            "histologie_subtyp": safe_get(input_case, "histologie_subtyp", default=""),
            "klarzellig": safe_get(input_case, "histologie_klarzellig", default=""),
            "tnm_cM": safe_get(input_case, "tnm_clinical", "M", default=""),

            # Ground truth
            "gt_metastatic": case_data.get("ground_truth_metastatic", ""),
            "gt_therapy": case_data.get("ground_truth_therapy", ""),

            # Model prediction
            "pred_metastatic": safe_get(prediction, "is_metastatic", default=""),
            "pred_imdc_risk": safe_get(prediction, "imdc_risk", default=""),
            "pred_therapy": safe_get(prediction, "recommended_therapy", default=""),
            "pred_category": safe_get(prediction, "therapy_category", default=""),
            "pred_confidence": safe_get(prediction, "confidence", default=""),

            # Basic evaluation
            "metastatic_correct": case_data.get("metastatic_correct", ""),
            "therapy_exact_match": case_data.get("therapy_exact_match", ""),
            "therapy_acceptable": case_data.get("therapy_clinically_acceptable", ""),

            # Judge placeholders (filled later if available)
            "judge_is_correct": "",
            "judge_correctness_reason": "",
            "judge_semantic_match": "",
            "judge_semantic_score": "",
            "judge_clinical_appropriate": "",
            "judge_clinical_score": "",
            "judge_reasoning_quality": "",
            "judge_reasoning_critique": "",
            "judge_overall_score": "",
            "judge_reasoning": "",
            "judge_inference_time_s": "",

            # Model reasoning (full, not truncated)
            "pred_reasoning": safe_get(prediction, "treatment_reasoning", default=""),

            # Metadata
            "model": case_data.get("model", ""),
            "timestamp": case_data.get("timestamp", ""),
            "inference_time_s": round(case_data.get("inference_time_seconds", 0), 2),
            "success": case_data.get("success", ""),
        }

        cases.append(row)

    return cases


def load_judge_evaluation(results_dir: Path) -> Tuple[Optional[Dict[str, dict]], Optional[dict]]:
    """Load judge evaluation file if it exists, indexed by case_id.

    Returns:
        Tuple of (evaluations_by_case, summary_metrics)
    """
    judge_files = list(results_dir.glob("judge_evaluation_*.json"))

    if not judge_files:
        return None, None

    # Use the most recent judge file if multiple exist
    judge_file = sorted(judge_files)[-1]

    with open(judge_file, "r", encoding="utf-8") as f:
        judge_data = json.load(f)

    # Index evaluations by case_id
    evaluations_by_case = {}
    for eval_item in judge_data.get("evaluations", []):
        case_id = eval_item.get("case_id")
        if case_id:
            evaluations_by_case[case_id] = eval_item

    # Extract summary metrics
    summary_metrics = {
        "judge_model": judge_data.get("judge_model", ""),
        "total_cases": judge_data.get("total_cases", 0),
        "evaluated_cases": judge_data.get("evaluated_cases", 0),
        "failed_evaluations": judge_data.get("failed_evaluations", 0),
        "metrics": judge_data.get("metrics", {}),
    }

    return evaluations_by_case, summary_metrics


def merge_judge_data(cases: List[dict], judge_data: Optional[Dict[str, dict]]) -> List[dict]:
    """Merge judge evaluation data into case rows."""
    if not judge_data:
        return cases

    for row in cases:
        case_id = row["case_id"]
        judge_eval = judge_data.get(case_id, {})
        evaluation = judge_eval.get("evaluation", {}) or {}

        # All judge evaluation fields (not truncated for full review)
        row["judge_is_correct"] = safe_get(evaluation, "is_correct", default="")
        row["judge_correctness_reason"] = safe_get(evaluation, "correctness_reason", default="")
        row["judge_semantic_match"] = safe_get(evaluation, "therapy_semantic_match", default="")
        row["judge_semantic_score"] = safe_get(evaluation, "therapy_semantic_score", default="")
        row["judge_clinical_appropriate"] = safe_get(evaluation, "clinical_appropriateness", default="")
        row["judge_clinical_score"] = safe_get(evaluation, "clinical_appropriateness_score", default="")
        row["judge_reasoning_quality"] = safe_get(evaluation, "reasoning_quality", default="")
        row["judge_reasoning_critique"] = safe_get(evaluation, "reasoning_critique", default="")
        row["judge_overall_score"] = safe_get(evaluation, "overall_score", default="")
        row["judge_reasoning"] = safe_get(evaluation, "judge_reasoning", default="")
        row["judge_inference_time_s"] = round(judge_eval.get("inference_time_seconds", 0), 2) if judge_eval.get("inference_time_seconds") else ""

    return cases


def export_to_csv(cases: List[dict], output_path: Path, summary_metrics: Optional[dict] = None):
    """Export cases to CSV with UTF-8 BOM for Excel compatibility."""
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cases)

        # Add summary rows if judge metrics available
        if summary_metrics and summary_metrics.get("metrics"):
            metrics = summary_metrics["metrics"]

            # Empty row as separator
            writer.writerow({})

            # Header row for summary section
            writer.writerow({
                "case_id": "=== JUDGE EVALUATION SUMMARY ==="
            })

            # Judge model info
            writer.writerow({
                "case_id": "Judge Model",
                "patient_name": summary_metrics.get('judge_model', 'N/A'),
            })

            # Case counts
            writer.writerow({
                "case_id": "Total Cases",
                "patient_name": summary_metrics.get('total_cases', 0),
            })
            writer.writerow({
                "case_id": "Evaluated",
                "patient_name": summary_metrics.get('evaluated_cases', 0),
            })
            writer.writerow({
                "case_id": "Failed",
                "patient_name": summary_metrics.get('failed_evaluations', 0),
            })

            # Empty row
            writer.writerow({})

            # Key metrics
            writer.writerow({
                "case_id": "=== KEY METRICS ==="
            })
            writer.writerow({
                "case_id": "ACCURACY",
                "patient_name": f"{metrics.get('accuracy', 0):.1%}",
                "age": f"{metrics.get('correct_count', 0)} correct",
                "ecog": f"{metrics.get('incorrect_count', 0)} incorrect",
            })
            writer.writerow({
                "case_id": "Semantic Match Rate",
                "patient_name": f"{metrics.get('therapy_semantic_match_rate', 0):.1%}",
                "age": f"{metrics.get('therapy_semantic_match_count', 0)} matches",
            })
            writer.writerow({
                "case_id": "Clinical Appropriate Rate",
                "patient_name": f"{metrics.get('clinical_appropriateness_rate', 0):.1%}",
                "age": f"{metrics.get('clinical_appropriateness_count', 0)} appropriate",
            })

            # Empty row
            writer.writerow({})

            # Average scores
            writer.writerow({
                "case_id": "=== AVERAGE SCORES ==="
            })
            writer.writerow({
                "case_id": "Avg Semantic Score",
                "patient_name": f"{metrics.get('avg_therapy_semantic_score', 0):.4f}",
            })
            writer.writerow({
                "case_id": "Avg Clinical Score",
                "patient_name": f"{metrics.get('avg_clinical_score', 0):.4f}",
            })
            writer.writerow({
                "case_id": "Avg Reasoning Quality",
                "patient_name": f"{metrics.get('avg_reasoning_quality', 0):.4f}",
            })
            writer.writerow({
                "case_id": "Avg Overall Score",
                "patient_name": f"{metrics.get('avg_overall_score', 0):.4f}",
            })

    print(f"Exported {len(cases)} cases to {output_path}")


def generate_output_filename(results_dir: Path) -> Path:
    """
    Generate output filename: {model}_treatment_{dd-mm-yy}.csv

    Example: gemma-3-27b-it_treatment_30-12-25.csv
    """
    # Extract model name from path (e.g., google_gemma-3-27b-it -> gemma-3-27b-it)
    model_dir = results_dir.parent.name  # e.g., "google_gemma-3-27b-it"
    model_name = model_dir.replace("google_", "").replace("openmeditron_", "")

    # Extract timestamp from path (e.g., 2025-12-30_00-02-19)
    timestamp_str = results_dir.name  # e.g., "2025-12-30_00-02-19"

    # Parse and reformat date to dd-mm-yy
    try:
        dt = datetime.strptime(timestamp_str.split("_")[0], "%Y-%m-%d")
        date_str = dt.strftime("%d-%m-%y")
    except ValueError:
        date_str = timestamp_str[:10].replace("-", "")

    # Build filename
    filename = f"{model_name}_treatment_{date_str}.csv"

    return REVIEWED_RESULTS_DIR / filename


def process_results_dir(results_dir: Path, output_path: Optional[Path] = None):
    """Process a single results directory and export to CSV."""
    if not results_dir.exists():
        print(f"Error: Directory not found: {results_dir}")
        return

    # Load case results
    cases = load_case_results(results_dir)
    if not cases:
        print(f"No case files found in {results_dir}")
        return

    # Load and merge judge data if available
    judge_data, summary_metrics = load_judge_evaluation(results_dir)
    if judge_data:
        print(f"Found judge evaluation with {len(judge_data)} cases")
        cases = merge_judge_data(cases, judge_data)
        if summary_metrics:
            metrics = summary_metrics.get("metrics", {})
            print(f"  → Accuracy: {metrics.get('accuracy', 0):.1%} ({metrics.get('correct_count', 0)}/{summary_metrics.get('evaluated_cases', 0)} correct)")
    else:
        summary_metrics = None
        print("No judge evaluation found (judge columns will be empty)")

    # Determine output path using naming scheme
    if output_path is None:
        output_path = generate_output_filename(results_dir)

    # Export
    export_to_csv(cases, output_path, summary_metrics)


def find_all_results_dirs(base_dir: Path) -> List[Path]:
    """Find all timestamp directories containing ncc_*.json files."""
    results_dirs = []

    for model_dir in base_dir.iterdir():
        if model_dir.is_dir():
            for timestamp_dir in model_dir.iterdir():
                if timestamp_dir.is_dir() and list(timestamp_dir.glob("ncc_*.json")):
                    results_dirs.append(timestamp_dir)

    return sorted(results_dirs)


def find_latest_results_dirs(base_dir: Path) -> List[Path]:
    """Find only the latest timestamp directory for each model."""
    latest_dirs = []

    for model_dir in base_dir.iterdir():
        if model_dir.is_dir():
            # Get all timestamp dirs for this model
            timestamp_dirs = [
                d for d in model_dir.iterdir()
                if d.is_dir() and list(d.glob("ncc_*.json"))
            ]
            if timestamp_dirs:
                # Sort by name (timestamp format sorts chronologically) and take latest
                latest = sorted(timestamp_dirs, key=lambda x: x.name)[-1]
                latest_dirs.append(latest)

    return sorted(latest_dirs)


def export_summary_csv(results_dirs: List[Path]):
    """Export a summary CSV comparing all models."""
    summary_rows = []

    for results_dir in results_dirs:
        # Get model name
        model_dir = results_dir.parent.name
        model_name = model_dir.replace("google_", "").replace("openmeditron_", "").replace("allenai_", "")

        # Get timestamp
        timestamp = results_dir.name

        # Load judge evaluation
        _, summary_metrics = load_judge_evaluation(results_dir)

        if summary_metrics and summary_metrics.get("metrics"):
            metrics = summary_metrics["metrics"]
            row = {
                "model": model_name,
                "timestamp": timestamp,
                "judge_model": summary_metrics.get("judge_model", ""),
                "total_cases": summary_metrics.get("total_cases", 0),
                "evaluated_cases": summary_metrics.get("evaluated_cases", 0),
                "accuracy": f"{metrics.get('accuracy', 0):.1%}",
                "correct_count": metrics.get("correct_count", 0),
                "incorrect_count": metrics.get("incorrect_count", 0),
                "semantic_match_rate": f"{metrics.get('therapy_semantic_match_rate', 0):.1%}",
                "clinical_ok_rate": f"{metrics.get('clinical_appropriateness_rate', 0):.1%}",
                "avg_semantic_score": f"{metrics.get('avg_therapy_semantic_score', 0):.3f}",
                "avg_clinical_score": f"{metrics.get('avg_clinical_score', 0):.3f}",
                "avg_reasoning_quality": f"{metrics.get('avg_reasoning_quality', 0):.3f}",
                "avg_overall_score": f"{metrics.get('avg_overall_score', 0):.3f}",
            }
        else:
            row = {
                "model": model_name,
                "timestamp": timestamp,
                "judge_model": "N/A",
                "total_cases": len(list(results_dir.glob("ncc_*.json"))),
                "evaluated_cases": 0,
                "accuracy": "N/A",
                "correct_count": "N/A",
                "incorrect_count": "N/A",
                "semantic_match_rate": "N/A",
                "clinical_ok_rate": "N/A",
                "avg_semantic_score": "N/A",
                "avg_clinical_score": "N/A",
                "avg_reasoning_quality": "N/A",
                "avg_overall_score": "N/A",
            }

        summary_rows.append(row)

    # Sort by accuracy (descending)
    def sort_key(r):
        acc = r.get("accuracy", "0%")
        if acc == "N/A":
            return -1
        return float(acc.replace("%", "")) / 100

    summary_rows.sort(key=sort_key, reverse=True)

    # Write summary CSV
    summary_path = REVIEWED_RESULTS_DIR / "models_comparison_summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "model", "accuracy", "correct_count", "incorrect_count",
        "semantic_match_rate", "clinical_ok_rate",
        "avg_semantic_score", "avg_clinical_score", "avg_reasoning_quality", "avg_overall_score",
        "total_cases", "evaluated_cases", "judge_model", "timestamp"
    ]

    with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\n{'='*60}")
    print(f"Summary exported to: {summary_path}")
    print(f"{'='*60}")
    print(f"{'Model':<35} {'Accuracy':>10} {'Correct':>8}")
    print(f"{'-'*35} {'-'*10} {'-'*8}")
    for row in summary_rows:
        print(f"{row['model']:<35} {row['accuracy']:>10} {row['correct_count']:>8}")


def main():
    parser = argparse.ArgumentParser(
        description="Export treatment prediction results to CSV for medical review"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        help="Path to a specific results directory (contains ncc_*.json files)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output CSV path (default: results_review.csv in results dir)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export results from results/modal_treatment/"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="With --all: export only the latest run per model (recommended)"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("results/modal_treatment"),
        help="Base directory for --all mode (default: results/modal_treatment)"
    )

    args = parser.parse_args()

    if args.all:
        if args.latest:
            # Export only latest results per model
            results_dirs = find_latest_results_dirs(args.base_dir)
            if not results_dirs:
                print(f"No results directories found in {args.base_dir}")
                return
            print(f"Found {len(results_dirs)} models (latest run each)")
        else:
            # Export all results directories
            results_dirs = find_all_results_dirs(args.base_dir)
            if not results_dirs:
                print(f"No results directories found in {args.base_dir}")
                return
            print(f"Found {len(results_dirs)} results directories (all runs)")

        for results_dir in results_dirs:
            print(f"\nProcessing: {results_dir}")
            process_results_dir(results_dir)

        # Export summary comparison
        export_summary_csv(results_dirs)

    elif args.results_dir:
        # Export single results directory
        process_results_dir(args.results_dir, args.output)

    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python scripts/export_results_csv.py --all --latest          # Latest run per model (recommended)")
        print("  python scripts/export_results_csv.py --all                   # All runs")
        print("  python scripts/export_results_csv.py --results-dir PATH      # Specific run")
        print("\nOutput: to_be_reviewed_results/{model}_treatment_{dd-mm-yy}.csv")
        print("        to_be_reviewed_results/models_comparison_summary.csv")


if __name__ == "__main__":
    main()
