# NCC Treatment Prediction: Complete Documentation

**Project:** Med_LLM - German Medical Oncology LLM Evaluation
**Date:** 2025-12-30
**Status:** Active Development

---

## Overview

This project evaluates Large Language Models (LLMs) on their ability to recommend cancer treatments for kidney cancer (Nierenzellkarzinom/RCC) cases based on German clinical guidelines.

### What We Do

1. **Input:** 35 clinical cases in German with patient data, staging, histology
2. **Process:** LLM analyzes case and recommends therapy following NCC guidelines
3. **Output:** Structured JSON with metastatic classification, IMDC risk, therapy recommendation
4. **Evaluate:** Compare to tumor board ground truth using multiple metrics

---

## Folder Structure

```
documentation/
├── README.md                              # This file
│
├── 01_technical/                          # Technical documentation
│   ├── points_of_contention.md            # All technical issues
│   ├── hyperparameters.md                 # Model parameters
│   ├── json_schema_issue.md               # Critical data bug
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
├── 05_results/                            # Experiment results
│   ├── latest_comparison.md               # Modal vs OpenRouter
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
- [JSON Schema Bug (Critical)](01_technical/json_schema_issue.md)
- [Hyperparameters](01_technical/hyperparameters.md)

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
- [Latest Results Comparison](05_results/latest_comparison.md)

---

## Key Numbers (Latest Run: 2025-12-30)

| Metric | Modal (vLLM) | OpenRouter (API) |
|--------|-------------|------------------|
| Model | google/gemma-3-27b-it | google/gemma-3-27b-it |
| Metastatic Accuracy | 100% (11/11) | 100% (11/11) |
| Therapy Exact Match | 28.6% (10/35) | 25.7% (9/35) |
| Therapy Acceptable | 28.6% (10/35) | 28.6% (10/35) |
| Processing Time | 122s | 540s |

---

## Infrastructure

### Modal (Primary)
- **Hardware:** NVIDIA H100 GPU
- **Framework:** vLLM with structured outputs
- **Processing:** Batched (all 35 cases at once)
- **Reproducibility:** Seed=42 for deterministic results

### OpenRouter (Comparison)
- **Access:** REST API
- **Processing:** Sequential (one case at a time)
- **Reproducibility:** No seed support

---

## Contact

- **Data Provider:** Medical oncologist (German-speaking)
- **Technical Implementation:** Claude Code assistance

---

## Files Reference

| File Type | Location |
|-----------|----------|
| Treatment Scripts | `scripts/modal_treatment_predict.py`, `scripts/treatment_openrouter.py` |
| Judge Script | `scripts/evaluate_treatment_llm_judge.py` |
| Case Data | `converted_data/send_27_12_25/ncc/ncc_cases_json.json` |
| Results | `results/modal_treatment/`, `results/openrouter_treatment/` |
