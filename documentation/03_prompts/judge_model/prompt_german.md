# Judge Model Prompt (German)

This is the complete, untruncated prompt sent to the LLM-as-Judge for evaluation.

---

## Template

```
Du bist ein erfahrener Uro-Onkologe, der als Gutachter für KI-generierte Therapieempfehlungen bei Nierenzellkarzinom (RCC) fungiert.

=== KLINISCHER FALL ===
Patient: {patient_name}, {age} Jahre
ECOG: {ecog}
Diagnose: {diagnose_kurz}
Stadium: {stadium}
Anamnese: {anamnese}

=== GROUND TRUTH (Tumorboard-Empfehlung) ===
Metastasierungsstadium: {gt_metastatic}
Therapieempfehlung: {gt_therapy}

=== KI-VORHERSAGE ===
Metastasierungsstadium: {pred_metastatic}
Metastasierungs-Begründung: {pred_reasoning}
IMDC-Risiko: {pred_imdc}
IMDC-Begründung: {pred_imdc_reasoning}
Therapie-Begründung: {pred_treatment_reasoning}
Empfohlene Therapie: {pred_therapy}
Therapie-Linie: {pred_category}

=== BEWERTUNGSAUFGABE ===
Bewerte die KI-Vorhersage anhand folgender Kriterien:

1. **Therapie Semantische Übereinstimmung** (therapy_semantic_match, therapy_semantic_score):
   - "NIVO+CABO" = "Nivolumab/Cabozantinib" = "Nivolumab + Cabozantinib" → TRUE, 1.0
   - "TKI/IO Kombination" wenn spezifische IO+TKI empfohlen → TRUE, 0.9
   - Gleiche Wirkstoffklasse aber anderes Medikament → FALSE, 0.5-0.7
   - Komplett unterschiedlich → FALSE, 0.0-0.3

2. **Klinische Angemessenheit** (clinical_appropriateness, clinical_appropriateness_score):
   - Metastasiert + ICI möglich: IO+TKI (Nivo+Cabo, Pembro+Axi, Pembro+Len) oder IO+IO (Nivo+Ipi)
   - Metastasiert + ICI nicht möglich: TKI mono (Pazopanib, Sunitinib, Cabozantinib)
   - Nicht-metastasiert: Chirurgie (Nephrektomie, Teilresektion) oder Überwachung
   - Leitlinienkonform → TRUE, 0.8-1.0
   - Akzeptabel aber nicht erste Wahl → TRUE, 0.6-0.8
   - Nicht leitlinienkonform → FALSE, 0.0-0.5

3. **Begründungsqualität** (reasoning_quality):
   - Vollständig, logisch, medizinisch korrekt → 0.8-1.0
   - Größtenteils korrekt mit kleinen Mängeln → 0.5-0.7
   - Unvollständig oder fehlerhaft → 0.0-0.4

4. **Gesamtbewertung** (overall_score):
   - Gewichteter Durchschnitt: 40% Semantik, 40% Klinik, 20% Begründung

Antworte NUR mit einem validen JSON-Objekt (keine Erklärung davor oder danach):
{
    "therapy_semantic_match": true/false,
    "therapy_semantic_score": 0.0-1.0,
    "clinical_appropriateness": true/false,
    "clinical_appropriateness_score": 0.0-1.0,
    "reasoning_quality": 0.0-1.0,
    "reasoning_critique": "Kurze Kritik...",
    "overall_score": 0.0-1.0,
    "judge_reasoning": "Begründung für Bewertung..."
}
```

---

## Variable Placeholders

### Case Information

| Placeholder | Description | Source |
|-------------|-------------|--------|
| `{patient_name}` | Patient name | `input_case.patient_name` |
| `{age}` | Patient age | `input_case.age` |
| `{ecog}` | ECOG status | `input_case.ecog` |
| `{diagnose_kurz}` | Short diagnosis | `input_case.diagnose_kurz` |
| `{stadium}` | Disease stage | `input_case.stadium` |
| `{anamnese}` | Medical history (truncated to 500 chars) | `input_case.anamnese[:500]` |

### Ground Truth

| Placeholder | Description | Source |
|-------------|-------------|--------|
| `{gt_metastatic}` | True metastatic status | `case_result.ground_truth_metastatic` |
| `{gt_therapy}` | Ground truth therapy | `case_result.ground_truth_therapy` |

### AI Prediction

| Placeholder | Description | Source |
|-------------|-------------|--------|
| `{pred_metastatic}` | Predicted metastatic | `prediction.is_metastatic` |
| `{pred_reasoning}` | Metastatic reasoning | `prediction.metastatic_reasoning` |
| `{pred_imdc}` | Predicted IMDC risk | `prediction.imdc_risk` |
| `{pred_imdc_reasoning}` | IMDC reasoning | `prediction.imdc_reasoning` |
| `{pred_treatment_reasoning}` | Treatment reasoning | `prediction.treatment_reasoning` |
| `{pred_therapy}` | Recommended therapy | `prediction.recommended_therapy` |
| `{pred_category}` | Therapy category | `prediction.therapy_category` |

---

## Expected Output Schema

```json
{
    "therapy_semantic_match": true,
    "therapy_semantic_score": 0.85,
    "clinical_appropriateness": true,
    "clinical_appropriateness_score": 0.9,
    "reasoning_quality": 0.8,
    "reasoning_critique": "Gut strukturierte Begründung mit korrekter IMDC-Einschätzung.",
    "overall_score": 0.86,
    "judge_reasoning": "Die empfohlene Therapie (Cabozantinib) entspricht der Ground Truth (TKI/IO) semantisch teilweise und ist klinisch angemessen für nicht-klarzelliges mRCC."
}
```

---

## Scoring Criteria Details

### 1. Semantic Match Scoring

| Scenario | Match | Score |
|----------|-------|-------|
| Exact same drug(s) | TRUE | 1.0 |
| Same drugs, different format (NIVO+CABO = Nivolumab/Cabozantinib) | TRUE | 1.0 |
| General category matches specific (TKI/IO → Nivo+Cabo) | TRUE | 0.9 |
| Same class, different drug (Nivo+Cabo → Pembro+Axi) | FALSE | 0.7 |
| Same class, different combination | FALSE | 0.5-0.6 |
| Different class entirely | FALSE | 0.0-0.3 |

### 2. Clinical Appropriateness Scoring

| Scenario | Appropriate | Score |
|----------|-------------|-------|
| Guideline first-choice therapy | TRUE | 0.9-1.0 |
| Guideline alternative therapy | TRUE | 0.8-0.9 |
| Acceptable but not first-line | TRUE | 0.6-0.8 |
| Off-label but reasonable | FALSE | 0.4-0.5 |
| Contraindicated or wrong stage | FALSE | 0.0-0.3 |

### 3. Reasoning Quality Scoring

| Quality | Score |
|---------|-------|
| Complete, logical, medically accurate | 0.8-1.0 |
| Mostly correct with minor gaps | 0.6-0.7 |
| Partially correct | 0.4-0.5 |
| Incomplete or contains errors | 0.2-0.3 |
| Fundamentally flawed | 0.0-0.1 |

### 4. Overall Score Calculation

```
overall_score = (therapy_semantic_score × 0.4) +
               (clinical_appropriateness_score × 0.4) +
               (reasoning_quality × 0.2)
```

---

## Source

**File:** `scripts/evaluate_treatment_llm_judge.py` (lines 201-258)
