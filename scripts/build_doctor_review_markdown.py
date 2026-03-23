#!/usr/bin/env python3
"""Build a doctor-facing Markdown review for prompt-only vs RAG hard cases."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
HARD_CASES_FILE = BASE_DIR / "converted_data" / "send_23_12_25" / "ncc" / "ncc_hard_cases.jsonl"
BASELINE_PREDICTIONS_DIR = BASE_DIR / "hard_cases_workspace" / "predictions"
BASELINE_JUDGES_DIR = BASE_DIR / "hard_cases_workspace" / "judges" / "gpt-5.2"
RAG_RESULTS_DIR = BASE_DIR / "results" / "modal_treatment_rag"
OUTPUT_PATH = BASE_DIR / "hard_cases_workspace" / "summaries" / "doctor_review_prompt_vs_rag_gpt52.md"

MODELS: List[Tuple[str, str]] = [
    ("google_gemma-3-27b-it", "Gemma 3 27B"),
    ("google_gemma-3-4b-it", "Gemma 3 4B"),
    ("allenai_olmo-3.1-32b-instruct", "OLMo 3.1 32B Instruct"),
    ("allenai_olmo-3.1-32b-think", "OLMo 3.1 32B Think"),
    ("openmeditron_meditron3-qwen2.5-7b", "Meditron3 Qwen2.5 7B"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def short_bool(value: Optional[bool]) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Pending"


def score_text(value: Optional[float]) -> str:
    if value is None:
        return "Pending"
    return f"{value:.3f}"


def md_escape(text: Optional[str]) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def html_block(label: str, text: Optional[str]) -> str:
    if not text:
        return f"<p><strong>{label}:</strong> <em>Not available</em></p>"
    return f"<p><strong>{label}:</strong> {md_escape(text)}</p>"


def html_list_block(label: str, items: Optional[List[str]]) -> str:
    if not items:
        return f"<p><strong>{label}:</strong> <em>Not available</em></p>"
    joined = ", ".join(md_escape(item) for item in items)
    return f"<p><strong>{label}:</strong> {joined}</p>"


def prediction_is_placeholder(prediction: dict) -> bool:
    recommendation = prediction.get("recommended_therapy") or ""
    category = prediction.get("therapy_category") or ""
    reasoning = prediction.get("treatment_reasoning") or ""
    placeholder_markers = [
        "Konkrete Therapie oder diagnostischer naechster Schritt",
        "IO+TKI/TKI mono/Surgery/Surveillance/Ablation/Diagnostik/etc.",
        "Schrittweise, leitliniengestuetzte Begruendung",
    ]
    text = " ".join([recommendation, category, reasoning])
    return any(marker in text for marker in placeholder_markers)


def load_baseline_cases(model_dir: str) -> Dict[str, dict]:
    model_path = BASELINE_PREDICTIONS_DIR / model_dir
    if not model_path.exists():
        return {}
    return {
        path.stem: load_json(path)
        for path in sorted(model_path.glob("ncc_*.json"))
    }


def load_baseline_judges(model_dir: str) -> Dict[str, dict]:
    judge_path = BASELINE_JUDGES_DIR / f"{model_dir}.json"
    if not judge_path.exists():
        return {}
    payload = load_json(judge_path)
    return {
        item["case_id"]: item.get("evaluation") or {}
        for item in payload.get("evaluations", [])
        if item.get("case_id")
    }


def load_rag_cases(model_dir: str) -> Dict[str, tuple[str, dict]]:
    model_root = RAG_RESULTS_DIR / model_dir
    if not model_root.exists():
        return {}

    latest_by_case: Dict[str, tuple[str, dict]] = {}
    for run_dir in sorted([p for p in model_root.iterdir() if p.is_dir()]):
        for case_path in sorted(run_dir.glob("ncc_*.json")):
            case_id = case_path.stem
            latest_by_case[case_id] = (run_dir.name, load_json(case_path))
    return latest_by_case


def load_rag_judges(model_dir: str) -> Dict[str, tuple[str, dict]]:
    model_root = RAG_RESULTS_DIR / model_dir
    if not model_root.exists():
        return {}

    latest_by_case: Dict[str, tuple[str, dict]] = {}
    for run_dir in sorted([p for p in model_root.iterdir() if p.is_dir()]):
        judge_path = run_dir / "judge_evaluation_gpt-5.2.json"
        if not judge_path.exists():
            continue
        payload = load_json(judge_path)
        for item in payload.get("evaluations", []):
            case_id = item.get("case_id")
            if case_id:
                latest_by_case[case_id] = (run_dir.name, item.get("evaluation") or {})
    return latest_by_case


def summarize_models(case_ids: List[str]) -> List[dict]:
    rows = []
    for model_dir, model_name in MODELS:
        baseline_judges = load_baseline_judges(model_dir)
        rag_judges = load_rag_judges(model_dir)
        baseline_correct = sum(1 for cid in case_ids if baseline_judges.get(cid, {}).get("is_correct"))
        baseline_clinical = sum(1 for cid in case_ids if baseline_judges.get(cid, {}).get("clinical_appropriateness"))
        baseline_scores = [baseline_judges.get(cid, {}).get("overall_score") for cid in case_ids if baseline_judges.get(cid, {}).get("overall_score") is not None]
        rag_case_ids = [cid for cid in case_ids if cid in rag_judges]
        rag_correct = sum(1 for cid in rag_case_ids if (rag_judges.get(cid, ("", {}))[1] or {}).get("is_correct"))
        rag_clinical = sum(1 for cid in rag_case_ids if (rag_judges.get(cid, ("", {}))[1] or {}).get("clinical_appropriateness"))
        rag_scores = [
            (rag_judges.get(cid, ("", {}))[1] or {}).get("overall_score")
            for cid in rag_case_ids
            if (rag_judges.get(cid, ("", {}))[1] or {}).get("overall_score") is not None
        ]
        rows.append(
            {
                "model_dir": model_dir,
                "model_name": model_name,
                "baseline_correct": baseline_correct,
                "baseline_clinical": baseline_clinical,
                "baseline_avg_overall": (sum(baseline_scores) / len(baseline_scores)) if baseline_scores else None,
                "rag_cases_judged": len(rag_case_ids),
                "rag_correct": rag_correct,
                "rag_clinical": rag_clinical,
                "rag_avg_overall": (sum(rag_scores) / len(rag_scores)) if rag_scores else None,
            }
        )
    return rows


def build_report() -> str:
    hard_cases = load_jsonl(HARD_CASES_FILE)
    case_ids = [case["case_id"] for case in hard_cases]
    model_summary_rows = summarize_models(case_ids)

    lines: List[str] = []
    lines.append("# Doctor Review: Prompt-Only vs Guideline-RAG on Hard RCC Cases")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("Primary paired judge in this report: `gpt-5.2`.")
    lines.append("")
    lines.append("This review compares the original prompt-only runs against the newer guideline-based RAG runs using the German S3 kidney cancer guideline.")
    lines.append("")
    lines.append("This doctor-facing version excludes models with incomplete or unreliable paired RAG coverage, so only fully reviewable comparisons are shown below.")
    lines.append("")
    lines.append("## Model Summary")
    lines.append("")
    lines.append("| Model | Prompt Correct | Prompt Clinical OK | Prompt Avg Overall | RAG Judged Cases | RAG Correct | RAG Clinical OK | RAG Avg Overall |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in model_summary_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model_name"],
                    f"{row['baseline_correct']}/11",
                    f"{row['baseline_clinical']}/11",
                    score_text(row["baseline_avg_overall"]),
                    str(row["rag_cases_judged"]),
                    f"{row['rag_correct']}/{row['rag_cases_judged']}" if row["rag_cases_judged"] else "Pending",
                    f"{row['rag_clinical']}/{row['rag_cases_judged']}" if row["rag_cases_judged"] else "Pending",
                    score_text(row["rag_avg_overall"]),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Case Review")
    lines.append("")

    for case in hard_cases:
        case_id = case["case_id"]
        lines.append(f"## {case['case_number']}: {case['patient']['display_line']}")
        lines.append("")
        lines.append(f"**Hard case label:** {case['hard_case_label']}")
        lines.append("")
        ground_truth = case["case_data"].get("geplantes_therapiekonzept") or ""
        if ground_truth:
            lines.append(f"**Tumorboard / Ground Truth:** {ground_truth}")
            lines.append("")

        for model_dir, model_name in MODELS:
            baseline_cases = load_baseline_cases(model_dir)
            baseline_judges = load_baseline_judges(model_dir)
            rag_cases = load_rag_cases(model_dir)
            rag_judges = load_rag_judges(model_dir)

            baseline_case = baseline_cases.get(case_id, {})
            baseline_prediction = baseline_case.get("prediction") if isinstance(baseline_case.get("prediction"), dict) else {}
            baseline_judge = baseline_judges.get(case_id, {}) or {}

            rag_run, rag_case = rag_cases.get(case_id, ("", {}))
            rag_prediction = rag_case.get("prediction") if isinstance(rag_case.get("prediction"), dict) else {}
            rag_judge_run, rag_judge = rag_judges.get(case_id, ("", {}))

            lines.append(f"### {model_name}")
            lines.append("")
            lines.append("<table>")
            lines.append("<tr><th style=\"width:50%\">Prompt-Only</th><th style=\"width:50%\">Guideline RAG</th></tr>")

            left_parts = [
                html_block("Recommendation", baseline_prediction.get("recommended_therapy")),
                html_block("Category", baseline_prediction.get("therapy_category")),
                html_block("Reasoning", baseline_prediction.get("treatment_reasoning")),
                html_block(
                    "Judge Verdict",
                    f"Correct: {short_bool(baseline_judge.get('is_correct'))}; "
                    f"Clinical OK: {short_bool(baseline_judge.get('clinical_appropriateness'))}; "
                    f"Overall: {score_text(baseline_judge.get('overall_score'))}",
                ),
                html_block("Judge Note", baseline_judge.get("correctness_reason")),
                html_block("Judge Reasoning", baseline_judge.get("judge_reasoning")),
            ]

            if rag_case and not prediction_is_placeholder(rag_prediction):
                rag_recommendation_text = rag_prediction.get("recommended_therapy")
                rag_reasoning_text = rag_prediction.get("treatment_reasoning")
                rag_category = rag_prediction.get("therapy_category")
                rag_citations = rag_prediction.get("guideline_citations") or []
                rag_status = f"Available from run `{rag_run}`"
            elif rag_case:
                rag_recommendation_text = None
                rag_reasoning_text = None
                rag_category = None
                rag_citations = []
                rag_status = f"Latest RAG file from run `{rag_run}` looks like a placeholder/template output and is excluded from review"
            else:
                rag_recommendation_text = None
                rag_reasoning_text = None
                rag_category = None
                rag_citations = []
                rag_status = "RAG output not available yet"

            if rag_judge:
                rag_judge_text = (
                    f"Correct: {short_bool(rag_judge.get('is_correct'))}; "
                    f"Clinical OK: {short_bool(rag_judge.get('clinical_appropriateness'))}; "
                    f"Overall: {score_text(rag_judge.get('overall_score'))}"
                )
                rag_judge_status = f"Available from run `{rag_judge_run}`"
            elif rag_case:
                rag_judge_text = "Pending"
                rag_judge_status = "RAG output exists, but judge file is not available yet"
            else:
                rag_judge_text = "Missing"
                rag_judge_status = "No RAG output, so no paired judge result"

            right_parts = [
                html_block("Recommendation", rag_recommendation_text),
                html_block("Category", rag_category),
                html_block("Reasoning", rag_reasoning_text),
                html_list_block("Guideline Citations", rag_citations),
                html_block("RAG Status", rag_status),
                html_block("Judge Verdict", rag_judge_text),
                html_block("Judge Status", rag_judge_status),
                html_block("Judge Note", rag_judge.get("correctness_reason")),
                html_block("Judge Reasoning", rag_judge.get("judge_reasoning")),
            ]

            lines.append("<tr>")
            lines.append(f"<td valign=\"top\">{''.join(left_parts)}</td>")
            lines.append(f"<td valign=\"top\">{''.join(right_parts)}</td>")
            lines.append("</tr>")
            lines.append("</table>")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build doctor-facing Markdown review for prompt-only vs RAG hard cases.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Markdown output path")
    args = parser.parse_args()

    content = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
