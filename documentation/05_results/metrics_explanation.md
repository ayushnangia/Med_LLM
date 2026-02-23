# Metrics Explanation

Detailed explanation of all evaluation metrics used in treatment prediction.

---

## Overview

The evaluation system uses three primary metrics:
1. **Metastatic Classification Accuracy** - Binary classification
2. **Therapy Exact Match** - Fuzzy string matching
3. **Therapy Clinically Acceptable** - Guideline-based validation

---

## 1. Metastatic Classification Accuracy

### Definition
Measures whether the LLM correctly identifies if a patient has metastatic disease.

### Calculation
```
accuracy = correct_predictions / total_metastatic_cases
```

**Note:** This metric is calculated ONLY on metastatic cases (not all cases).

### Ground Truth Source
```json
"ground_truth_metastatic": true  // from case JSON
```

### Prediction Source
```json
"is_metastatic": true  // from LLM output
```

### Interpretation

| Accuracy | Interpretation |
|----------|----------------|
| 100% | Perfect metastatic classification |
| 80-99% | Good, but some misses |
| <80% | Significant classification errors |

### Why It Matters
Metastatic vs non-metastatic determines the entire treatment approach:
- Metastatic → Systemic therapy (drugs)
- Non-metastatic → Local therapy (surgery)

Misclassification could lead to completely wrong treatment.

---

## 2. Therapy Exact Match

### Definition
Measures whether the recommended therapy matches the ground truth using fuzzy string matching.

### Calculation
```python
def is_exact_match(prediction, ground_truth):
    # Normalize strings
    pred_lower = prediction.lower()
    gt_lower = ground_truth.lower()

    # Check for substring matches
    # Handle synonyms (NIVO = Nivolumab, CABO = Cabozantinib)
    return fuzzy_match(pred_lower, gt_lower)
```

### Example Matches

| Ground Truth | Prediction | Match? |
|--------------|------------|--------|
| "Nivolumab/Cabozantinib" | "NIVO+CABO" | ✅ Yes |
| "Cabozantinib" | "Cabozantinib 60mg" | ✅ Yes |
| "Nephrektomie" | "Radikale Nephrektomie" | ✅ Yes |
| "Nivolumab+Cabozantinib" | "Sunitinib" | ❌ No |

### Interpretation

| Rate | Interpretation |
|------|----------------|
| >50% | Good semantic understanding |
| 25-50% | Acceptable, room for improvement |
| <25% | Poor therapy matching |

### Limitations
- String matching may miss semantically equivalent alternatives
- Different phrasings may not match (e.g., "TKI mono" vs "Cabozantinib")
- This is why we also use "Clinically Acceptable" metric

---

## 3. Therapy Clinically Acceptable

### Definition
Measures whether the recommended therapy is guideline-compliant, even if not an exact match to ground truth.

### Calculation
```python
def is_clinically_acceptable(prediction, metastatic, imdc_risk):
    if metastatic:
        valid_therapies = VALID_METASTATIC_THERAPIES[imdc_risk]
        return any(valid in prediction for valid in valid_therapies)
    else:
        return any(valid in prediction for valid in VALID_NON_METASTATIC_THERAPIES)
```

### Valid Therapy Lists

**Metastatic (by IMDC risk):**
- Favorable: Nivo+Cabo, Pembro+Axi, Pembro+Len, Pazopanib, Sunitinib, etc.
- Intermediate: Same + Nivo+Ipi
- Unfavorable: Same + Temsirolimus

**Non-Metastatic:**
- Surveillance, Partial nephrectomy, Radical nephrectomy, Ablation

### Example Evaluations

| Ground Truth | Prediction | Exact Match | Acceptable |
|--------------|------------|-------------|------------|
| Nivo+Cabo | Pembro+Axi | ❌ | ✅ (both IO+TKI) |
| Nephrektomie | Nierenteilresektion | ❌ | ✅ (both surgery) |
| Nivo+Cabo | Aspirin | ❌ | ❌ (not RCC therapy) |

### Interpretation

| Rate | Interpretation |
|------|----------------|
| >70% | Good guideline adherence |
| 40-70% | Mixed results |
| <40% | Poor guideline adherence |

### Relationship to Exact Match

| Exact | Acceptable | Meaning |
|-------|------------|---------|
| ✅ | ✅ | Perfect - exactly matches ground truth |
| ❌ | ✅ | Good - valid alternative therapy |
| ❌ | ❌ | Poor - guideline violation |

---

## Combined Interpretation

### Ideal Results
- Metastatic Accuracy: 100%
- Exact Match: >50%
- Clinically Acceptable: >80%

### Analysis Checklist
When results fall below ideal, investigate:
1. Are the valid therapy lists complete?
2. Are non-metastatic cases being evaluated correctly?
3. Is fuzzy matching missing valid therapies?

For actual results, see `findings/evaluation_report_*.md`.

---

## Metric Sources

### Code Locations

| Metric | File | Function |
|--------|------|----------|
| Metastatic Accuracy | modal_treatment_predict.py | Line 730 |
| Therapy Exact Match | modal_treatment_predict.py | Line 732 |
| Therapy Acceptable | modal_treatment_predict.py | is_therapy_clinically_acceptable() |

### Result Storage

```json
{
  "metastatic_correct": true,
  "therapy_exact_match": true,
  "therapy_clinically_acceptable": true
}
```

---

## Future Improvements

### Planned Enhancements
1. **Dose matching** - Validate dosing (60mg vs 40mg)
2. **Sequence matching** - Validate therapy line appropriateness
3. **Contraindication checking** - Flag potential issues
4. **Confidence calibration** - Correlate confidence with accuracy

### LLM-as-Judge Metrics
For more nuanced evaluation, see the judge model metrics:
- therapy_semantic_score (0.0-1.0)
- clinical_appropriateness_score (0.0-1.0)
- reasoning_quality (0.0-1.0)
- overall_score (weighted average)
