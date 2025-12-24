# Med_LLM - Medical Oncology Dataset for LLM Training

This folder contains clinical case data converted from proprietary formats (DOCX, XLSX) to open source formats (JSON, CSV, TXT) for training Large Language Models on medical decision-making.

## Project Overview

**Purpose:** Build a training dataset for medical LLMs to assist in clinical decision-making during tumor board discussions.

**Domain:** German oncology/urology - focuses on urological cancers (prostate, kidney, testicular, penile, urothelial) and non-urological cancers.

**Language:** German medical terminology

**Data Provider:** Medical doctor (oncology/urology specialist)

---

## Folder Structure

```
converted_data/
└── send_23_12_25/                       # Data snapshot dated Dec 23, 2025
    │
    ├── Documentation Files
    │   ├── info.txt                     # Project status and progress notes
    │   ├── list_models.txt              # Recommended LLM models for testing
    │   ├── case_structure_json_v_1_1.json   # JSON schema specification
    │   ├── therapy_structure_ncc_metatastic_*.json      # mRCC therapy decision tree
    │   └── therapy_structure_ncc_non_metastatic_*.json  # NMRCC therapy decision tree
    │
    └── Cancer Case Data (by type)
        ├── ncc/          # Kidney Cancer (Nierenzellkarzinom) - 14 cases
        ├── pca/          # Prostate Cancer (Prostatakarzinom) - 2 cases
        ├── hoden_ca/     # Testicular Cancer (Hodentumor) - 2 cases
        ├── penis_ca/     # Penile Cancer (Peniskarzinom) - 2 cases
        ├── uca/          # Urothelial Cancer (Urothelkarzinom) - 2 cases
        ├── combi/        # Combined/Polymalignancy cases - 2 cases
        └── non_uro/      # Non-urological cancers - 2 cases
```

Each cancer folder contains:
- `*_cases_json.json` - Detailed case data in JSON format
- `*.csv` - Case summary spreadsheet

---

## File Formats

### JSON Files (`.json`)
Structured clinical case data following schema v1.1. Each case includes:
- **case_meta**: Case ID, presentation date, tumor board info
- **patient**: Demographics, ECOG/Karnofsky performance status, comorbidities
- **entitaeten**: Disease entities with TNM staging, molecular markers, imaging, therapies
- **geplantes_therapiekonzept**: Planned therapy concept

### CSV Files (`.csv`)
Tabular case summaries with columns:
| Column | Description |
|--------|-------------|
| Nr. | Case number |
| Cases | Patient name and DOB |
| Classes | Tumor entity classification |
| Therapy line | Treatment stage/status |
| json | JSON available (True/False) |
| json_ver | Schema version |
| urological/non_urological | Specialty flag |

### TXT Files (`.txt`)
Plain text documentation and notes.

---

## JSON Schema (v1.1)

### Case Structure
```json
{
  "schema_version": "1.1",
  "cases": [
    {
      "case_meta": {
        "fallnummer": "unique_id",
        "datum_vorstellung": "YYYY-MM-DD",
        "tumorboard": null,
        "diskussionstyp": null
      },
      "patient": {
        "nachname": "Last name",
        "vorname": "First name",
        "geburtsdatum": "YYYY-MM-DD",
        "alter_jahre": 65,
        "performance_status": {
          "ecog": 0,
          "karnofsky_prozent": 100
        },
        "komorbiditaet_level": "unknown|low|high",
        "lebenserwartung": "unknown|limited|normal"
      },
      "entitaeten": [
        {
          "entity_id": "E1",
          "entitaet_typ": "nierenzellkarzinom",
          "diagnose_kurz": "Short diagnosis",
          "klassifikation": {
            "tnm_clinical": { "T": "T1", "N": "N0", "M": "M0" },
            "tnm_pathological": { "T": null, "N": null, "M": null }
          },
          "molekular": { "brca": null, "pd_l1": null },
          "bildgebung": [],
          "therapien_und_eingriffe": []
        }
      ]
    }
  ]
}
```

### Missing Values Convention
- `null` - Absent single values
- `[]` - Absent arrays
- `"unknown"` - Default for comorbidity_level and lebenserwartung

---

## Medical Domain Reference

### TNM Classification
- **T** (Tumor): T0-T4 based on size and local extension
- **N** (Nodes): N0 (no involvement), N1 (regional involvement)
- **M** (Metastasis): M0 (none), M1 (distant metastases)

### Performance Status
- **ECOG**: 0-4 scale (0 = fully active, 4 = bedridden)
- **Karnofsky**: 0-100% scale (100% = normal, no complaints)

### IMDC Risk Stratification (for metastatic RCC)
Risk factors:
1. Karnofsky < 80%
2. Time from diagnosis to systemic therapy < 1 year
3. Hemoglobin below normal
4. Corrected calcium above normal
5. Neutrophils above normal
6. Platelets above normal

Categories:
- **Favorable (günstig)**: 0 risk factors
- **Intermediate (intermediär)**: 1-2 risk factors
- **Unfavorable (ungünstig)**: ≥3 risk factors

---

## Therapy Decision Trees

### Metastatic RCC (mRCC)
File: `therapy_structure_ncc_metatastic_*.json`

First-line options based on IMDC risk:
- **ICI+TKI combinations**: Nivolumab+Cabozantinib, Pembrolizumab+Axitinib, Pembrolizumab+Lenvatinib
- **ICI+ICI**: Nivolumab+Ipilimumab
- **TKI monotherapy**: Pazopanib, Sunitinib, Cabozantinib

### Non-Metastatic RCC (NMRCC)
File: `therapy_structure_ncc_non_metastatic_*.json`

Management pathways:
- Active surveillance (small tumors, high comorbidity)
- Ablation therapy (cryoablation, radiofrequency)
- Partial nephrectomy (nephron-sparing)
- Radical nephrectomy

---

## Data Statistics

| Cancer Type | Cases | File |
|-------------|-------|------|
| Kidney Cancer (NCC) | 14 | ncc/ncc_cases_json.json |
| Prostate Cancer (PCA) | 2 | pca/pca_cases_json.json |
| Testicular Cancer | 2 | hoden_ca/hoden_ca_cases_json.json |
| Penile Cancer | 2 | penis_ca/penis_ca_cases_json.json |
| Urothelial Cancer | 2 | uca/uca_ca_cases_json.json |
| Combined Cases | 2 | combi/combi_ca_cases_json.json |
| Non-Urological | 2 | non_uro/non_uro_ca_cases_json.json |
| **Total** | **26** | |

---

## Recommended LLM Models

From `list_models.txt`:

**Medical-specific models:**
- `m42-health/Llama3-Med42-8B`
- `medicalai/ClinicalBERT`
- `Intelligent-Internet/II-Medical-8B`

**General models (installed):**
- GLM-4, Gemma 3, Qwen variants, Llama3, Mistral

---

## Usage Examples

### Python - Load JSON Cases
```python
import json

with open('send_23_12_25/ncc/ncc_cases_json.json') as f:
    data = json.load(f)

for case in data['cases']:
    patient = case['patient']
    print(f"{patient['nachname']}, {patient['vorname']}: {case['entitaeten'][0]['diagnose_kurz']}")
```

### Python - Load CSV
```python
import pandas as pd

df = pd.read_csv('send_23_12_25/ncc/ncc.csv')
print(df[['Cases', 'Classes : tumor entity _ real', 'Therapy line']])
```

### Validate JSON Schema
```python
import json
import jsonschema

with open('send_23_12_25/case_structure_json_v_1_1.json') as f:
    schema = json.load(f)

# Use schema to validate new cases
```

---

## Source Data

Original files were in proprietary formats:
- **DOCX** (Microsoft Word) → Converted to JSON/TXT
- **XLSX** (Microsoft Excel) → Converted to CSV

Conversion performed using:
- `python-docx` - DOCX parsing
- `openpyxl` / `pandas` - XLSX to CSV conversion

---

## License & Usage

This dataset is intended for:
- Medical LLM training and evaluation
- Clinical decision support research
- Educational purposes in oncology

**Note:** All patient names in this dataset are fictional/anonymized for privacy.

---

## Contact

Project maintained by medical oncology/urology specialist.

Data snapshot: December 23, 2025
