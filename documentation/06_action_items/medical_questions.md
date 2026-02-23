# Medical Questions for Expert Review

Questions requiring input from the medical oncologist/data provider.

---

## Overview

These questions need clarification to improve the treatment prediction system. They are organized by priority and topic.

---

## High Priority Questions

### 1. Ground Truth Definition

**Question:** How is `ground_truth_therapy` determined?

**Context:**
The current data includes therapy recommendations like:
```
"Einleitung palliative Systemtherapie TKI/IO (z.B. Nivolumab/Cabozantinib)."
```

**Specific Questions:**
- [ ] Is this the tumor board consensus recommendation?
- [ ] Is this the actual treatment given to the patient?
- [ ] Who documents this field?
- [ ] If tumor board recommends X but patient receives Y, which is "ground truth"?

**Why This Matters:**
- Our metrics compare LLM output to this field
- Inconsistent ground truth = unreliable metrics
- Research papers need clear ground truth definition

---

### 2. IMDC for Non-Clear-Cell RCC

**Question:** How should IMDC risk stratification be handled for non-clear-cell histologies?

**Current Behavior:**
The prompt states: "IMDC-Risikostratifizierung ist nur für klarzelliges mRCC validiert"

The LLM often calculates IMDC anyway with a disclaimer:
> "Da es sich um ein nicht-klarzelliges RCC handelt, ist die IMDC-Risikostratifizierung nicht validiert, wird aber zur Orientierung herangezogen."

**Options:**
- [ ] A: Skip IMDC entirely for non-clear-cell
- [ ] B: Calculate IMDC but note it's not validated
- [ ] C: Use different risk assessment
- [ ] D: Document why not applicable

**Which approach is correct?**

---

### 3. ICI Eligibility Criteria

**Question:** What criteria determine ICI eligibility?

**Current Data:**
Many cases have:
```json
"ici_durchfuehrbar": null
```

**Specific Questions:**
- [ ] What medical conditions make ICI ineligible?
  - Autoimmune disease?
  - Prior transplant?
  - Active infection?
- [ ] Should we require this field for metastatic cases?
- [ ] How should the LLM handle missing ICI eligibility?

---

## Medium Priority Questions

### 4. Therapy Guidelines Completeness

**Question:** Are the current guidelines in the prompt sufficient?

**Currently Included:**
- Metastatic clear-cell: IMDC-based IO+TKI or TKI mono
- Non-metastatic: Surgery, ablation, surveillance

**Potentially Missing:**
- [ ] Adjuvant Pembrolizumab (post-nephrectomy for high-risk)
- [ ] Non-clear-cell specific protocols
- [ ] Third-line therapy options
- [ ] Oligometastatic disease management
- [ ] Cytoreductive nephrectomy criteria

**Should we add any of these?**

---

### 5. Clinical Acceptability Criteria

**Question:** Is our list of "acceptable" therapies correct?

**Current Lists:**

**Metastatic Favorable:**
- Nivo+Cabo, Pembro+Axi, Pembro+Len, Avelu+Axi
- Pazopanib, Sunitinib, Tivozanib

**Metastatic Intermediate/Unfavorable:**
- Same as above + Nivo+Ipi, Cabozantinib, Temsirolimus

**Non-Metastatic:**
- Surveillance, Partial nephrectomy, Radical nephrectomy, Ablation

**Questions:**
- [ ] Are any therapies missing?
- [ ] Are any therapies incorrectly listed?
- [ ] Should older therapies (e.g., Bevacizumab+IFN) still be "acceptable"?

---

### 6. Histology-Specific Guidance

**Question:** Is our guidance for non-clear-cell subtypes sufficient?

**Current Guidance:**
> "Bei NICHT-KLARZELLIGEM RCC ist TKI-Monotherapie oft bevorzugt"

**Subtypes to Consider:**
- [ ] Papillary Type 1 vs Type 2
- [ ] Chromophobe
- [ ] Collecting duct
- [ ] Unclassified

**Should we provide subtype-specific recommendations?**

---

## Low Priority Questions

### 7. Performance Status Standardization

**Question:** Which performance status should we prefer?

**Current Data:**
- Some cases have ECOG only
- Some cases have Karnofsky only
- Some cases have both
- Some cases have neither

**Questions:**
- [ ] Should we require at least one?
- [ ] Which is preferred for this use case?
- [ ] Should we auto-convert between scales?

---

### 8. Comorbidity Assessment

**Question:** How should comorbidities affect therapy selection?

**Current Data:**
Comorbidities listed as free text, e.g.:
- "obstruktive Kardiomyopathie"
- "arterielle Hypertonie"
- "Diabetes mellitus"

**Questions:**
- [ ] Should we use standardized comorbidity scoring (e.g., Charlson)?
- [ ] Which comorbidities contraindicate specific therapies?
- [ ] How does "high comorbidity" affect non-metastatic treatment choice?

---

## Data Quality Questions

### 9. Missing Data Handling

**Question:** How should we handle missing fields?

**Frequently Missing:**
- Karnofsky status
- ICI eligibility
- IMDC risk factors (lab values)
- Comorbidity level

**Should we:**
- [ ] Require these fields?
- [ ] Use defaults?
- [ ] Flag cases as incomplete?

---

### 10. Case Selection

**Question:** Are all 35 cases appropriate for evaluation?

**Potential Concerns:**
- Cases 15-35 use different JSON structure (may have data issues)
- Some cases may be edge cases not suitable for automated evaluation

**Questions:**
- [ ] Should we exclude any cases?
- [ ] Are there known problematic cases?
- [ ] Should we add more cases?

---

## Response Format

For each question, please provide:
1. **Answer** - Your recommendation
2. **Rationale** - Medical reasoning
3. **Implementation notes** - Any technical considerations

---

## Contact

Please direct responses to the technical team for implementation.

Deadline: [To be determined]
