# Technical Points of Contention

This document lists all technical issues that need discussion or resolution.

---

## 1. JSON Schema Version Inconsistency (CRITICAL)

**Status:** Unresolved
**Severity:** High
**Impact:** Cases 15-35 have incorrect ECOG/Karnofsky values (null)

**Problem:** Two different JSON schema structures exist in the data:

| Aspect | Schema v1.1 (Cases 1-14) | Schema v1.2 (Cases 15-35) |
|--------|--------------------------|---------------------------|
| Container | Direct top-level fields | Nested under `case_template` |
| Patient ECOG | `patient.performance_status.ecog` | `patient.ecog` (flattened) |
| Patient Karnofsky | `patient.performance_status.karnofsky_prozent` | Not present |
| TNM path | `klassifikation.tnm_clinical` + `tnm_pathological` | `klassifikation.tnm` (single) |
| IMDC location | `rcc_spezifisch.imdc` | `risikomodelle.imdc` |

**Current Code (Broken):**
```python
"ecog": patient.get("performance_status", {}).get("ecog"),
```

**Required Fix:**
```python
"ecog": patient.get("ecog") or patient.get("performance_status", {}).get("ecog"),
```

**Files Affected:**
- `scripts/modal_treatment_predict.py` (line 272-273)
- `scripts/treatment_openrouter.py` (line 505-506)

**See:** [json_schema_issue.md](json_schema_issue.md) for detailed analysis.

---

## 2. Seed Support in OpenRouter

**Status:** Not fixable (API limitation)
**Severity:** Medium
**Impact:** Results not fully reproducible

**Problem:** OpenRouter API does not support seed parameter for reproducibility.

| Platform | Seed Support |
|----------|--------------|
| Modal (vLLM) | Yes (seed=42) |
| OpenRouter | No |

**Implication:** Slight variations in results between runs on OpenRouter.

**Workaround:** Use Modal for reproducible experiments, OpenRouter for validation.

---

## 3. Structured Output Handling

**Status:** Documented
**Severity:** Low
**Impact:** Different JSON validation approaches

| Feature | Modal (vLLM) | OpenRouter (API) |
|---------|--------------|------------------|
| JSON Schema Enforcement | Yes (Pydantic + vLLM) | No |
| Validation | Two-stage (strict → lenient) | Single-stage (dict only) |
| Error Recovery | Fallback to lenient parsing | Returns None |

**Implication:** Modal has stronger JSON guarantees.

---

## 4. Batch vs Sequential Processing

**Status:** By design
**Severity:** Low
**Impact:** Speed difference only

| Platform | Processing |
|----------|------------|
| Modal | Batched |
| OpenRouter | Sequential |

**Note:** This is a fundamental architectural difference, not a bug. Modal is significantly faster due to batching.

---

## 5. Model Name Mapping

**Status:** Resolved
**Severity:** Low

**Modal uses short names internally:**
```
gemma-3-27b → google/gemma-3-27b-it (HuggingFace)
```

**OpenRouter uses full API paths:**
```
google/gemma-3-27b-it (direct)
```

**Current Status:** Both scripts now correctly resolve to same model.

---

## 6. Prompt Truncation (FIXED)

**Status:** Resolved
**Previous Issue:** Both scripts truncated `prompt_text` to 1000 chars in saved results.
**Fix Applied:** Full prompt now saved.

---

## 7. Missing `full_case` Field (FIXED)

**Status:** Resolved
**Previous Issue:** OpenRouter didn't save the full original case JSON.
**Fix Applied:** Both scripts now save `full_case` for reference.

---

## Summary

| Issue | Status | Priority |
|-------|--------|----------|
| JSON Schema Bug | Unresolved | HIGH |
| Seed Support | Not fixable | MEDIUM |
| Structured Output | Documented | LOW |
| Batch vs Sequential | By design | LOW |
| Model Mapping | Resolved | - |
| Prompt Truncation | Resolved | - |
| Missing full_case | Resolved | - |
