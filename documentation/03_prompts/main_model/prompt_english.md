# Main Model Prompt (English Translation)

This is the English translation of the complete prompt sent to the LLM for treatment prediction.

---

## Template

```
You are an experienced oncologist, specialized in renal cell carcinoma (RCC).
Analyze the following clinical case and create a structured therapy recommendation.

=== CLINICAL CASE ===
Patient: {patient_name}, {age} years old
ECOG: {ecog}, Karnofsky: {karnofsky}%
Comorbidity: {comorbidity}
Life expectancy: {life_expectancy}

Diagnosis: {diagnose_kurz}
Stage: {stadium}
cTNM: T{cT} N{cN} M{cM} | pTNM: T{pT} N{pN} M{pM}

HISTOLOGY (IMPORTANT for therapy decision):
Subtype: {histologie_subtyp}, Clear-cell: {Yes/No}, Grading: {grading}

Medical history:
{anamnese}

Secondary diagnoses: {nebendiagnosen}

Current medication: {medikation}

Imaging:
  - {bildgebung_details}

IMDC risk factors: {imdc_faktoren}
ICI combination feasible: {ici_durchfuehrbar}
Prior systemic therapies: {prior_therapies}

=== THERAPY GUIDELINES ===

METASTATIC CLEAR-CELL RCC - THERAPY ALGORITHM:

IMDC RISK STRATIFICATION:
- Favorable (0 risk factors)
- Intermediate (1-2 risk factors)
- Unfavorable (≥3 risk factors)

Risk factors: Karnofsky <80%, Time to systemic therapy <1 year, Hemoglobin↓, Calcium↑, Neutrophils↑, Platelets↑

FIRST-LINE (when ICI combination possible):
- Favorable: NIVO+CABO (A), PEMBRO+AXI (A), PEMBRO+LEN (A), AVELU+AXI (B)
- Intermediate: NIVO+CABO (A), NIVO+IPI (A), PEMBRO+AXI (A), PEMBRO+LEN (A)
- Unfavorable: NIVO+CABO (A), NIVO+IPI (A), PEMBRO+AXI (A), PEMBRO+LEN (A)

FIRST-LINE (when ICI combination NOT possible):
- Favorable: Pazopanib (A), Sunitinib (A), Tivozanib (A), BEV+IFN (A)
- Intermediate: Cabozantinib (B), Pazopanib (B), Sunitinib (B)
- Unfavorable: Cabozantinib (B), Sunitinib (B), Temsirolimus (0)

SECOND-LINE after ICI combination: Cabozantinib (A), Lenvatinib+Everolimus (A), Sunitinib (A)
SECOND-LINE after VEGF/R monotherapy: Cabozantinib (A), Nivolumab (A)

Legend: A=strong recommendation, B=weak recommendation, 0=option


NON-METASTATIC RCC - THERAPY ALGORITHM:

THERAPY OPTIONS by tumor size/stage:

1. ACTIVE SURVEILLANCE (GoR 0):
   - Small renal tumors + high comorbidity OR limited life expectancy
   - Biopsy BEFORE surveillance required

2. ABLATION (Cryoablation/Radiofrequency ablation) (GoR 0):
   - Small renal tumors + high comorbidity OR limited life expectancy
   - Biopsy BEFORE ablation required

3. PARTIAL NEPHRECTOMY (Nephron-sparing Surgery):
   - cT1 (≤7cm): SHOULD be performed (GoR A)
   - >T1: SHOULD be considered if technically possible (GoR B)
   - Approach: open/laparoscopic/robotic (surgical experience)

4. RADICAL NEPHRECTOMY:
   - When partial resection not possible (GoR A)
   - Minimally invasive when local findings allow (GoR A)

PERIOPERATIVE PRINCIPLES:
- NO adrenalectomy with unremarkable imaging (GoR A)
- NO systematic lymphadenectomy with unremarkable imaging (GoR A)
- LND acceptable for enlarged lymph nodes

TNM STAGES:
- T1a: ≤4cm, confined to kidney
- T1b: >4-7cm, confined to kidney
- T2a: >7-10cm, confined to kidney
- T2b: >10cm, confined to kidney
- T3: Extension into major veins or perinephric tissue
- T4: Beyond Gerota's fascia

Legend: GoR A=strong recommendation, GoR B=weak recommendation, GoR 0=option

IMPORTANT NOTE:
- The guidelines apply primarily to CLEAR-CELL RCC
- For NON-CLEAR-CELL RCC (papillary, chromophobe, etc.), TKI monotherapy is often preferred
- IMDC risk stratification is only validated for clear-cell mRCC

=== TASK ===
Analyze the case step by step:

1. METASTASIS: Determine whether the patient is metastatic or non-metastatic (based on TNM M-status, medical history, imaging).

2. HISTOLOGY: Consider the histological subtype (clear-cell vs. non-clear-cell).

3. RISK STRATIFICATION: If metastatic AND clear-cell, calculate the IMDC risk.

4. THERAPY RECOMMENDATION: Follow the corresponding therapy algorithm and justify your recommendation.

Answer in the following JSON format:
{
    "is_metastatic": true/false,
    "metastatic_reasoning": "Reasoning for metastatic status...",
    "imdc_risk": "favorable/intermediate/unfavorable/not_applicable",
    "imdc_reasoning": "IMDC calculation or null if non-metastatic/non-clear-cell...",
    "treatment_reasoning": "Step-by-step reasoning following guideline...",
    "recommended_therapy": "Specific therapy recommendation",
    "therapy_category": "IO+TKI/TKI mono/Surgery/Surveillance/Ablation/etc.",
    "recommendation_strength": "A/B/0",
    "confidence": 0.0-1.0
}
```

---

## Key Terms Translation

| German | English |
|--------|---------|
| Nierenzellkarzinom (RCC) | Renal cell carcinoma (RCC) |
| Therapieempfehlung | Therapy recommendation |
| Klinischer Fall | Clinical case |
| Komorbidität | Comorbidity |
| Lebenserwartung | Life expectancy |
| Stadium | Stage |
| Anamnese | Medical history |
| Nebendiagnosen | Secondary diagnoses |
| Bildgebung | Imaging |
| Leitlinien | Guidelines |
| Metastasiert | Metastatic |
| Klarzellig | Clear-cell |
| Günstig | Favorable |
| Intermediär | Intermediate |
| Ungünstig | Unfavorable |
| Risikofaktoren | Risk factors |
| Erstlinie | First-line |
| Zweitlinie | Second-line |
| Starke Empfehlung | Strong recommendation |
| Schwache Empfehlung | Weak recommendation |
| Option | Option |
| Aktive Überwachung | Active surveillance |
| Nierenteilresektion | Partial nephrectomy |
| Radikale Nephrektomie | Radical nephrectomy |
| Kryoablation | Cryoablation |
| Radiofrequenzablation | Radiofrequency ablation |

---

## IMDC Risk Factors (English)

1. **Karnofsky performance status <80%** - Patient not fully active
2. **Time from diagnosis to systemic therapy <1 year** - Rapid progression
3. **Hemoglobin below lower limit of normal** - Anemia
4. **Corrected calcium above upper limit of normal** - Hypercalcemia
5. **Neutrophils above upper limit of normal** - Neutrophilia
6. **Platelets above upper limit of normal** - Thrombocytosis

---

## Expected Output (English)

```json
{
    "is_metastatic": true,
    "metastatic_reasoning": "The patient shows multiple recurrences in lung, lymph nodes, and liver, which clearly indicates metastasis.",
    "imdc_risk": "unfavorable",
    "imdc_reasoning": "Since this is a non-clear-cell RCC, IMDC risk stratification is not validated but is used for orientation.",
    "treatment_reasoning": "The patient has metastatic, non-clear-cell (papillary) RCC. Guidelines recommend TKI monotherapy for non-clear-cell RCC.",
    "recommended_therapy": "Cabozantinib 60mg orally daily",
    "therapy_category": "TKI mono",
    "recommendation_strength": "B",
    "confidence": 0.85
}
```
