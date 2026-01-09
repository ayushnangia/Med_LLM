# Scripts

Python scripts for data conversion, classification, and evaluation.

## Requirements

```bash
pip install python-docx openpyxl pandas requests scikit-learn matplotlib seaborn
```

**ALWAYS use the project's virtual environment:**
```bash
source ../venv/bin/activate
```

## Data Conversion Scripts

### convert_to_open_formats.py

Converts all data files from proprietary formats to open source formats:
- **DOCX → JSON** (case data, schemas)
- **DOCX → TXT** (plain text documents)
- **XLSX → CSV** (spreadsheets)

```bash
python scripts/convert_to_open_formats.py
```

**Output:** `converted_data/send_23_12_25/`

### verify_data_integrity.py

Verifies that no data was lost during conversion:
- Compares DOCX case counts with JSON output
- Verifies JSON patient data matches CSV
- Checks XLSX row counts match CSV

```bash
python scripts/verify_data_integrity.py
```

## Classification Pipeline Scripts

### inference_ollama.py

Ollama API wrapper for medical case classification.

```python
from inference_ollama import OllamaClassifier

classifier = OllamaClassifier(model="qwen3:latest")
result = classifier.classify(case_json)
```

### classify_cases.py

Runs classification on all cases and saves results to `findings/`.

```bash
# List available models
python scripts/classify_cases.py --list-models

# Run classification
python scripts/classify_cases.py --model qwen3:latest
```

**Output:** `findings/results_{model}_{timestamp}.json`

### evaluate_results.py

Generates evaluation metrics, confusion matrices, and reports.

```bash
python scripts/evaluate_results.py
```

**Output:**
- `findings/evaluation_report.md` - Detailed metrics
- `findings/confusion_matrix_{model}.png` - Visualizations

## Treatment Prediction Scripts

### modal_treatment_predict.py

Runs NCC treatment prediction on Modal (serverless GPU) using vLLM.

```bash
modal run scripts/modal_treatment_predict.py --model gemma-3-27b
modal run scripts/modal_treatment_predict.py --model olmo-3.1-32b-think
```

**Available models:** `gemma-3-4b`, `gemma-3-12b`, `gemma-3-27b`, `medgemma-4b`, `medgemma-27b`, `meditron3-7b`, `olmo-3.1-32b-instruct`, `olmo-3.1-32b-think`

**Output:** `results/modal_treatment/{model}/{timestamp}/ncc_*.json`

### treatment_openrouter.py

Runs NCC treatment prediction via OpenRouter API.

```bash
export OPENROUTER_API_KEY="your-key"
python scripts/treatment_openrouter.py --model gemma3:27b
```

### evaluate_treatment_llm_judge.py

Uses LLM-as-Judge to evaluate treatment predictions.

```bash
python scripts/evaluate_treatment_llm_judge.py \
  --results-dir results/modal_treatment/google_gemma-3-27b-it/2025-12-30_00-02-19/
```

### export_results_csv.py

Exports results to CSV for medical review.

```bash
python scripts/export_results_csv.py --all --latest   # Latest run per model
python scripts/export_results_csv.py --all            # All runs
```

**Output:** `to_be_reviewed_results/{model}_treatment_{dd-mm-yy}.csv`

## Known Issues and Fixes

### 1. JSON Schema Compatibility (Fixed January 2026)

**Problem:** Cases 15-32 had empty ECOG/Karnofsky because the NCC data uses two different JSON schemas.

**Symptoms:**
- Empty `ecog` and `karnofsky` columns in CSV for cases 15-32
- Model prompts show `ECOG: ?` for these cases

**Fix Applied:** Both `modal_treatment_predict.py` and `treatment_openrouter.py` now handle both schemas:
- Schema v1.1 (cases 1-14): `patient.performance_status.ecog`
- Schema v1.0 (cases 15-35): `patient.ecog` (flat) + `marker_oder_labor.sonstige[]`

**Action Required:** Re-run inference to get correct data in results.

### 2. Thinking Model Token Limit (Fixed January 2026)

**Problem:** Thinking models (e.g., `olmo-3.1-32b-think`) failed on 11/35 cases with JSON parse errors.

**Cause:** `max_tokens` was 4096, but `<think>` blocks consumed all tokens before JSON output.

**Symptoms:**
- `tokens_used: 4096` exactly in failed cases
- Error: `Invalid JSON: expected value at line 1 column 1`
- Raw response truncated mid-word

**Fix Applied:** Increased `max_tokens` from 4096 to 65536 for thinking models.

## Output Structure

After running `convert_to_open_formats.py`:

```
converted_data/send_23_12_25/
├── case_structure_json_v_1_1.json
├── info.txt
├── list_models.txt
├── therapy_structure_*.json
├── ncc/
│   ├── ncc_cases_json.json
│   └── ncc.csv
├── pca/
│   ├── pca_cases_json.json
│   └── pca.csv
└── ... (other cancer type folders)
```
