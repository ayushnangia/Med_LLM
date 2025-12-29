# Technical Action Items

Prioritized list of technical fixes and improvements.

---

## Critical (Must Fix)

### 1. JSON Schema Extraction Bug

**Priority:** CRITICAL
**Status:** Unresolved
**Impact:** Cases 15-35 have incorrect ECOG/Karnofsky values

**Problem:**
```python
# Current (broken for v1.2 cases):
"ecog": patient.get("performance_status", {}).get("ecog"),

# Cases 15-35 have flattened structure:
"ecog": patient.get("ecog")  # Direct field, not nested
```

**Fix Required:**
```python
# Check both paths:
"ecog": patient.get("ecog") or patient.get("performance_status", {}).get("ecog"),
"karnofsky": patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent"),
```

**Files to Update:**
- [ ] `scripts/modal_treatment_predict.py` (lines 272-273)
- [ ] `scripts/treatment_openrouter.py` (lines 505-506)

**Verification:**
```bash
# Run after fix to verify ECOG values
python -c "
import json
with open('converted_data/send_27_12_25/ncc/ncc_cases_json.json') as f:
    data = json.load(f)
for i, case in enumerate(data['cases'][14:], 15):
    template = case.get('case_template', {})
    patient = template.get('patient', {})
    ecog = patient.get('ecog')
    print(f'Case {i}: ECOG = {ecog}')
"
```

---

## High Priority

### 2. Standardize JSON Schema

**Priority:** HIGH
**Status:** Planning
**Impact:** Data consistency

**Options:**
- A) Update extraction logic to handle both schemas (quick fix, done above)
- B) Convert all data to single schema (thorough, requires medical input)

**Recommendation:** Do both - fix extraction now, plan schema migration.

### 3. Add Seed Support Discussion

**Priority:** HIGH
**Status:** Document limitation
**Impact:** Reproducibility

**Current State:**
- Modal: seed=42 ✅
- OpenRouter: No seed support ❌

**Action:** Document in results that OpenRouter results may vary between runs.

---

## Medium Priority

### 4. Improve Clinical Acceptability Logic

**Priority:** MEDIUM
**Status:** Review needed

**Current Issues:**
- 28.6% acceptable rate seems low
- May be missing valid therapy synonyms

**Investigation Steps:**
1. [ ] Export cases where acceptable=False
2. [ ] Review predicted therapies vs ground truth
3. [ ] Identify missing synonyms/alternatives
4. [ ] Update VALID_*_THERAPIES lists if needed

### 5. Add Response Validation

**Priority:** MEDIUM
**Status:** Enhancement

**Current State:**
- Modal uses Pydantic validation
- OpenRouter does manual JSON parsing

**Enhancement:**
Add validation to OpenRouter to match Modal quality.

---

## Low Priority

### 6. Unify Model Registry

**Priority:** LOW
**Status:** Nice to have

**Current State:**
- Modal: MODEL_CONFIGS dict with short names
- OpenRouter: MODEL_REGISTRY from classifier

**Enhancement:**
Create shared model registry for consistency.

### 7. Add Logging

**Priority:** LOW
**Status:** Enhancement

**Recommendation:**
Add structured logging for:
- API calls
- Parse failures
- Validation errors

---

## Completed

### ✅ Hyperparameter Alignment
- temperature: 0.3 (both)
- top_p: 0.95 (both)
- max_tokens: 32768 (both)

### ✅ Prompt Truncation Fixed
- Full prompt now saved in results

### ✅ Missing full_case Field
- Both scripts now save full_case

---

## Testing Checklist

After implementing fixes:

- [ ] Run Modal prediction on all 35 cases
- [ ] Run OpenRouter prediction on all 35 cases
- [ ] Compare results match previous runs
- [ ] Verify ECOG values for cases 15-35
- [ ] Check no new errors introduced

---

## Scripts Reference

| Script | Purpose | Status |
|--------|---------|--------|
| `modal_treatment_predict.py` | Primary prediction | Needs ECOG fix |
| `treatment_openrouter.py` | Comparison prediction | Needs ECOG fix |
| `evaluate_treatment_llm_judge.py` | LLM-as-judge | OK |
| `verify_data_integrity.py` | Data validation | OK |
