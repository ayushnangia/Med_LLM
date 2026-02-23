# Latest Results Comparison

Comparison of Modal vs OpenRouter treatment prediction results.

---

## Run Details

| Aspect | Modal | OpenRouter |
|--------|-------|------------|
| **Date** | 2025-12-30 00:02:19 | 2025-12-30 00:02:17 |
| **Model** | google/gemma-3-27b-it | google/gemma-3-27b-it |
| **Provider** | Modal (vLLM) | OpenRouter API |
| **Total Cases** | 35 | 35 |

---

## Hyperparameters (Aligned)

| Parameter | Modal | OpenRouter |
|-----------|-------|------------|
| temperature | 0.3 | 0.3 |
| top_p | 0.95 | 0.95 |
| max_tokens | 32768 | 32768 |
| seed | 42 | N/A |

---

## Results Summary

### Primary Metrics

| Metric | Modal | OpenRouter | Difference |
|--------|-------|------------|------------|
| **Metastatic Accuracy** | 100.0% | 100.0% | 0% |
| **Metastatic Correct** | 11/11 | 11/11 | 0 |
| **Therapy Exact Match** | 28.6% | 25.7% | +2.9% |
| **Therapy Exact Matches** | 10/35 | 9/35 | +1 |
| **Therapy Acceptable** | 28.6% | 28.6% | 0% |
| **Therapy Acceptable Count** | 10/35 | 10/35 | 0 |

### Performance Metrics

| Metric | Modal | OpenRouter | Ratio |
|--------|-------|------------|-------|
| **Total Time** | 122.2s | 539.9s | 4.4x faster |
| **Per Case** | 3.5s | 15.4s | 4.4x faster |
| **Errors** | 0 | 0 | Same |

---

## Detailed Breakdown

### Metastatic Classification

**Note:** Metastatic accuracy is calculated only on the 11 metastatic cases.

| Metric | Modal | OpenRouter |
|--------|-------|------------|
| True Positives (metastatic correctly identified) | 11 | 11 |
| False Negatives (metastatic missed) | 0 | 0 |
| Non-metastatic cases | 24 | 24 |
| Accuracy on metastatic | 100% | 100% |

### Therapy Matching

| Match Type | Modal | OpenRouter |
|------------|-------|------------|
| Exact Match | 10 (28.6%) | 9 (25.7%) |
| Clinically Acceptable Only | 0 | 1 |
| Not Acceptable | 25 | 25 |

**Observation:** Both platforms have the same number of clinically acceptable recommendations (10), but Modal has 1 more exact match.

---

## Per-Case Comparison (Sample)

| Case | Modal Therapy | OpenRouter Therapy | Ground Truth | Match |
|------|---------------|-------------------|--------------|-------|
| ncc_1 | Cabozantinib 60mg | Cabozantinib | TKI/IO (Nivo/Cabo) | ✅ Both |
| ncc_2 | Nivo+Cabo | Nivo+Cabo | Nivo+Cabo | ✅ Both |
| ncc_3 | Nephrektomie | Nephrektomie | Nephrektomie | ✅ Both |
| ... | ... | ... | ... | ... |

---

## Analysis

### Why Results Are Similar

1. **Same model** - Both use google/gemma-3-27b-it
2. **Aligned hyperparameters** - Same temperature, top_p, max_tokens
3. **Same prompt** - Identical prompt structure and guidelines
4. **Same evaluation** - Same metrics and acceptability criteria

### Why Results Differ Slightly

1. **No seed in OpenRouter** - Slight randomness in API
2. **Different JSON handling** - Modal uses structured outputs
3. **Response format** - OpenRouter wraps JSON in markdown

### Speed Difference Explanation

| Factor | Modal | OpenRouter |
|--------|-------|------------|
| Processing | Batched | Sequential |
| Network | Direct GPU | API over internet |
| Overhead | vLLM optimized | HTTP round-trips |

---

## Recommendations

### For Reproducibility
Use **Modal** - supports seed parameter for deterministic results.

### For Quick Testing
Use **OpenRouter** - simpler setup, no GPU infrastructure needed.

### For Production
Use **Modal** - 4.4x faster, more reliable JSON output.

---

## Result Files

### Modal
```
results/modal_treatment/google_gemma-3-27b-it/2025-12-30_00-02-19/
├── summary.json
├── ncc_1.json
├── ncc_2.json
├── ...
└── ncc_35.json
```

### OpenRouter
```
results/openrouter_treatment/google_gemma-3-27b-it/2025-12-30_00-02-17/
├── summary.json
├── ncc_1.json
├── ncc_2.json
├── ...
└── ncc_35.json
```

---

## Summary JSON Format

```json
{
  "model": "google/gemma-3-27b-it",
  "provider": "modal",
  "timestamp": "2025-12-30_00-02-19",
  "total_cases": 35,
  "metastatic_accuracy": 1.0,
  "metastatic_correct": 11,
  "therapy_exact_match_rate": 0.2857142857142857,
  "therapy_exact_matches": 10,
  "therapy_acceptable_rate": 0.2857142857142857,
  "therapy_acceptable": 10,
  "total_time": 122.24953818321228,
  "errors": 0
}
```
