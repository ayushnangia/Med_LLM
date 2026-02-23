# Judge Model Prompt (English Translation)

This is the English translation of the complete LLM-as-Judge prompt.

---

## Template

```
You are an experienced oncologist acting as an evaluator for AI-generated therapy recommendations for renal cell carcinoma (RCC).

=== CLINICAL CASE ===
Patient: {patient_name}, {age} years old
ECOG: {ecog}
Diagnosis: {diagnose_kurz}
Stage: {stadium}
Medical history: {anamnese}

=== GROUND TRUTH (Tumor Board Recommendation) ===
Metastatic: {gt_metastatic}
Therapy recommendation: {gt_therapy}

=== AI PREDICTION ===
Metastatic: {pred_metastatic}
Metastasis reasoning: {pred_reasoning}
IMDC risk: {pred_imdc}
IMDC reasoning: {pred_imdc_reasoning}
Therapy reasoning: {pred_treatment_reasoning}
Recommended therapy: {pred_therapy}
Therapy category: {pred_category}

=== EVALUATION TASK ===
Evaluate the AI prediction based on the following criteria:

1. **Therapy Semantic Match** (therapy_semantic_match, therapy_semantic_score):
   - "NIVO+CABO" = "Nivolumab/Cabozantinib" = "Nivolumab + Cabozantinib" → TRUE, 1.0
   - "TKI/IO combination" when specific IO+TKI recommended → TRUE, 0.9
   - Same drug class but different medication → FALSE, 0.5-0.7
   - Completely different → FALSE, 0.0-0.3

2. **Clinical Appropriateness** (clinical_appropriateness, clinical_appropriateness_score):
   - Metastatic + ICI possible: IO+TKI (Nivo+Cabo, Pembro+Axi, Pembro+Len) or IO+IO (Nivo+Ipi)
   - Metastatic + ICI not possible: TKI mono (Pazopanib, Sunitinib, Cabozantinib)
   - Non-metastatic: Surgery (Nephrectomy, Partial resection) or Surveillance
   - Guideline-compliant → TRUE, 0.8-1.0
   - Acceptable but not first choice → TRUE, 0.6-0.8
   - Not guideline-compliant → FALSE, 0.0-0.5

3. **Reasoning Quality** (reasoning_quality):
   - Complete, logical, medically correct → 0.8-1.0
   - Mostly correct with minor deficiencies → 0.5-0.7
   - Incomplete or erroneous → 0.0-0.4

4. **Overall Score** (overall_score):
   - Weighted average: 40% semantics, 40% clinical, 20% reasoning

Answer ONLY with a valid JSON object (no explanation before or after):
{
    "therapy_semantic_match": true/false,
    "therapy_semantic_score": 0.0-1.0,
    "clinical_appropriateness": true/false,
    "clinical_appropriateness_score": 0.0-1.0,
    "reasoning_quality": 0.0-1.0,
    "reasoning_critique": "Brief critique...",
    "overall_score": 0.0-1.0,
    "judge_reasoning": "Reasoning for evaluation..."
}
```

---

## Key Terms Translation

| German | English |
|--------|---------|
| Gutachter | Evaluator |
| KI-generierte Therapieempfehlungen | AI-generated therapy recommendations |
| Tumorboard-Empfehlung | Tumor board recommendation |
| KI-Vorhersage | AI prediction |
| Metastasierungs-Begründung | Metastasis reasoning |
| Therapie-Begründung | Therapy reasoning |
| Empfohlene Therapie | Recommended therapy |
| Therapie-Kategorie | Therapy category |
| Bewertungsaufgabe | Evaluation task |
| Semantische Übereinstimmung | Semantic match |
| Klinische Angemessenheit | Clinical appropriateness |
| Begründungsqualität | Reasoning quality |
| Gesamtbewertung | Overall score |
| Gewichteter Durchschnitt | Weighted average |
| Leitlinienkonform | Guideline-compliant |
| Wirkstoffklasse | Drug class |
| Kurze Kritik | Brief critique |
| Begründung für Bewertung | Reasoning for evaluation |

---

## Evaluation Criteria Explained

### 1. Therapy Semantic Match

**Purpose:** Does the AI recommendation semantically match the ground truth?

**Examples:**

| Ground Truth | Prediction | Match | Score | Reason |
|--------------|------------|-------|-------|--------|
| Nivolumab/Cabozantinib | NIVO+CABO | TRUE | 1.0 | Same drugs |
| TKI/IO | Pembrolizumab+Axitinib | TRUE | 0.9 | Specific matches general |
| Nivolumab+Cabozantinib | Pembrolizumab+Lenvatinib | FALSE | 0.7 | Same class (IO+TKI) |
| Nephrectomy | Cabozantinib | FALSE | 0.1 | Completely different |

### 2. Clinical Appropriateness

**Purpose:** Is the recommendation medically sound according to guidelines?

**Decision Tree:**
```
Is patient metastatic?
├── YES → Is ICI combination possible?
│         ├── YES → IO+TKI or IO+IO appropriate
│         └── NO → TKI monotherapy appropriate
└── NO → Surgery or surveillance appropriate
```

### 3. Reasoning Quality

**Purpose:** Is the AI's explanation complete, logical, and medically accurate?

**Checklist:**
- [ ] Identifies metastatic status correctly
- [ ] Considers histology (clear-cell vs non-clear-cell)
- [ ] Addresses IMDC risk (if applicable)
- [ ] References relevant guidelines
- [ ] Considers patient-specific factors (comorbidities, prior therapy)
- [ ] Conclusion follows logically from reasoning

### 4. Overall Score

**Formula:**
```
overall = (semantic × 0.4) + (clinical × 0.4) + (reasoning × 0.2)
```

**Interpretation:**
| Score | Interpretation |
|-------|----------------|
| 0.9-1.0 | Excellent - near-perfect recommendation |
| 0.7-0.9 | Good - clinically acceptable |
| 0.5-0.7 | Fair - some concerns but usable |
| 0.3-0.5 | Poor - significant issues |
| 0.0-0.3 | Unacceptable - should not be used |

---

## Example Judge Output (English)

```json
{
    "therapy_semantic_match": true,
    "therapy_semantic_score": 0.85,
    "clinical_appropriateness": true,
    "clinical_appropriateness_score": 0.9,
    "reasoning_quality": 0.8,
    "reasoning_critique": "Well-structured reasoning with correct IMDC assessment. Minor gap: did not explicitly address ICI eligibility.",
    "overall_score": 0.86,
    "judge_reasoning": "The recommended therapy (Cabozantinib) partially matches the ground truth (TKI/IO) semantically and is clinically appropriate for non-clear-cell mRCC. The reasoning correctly identifies the non-clear-cell histology and recommends TKI monotherapy per guidelines."
}
```
