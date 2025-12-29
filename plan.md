# Med_LLM Project Plan

**Last Updated:** December 30, 2025
**Project Lead:** Dr. Radu (Oncology/Urology Specialist)
**Repository:** https://github.com/ayushnangia/Med_LLM
**Branch:** `google-drive-data-v2`

---

## Executive Summary

This project evaluates Large Language Models for German medical oncology decision-making. We have completed two main pipelines:

| Pipeline | Purpose | Best Result | Status |
|----------|---------|-------------|--------|
| **Classification** | 7-class cancer type detection | 100% accuracy (MiMo v2) | ✅ Complete |
| **Treatment Prediction** | NCC therapy recommendation | 100% metastatic, 28.6% therapy match (Gemma-3-27B) | ✅ Complete |

**Current Blockers:**
1. JSON Schema Bug - Cases 15-35 missing ECOG/Karnofsky data (Dr. Radu changed schema)
2. Medical Review Needed - 10 questions pending for Dr. Radu

---

## For Dr. Radu (Medical Expert Review)

### Action Required

Please review these files on GitHub:

| Priority | File | What to Do |
|----------|------|------------|
| **HIGH** | [`documentation/06_action_items/medical_questions.md`](https://github.com/ayushnangia/Med_LLM/blob/google-drive-data-v2/documentation/06_action_items/medical_questions.md) | Answer 10 medical questions |
| **HIGH** | [`documentation/01_technical/json_schema_issue.md`](https://github.com/ayushnangia/Med_LLM/blob/google-drive-data-v2/documentation/01_technical/json_schema_issue.md) | Confirm which JSON schema is correct |
| **MEDIUM** | [`documentation/02_medical/clinical_acceptability.md`](https://github.com/ayushnangia/Med_LLM/blob/google-drive-data-v2/documentation/02_medical/clinical_acceptability.md) | Validate acceptable therapy lists |
| **MEDIUM** | [`documentation/04_examples/main_model/`](https://github.com/ayushnangia/Med_LLM/blob/google-drive-data-v2/documentation/04_examples/main_model/) | Review LLM reasoning quality |

### Key Questions Needing Your Input

1. **Ground Truth Definition:** Is `ground_truth_therapy` the tumor board consensus or actual treatment given?
2. **JSON Schema:** You changed the structure for cases 15-35. Which version should we standardize on?
3. **IMDC for Non-Clear-Cell:** Should we skip IMDC entirely or calculate with disclaimer?
4. **Clinical Acceptability:** Are our "valid therapy" lists complete and correct?
5. **ICI Eligibility:** What criteria determine if ICI combination is feasible?

### The JSON Schema Problem (Your Change Caused a Bug)

Cases 1-14 and 15-35 have different structures:

| Field | Cases 1-14 (Schema v1.1) | Cases 15-35 (Schema v1.2) |
|-------|--------------------------|---------------------------|
| ECOG | `patient.performance_status.ecog` | `patient.ecog` |
| Karnofsky | `patient.performance_status.karnofsky_prozent` | Not present |
| TNM | Separate `tnm_clinical` + `tnm_pathological` | Single `tnm` field |
| IMDC | `rcc_spezifisch.imdc` | `risikomodelle.imdc` |

**Result:** Cases 15-35 return `ECOG: null` because our code only checks the v1.1 path.

**Your Options:**
- A) Standardize all data to v1.1 format (nested)
- B) Standardize all data to v1.2 format (flattened)
- C) We update code to handle both (quick fix, but messy long-term)

---

## Project Timeline

| Date | Milestone |
|------|-----------|
| Dec 23, 2025 | Data preparation complete (26 cases) |
| Dec 27, 2025 | Classification pipeline complete (88.46% accuracy) |
| Dec 27, 2025 | New data batch received (35 NCC cases total) |
| Dec 29, 2025 | Treatment prediction scripts created (Modal + OpenRouter) |
| Dec 30, 2025 | Hyperparameters aligned, LLM-as-Judge implemented |
| Dec 30, 2025 | Comprehensive documentation created |

---

## Pipeline 1: Classification (Complete)

**Task:** Given a clinical case, predict the cancer type (7 classes).

### Classes
1. `nierenzellkarzinom` (NCC) - Kidney Cancer
2. `prostatakarzinom` (PCA) - Prostate Cancer
3. `hodentumor` (HODEN) - Testicular Cancer
4. `peniskarzinom` (PENIS) - Penile Cancer
5. `urothelkarzinom` (UCA) - Urothelial Cancer
6. `polymalignancy` (COMBI) - Combined/Multiple
7. `non_urological` (NON_URO) - Non-Urological

### Results (14 models tested on 26 cases via OpenRouter)

| Rank | Model | Accuracy | Response Time |
|------|-------|----------|---------------|
| 1 | MiMo v2 (Free) | **100.0%** | 1.54s |
| 2 | Kimi K2 | 96.2% | 5.62s |
| 3 | Gemini 3 Pro | 96.2% | 2.68s |
| 4 | Claude Opus 4.5 | 96.2% | 1.71s |
| 5 | GPT-5.2 | 96.2% | 0.73s |
| 6 | DeepSeek v3.2 | 96.2% | 4.17s |
| 7 | Gemma 3 (12B) | 92.3% | 0.79s |
| 8 | Gemma 3 (27B) | 92.3% | 1.50s |
| 9 | Gemma 3 (4B) | 84.6% | 0.80s |

**Full report:** `findings/SUMMARY_REPORT.md`

### Running Classification
```bash
source venv/bin/activate
export OPENROUTER_API_KEY="your-key"
python scripts/classify_openrouter.py --model MODEL_NAME
python scripts/evaluate_results.py
```

---

## Pipeline 2: Treatment Prediction (Complete)

**Task:** Given an NCC case, recommend appropriate therapy following German oncology guidelines.

### How It Works

1. **Input:** Patient case (demographics, staging, histology, comorbidities)
2. **Prompt:** German clinical prompt with embedded therapy guidelines
3. **Output:** Structured JSON with:
   - Metastatic classification (yes/no)
   - IMDC risk category (favorable/intermediate/unfavorable)
   - Therapy recommendation
   - Clinical reasoning

### Infrastructure Comparison

| Aspect | Modal (vLLM) | OpenRouter (API) |
|--------|--------------|------------------|
| **Model** | google/gemma-3-27b-it | google/gemma-3-27b-it |
| **Processing** | Batched (GPU) | Sequential (API) |
| **Time (35 cases)** | 122 seconds | 540 seconds |
| **JSON Handling** | Pydantic + vLLM structured | Manual regex parsing |
| **Seed Support** | Yes (42) | No |
| **Cost** | ~$0.50/run | ~$2.00/run |

### Latest Results (Dec 30, 2025)

| Metric | Modal | OpenRouter | Definition |
|--------|-------|------------|------------|
| **Metastatic Accuracy** | 100% (11/11) | 100% (11/11) | Correctly identify metastatic cases |
| **Therapy Exact Match** | 28.6% (10/35) | 25.7% (9/35) | Fuzzy match to ground truth |
| **Therapy Acceptable** | 28.6% (10/35) | 28.6% (10/35) | Guideline-compliant recommendation |
| **Errors** | 0 | 0 | Parse/API failures |

**Note:** Metastatic accuracy is only calculated on the 11 metastatic cases, not all 35.

### Why Is Therapy Match Only 28.6%?

This needs investigation. Possible reasons:
1. Ground truth uses different terminology than model output
2. Non-metastatic cases (24/35) may have different evaluation criteria
3. Clinical acceptability criteria may be incomplete
4. JSON schema bug affecting ECOG values

### Running Treatment Prediction

```bash
# Modal (requires modal CLI + account)
modal run scripts/modal_treatment_predict.py --model gemma-3-27b

# OpenRouter (requires API key)
export OPENROUTER_API_KEY="your-key"
python scripts/treatment_openrouter.py --model gemma3:27b
```

---

## Pipeline 3: LLM-as-Judge (Complete)

**Task:** Use a separate LLM to evaluate the quality of therapy recommendations.

### Evaluation Criteria

| Metric | Weight | Range | Description |
|--------|--------|-------|-------------|
| `therapy_semantic_score` | 40% | 0.0-1.0 | Does therapy match ground truth semantically? |
| `clinical_appropriateness_score` | 40% | 0.0-1.0 | Is it guideline-compliant? |
| `reasoning_quality` | 20% | 0.0-1.0 | Is the explanation complete and logical? |
| `overall_score` | - | 0.0-1.0 | Weighted average |

### Running LLM-as-Judge
```bash
python scripts/evaluate_treatment_llm_judge.py \
  --results-dir results/modal_treatment/google_gemma-3-27b-it/2025-12-30_00-02-19/
```

---

## Hyperparameters (Aligned Across Platforms)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `temperature` | 0.3 | Low for consistency |
| `top_p` | 0.95 | Standard sampling |
| `max_tokens` | 32768 | Allow full reasoning |
| `seed` | 42 | Modal only (OpenRouter N/A) |

---

## Technical Issues

### CRITICAL: JSON Schema Extraction Bug

**Status:** Needs fix
**Impact:** Cases 15-35 return null for ECOG/Karnofsky

**Files to Update:**
- `scripts/modal_treatment_predict.py` (lines 272-273)
- `scripts/treatment_openrouter.py` (lines 505-506)

**Fix:**
```python
# Current (broken for v1.2):
"ecog": patient.get("performance_status", {}).get("ecog"),

# Required fix:
"ecog": patient.get("ecog") or patient.get("performance_status", {}).get("ecog"),
"karnofsky": patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent"),
```

### RESOLVED Issues

| Issue | Status | Resolution |
|-------|--------|------------|
| Hyperparameter mismatch | ✅ Fixed | Aligned temp=0.3, top_p=0.95, max_tokens=32768 |
| Prompt truncation in logs | ✅ Fixed | Full prompt now saved |
| Missing full_case field | ✅ Fixed | Both scripts save original case JSON |
| Model name discrepancy | ✅ Fixed | Both use google/gemma-3-27b-it |

---

## Data Summary

| Cancer Type | Cases | Classification | Treatment Prediction |
|-------------|-------|----------------|---------------------|
| NCC (Kidney) | 35 | ✅ | ✅ Complete |
| PCA (Prostate) | 2 | ✅ | ⏳ Pending |
| HODEN_CA (Testicular) | 2 | ✅ | ⏳ Pending |
| PENIS_CA (Penile) | 2 | ✅ | ⏳ Pending |
| UCA (Urothelial) | 2 | ✅ | ⏳ Pending |
| COMBI (Combined) | 2 | ✅ | ⏳ Pending |
| NON_URO (Non-Urological) | 2 | ✅ | ⏳ Pending |

**Data Location:** `converted_data/send_27_12_25/ncc/ncc_cases_json.json`

---

## Project Structure

```
Med_LLM/
├── CLAUDE.md                         # Development instructions
├── plan.md                           # This file
├── requirements.txt                  # Python dependencies
├── venv/                             # Python virtual environment
│
├── scripts/
│   ├── convert_to_open_formats.py    # DOCX→JSON conversion
│   ├── verify_data_integrity.py      # Data validation
│   ├── classify_cases.py             # Classification (Ollama)
│   ├── classify_openrouter.py        # Classification (OpenRouter)
│   ├── evaluate_results.py           # Classification metrics
│   ├── modal_treatment_predict.py    # Treatment prediction (Modal)
│   ├── treatment_openrouter.py       # Treatment prediction (OpenRouter)
│   └── evaluate_treatment_llm_judge.py  # LLM-as-Judge
│
├── data_llm/                         # Original data (DOCX, XLSX)
├── converted_data/                   # Converted data (JSON, CSV)
│
├── results/
│   ├── ollama/                       # Classification results (local)
│   ├── openrouter/                   # Classification results (API)
│   ├── modal_treatment/              # Treatment prediction (Modal)
│   └── openrouter_treatment/         # Treatment prediction (OpenRouter)
│
├── findings/                         # Quick-access results
│
└── documentation/                    # Comprehensive documentation
    ├── README.md
    ├── 01_technical/                 # Technical points of contention
    ├── 02_medical/                   # Medical questions
    ├── 03_prompts/                   # Full prompts (German + English)
    ├── 04_examples/                  # Input/output examples
    ├── 05_results/                   # Latest comparison
    └── 06_action_items/              # Todo lists
```

---

## Next Steps

### Immediate (Blocking)

| Task | Owner | Priority |
|------|-------|----------|
| Answer medical questions | Dr. Radu | HIGH |
| Decide on JSON schema standardization | Dr. Radu | HIGH |
| Fix ECOG/Karnofsky extraction bug | Developer | HIGH |

### Short-term

| Task | Owner | Priority |
|------|-------|----------|
| Investigate low therapy match rate (28.6%) | Developer | MEDIUM |
| Run LLM-as-Judge on all 35 cases | Developer | MEDIUM |
| Validate clinical acceptability lists | Dr. Radu | MEDIUM |

### Future

| Task | Owner | Priority |
|------|-------|----------|
| Expand treatment prediction to PCA, UCA | Developer | LOW |
| Test additional models (Med42, Meditron) | Developer | LOW |
| Add more NCC cases | Dr. Radu | LOW |

---

## Quick Commands

```bash
# Activate environment
source venv/bin/activate

# Classification
python scripts/classify_cases.py --model mistral:7b-instruct

# Treatment Prediction (Modal)
modal run scripts/modal_treatment_predict.py --model gemma-3-27b

# Treatment Prediction (OpenRouter)
export OPENROUTER_API_KEY="your-key"
python scripts/treatment_openrouter.py --model gemma3:27b

# LLM-as-Judge
python scripts/evaluate_treatment_llm_judge.py --results-dir results/modal_treatment/...
```

---

## Documentation Links

All comprehensive documentation is in the `documentation/` folder:

- [README](documentation/README.md) - Overview
- [Technical Issues](documentation/01_technical/) - JSON schema, hyperparameters, infrastructure
- [Medical Questions](documentation/02_medical/) - Questions for Dr. Radu
- [Prompts](documentation/03_prompts/) - Full German + English prompts
- [Examples](documentation/04_examples/) - Complete input/output examples
- [Results](documentation/05_results/) - Latest comparison and metrics
- [Action Items](documentation/06_action_items/) - Technical and medical todos
