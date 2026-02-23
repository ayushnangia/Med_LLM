# Main Model Prompt (German)

This is the complete, untruncated prompt sent to the LLM for treatment prediction.

---

## Template

```
Du bist ein erfahrener Onkologe, spezialisiert auf Nierenzellkarzinom (RCC).
Analysiere den folgenden klinischen Fall und erstelle eine strukturierte Therapieempfehlung.

=== KLINISCHER FALL ===
Patient: {patient_name}, {age} Jahre
ECOG: {ecog}, Karnofsky: {karnofsky}%
Komorbidität: {comorbidity}
Lebenserwartung: {life_expectancy}

Diagnose: {diagnose_kurz}
Stadium: {stadium}
cTNM: T{cT} N{cN} M{cM} | pTNM: T{pT} N{pN} M{pM}

HISTOLOGIE (WICHTIG für Therapieentscheidung):
Subtyp: {histologie_subtyp}, Klarzellig: {Ja/Nein}, Grading: {grading}

Anamnese:
{anamnese}

Nebendiagnosen: {nebendiagnosen}

Aktuelle Medikation: {medikation}

Bildgebung:
  - {bildgebung_details}

IMDC-Risikofaktoren: {imdc_faktoren}
ICI-Kombination durchführbar: {ici_durchfuehrbar}
Vorherige Systemtherapien: {prior_therapies}

=== THERAPIE-LEITLINIEN ===

METASTASIERTES KLARZELLIGES RCC - THERAPIE-ALGORITHMUS:

IMDC-RISIKOSTRATIFIZIERUNG:
- Günstig (0 Risikofaktoren)
- Intermediär (1-2 Risikofaktoren)
- Ungünstig (≥3 Risikofaktoren)

Risikofaktoren: Karnofsky <80%, Zeit bis Systemtherapie <1 Jahr, Hämoglobin↓, Calcium↑, Neutrophile↑, Thrombozyten↑

ERSTLINIE (wenn ICI-Kombination möglich):
- Günstig: NIVO+CABO (A), PEMBRO+AXI (A), PEMBRO+LEN (A), AVELU+AXI (B)
- Intermediär: NIVO+CABO (A), NIVO+IPI (A), PEMBRO+AXI (A), PEMBRO+LEN (A)
- Ungünstig: NIVO+CABO (A), NIVO+IPI (A), PEMBRO+AXI (A), PEMBRO+LEN (A)

ERSTLINIE (wenn ICI-Kombination NICHT möglich):
- Günstig: Pazopanib (A), Sunitinib (A), Tivozanib (A), BEV+IFN (A)
- Intermediär: Cabozantinib (B), Pazopanib (B), Sunitinib (B)
- Ungünstig: Cabozantinib (B), Sunitinib (B), Temsirolimus (0)

ZWEITLINIE nach ICI-Kombination: Cabozantinib (A), Lenvatinib+Everolimus (A), Sunitinib (A)
ZWEITLINIE nach VEGF/R-Monotherapie: Cabozantinib (A), Nivolumab (A)

Legende: A=starke Empfehlung, B=schwache Empfehlung, 0=Option


NICHT-METASTASIERTES RCC - THERAPIE-ALGORITHMUS:

THERAPIEOPTIONEN nach Tumorgröße/Stadium:

1. AKTIVE ÜBERWACHUNG (GoR 0):
   - Kleine Nierentumoren + hohe Komorbidität ODER begrenzte Lebenserwartung
   - Biopsie VOR Überwachung erforderlich

2. ABLATION (Kryoablation/Radiofrequenzablation) (GoR 0):
   - Kleine Nierentumoren + hohe Komorbidität ODER begrenzte Lebenserwartung
   - Biopsie VOR Ablation erforderlich

3. NIERENTEILRESEKTION (Nephron-sparing Surgery):
   - cT1 (≤7cm): SOLL durchgeführt werden (GoR A)
   - >T1: SOLLTE erwogen werden wenn technisch möglich (GoR B)
   - Zugang: offen/laparoskopisch/robotisch (chirurgische Erfahrung)

4. RADIKALE NEPHREKTOMIE:
   - Wenn Teilresektion nicht möglich (GoR A)
   - Minimalinvasiv wenn lokale Befunde es erlauben (GoR A)

PERIOPERATIVE PRINZIPIEN:
- KEINE Adrenalektomie bei unauffälliger Bildgebung (GoR A)
- KEINE systematische Lymphadenektomie bei unauffälliger Bildgebung (GoR A)
- LND bei vergrößerten Lymphknoten akzeptabel

TNM-STADIEN:
- T1a: ≤4cm, auf Niere begrenzt
- T1b: >4-7cm, auf Niere begrenzt
- T2a: >7-10cm, auf Niere begrenzt
- T2b: >10cm, auf Niere begrenzt
- T3: Ausdehnung in große Venen oder perirenales Gewebe
- T4: Über Gerota-Faszie hinaus

Legende: GoR A=starke Empfehlung, GoR B=schwache Empfehlung, GoR 0=Option

WICHTIGER HINWEIS:
- Die Leitlinien gelten primär für KLARZELLIGES RCC
- Bei NICHT-KLARZELLIGEM RCC (papillär, chromophob, etc.) ist TKI-Monotherapie oft bevorzugt
- IMDC-Risikostratifizierung ist nur für klarzelliges mRCC validiert

=== AUFGABE ===
Analysiere den Fall schrittweise:

1. METASTASIERUNG: Bestimme ob der Patient metastasiert oder nicht-metastasiert ist (basierend auf TNM M-Status, Anamnese, Bildgebung).

2. HISTOLOGIE: Berücksichtige den histologischen Subtyp (klarzellig vs. nicht-klarzellig).

3. RISIKOSTRATIFIZIERUNG: Falls metastasiert UND klarzellig, berechne das IMDC-Risiko.

4. THERAPIEEMPFEHLUNG: Folge dem entsprechenden Therapie-Algorithmus und begründe deine Empfehlung.

Antworte im folgenden JSON-Format:
{
    "is_metastatic": true/false,
    "metastatic_reasoning": "Begründung für Metastasierungsstatus...",
    "imdc_risk": "guenstig/intermediaer/unguenstig/nicht_anwendbar",
    "imdc_reasoning": "IMDC-Berechnung oder null wenn nicht-metastasiert/nicht-klarzellig...",
    "treatment_reasoning": "Schrittweise Begründung nach Leitlinie...",
    "recommended_therapy": "Konkrete Therapieempfehlung",
    "therapy_category": "IO+TKI/TKI mono/Surgery/Surveillance/Ablation/etc.",
    "recommendation_strength": "A/B/0",
    "confidence": 0.0-1.0
}
```

---

## Variable Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{patient_name}` | Patient surname, first name | `Turtle, Ninja` |
| `{age}` | Age in years | `52` |
| `{ecog}` | ECOG performance status | `0` |
| `{karnofsky}` | Karnofsky score | `100` or `?` |
| `{comorbidity}` | Comorbidity level | `unknown` |
| `{life_expectancy}` | Life expectancy | `unknown` |
| `{diagnose_kurz}` | Short diagnosis | `Metastasiertes papilläres RCC` |
| `{stadium}` | Disease stage | `metastasiert (pulmonal, lymphonodal, hepatisch)` |
| `{cT}`, `{cN}`, `{cM}` | Clinical TNM | `unknown`, `unknown`, `M1` |
| `{pT}`, `{pN}`, `{pM}` | Pathological TNM | `T3b`, `NX`, `None` |
| `{histologie_subtyp}` | Histological subtype | `papillär` |
| `{Ja/Nein}` | Clear-cell status | `Nein` |
| `{grading}` | Tumor grade | `G3` |
| `{anamnese}` | Medical history | Free text |
| `{nebendiagnosen}` | Secondary diagnoses | Comma-separated list |
| `{medikation}` | Current medications | Formatted list |
| `{bildgebung_details}` | Imaging findings | Formatted entries |
| `{imdc_faktoren}` | IMDC risk factors | `Nicht dokumentiert` |
| `{ici_durchfuehrbar}` | ICI eligibility | `Nicht dokumentiert` |
| `{prior_therapies}` | Prior systemic therapies | `Keine` |

---

## Expected Output Schema

```json
{
    "is_metastatic": true,
    "metastatic_reasoning": "String explaining metastatic determination",
    "imdc_risk": "guenstig|intermediaer|unguenstig|nicht_anwendbar",
    "imdc_reasoning": "String explaining IMDC calculation or why N/A",
    "treatment_reasoning": "String with step-by-step therapy reasoning",
    "recommended_therapy": "Specific therapy recommendation",
    "therapy_category": "IO+TKI|TKI mono|Surgery|Surveillance|Ablation|etc.",
    "recommendation_strength": "A|B|0",
    "confidence": 0.85
}
```

---

## Source

**File:** `scripts/modal_treatment_predict.py` (lines 418-481)
**File:** `scripts/treatment_openrouter.py` (lines 308-371)
