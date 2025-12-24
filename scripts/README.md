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
