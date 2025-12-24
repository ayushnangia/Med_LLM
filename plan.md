# Med_LLM Project Plan

## Project Overview

**Project Lead:** Dr. Radu (Oncology/Urology Specialist)
**Goal:** Develop and evaluate LLMs for medical case classification and therapy recommendation
**Domain:** German urological oncology (tumor board discussions)

### Current Status (Dec 23, 2025)
- ✅ JSON schema standardized (v1.1)
- ✅ Therapy decision trees created (mRCC, NMRCC)
- ✅ 26 cases converted to JSON format
- ⏳ ~210 raw cases pending conversion
- ⏳ Classification pipeline pending

---

## Phase 1: Data Preparation ✅ COMPLETED

### Accomplished
- Converted all DOCX files to JSON/TXT
- Converted all XLSX files to CSV
- Created standardized folder structure
- Verified data integrity (no corruption)

### Output
```
converted_data/send_23_12_25/
├── ncc/           # 14 kidney cancer cases
├── pca/           # 2 prostate cancer cases
├── hoden_ca/      # 2 testicular cancer cases
├── penis_ca/      # 2 penile cancer cases
├── uca/           # 2 urothelial cancer cases
├── combi/         # 2 combined cases
└── non_uro/       # 2 non-urological cases
```

---

## Phase 2: Dataset Expansion

### Goal
Add at least 10 cases per class (as requested by Dr. Radu)

### Tasks
1. Convert remaining ~210 raw cases from XLSX to JSON
2. Validate each case against schema v1.1
3. Ensure balanced class distribution
4. Quality check with medical accuracy review

### Target Distribution
| Class | Current | Target | Description |
|-------|---------|--------|-------------|
| NCC | 14 | 40+ | Kidney Cancer |
| PCA | 2 | 12+ | Prostate Cancer |
| HODEN_CA | 2 | 12+ | Testicular Cancer |
| PENIS_CA | 2 | 12+ | Penile Cancer |
| UCA | 2 | 12+ | Urothelial Cancer |
| COMBI | 2 | 12+ | Polymalignancy |
| NON_URO | 2 | 12+ | Non-Urological |

---

## Phase 3: Classification Pipeline

### Objective
Multi-class classification: Given a clinical case, predict the cancer type.

### Classes (7)
1. `nierenzellkarzinom` (NCC) - Kidney Cancer
2. `prostatakarzinom` (PCA) - Prostate Cancer
3. `hodentumor` (HODEN) - Testicular Cancer
4. `peniskarzinom` (PENIS) - Penile Cancer
5. `urothelkarzinom` (UCA) - Urothelial Cancer
6. `polymalignancy` (COMBI) - Combined/Multiple
7. `non_urological` (NON_URO) - Non-Urological

### Prompt Template
```
Du bist ein medizinischer Experte für Onkologie. Analysiere den folgenden klinischen Fall und klassifiziere die Tumorentität.

FALL:
Patient: {nachname}, {vorname}, {alter_jahre} Jahre
Anamnese: {anamnese_freitext}
Diagnose: {diagnose_kurz}
TNM: {tnm_staging}
Befunde: {bildgebung}

KLASSIFIZIERE in eine der folgenden Kategorien:
- nierenzellkarzinom (Nierenkrebs/RCC)
- prostatakarzinom (Prostatakrebs)
- hodentumor (Hodenkrebs)
- peniskarzinom (Peniskrebs)
- urothelkarzinom (Blasen-/Harnwegskrebs)
- polymalignancy (Mehrfachtumoren)
- non_urological (Nicht-urologisch)

Antwort (nur die Kategorie):
```

### Inference with Ollama

**API Endpoint:** `http://localhost:11434/api/generate`

**Python Implementation:**
```python
import requests
import json

def classify_case(case_json: dict, model: str = "gemma3:27b") -> str:
    prompt = build_prompt(case_json)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low for classification
                "num_predict": 50    # Short response
            }
        }
    )

    result = response.json()["response"]
    return parse_classification(result)
```

---

## Phase 4: Model Evaluation

### Models to Test

**General Models (Installed):**
| Model | Size | Type |
|-------|------|------|
| gemma3:27b | 27B | General |
| gemma3:12b | 12B | General |
| qwen3:30b | 30B | General |
| qwen3:8b | 8B | General |
| llama3:8b | 8B | General |
| mistral:7b-instruct | 7B | General |

**Medical Models (To Install):**
| Model | Size | Specialty |
|-------|------|-----------|
| m42-health/Llama3-Med42-8B | 8B | Medical |
| ClinicalBERT | - | Clinical NLP |
| II-Medical-8B | 8B | Medical |

### Evaluation Metrics

1. **Overall Accuracy**: Correct predictions / Total cases
2. **Per-Class Metrics**:
   - Precision: TP / (TP + FP)
   - Recall: TP / (TP + FN)
   - F1-Score: 2 × (Precision × Recall) / (Precision + Recall)
3. **Confusion Matrix**: Visualize misclassifications

### Evaluation Script
```python
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

def evaluate_model(predictions, ground_truth, model_name):
    # Classification report
    report = classification_report(
        ground_truth, predictions,
        target_names=CLASS_NAMES,
        output_dict=True
    )

    # Confusion matrix
    cm = confusion_matrix(ground_truth, predictions)

    # Visualization
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d',
                xticklabels=CLASS_NAMES,
                yticklabels=CLASS_NAMES)
    plt.title(f'Confusion Matrix - {model_name}')
    plt.savefig(f'results/{model_name}_confusion.png')

    return report
```

---

## Phase 5: Results Presentation

### Report Structure

#### 1. Executive Summary
- Best performing model
- Overall accuracy achieved
- Key findings

#### 2. Model Comparison Table
| Model | Accuracy | F1 (macro) | Inference Time |
|-------|----------|------------|----------------|
| gemma3:27b | XX% | X.XX | Xs/case |
| qwen3:30b | XX% | X.XX | Xs/case |
| Med42-8B | XX% | X.XX | Xs/case |

#### 3. Per-Class Performance
| Class | Best Model | Precision | Recall | F1 |
|-------|------------|-----------|--------|-----|
| NCC | | | | |
| PCA | | | | |
| ... | | | | |

#### 4. Confusion Matrix Visualizations
- One per model tested
- Highlight common misclassifications

#### 5. Recommendations
- Recommended model for production
- Suggested improvements
- Next steps

### Output Files
```
results/
├── summary_report.md
├── model_comparison.csv
├── gemma3_27b_confusion.png
├── qwen3_30b_confusion.png
├── med42_8b_confusion.png
└── per_class_metrics.csv
```

---

## Technical Implementation

### Project Structure
```
Med_LLM/
├── CLAUDE.md
├── plan.md                    # This file
├── venv/                      # Python environment
├── scripts/
│   ├── convert_to_open_formats.py
│   ├── verify_data_integrity.py
│   ├── inference_ollama.py    # NEW: Ollama wrapper
│   ├── classify_cases.py      # NEW: Classification pipeline
│   └── evaluate_results.py    # NEW: Evaluation & visualization
├── data_llm/                  # Original data (DOCX, XLSX)
├── converted_data/            # Converted data (JSON, CSV)
└── results/                   # NEW: Evaluation results
```

### Dependencies
```bash
pip install requests scikit-learn matplotlib seaborn pandas
```

### Running the Pipeline
```bash
# 1. Ensure Ollama is running
ollama serve

# 2. Run classification
python scripts/classify_cases.py --model gemma3:27b

# 3. Evaluate results
python scripts/evaluate_results.py

# 4. Generate report
python scripts/generate_report.py
```

---

## Timeline

| Phase | Status | Priority |
|-------|--------|----------|
| Phase 1: Data Prep | ✅ Done | - |
| Phase 2: Dataset Expansion | ⏳ Pending | High |
| Phase 3: Classification Pipeline | ⏳ Pending | High |
| Phase 4: Model Evaluation | ⏳ Pending | Medium |
| Phase 5: Results Presentation | ⏳ Pending | Medium |

### Next Meeting Deliverables (per Dr. Radu)
1. Add 10+ cases per class
2. First results regarding detection between classes
