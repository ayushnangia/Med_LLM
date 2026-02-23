# JSON Schema Issue (CRITICAL)

This document details the critical bug affecting cases 15-35.

---

## Problem Summary

**Cases 15-35 return `null` for ECOG and Karnofsky values** because the data loading code only checks one JSON path, but cases 15-35 use a different schema structure.

---

## Schema Comparison

### Schema v1.1 (Cases 1-14) - Standard Structure

```json
{
  "patient": {
    "nachname": "Turtle",
    "vorname": "Ninja",
    "alter_jahre": 52,
    "performance_status": {
      "ecog": 0,
      "karnofsky_prozent": 100
    }
  },
  "entitaeten": [...],
  "anamnese_freitext": "..."
}
```

**Path to ECOG:** `patient.performance_status.ecog`

### Schema v1.2 (Cases 15-35) - Template Structure

```json
{
  "case_template": {
    "patient": {
      "nachname": null,
      "vorname": null,
      "alter_jahre": null,
      "ecog": 0,
      "fallnummer": "123"
    },
    "entitaeten": [...],
    "anamnese_freitext": "..."
  },
  "schema_version": "1.1",
  "hinweis_missing_values": "..."
}
```

**Path to ECOG:** `case_template.patient.ecog` (flattened, no `performance_status`)

---

## Current Buggy Code

**File:** `scripts/modal_treatment_predict.py` (lines 272-273)
**File:** `scripts/treatment_openrouter.py` (lines 505-506)

```python
# This only works for Schema v1.1
"ecog": patient.get("performance_status", {}).get("ecog"),
"karnofsky": patient.get("performance_status", {}).get("karnofsky_prozent"),
```

**What happens for Cases 15-35:**
1. `patient.get("performance_status", {})` returns `{}` (empty dict)
2. `{}.get("ecog")` returns `None`
3. ECOG is stored as `null` in the result

---

## Required Fix

```python
# Check both paths - v1.2 first (flattened), then v1.1 (nested)
"ecog": patient.get("ecog") or patient.get("performance_status", {}).get("ecog"),
"karnofsky": patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent"),
```

---

## All Field Path Differences

| Field | Schema v1.1 Path | Schema v1.2 Path |
|-------|------------------|------------------|
| ECOG | `patient.performance_status.ecog` | `case_template.patient.ecog` |
| Karnofsky | `patient.performance_status.karnofsky_prozent` | Not present |
| TNM Clinical | `entitaeten[0].klassifikation.tnm_clinical` | `case_template.entitaeten[0].klassifikation.tnm` |
| TNM Pathological | `entitaeten[0].klassifikation.tnm_pathological` | (merged into tnm) |
| IMDC | `entitaeten[0].rcc_spezifisch.imdc` | `case_template.entitaeten[0].risikomodelle.imdc` |
| IMDC Category | `rcc_spezifisch.imdc.kategorie` | `risikomodelle.imdc.risk_category` |

---

## Data File Locations

**Schema v1.1 Cases (1-14):**
```
converted_data/send_27_12_25/ncc/ncc_cases_json.json
  → cases[0] through cases[13]
```

**Schema v1.2 Cases (15-35):**
```
converted_data/send_27_12_25/ncc/ncc_cases_json.json
  → cases[14] through cases[34]
  → All have "case_template" wrapper
```

---

## Verification

To verify which cases have the bug:

```python
import json

with open("converted_data/send_27_12_25/ncc/ncc_cases_json.json") as f:
    data = json.load(f)

for i, case in enumerate(data["cases"]):
    if "case_template" in case:
        patient = case.get("case_template", {}).get("patient", {})
        ecog_v1 = patient.get("performance_status", {}).get("ecog")
        ecog_v2 = patient.get("ecog")
        print(f"Case {i+1}: v1.1={ecog_v1}, v1.2={ecog_v2}")
```

**Expected Output:**
```
Case 15: v1.1=None, v1.2=0
Case 16: v1.1=None, v1.2=1
...
```

---

## Impact Assessment

| Metric | With Bug | After Fix |
|--------|----------|-----------|
| Cases with valid ECOG | 14/35 (40%) | 35/35 (100%) |
| ECOG used in prompt | "?" for cases 15-35 | Actual values |
| IMDC calculation | May be incorrect | Correct |

---

## Recommended Actions

### Option A: Fix Extraction Logic (Quick)
Update both scripts to check both JSON paths.

**Pros:** Quick fix, no data changes
**Cons:** Adds complexity to code

### Option B: Standardize Data (Thorough)
Convert all cases to consistent schema.

**Pros:** Clean data, simpler code
**Cons:** Requires data migration

### Recommendation
Implement Option A first for immediate fix, then work on Option B with medical team.
