# Documentation: RCC Treatment Prediction Pipeline

**Project:** Med_LLM — German Medical Oncology LLM Evaluation
**Status:** Active Development

---

## Overview

This project evaluates Large Language Models (LLMs) on their ability to recommend cancer treatments for renal cell carcinoma (Nierenzellkarzinom, RCC) cases based on German clinical guidelines.

### What We Do

1. **Input:** Anonymized clinical cases in German with patient data, staging, histology
2. **Process:** LLMs analyze each case and recommend therapy following NCC guidelines
3. **Evaluate:** AI judges (GPT-5.2 and MedGemma 27B) independently score each prediction
4. **Validate:** A board-certified uro-oncologist reviews all model predictions and judge evaluations
5. **Output:** Structured JSON with metastatic classification, IMDC risk, therapy recommendation, and judge scores

### Three-Tier Evaluation Pipeline

1. **Tier 1 — LLM Prediction:** Multiple models generate therapy recommendations from structured clinical JSON
2. **Tier 2 — AI Judge:** Two AI judges independently score each prediction on semantic match, clinical appropriateness, and reasoning quality
3. **Tier 3 — Expert Validation:** Board-certified uro-oncologist reviews all predictions and judge evaluations

---

## Folder Structure

```
documentation/
├── README.md                              # This file
│
├── 01_technical/                          # Technical documentation
│   ├── points_of_contention.md            # Technical issues and decisions
│   ├── hyperparameters.md                 # Model parameters
│   ├── json_schema_issue.md              # Data schema differences
│   └── infrastructure.md                  # Modal vs OpenRouter
│
├── 02_medical/                            # Medical/Clinical documentation
│   ├── points_of_contention.md            # Questions for medical expert
│   ├── therapy_guidelines.md              # Guidelines in the prompt
│   └── clinical_acceptability.md          # Evaluation criteria
│
├── 03_prompts/                            # Complete prompts (not truncated)
│   ├── main_model/
│   │   ├── prompt_german.md               # Full German prompt
│   │   └── prompt_english.md              # Full English translation
│   └── judge_model/
│       ├── prompt_german.md               # Full German judge prompt
│       └── prompt_english.md              # Full English translation
│
├── 04_examples/                           # Complete input/output examples
│   ├── main_model/
│   │   ├── input_case_ncc_1.json          # Full input case
│   │   ├── output_modal_ncc_1.json        # Modal output
│   │   ├── output_openrouter_ncc_1.json   # OpenRouter output
│   │   └── example_walkthrough.md         # Step-by-step explanation
│   └── judge_model/
│       ├── input_judge_example.json       # Judge input
│       ├── output_judge_example.json      # Judge output
│       └── example_walkthrough.md         # Step-by-step explanation
│
├── 05_results/                            # Evaluation methodology
│   ├── latest_comparison.md               # Platform comparison methodology
│   └── metrics_explanation.md             # What metrics mean
│
└── 06_action_items/                       # Next steps
    ├── technical_todo.md                  # Technical fixes needed
    └── medical_questions.md               # Questions for medical expert
```

---

## Quick Links

### For Technical Review
- [Technical Points of Contention](01_technical/points_of_contention.md)
- [JSON Schema Differences](01_technical/json_schema_issue.md)
- [Hyperparameters](01_technical/hyperparameters.md)
- [Infrastructure](01_technical/infrastructure.md)

### For Medical Review
- [Medical Points of Contention](02_medical/points_of_contention.md)
- [Therapy Guidelines](02_medical/therapy_guidelines.md)
- [Clinical Acceptability Criteria](02_medical/clinical_acceptability.md)

### Full Prompts
- [Main Model Prompt (German)](03_prompts/main_model/prompt_german.md)
- [Main Model Prompt (English)](03_prompts/main_model/prompt_english.md)
- [Judge Model Prompt (German)](03_prompts/judge_model/prompt_german.md)
- [Judge Model Prompt (English)](03_prompts/judge_model/prompt_english.md)

### Examples
- [Main Model Example Walkthrough](04_examples/main_model/example_walkthrough.md)
- [Judge Model Example Walkthrough](04_examples/judge_model/example_walkthrough.md)

### Results
- For actual results and numbers, see `findings/evaluation_report_*.md` and `findings/SUMMARY_REPORT.md`

---

## Infrastructure

### Modal (Primary)
- **Hardware:** NVIDIA H100 GPU
- **Framework:** vLLM with structured outputs
- **Processing:** Batched (all cases at once)
- **Reproducibility:** Seed=42 for deterministic results

### OpenRouter (Comparison)
- **Access:** REST API
- **Processing:** Sequential (one case at a time)
- **Reproducibility:** No seed support

---

## Contact

- **Clinical Lead:** Dr. Radu Alexa, Board-Certified Uro-Oncologist
- **Technical Implementation:** Ayush Nangia, Aman Gokrani

---

## Files Reference

| File Type | Location |
|-----------|----------|
| Treatment Scripts | `scripts/modal_treatment_predict.py`, `scripts/treatment_openrouter.py` |
| Judge Scripts | `scripts/modal_judge.py`, `scripts/evaluate_treatment_llm_judge.py` |
| Report Generation | `scripts/generate_evaluation_report.py`, `scripts/create_summary_report.py` |
| Case Data | `converted_data/` |
| Results | `results/modal_treatment/`, `results/openrouter_treatment/` |
| Findings | `findings/evaluation_report_*.md`, `findings/SUMMARY_REPORT.md` |
