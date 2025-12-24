# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Attribution

This project was developed with assistance from **Claude Code** (claude.ai/code) using **Claude Opus 4.5**.

## Project Overview

Med_LLM is a German medical oncology dataset project for training Large Language Models on clinical decision-making. The project focuses on urological cancer cases (prostate, kidney, testicular, penile, urothelial) and non-urological cancers, structured for tumor board discussions.

## Data Provider Workflow

This project is led by a medical doctor (oncology/urology specialist) who provides clinical case data. The typical workflow:

1. **Doctor provides data** in DOCX files (case narratives, structured forms)
2. **Read ALL documentation first** before any conversion work
3. **Convert DOCX → JSON** following the schema specification
4. **Validate** against schema and medical accuracy

**Critical:** Always read `info.docx` and `case_structure_json_v_1_1.docx` to understand current project state before processing new data.

## Data Structure

```
data_llm/send_23_12_25/
├── Documentation (DOCX):
│   ├── info.docx                    # Project status and progress
│   ├── case_structure_json_v_1_1.docx   # JSON schema specification
│   ├── list_models.docx             # Available LLM models
│   └── therapy_structure_*.docx     # NCC guideline-based therapy schemas
│
└── Cancer Case Data (by type):
    ├── pca/      # Prostate Cancer (Prostatakarzinom)
    ├── ncc/      # Kidney Cancer (Nierenzellkarzinom/RCC)
    ├── hoden_ca/ # Testicular Cancer
    ├── penis_ca/ # Penile Cancer
    ├── uca/      # Urothelial Cancer
    ├── combi/    # Combined/Mixed cases
    └── non_uro/  # Non-urological cancers
```

Each cancer folder contains:
- `*.xlsx` - Case data spreadsheet
- `*_cases_json.docx` - Cases formatted as JSON

## JSON Schema (v1.1)

The case structure follows this hierarchy:
- **case_meta**: Case ID, date, tumor board, discussion type
- **patient**: Demographics, ECOG/Karnofsky status, comorbidity, life expectancy
- **entitaeten**: Disease entities containing:
  - **klassifikation**: TNM staging (cTNM, pTNM)
  - **rcc_spezifisch**: RCC-specific data (histology, IMDC risk)
  - **systemtherapie_kontext**: Prior/planned systemic therapy
  - **molekular**: Biomarkers (BRCA, PD-L1)
  - **bildgebung**: Imaging findings
  - **therapien_und_eingriffe**: Treatments/procedures
- **geplantes_therapiekonzept**: Planned therapy concept

## Medical Domain Context

- **Language**: German medical terminology
- **Staging**: TNM classification system
- **Risk Stratification**: IMDC criteria for metastatic RCC
- **Performance Status**: ECOG and Karnofsky scales
- **Guidelines**: NCC (National Cancer Center) evidence-based recommendations with GoR/LoE

## Target LLM Models

Recommended medical-specific models (from list_models.docx):
- m42-health/Llama3-Med42-8B
- ClinicalBERT
- II-Medical-8B

Currently installed general models: GLM-4.6, Gemma 3, Qwen variants, Llama3, Mistral

## Working with This Project

This is a data-only project with no build system. When asked to:
- **Add cases**: Follow the JSON schema in `case_structure_json_v_1_1.docx`
- **Convert data**: Transform XLSX rows into JSON format per the schema
- **Validate cases**: Check TNM staging consistency, required fields, IMDC calculations
- **Create therapy recommendations**: Reference the therapy_structure documents for decision trees

## XLSX to JSON Conversion

**Column Mapping:**
| XLSX Column | JSON Field | Transformation |
|-------------|------------|----------------|
| Cases | nachname, vorname, geburtsdatum | Parse "Surname, Firstname, DD.MM.YYYY" |
| Classes | entitaet_typ | Map to standardized entity type |
| Therapy line | stadium_oder_risikoklasse | Treatment stage/status |
| json_ver | schema_version | Target schema version |

**Missing Values Convention:**
- Use `null` for absent single values
- Use `[]` for absent arrays
- Use `"unknown"` for comorbidity_level and lebenserwartung

## Python Environment

**ALWAYS use the virtual environment:**
```bash
source venv/bin/activate
```

**Required Libraries:**
```bash
pip install python-docx openpyxl pandas jsonschema requests scikit-learn matplotlib seaborn
```

## Project Structure

```
Med_LLM/
├── CLAUDE.md              # This file
├── plan.md                # Project plan and phases
├── venv/                  # Python virtual environment (ALWAYS USE THIS)
├── scripts/               # Python scripts
│   ├── convert_to_open_formats.py   # DOCX→JSON, XLSX→CSV
│   ├── verify_data_integrity.py     # Verify conversions
│   ├── inference_ollama.py          # Ollama API wrapper
│   ├── inference_openrouter.py      # OpenRouter API wrapper
│   ├── classify_cases.py            # Run Ollama classification
│   ├── classify_openrouter.py       # Run OpenRouter classification
│   ├── run_all_models.py            # Batch run multiple models
│   └── evaluate_results.py          # Generate reports
├── data_llm/              # Original data (DOCX, XLSX)
├── converted_data/        # Converted data (JSON, CSV, TXT)
├── results/               # Structured experiment results
│   ├── ollama/            # Local model results
│   └── openrouter/        # API model results
└── findings/              # Quick access results and reports
```

## Scripts Usage

**Data Conversion:**
```bash
source venv/bin/activate
python scripts/convert_to_open_formats.py
python scripts/verify_data_integrity.py
```

**Classification with Ollama (Local):**
```bash
source venv/bin/activate
python scripts/classify_cases.py --model mistral:7b-instruct
python scripts/evaluate_results.py
```

**Classification with OpenRouter (API):**
```bash
source venv/bin/activate
export OPENROUTER_API_KEY="your-key-here"
python scripts/classify_openrouter.py --model gemma3:27b
```

**Run All Models:**
```bash
python scripts/run_all_models.py --provider all
python scripts/run_all_models.py --report-only  # Generate comparison
```

## Findings Folder

All experiment results are logged to `findings/`:
- `results_{model}_{timestamp}.json` - Raw classification results
- `confusion_matrix_{model}.png` - Visualization
- `evaluation_report.md` - Comprehensive metrics report

## Models to Test

**Local Ollama Models (Tested):**
| Model | Accuracy | Notes |
|-------|----------|-------|
| mistral:7b-instruct | 88.46% | Best local performer |
| gemma3:4b | 84.62% | Fast, excellent accuracy |
| llama3:8b | 76.92% | Good balance |
| qwen3:latest | 69.23% | Slow (thinking mode) |

**OpenRouter API Models:**
```bash
export OPENROUTER_API_KEY="your-key"
python scripts/classify_openrouter.py --model MODEL
```
- `gemma3:27b` - google/gemma-3-27b-it
- `gemma3:12b` - google/gemma-3-12b-it
- `qwen3:30b` - qwen/qwen3-30b-a3b
- `qwen2.5:14b-instruct` - qwen/qwen-2.5-14b-instruct
- `llama3.3:70b` - meta-llama/llama-3.3-70b-instruct

**Medical Models (Not on OpenRouter):**
- `m42-health/Llama3-Med42-8B`
- `medicalai/ClinicalBERT`
- `Intelligent-Internet/II-Medical-8B`

## Conversion Workflow

1. Read XLSX for case inventory (`openpyxl`)
2. Extract existing JSON from DOCX reference files (`python-docx`)
3. Parse new case data and structure per schema
4. Validate against `case_structure_json_v_1_1` schema
5. Output to consolidated `.json` files
