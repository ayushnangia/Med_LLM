# Clinical Acceptability Criteria

Definition and implementation of "clinically acceptable" therapy evaluation.

---

## Overview

A therapy recommendation is considered **clinically acceptable** if it follows established guidelines, even if it doesn't exactly match the ground truth recommendation.

---

## Implementation

### Function: `is_therapy_clinically_acceptable()`

**Location:**
- `scripts/modal_treatment_predict.py` (lines 515-540)
- `scripts/treatment_openrouter.py` (lines 149-173)

**Logic:**
1. Extract recommended therapy and category from prediction
2. Check if patient is metastatic or non-metastatic
3. Match against valid therapy lists for that category
4. Return True if any valid therapy is found in recommendation

---

## Valid Metastatic Therapies

### By IMDC Risk Category

```python
VALID_METASTATIC_THERAPIES = {
    "guenstig": {
        "first_line_ici": [
            "Nivolumab+Cabozantinib",
            "Pembrolizumab+Axitinib",
            "Pembrolizumab+Lenvatinib",
            "Avelumab+Axitinib"
        ],
        "first_line_no_ici": [
            "Pazopanib",
            "Sunitinib",
            "Tivozanib",
            "Bevacizumab+Interferon"
        ],
    },
    "intermediaer": {
        "first_line_ici": [
            "Nivolumab+Cabozantinib",
            "Nivolumab+Ipilimumab",
            "Pembrolizumab+Axitinib",
            "Pembrolizumab+Lenvatinib"
        ],
        "first_line_no_ici": [
            "Cabozantinib",
            "Pazopanib",
            "Sunitinib",
            "Tivozanib"
        ],
    },
    "unguenstig": {
        "first_line_ici": [
            "Nivolumab+Cabozantinib",
            "Nivolumab+Ipilimumab",
            "Pembrolizumab+Axitinib",
            "Pembrolizumab+Lenvatinib"
        ],
        "first_line_no_ici": [
            "Cabozantinib",
            "Sunitinib",
            "Temsirolimus"
        ],
    },
    "second_line": [
        "Cabozantinib",
        "Lenvatinib+Everolimus",
        "Sunitinib",
        "Nivolumab"
    ],
}
```

### Additional Accepted Terms

The function also accepts general therapy categories:
- `io+tki`
- `tki`
- `immuntherapie`
- `systemtherapie`
- `checkpoint`
- `nivo`
- `pembro`
- `cabo`

---

## Valid Non-Metastatic Therapies

```python
VALID_NON_METASTATIC_THERAPIES = [
    # Surveillance
    "Aktive Überwachung",
    "Surveillance",

    # Partial nephrectomy
    "Nierenteilresektion",
    "Partielle Nephrektomie",
    "Nephron-sparing",

    # Radical nephrectomy
    "Radikale Nephrektomie",
    "Nephrektomie",

    # Ablation
    "Kryoablation",
    "Radiofrequenzablation",
    "Ablation",

    # Surgical approaches (counted as surgery)
    "Robotisch",
    "Laparoskopisch",
    "Offen",
]
```

---

## Matching Logic

### For Metastatic Cases

```python
if ground_truth_metastatic:
    all_valid = []

    # Get therapies for the IMDC risk category
    risk = ground_truth_imdc or prediction.imdc_risk
    if risk and risk in VALID_METASTATIC_THERAPIES:
        for therapies in VALID_METASTATIC_THERAPIES[risk].values():
            all_valid.extend([t.lower() for t in therapies])

    # Always include second-line options
    all_valid.extend([t.lower() for t in VALID_METASTATIC_THERAPIES["second_line"]])

    # Add general terms
    all_valid.extend(["io+tki", "tki", "immuntherapie", ...])

    # Check if any valid therapy appears in recommendation
    return any(valid in recommended.lower() or valid in category.lower()
               for valid in all_valid)
```

### For Non-Metastatic Cases

```python
else:
    valid_lower = [t.lower() for t in VALID_NON_METASTATIC_THERAPIES]
    return any(valid in recommended.lower() or valid in category.lower()
               for valid in valid_lower)
```

---

## Examples

### Example 1: Exact Match

**Ground Truth:** `"Nivolumab/Cabozantinib"`
**Prediction:** `"Nivolumab+Cabozantinib"`
**Result:** ✅ Acceptable (substring match on "nivolumab" and "cabozantinib")

### Example 2: Same Class, Different Drug

**Ground Truth:** `"Pembrolizumab+Axitinib"`
**Prediction:** `"Nivolumab+Cabozantinib"`
**IMDC Risk:** Intermediate
**Result:** ✅ Acceptable (both are valid first-line IO+TKI for intermediate risk)

### Example 3: Wrong Category

**Ground Truth:** `"Nivolumab+Cabozantinib"` (IO+TKI)
**Prediction:** `"Sunitinib"` (TKI mono)
**ICI Eligibility:** Yes
**Result:** ⚠️ Depends on context (TKI mono is acceptable if ICI not possible)

### Example 4: Non-Metastatic

**Ground Truth:** `"Partielle Nephrektomie"`
**Prediction:** `"Nierenteilresektion"`
**Result:** ✅ Acceptable (same procedure, different German terms)

### Example 5: Wrong for Stage

**Ground Truth:** `"Nephrektomie"` (non-metastatic)
**Prediction:** `"Nivolumab+Cabozantinib"` (systemic therapy)
**Metastatic:** False
**Result:** ❌ Not acceptable (systemic therapy for non-metastatic case)

---

## Evaluation Metrics

### Therapy Exact Match
- Fuzzy string matching between prediction and ground truth
- Considers synonyms and abbreviations
- Binary: True/False

### Therapy Clinically Acceptable
- Guideline-based evaluation
- Uses IMDC risk stratification
- Binary: True/False

### Relationship

| Exact Match | Clinically Acceptable | Interpretation |
|-------------|----------------------|----------------|
| True | True | Perfect match |
| False | True | Different but valid alternative |
| False | False | Guideline deviation |
| True | False | Should not occur |

---

## Limitations

1. **No dose checking** - Only drug names, not dosing
2. **No sequencing logic** - Doesn't verify prior therapy considerations
3. **Simplified ICI eligibility** - Uses substring matching
4. **German/English mixing** - May miss some synonyms

---

## Potential Improvements

1. Add dose validation (e.g., "Cabozantinib 60mg" vs "Cabozantinib 40mg")
2. Add prior therapy sequencing logic
3. Expand synonym dictionary
4. Add contraindication checking
5. Integrate with drug interaction database
