# Platform Comparison: Modal vs OpenRouter

Methodology for comparing treatment prediction results across inference platforms.

---

## Purpose

When running the same model on both Modal (vLLM) and OpenRouter (API), this comparison validates that results are consistent and identifies platform-specific differences.

---

## Run Configuration

Both platforms use identical:
- Model (same HuggingFace model ID)
- Prompt (same template and guidelines)
- Hyperparameters (temperature, top_p, max_tokens)

The only differences are:
- **Seed support:** Modal supports `seed=42` for reproducibility; OpenRouter does not
- **JSON handling:** Modal uses vLLM structured outputs; OpenRouter uses manual parsing
- **Processing:** Modal is batched; OpenRouter is sequential

---

## Metrics Compared

### Primary Metrics

| Metric | Description |
|--------|-------------|
| **Metastatic Accuracy** | Correct identification of metastatic vs non-metastatic cases |
| **Therapy Exact Match** | Fuzzy string match between prediction and ground truth |
| **Therapy Acceptable** | Guideline-compliant therapy (even if not exact match) |

### Performance Metrics

| Metric | Description |
|--------|-------------|
| **Total Time** | Wall-clock time for all cases |
| **Per Case** | Average processing time per case |
| **Errors** | Number of failed predictions |

---

## Why Results May Differ Slightly

1. **No seed in OpenRouter** — slight randomness in API responses
2. **Different JSON handling** — Modal uses structured outputs, OpenRouter wraps JSON in markdown
3. **Response format** — OpenRouter occasionally produces malformed JSON requiring fallback parsing

---

## Recommendations

### For Reproducibility
Use **Modal** — supports seed parameter for deterministic results.

### For Quick Testing
Use **OpenRouter** — simpler setup, no GPU infrastructure needed.

### For Production
Use **Modal** — faster (batching), more reliable JSON output.

---

## Result File Locations

### Modal
```
results/modal_treatment/{model_name}/{timestamp}/
├── summary.json
├── ncc_1.json
├── ncc_2.json
└── ...
```

### OpenRouter
```
results/openrouter_treatment/{model_name}/{timestamp}/
├── summary.json
├── ncc_1.json
├── ncc_2.json
└── ...
```

---

## Summary JSON Format

Each run produces a `summary.json` with aggregate metrics:

```json
{
  "model": "model/name",
  "provider": "modal|openrouter",
  "timestamp": "YYYY-MM-DD_HH-MM-SS",
  "total_cases": ...,
  "metastatic_accuracy": ...,
  "therapy_exact_match_rate": ...,
  "therapy_acceptable_rate": ...,
  "total_time": ...,
  "errors": ...
}
```

For actual results, see `findings/evaluation_report_*.md`.
