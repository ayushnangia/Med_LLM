# Main Model Example Walkthrough

Step-by-step explanation of a complete treatment prediction example.

---

## Case: ncc_1

### Patient Summary (German)

**Patient:** Turtle, Ninja, 52 Jahre
**Diagnose:** Metastasiertes papilläres Nierenzellkarzinom (RCC)
**Stadium:** M1 (pulmonal, lymphonodal, hepatisch)
**Histologie:** Papillär (nicht-klarzellig), G3
**ECOG:** 0
**Nebendiagnosen:** Obstruktive Kardiomyopathie, Hyperthyreose, Hypertonie, Diabetes, LAE, Hyperlipidämie

### Patient Summary (English Translation)

**Patient:** Turtle, Ninja, 52 years old
**Diagnosis:** Metastatic papillary renal cell carcinoma (RCC)
**Stage:** M1 (pulmonary, lymph nodal, hepatic metastases)
**Histology:** Papillary (non-clear-cell), Grade 3
**ECOG:** 0 (fully active)
**Comorbidities:** Obstructive cardiomyopathy, hyperthyroidism, hypertension, diabetes, pulmonary embolism, hyperlipidemia

---

## Step 1: Input Preparation

The case JSON is loaded and formatted into a prompt.

### Key Input Fields

| Field | Value | Notes |
|-------|-------|-------|
| patient_name | "Turtle, Ninja" | Anonymized |
| age | 52 | |
| ecog | 0 | Fully active |
| histologie_subtyp | "papillär" | Non-clear-cell |
| histologie_klarzellig | false | Important for therapy selection |
| tnm_clinical.M | "M1" | Metastatic |
| ground_truth_therapy | "TKI/IO (z.B. Nivolumab/Cabozantinib)" | Tumor board recommendation |

### Medical History (German → English)

**German:**
> Met. pap. RCC. Z. n. Nephrektomie links 2014 (papilläres RCC pT3b, Nx, L0, V0, Pn0, G3, Rx). Z. n. offener Resektion eines Lokalrezidivs 2024. Aktuell multiple Rezidive (pulmonal, lymphonodal, hepatisch).

**English:**
> Metastatic papillary RCC. Status post left nephrectomy 2014 (papillary RCC pT3b, Nx, L0, V0, Pn0, G3, Rx). Status post open resection of local recurrence 2024. Currently multiple recurrences (pulmonary, lymph nodal, hepatic).

---

## Step 2: Prompt Construction

The prompt includes:
1. Role assignment (experienced oncologist)
2. Clinical case details
3. Therapy guidelines (metastatic + non-metastatic algorithms)
4. Task instructions (4-step analysis)
5. Expected JSON output format

**Total prompt length:** ~3,000 tokens

---

## Step 3: LLM Inference

### Modal Output

**Processing time:** 3.49 seconds
**Tokens used:** 487

**Prediction:**
```json
{
  "is_metastatic": true,
  "metastatic_reasoning": "Der Patient weist multiple Rezidive in Lunge, Lymphknoten und Leber auf...",
  "imdc_risk": "unguenstig",
  "imdc_reasoning": "Da es sich um ein nicht-klarzelliges RCC handelt, ist die IMDC-Risikostratifizierung nicht validiert...",
  "treatment_reasoning": "Der Patient hat ein metastasiertes, nicht-klarzelliges (papilläres) RCC. Die Leitlinien empfehlen bei nicht-klarzelligem RCC oft eine TKI-Monotherapie...",
  "recommended_therapy": "Cabozantinib 60mg p.o. täglich",
  "therapy_category": "TKI mono",
  "recommendation_strength": "B",
  "confidence": 0.85
}
```

### OpenRouter Output

**Processing time:** 31.40 seconds
**Tokens used:** 2,204

**Prediction:**
```json
{
  "is_metastatic": true,
  "metastatic_reasoning": "Der Patient weist multiple Fernmetastasen in Lunge, Lymphknoten und Leber auf...",
  "imdc_risk": "unguenstig",
  "imdc_reasoning": "Da der Patient ein Rezidiv nach Nephrektomie und Lokalrezidiv aufweist...",
  "treatment_reasoning": "Der Patient hat ein metastasiertes, nicht-klarzelliges (papilläres) Nierenzellkarzinom...",
  "recommended_therapy": "Cabozantinib",
  "therapy_category": "TKI mono",
  "recommendation_strength": "B",
  "confidence": 0.8
}
```

---

## Step 4: Evaluation

### Metastatic Classification

| | Ground Truth | Modal | OpenRouter |
|--|--------------|-------|------------|
| is_metastatic | true | true | true |
| **Correct** | - | ✅ | ✅ |

### Therapy Recommendation

| | Ground Truth | Modal | OpenRouter |
|--|--------------|-------|------------|
| Therapy | TKI/IO (Nivo/Cabo) | Cabozantinib 60mg | Cabozantinib |
| Category | - | TKI mono | TKI mono |

### Evaluation Results

| Metric | Modal | OpenRouter |
|--------|-------|------------|
| metastatic_correct | ✅ true | ✅ true |
| therapy_exact_match | ✅ true | ✅ true |
| therapy_clinically_acceptable | ✅ true | ✅ true |

---

## Analysis

### Why Both Got "Exact Match"?

The ground truth mentions "TKI/IO (z.B. **Nivolumab/Cabozantinib**)".

The fuzzy matching finds "Cabozantinib" in both:
- Ground truth contains "Cabozantinib"
- Prediction is "Cabozantinib"

### Why Is TKI Mono Acceptable?

The prompt explicitly states:
> "Bei NICHT-KLARZELLIGEM RCC (papillär, chromophob, etc.) ist TKI-Monotherapie oft bevorzugt"

Since this patient has papillary (non-clear-cell) RCC, TKI monotherapy is guideline-compliant.

### Differences Between Modal and OpenRouter

| Aspect | Modal | OpenRouter |
|--------|-------|------------|
| Dosing specified | Yes (60mg p.o.) | No |
| Confidence | 0.85 | 0.80 |
| Processing time | 3.5s | 31.4s |
| Response format | Clean JSON | JSON in markdown code block |

---

## Key Insights

1. **Both models correctly identified:**
   - Metastatic status (M1)
   - Non-clear-cell histology
   - Need for systemic therapy
   - TKI monotherapy preference for non-clear-cell

2. **Both models noted:**
   - IMDC not validated for non-clear-cell
   - Multiple comorbidities affect therapy choice
   - DOAC interaction consideration

3. **Quality observation:**
   - Modal provided more specific dosing
   - Both provided comprehensive reasoning
   - Slightly different confidence levels

---

## Files

- **Input:** `input_case_ncc_1.json`
- **Modal output:** `output_modal_ncc_1.json`
- **OpenRouter output:** `output_openrouter_ncc_1.json`
