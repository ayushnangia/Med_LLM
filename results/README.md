# Results Directory

This directory contains classification experiment results organized by provider and model.

## Directory Structure

```
results/
├── README.md
├── ollama/                          # Local Ollama models
│   └── {model_name}/
│       └── {YYYY-MM-DD_HH-MM-SS}/
│           ├── config.json          # Model configuration
│           ├── predictions.json     # All predictions with details
│           ├── summary.json         # Summary statistics
│           └── run.log              # Detailed execution log
│
└── openrouter/                      # OpenRouter API models
    └── {model_name}/
        └── {YYYY-MM-DD_HH-MM-SS}/
            ├── config.json
            ├── predictions.json
            ├── summary.json
            └── run.log
```

## File Descriptions

### config.json
Model configuration used for the run:
```json
{
  "provider": "openrouter",
  "model_id": "google/gemma-3-27b-it",
  "temperature": 0.1,
  "max_tokens": 200,
  "run_timestamp": "2025-12-24T12:30:45"
}
```

### predictions.json
Detailed predictions for each case:
```json
{
  "metadata": {
    "provider": "openrouter",
    "model": "google/gemma-3-27b-it",
    "timestamp": "2025-12-24T12:30:45",
    "total_cases": 26
  },
  "predictions": [
    {
      "case_id": "ncc_1",
      "patient_name": "Turtle, Ninja",
      "ground_truth": "nierenzellkarzinom",
      "predicted": "nierenzellkarzinom",
      "correct": true,
      "inference_time": 2.34,
      "tokens_used": 150,
      "raw_response": "nierenzellkarzinom"
    }
  ],
  "summary": {
    "correct": 23,
    "incorrect": 3,
    "errors": 0,
    "accuracy": 0.8846
  }
}
```

### summary.json
Quick summary for comparison:
```json
{
  "model": "google/gemma-3-27b-it",
  "accuracy": 0.8846,
  "correct": 23,
  "total": 26,
  "avg_inference_time": 2.5
}
```

## Running Experiments

### Single Model (Ollama)
```bash
source venv/bin/activate
python scripts/classify_cases.py --model mistral:7b-instruct
```

### Single Model (OpenRouter)
```bash
export OPENROUTER_API_KEY="your-key"
python scripts/classify_openrouter.py --model gemma3:27b
```

### Multiple Models
```bash
python scripts/run_all_models.py --provider all
```

### Generate Comparison Report
```bash
python scripts/run_all_models.py --report-only
```

## Viewing Results

Results are also saved to `findings/` for backward compatibility with the evaluation scripts:
```bash
python scripts/evaluate_results.py
```
