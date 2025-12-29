# Med_LLM Project Plan

## Project Overview

**Project Lead:** Dr. Radu (Oncology/Urology Specialist)
**Goal:** Develop and evaluate LLMs for medical case classification and therapy recommendation
**Domain:** German urological oncology (tumor board discussions)

### Current Status (Dec 30, 2025)

| Component | Status | Details |
|-----------|--------|---------|
| Data Preparation | ✅ Done | JSON/CSV conversion complete |
| Classification Pipeline | ✅ Done | 7-class cancer type classification |
| Treatment Prediction | ✅ Done | NCC therapy recommendation system |
| LLM-as-Judge | ✅ Done | Semantic + clinical evaluation |
| Documentation | ✅ Done | Comprehensive docs for medical review |

---

## Completed Work

### Phase 1: Data Preparation ✅

- Converted DOCX files to JSON/TXT
- Converted XLSX files to CSV
- Standardized folder structure
- 35 NCC cases available (14 schema v1.1 + 21 schema v1.2)

### Phase 2: Classification Pipeline ✅

**7-class cancer type classification**

| Model | Accuracy | Notes |
|-------|----------|-------|
| mistral:7b-instruct | 88.46% | Best local performer |
| gemma3:4b | 84.62% | Fast, excellent accuracy |
| llama3:8b | 76.92% | Good balance |

Results in: `findings/` and `results/ollama/`

### Phase 3: Treatment Prediction (NCC) ✅

**Therapy recommendation for kidney cancer cases**

| Platform | Model | Metastatic Acc | Therapy Match | Time |
|----------|-------|----------------|---------------|------|
| Modal (vLLM) | Gemma-3-27B | 100% | 28.6% | 122s |
| OpenRouter | Gemma-3-27B | 100% | 28.6% | 540s |

Scripts:
- `scripts/modal_treatment_predict.py` - Modal serverless GPU
- `scripts/treatment_openrouter.py` - OpenRouter API
- `scripts/evaluate_treatment_llm_judge.py` - LLM-as-Judge evaluation

Results in: `results/modal_treatment/` and `results/openrouter_treatment/`

### Phase 4: Documentation ✅

Created comprehensive documentation in `documentation/`:

```
documentation/
├── README.md
├── 01_technical/          # Technical points of contention
├── 02_medical/            # Medical questions for expert
├── 03_prompts/            # Full prompts (German + English)
├── 04_examples/           # Complete input/output examples
├── 05_results/            # Latest comparison and metrics
└── 06_action_items/       # Todo lists (technical + medical)
```

---

## Open Issues

### Technical (Developer)

| Issue | Priority | Status |
|-------|----------|--------|
| JSON Schema Bug (Cases 15-35 ECOG=null) | CRITICAL | Needs fix |
| OpenRouter no seed support | LOW | Document limitation |

Fix required in:
- `scripts/modal_treatment_predict.py` (lines 272-273)
- `scripts/treatment_openrouter.py` (lines 505-506)

```python
# Current (broken):
"ecog": patient.get("performance_status", {}).get("ecog"),

# Required fix:
"ecog": patient.get("ecog") or patient.get("performance_status", {}).get("ecog"),
```

### Medical (Dr. Radu)

See `documentation/06_action_items/medical_questions.md`:

1. Ground truth definition (tumor board vs actual treatment?)
2. IMDC handling for non-clear-cell RCC
3. ICI eligibility criteria
4. Clinical acceptability validation
5. JSON schema standardization (he changed schema between cases)

---

## Project Structure

```
Med_LLM/
├── CLAUDE.md                    # Development instructions
├── plan.md                      # This file
├── venv/                        # Python environment
├── scripts/
│   ├── convert_to_open_formats.py
│   ├── verify_data_integrity.py
│   ├── inference_ollama.py
│   ├── inference_openrouter.py
│   ├── classify_cases.py
│   ├── classify_openrouter.py
│   ├── run_all_models.py
│   ├── evaluate_results.py
│   ├── modal_treatment_predict.py   # Treatment prediction (Modal)
│   ├── treatment_openrouter.py      # Treatment prediction (OpenRouter)
│   └── evaluate_treatment_llm_judge.py  # LLM-as-Judge
├── data_llm/                    # Original data (DOCX, XLSX)
├── converted_data/              # Converted data (JSON, CSV)
├── results/
│   ├── ollama/                  # Classification results
│   ├── openrouter/              # Classification results
│   ├── modal_treatment/         # Treatment prediction (Modal)
│   └── openrouter_treatment/    # Treatment prediction (OpenRouter)
├── findings/                    # Quick access results
└── documentation/               # Comprehensive documentation
```

---

## Running the Pipeline

### Classification (7-class)
```bash
source venv/bin/activate
python scripts/classify_cases.py --model mistral:7b-instruct
python scripts/evaluate_results.py
```

### Treatment Prediction (NCC)
```bash
# Modal (requires modal CLI)
modal run scripts/modal_treatment_predict.py --model gemma-3-27b

# OpenRouter (requires OPENROUTER_API_KEY)
export OPENROUTER_API_KEY="your-key"
python scripts/treatment_openrouter.py --model gemma3:27b
```

### LLM-as-Judge Evaluation
```bash
python scripts/evaluate_treatment_llm_judge.py --results-dir results/modal_treatment/...
```

---

## Key Metrics

### Treatment Prediction (Gemma-3-27B on 35 NCC cases)

| Metric | Definition | Result |
|--------|------------|--------|
| Metastatic Accuracy | Correctly identify metastatic cases | 100% (11/11) |
| Therapy Exact Match | Fuzzy match to ground truth | 28.6% (10/35) |
| Therapy Acceptable | Guideline-compliant recommendation | 28.6% (10/35) |

### LLM-as-Judge Scores

| Metric | Weight | Description |
|--------|--------|-------------|
| therapy_semantic_score | 40% | Does therapy match ground truth? |
| clinical_appropriateness_score | 40% | Is it guideline-compliant? |
| reasoning_quality | 20% | Is the explanation sound? |

---

## Next Steps

1. **Dr. Radu:** Review medical questions in `documentation/06_action_items/medical_questions.md`
2. **Technical:** Fix JSON schema extraction bug for cases 15-35
3. **Technical:** Investigate low therapy match rate (28.6%)
4. **Future:** Expand to other cancer types (PCA, UCA, etc.)

---

## Data Summary

| Cancer Type | Cases | Status |
|-------------|-------|--------|
| NCC (Kidney) | 35 | ✅ Treatment prediction complete |
| PCA (Prostate) | 2 | Classification only |
| HODEN_CA (Testicular) | 2 | Classification only |
| PENIS_CA (Penile) | 2 | Classification only |
| UCA (Urothelial) | 2 | Classification only |
| COMBI (Combined) | 2 | Classification only |
| NON_URO (Non-Urological) | 2 | Classification only |

---

## Hyperparameters (Aligned)

| Parameter | Value | Notes |
|-----------|-------|-------|
| temperature | 0.3 | Low for consistency |
| top_p | 0.95 | Standard |
| max_tokens | 32768 | Full reasoning |
| seed | 42 | Modal only (OpenRouter N/A) |
