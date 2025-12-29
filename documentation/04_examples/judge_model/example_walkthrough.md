# Judge Model Example Walkthrough

Step-by-step explanation of a complete LLM-as-Judge evaluation example.

---

## Overview

The LLM-as-Judge evaluates AI-generated therapy recommendations by comparing them to ground truth (tumor board recommendations) across three dimensions:
1. Semantic match (does the therapy match?)
2. Clinical appropriateness (is it guideline-compliant?)
3. Reasoning quality (is the explanation sound?)

---

## Input: Case ncc_1

### Clinical Case Summary

| Field | Value |
|-------|-------|
| Patient | Turtle, Ninja, 52 years |
| ECOG | 0 |
| Diagnosis | Metastatic papillary RCC |
| Stage | metastatic (pulmonary, lymph nodal, hepatic) |

### Ground Truth (Tumor Board)

```
Metastatic: true
Therapy: "Einleitung palliative Systemtherapie TKI/IO (z.B. Nivolumab/Cabozantinib)"
```

Translation: "Initiation of palliative systemic therapy TKI/IO (e.g., Nivolumab/Cabozantinib)"

### AI Prediction (to be evaluated)

```json
{
  "is_metastatic": true,
  "imdc_risk": "unguenstig",
  "recommended_therapy": "Cabozantinib 60mg p.o. täglich",
  "therapy_category": "TKI mono"
}
```

---

## Judge Evaluation Process

### Step 1: Semantic Match Analysis

**Question:** Does "Cabozantinib 60mg" match "TKI/IO (Nivolumab/Cabozantinib)"?

**Analysis:**
- Ground truth mentions both Nivolumab AND Cabozantinib (IO+TKI combination)
- Prediction recommends Cabozantinib only (TKI mono)
- Cabozantinib appears in both → partial match

**Result:**
```json
"therapy_semantic_match": true,
"therapy_semantic_score": 0.85
```

Score is 0.85 (not 1.0) because:
- The same drug is recommended
- But combination (IO+TKI) vs monotherapy (TKI) differs

### Step 2: Clinical Appropriateness Analysis

**Question:** Is TKI monotherapy appropriate for this patient?

**Analysis:**
- Patient has **papillary** (non-clear-cell) RCC
- Guidelines state: "Bei NICHT-KLARZELLIGEM RCC ist TKI-Monotherapie oft bevorzugt"
- Cabozantinib is an established option for metastatic RCC

**Result:**
```json
"clinical_appropriateness": true,
"clinical_appropriateness_score": 0.9
```

Score is 0.9 because:
- Guideline-compliant for non-clear-cell histology
- Considers patient's comorbidities
- Appropriate first-line choice

### Step 3: Reasoning Quality Analysis

**Question:** Is the AI's explanation complete and medically sound?

**Checklist:**
- [x] Metastatic status correctly identified
- [x] Histology (papillary) correctly considered
- [x] IMDC noted as not validated for non-clear-cell
- [x] Comorbidities addressed (cardiomyopathy, etc.)
- [x] Drug interactions considered (DOAK)
- [ ] ICI eligibility not explicitly discussed

**Result:**
```json
"reasoning_quality": 0.85
```

Score is 0.85 because:
- Comprehensive analysis
- Minor gap: ICI eligibility not addressed

### Step 4: Overall Score Calculation

**Formula:**
```
overall = (semantic × 0.4) + (clinical × 0.4) + (reasoning × 0.2)
overall = (0.85 × 0.4) + (0.9 × 0.4) + (0.85 × 0.2)
overall = 0.34 + 0.36 + 0.17
overall = 0.87
```

---

## Judge Output

### German (Original)

```json
{
  "therapy_semantic_match": true,
  "therapy_semantic_score": 0.85,
  "clinical_appropriateness": true,
  "clinical_appropriateness_score": 0.9,
  "reasoning_quality": 0.85,
  "reasoning_critique": "Die Begründung ist gut strukturiert und berücksichtigt alle relevanten Faktoren: Metastasierungsstatus, Histologie, IMDC-Risiko, Komorbiditäten und Medikamenteninteraktionen. Die Erklärung zur IMDC-Nichtvalidierung für nicht-klarzelliges RCC zeigt medizinisches Verständnis. Einziger kleiner Mangel: ICI-Eligibilität wurde nicht explizit adressiert.",
  "overall_score": 0.87,
  "judge_reasoning": "Die KI-Vorhersage stimmt semantisch mit der Ground Truth überein, da beide Cabozantinib als Teil der Empfehlung enthalten. Die Empfehlung von TKI-Monotherapie ist klinisch angemessen für nicht-klarzelliges (papilläres) mRCC gemäß den Leitlinien."
}
```

### English Translation

```json
{
  "therapy_semantic_match": true,
  "therapy_semantic_score": 0.85,
  "clinical_appropriateness": true,
  "clinical_appropriateness_score": 0.9,
  "reasoning_quality": 0.85,
  "reasoning_critique": "The reasoning is well-structured and considers all relevant factors: metastatic status, histology, IMDC risk, comorbidities, and drug interactions. The explanation of IMDC non-validation for non-clear-cell RCC shows medical understanding. Only minor gap: ICI eligibility was not explicitly addressed.",
  "overall_score": 0.87,
  "judge_reasoning": "The AI prediction semantically matches the ground truth, as both contain Cabozantinib as part of the recommendation. The recommendation of TKI monotherapy is clinically appropriate for non-clear-cell (papillary) mRCC according to guidelines."
}
```

---

## Interpretation

### Score Interpretation

| Score Range | Quality | Interpretation |
|-------------|---------|----------------|
| 0.87 | Good | Clinically acceptable recommendation |

### What the Judge Recognized

1. **Partial semantic match** - Same drug, different combination
2. **Clinical appropriateness** - TKI mono valid for non-clear-cell
3. **Good reasoning** - Comprehensive with minor gap

### What Could Improve the Score to 1.0

1. Recommend IO+TKI instead of TKI mono (better semantic match)
2. Explicitly discuss ICI eligibility
3. Address why IO was not included despite being mentioned in ground truth

---

## Thinking Model Output

The judge model (qwen/qwq-32b) is a "thinking" model that shows its reasoning:

```
<think>
Lassen Sie mich diese KI-generierte Therapieempfehlung systematisch bewerten.

1. SEMANTISCHE ÜBEREINSTIMMUNG:
- Ground Truth: "TKI/IO (z.B. Nivolumab/Cabozantinib)"
- KI-Vorhersage: "Cabozantinib 60mg p.o. täglich"
- Cabozantinib ist in beiden enthalten
- TKI/IO vs. TKI mono ist ein Unterschied
- Score: 0.85

2. KLINISCHE ANGEMESSENHEIT:
- Patient hat papilläres (nicht-klarzelliges) RCC
- Leitlinien empfehlen TKI-Monotherapie für nicht-klarzelliges RCC
- Score: 0.9
...
</think>

{JSON output}
```

This shows the judge's reasoning process before producing the final evaluation.

---

## Files

- **Input:** `input_judge_example.json`
- **Output:** `output_judge_example.json`
