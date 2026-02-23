# Medical Points of Contention

Questions and issues requiring input from the medical expert.

---

## 1. Ground Truth Definition

### Question
How is `ground_truth_therapy` determined?

### Current Data Example
```json
"ground_truth_therapy": "Einleitung palliative Systemtherapie TKI/IO (z.B. Nivolumab/Cabozantinib)."
```

### Specific Questions
1. Is this the **tumor board consensus** recommendation?
2. Is this the **actual treatment given** to the patient?
3. Who documents this field - the treating physician or tumor board secretary?
4. How should we handle cases where tumor board recommendation differs from actual treatment?

### Why This Matters
- Evaluation metrics compare LLM output to ground truth
- If ground truth is inconsistent, metrics are unreliable
- Need clear definition for research paper

---

## 2. IMDC Risk Stratification for Non-Clear-Cell RCC

### Current Behavior
The prompt explicitly states:
> "IMDC-Risikostratifizierung ist nur für klarzelliges mRCC validiert"

(English: "IMDC risk stratification is only validated for clear-cell mRCC")

### Question
For non-clear-cell RCC (papillary, chromophobe), should we:

| Option | Description |
|--------|-------------|
| A | Skip IMDC entirely (current approach) |
| B | Use IMDC but note it's not validated |
| C | Use a different risk assessment |
| D | Document why IMDC is not applicable |

### Current LLM Behavior
The LLM often calculates IMDC anyway with the note:
> "Da es sich um ein nicht-klarzelliges RCC handelt, ist die IMDC-Risikostratifizierung nicht validiert, wird aber zur Orientierung herangezogen."

Is this acceptable behavior?

---

## 3. Therapy Guideline Completeness

### Current Guidelines in Prompt

**Metastatic Clear-Cell RCC:**
- First-line with ICI: NIVO+CABO, PEMBRO+AXI, PEMBRO+LEN, AVELU+AXI, NIVO+IPI
- First-line without ICI: Pazopanib, Sunitinib, Tivozanib, Cabozantinib, Temsirolimus
- Second-line: Cabozantinib, Lenvatinib+Everolimus, Nivolumab

**Non-Metastatic RCC:**
- Active surveillance
- Ablation (cryoablation, radiofrequency)
- Partial nephrectomy
- Radical nephrectomy

### Missing Guidelines (Potentially)

| Guideline | Status |
|-----------|--------|
| Adjuvant Pembrolizumab after nephrectomy | Not included |
| Non-clear-cell specific protocols | Not included |
| Third-line therapy options | Not included |
| Oligometastatic disease management | Not included |
| Cytoreductive nephrectomy criteria | Not included |

### Question
Are the current guidelines sufficient, or should we add more detail?

---

## 4. Clinical Acceptability Criteria

### Current "Acceptable" Therapies

**Metastatic by IMDC Risk:**

| Risk | ICI Possible | ICI Not Possible |
|------|--------------|------------------|
| Favorable | Nivo+Cabo, Pembro+Axi, Pembro+Len, Avelu+Axi | Pazopanib, Sunitinib, Tivozanib |
| Intermediate | Nivo+Cabo, Nivo+Ipi, Pembro+Axi, Pembro+Len | Cabozantinib, Pazopanib, Sunitinib |
| Unfavorable | Nivo+Cabo, Nivo+Ipi, Pembro+Axi, Pembro+Len | Cabozantinib, Sunitinib, Temsirolimus |

**Non-Metastatic:**
- Aktive Überwachung / Surveillance
- Nierenteilresektion / Partielle Nephrektomie
- Radikale Nephrektomie
- Kryoablation / Radiofrequenzablation

### Questions
1. Is this list complete?
2. Should we add or remove any therapies?
3. Are the IMDC-risk assignments correct?
4. Should second-line therapies count as "acceptable" for first-line failures?

---

## 5. Histology Handling

### Current Prompt Guidance
> "Bei NICHT-KLARZELLIGEM RCC (papillär, chromophob, etc.) ist TKI-Monotherapie oft bevorzugt"

(English: "For non-clear-cell RCC (papillary, chromophobe, etc.), TKI monotherapy is often preferred")

### Questions
1. Is this guidance sufficient for non-clear-cell subtypes?
2. Should we provide subtype-specific recommendations?
   - Papillary Type 1 vs Type 2
   - Chromophobe
   - Collecting duct
   - Unclassified
3. Are there IO combinations approved for non-clear-cell?

---

## 6. ICI Eligibility Documentation

### Current Data State
Many cases have:
```json
"ici_durchfuehrbar": null
```

This means "ICI eligibility not documented."

### Questions
1. Should we require ICI eligibility for all metastatic cases?
2. What criteria determine ICI eligibility?
   - Autoimmune disease history
   - Prior transplant
   - Immunosuppressive therapy
   - Performance status
   - Organ function
3. How should the LLM handle missing ICI eligibility?

---

## 7. ECOG vs Karnofsky

### Current Data
- Some cases have ECOG only
- Some cases have Karnofsky only
- Some cases have both
- Some cases have neither

### Questions
1. Which performance status is preferred?
2. Should we require at least one?
3. How to convert between scales if only one is provided?

**Standard Conversion:**
| ECOG | Karnofsky |
|------|-----------|
| 0 | 100% |
| 1 | 80-90% |
| 2 | 60-70% |
| 3 | 40-50% |
| 4 | 10-30% |

---

## 8. Comorbidity Assessment

### Current Data
```json
"comorbidity": "unknown"
```

or

```json
"nebendiagnosen": ["Diabetes", "Hypertonie", ...]
```

### Questions
1. Should we use a standardized comorbidity index (e.g., Charlson)?
2. How does comorbidity affect therapy choice?
3. Which comorbidities contraindicate specific therapies?

---

## Summary Action Items

| Topic | Priority | Status |
|-------|----------|--------|
| Ground truth definition | HIGH | Needs clarification |
| IMDC for non-clear-cell | HIGH | Needs decision |
| Guideline completeness | MEDIUM | Needs review |
| Clinical acceptability | MEDIUM | Needs validation |
| Histology handling | MEDIUM | Needs expansion |
| ICI eligibility | MEDIUM | Needs criteria |
| Performance status | LOW | Needs standardization |
| Comorbidity | LOW | Needs standardization |
