#!/usr/bin/env python3
"""
Run NCC treatment prediction using OpenRouter API.

Usage:
    # Set API key first (or add to .env)
    export OPENROUTER_API_KEY="your-key-here"

    # Run treatment prediction
    python scripts/treatment_openrouter.py --model gemma3:27b
    python scripts/treatment_openrouter.py --model google/gemma-3-27b-it

    # List available models
    python scripts/treatment_openrouter.py --list-models

Output Structure:
    results/
    └── openrouter_treatment/
        └── gemma-3-27b-it/
            └── 2025-12-29_12-30-45/
                ├── ncc_1.json
                ├── ncc_2.json
                ├── ...
                └── summary.json
"""

import os
import json
import re
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

# Import base classifier for model registry
from inference_openrouter import OpenRouterClassifier

import requests

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "converted_data" / "send_27_12_25"
RESULTS_DIR = BASE_DIR / "results"


# ============================================================================
# Therapy Flowchart Summary (embedded for prompt) - EXACT COPY FROM MODAL
# ============================================================================

METASTATIC_THERAPY_SUMMARY = """
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
"""

NON_METASTATIC_THERAPY_SUMMARY = """
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
"""

# ============================================================================
# Clinically Acceptable Therapies - EXACT COPY FROM MODAL
# ============================================================================

VALID_METASTATIC_THERAPIES = {
    "guenstig": {
        "first_line_ici": ["Nivolumab+Cabozantinib", "Pembrolizumab+Axitinib", "Pembrolizumab+Lenvatinib", "Avelumab+Axitinib"],
        "first_line_no_ici": ["Pazopanib", "Sunitinib", "Tivozanib", "Bevacizumab+Interferon"],
    },
    "intermediaer": {
        "first_line_ici": ["Nivolumab+Cabozantinib", "Nivolumab+Ipilimumab", "Pembrolizumab+Axitinib", "Pembrolizumab+Lenvatinib"],
        "first_line_no_ici": ["Cabozantinib", "Pazopanib", "Sunitinib", "Tivozanib"],
    },
    "unguenstig": {
        "first_line_ici": ["Nivolumab+Cabozantinib", "Nivolumab+Ipilimumab", "Pembrolizumab+Axitinib", "Pembrolizumab+Lenvatinib"],
        "first_line_no_ici": ["Cabozantinib", "Sunitinib", "Temsirolimus"],
    },
    "second_line": ["Cabozantinib", "Lenvatinib+Everolimus", "Sunitinib", "Nivolumab"],
}

VALID_NON_METASTATIC_THERAPIES = [
    "Aktive Überwachung", "Surveillance",
    "Nierenteilresektion", "Partielle Nephrektomie", "Nephron-sparing",
    "Radikale Nephrektomie", "Nephrektomie",
    "Kryoablation", "Radiofrequenzablation", "Ablation",
    "Robotisch", "Laparoskopisch", "Offen",
]


def is_therapy_clinically_acceptable(prediction: dict, ground_truth_metastatic: bool, ground_truth_imdc: str = None) -> bool:
    """Check if predicted therapy is clinically acceptable per guidelines."""
    if prediction is None:
        return False

    recommended = (prediction.get("recommended_therapy") or "").lower()
    category = (prediction.get("therapy_category") or "").lower()

    if ground_truth_metastatic:
        # Metastatic: check against valid systemic therapies
        all_valid = []
        risk = ground_truth_imdc or prediction.get("imdc_risk")
        if risk and risk in VALID_METASTATIC_THERAPIES:
            for therapies in VALID_METASTATIC_THERAPIES[risk].values():
                all_valid.extend([t.lower() for t in therapies])
        all_valid.extend([t.lower() for t in VALID_METASTATIC_THERAPIES["second_line"]])

        # Also accept general categories
        all_valid.extend(["io+tki", "tki", "immuntherapie", "systemtherapie", "checkpoint", "nivo", "pembro", "cabo"])

        return any(valid in recommended or valid in category for valid in all_valid)
    else:
        # Non-metastatic: check against valid surgical/local therapies
        valid_lower = [t.lower() for t in VALID_NON_METASTATIC_THERAPIES]
        return any(valid in recommended or valid in category for valid in valid_lower)


# ============================================================================
# Treatment Predictor Class
# ============================================================================

class OpenRouterTreatmentPredictor:
    """OpenRouter API wrapper for NCC treatment prediction."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Reuse model registry from classifier
    MODEL_REGISTRY = OpenRouterClassifier.MODEL_REGISTRY

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        top_p: float = 0.95,
        max_tokens: int = 32768,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        self.model_input = model
        self.model = self.MODEL_REGISTRY.get(model, model)
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.total_tokens = 0

    def build_prompt(self, case: dict) -> str:
        """Build treatment prediction prompt - EXACT COPY FROM MODAL."""
        # Format TNM staging
        tnm_clinical = case.get("tnm_clinical") or {}
        tnm_path = case.get("tnm_pathological") or {}
        tnm_parts = []
        if tnm_clinical:
            tnm_parts.append(f"cTNM: T{tnm_clinical.get('T', '?')} N{tnm_clinical.get('N', '?')} M{tnm_clinical.get('M', '?')}")
        if tnm_path and tnm_path.get('T'):
            tnm_parts.append(f"pTNM: T{tnm_path.get('T', '?')} N{tnm_path.get('N', '?')} M{tnm_path.get('M', '?')}")
        tnm_str = " | ".join(tnm_parts) if tnm_parts else "TNM: nicht dokumentiert"

        # Format histologie - CRITICAL for therapy decision
        histologie_parts = []
        if case.get("histologie_subtyp"):
            histologie_parts.append(f"Subtyp: {case['histologie_subtyp']}")
        if case.get("histologie_klarzellig") is not None:
            histologie_parts.append(f"Klarzellig: {'Ja' if case['histologie_klarzellig'] else 'Nein'}")
        if case.get("histologie_sarcomatoid"):
            histologie_parts.append("Sarkomatoid: Ja")
        if case.get("histologie_grading") or case.get("grading"):
            histologie_parts.append(f"Grading: {case.get('histologie_grading') or case.get('grading')}")
        histologie_str = ", ".join(histologie_parts) if histologie_parts else "Nicht dokumentiert"

        # Format comorbidities - NO TRUNCATION
        comorbidities = case.get("nebendiagnosen", [])
        if comorbidities:
            comorbid_list = []
            for c in comorbidities:
                if isinstance(c, str):
                    comorbid_list.append(c)
                elif isinstance(c, dict):
                    comorbid_list.append(str(c.get("name", c.get("diagnose", str(c)))))
                else:
                    comorbid_list.append(str(c))
            comorbid_str = ", ".join(comorbid_list)
        else:
            comorbid_str = "Keine dokumentiert"

        # Format Medikation
        medikation = case.get("medikation", [])
        if medikation:
            med_list = []
            for m in medikation:
                if isinstance(m, str):
                    med_list.append(m)
                elif isinstance(m, dict):
                    med_name = m.get("wirkstoff_oder_klasse", "")
                    if m.get("details"):
                        med_name += f" ({m['details']})"
                    med_list.append(med_name)
            medikation_str = ", ".join(med_list) if med_list else "Keine"
        else:
            medikation_str = "Keine dokumentiert"

        # Format Bildgebung - CRITICAL for metastasis assessment
        bildgebung = case.get("bildgebung", [])
        if bildgebung:
            bildgebung_parts = []
            for b in bildgebung:
                if isinstance(b, dict):
                    entry = f"{b.get('modalitaet', '?')} {b.get('region', '')}"
                    if b.get('datum'):
                        entry += f" ({b['datum']})"
                    if b.get('befund_kurz'):
                        entry += f": {b['befund_kurz']}"
                    bildgebung_parts.append(entry)
            bildgebung_str = "\n  - ".join(bildgebung_parts) if bildgebung_parts else "Keine"
        else:
            bildgebung_str = "Keine dokumentiert"

        # Format IMDC risk factors if available
        imdc_rf = case.get("imdc_risikofaktoren", {})
        imdc_parts = []
        if imdc_rf:
            if imdc_rf.get("karnofsky_prozent") is not None:
                imdc_parts.append(f"Karnofsky: {imdc_rf['karnofsky_prozent']}%")
            if imdc_rf.get("haemoglobin_unter_norm") is not None:
                imdc_parts.append(f"Hb↓: {'Ja' if imdc_rf['haemoglobin_unter_norm'] else 'Nein'}")
            if imdc_rf.get("korrigiertes_calcium_ueber_norm") is not None:
                imdc_parts.append(f"Ca↑: {'Ja' if imdc_rf['korrigiertes_calcium_ueber_norm'] else 'Nein'}")
            if imdc_rf.get("neutrophile_ueber_norm") is not None:
                imdc_parts.append(f"Neutro↑: {'Ja' if imdc_rf['neutrophile_ueber_norm'] else 'Nein'}")
            if imdc_rf.get("thrombozyten_ueber_norm") is not None:
                imdc_parts.append(f"Thrombo↑: {'Ja' if imdc_rf['thrombozyten_ueber_norm'] else 'Nein'}")
        imdc_str = ", ".join(imdc_parts) if imdc_parts else "Nicht dokumentiert"

        # Format ICI eligibility
        ici_status = case.get("ici_durchfuehrbar")
        if ici_status is True:
            ici_str = "Ja"
        elif ici_status is False:
            gruende = case.get("ici_gruende_nein", [])
            ici_str = f"Nein ({', '.join(gruende)})" if gruende else "Nein"
        else:
            ici_str = "Nicht dokumentiert"

        # Format prior therapies
        prior = case.get("prior_therapies", [])
        prior_str = ", ".join(prior) if prior else "Keine"

        prompt = f"""Du bist ein erfahrener Onkologe, spezialisiert auf Nierenzellkarzinom (RCC).
Analysiere den folgenden klinischen Fall und erstelle eine strukturierte Therapieempfehlung.

=== KLINISCHER FALL ===
Patient: {case.get('patient_name', 'Unbekannt')}, {case.get('age', '?')} Jahre
ECOG: {case.get('ecog', '?')}, Karnofsky: {case.get('karnofsky') or '?'}%
Komorbidität: {case.get('comorbidity', 'unknown')}
Lebenserwartung: {case.get('life_expectancy', 'unknown')}

Diagnose: {case.get('diagnose_kurz', '')}
Stadium: {case.get('stadium', '')}
{tnm_str}

HISTOLOGIE (WICHTIG für Therapieentscheidung):
{histologie_str}

Anamnese:
{case.get('anamnese', '')}

Nebendiagnosen: {comorbid_str}

Aktuelle Medikation: {medikation_str}

Bildgebung:
  - {bildgebung_str}

IMDC-Risikofaktoren: {imdc_str}
ICI-Kombination durchführbar: {ici_str}
Vorherige Systemtherapien: {prior_str}

=== THERAPIE-LEITLINIEN ===

{METASTATIC_THERAPY_SUMMARY}

{NON_METASTATIC_THERAPY_SUMMARY}

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
{{
    "is_metastatic": true/false,
    "metastatic_reasoning": "Begründung für Metastasierungsstatus...",
    "imdc_risk": "guenstig/intermediaer/unguenstig/nicht_anwendbar",
    "imdc_reasoning": "IMDC-Berechnung oder null wenn nicht-metastasiert/nicht-klarzellig...",
    "treatment_reasoning": "Schrittweise Begründung nach Leitlinie...",
    "recommended_therapy": "Konkrete Therapieempfehlung",
    "therapy_category": "IO+TKI/TKI mono/Surgery/Surveillance/Ablation/etc.",
    "recommendation_strength": "A/B/0",
    "confidence": 0.0-1.0
}}"""

        return prompt

    def parse_response(self, response: str) -> Optional[dict]:
        """Parse JSON from response."""
        try:
            # Handle thinking models
            if "</think>" in response:
                response = response.split("</think>")[-1].strip()

            # Find JSON
            json_match = re.search(r'\{[\s\S]*"is_metastatic"[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))

            # Try direct parse
            return json.loads(response)
        except:
            return None

    def predict(self, case: dict) -> dict:
        """Run treatment prediction for a single case."""
        prompt = self.build_prompt(case)
        start_time = time.time()

        try:
            response = requests.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/med-llm",
                    "X-Title": "Med_LLM Treatment"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "max_tokens": self.max_tokens
                },
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            inference_time = time.time() - start_time

            raw_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = result.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            self.total_tokens += tokens_used

            output = self.parse_response(raw_response)

            return {
                "output": output,
                "raw_response": raw_response,
                "inference_time": inference_time,
                "tokens_used": tokens_used,
                "success": output is not None,
                "prompt": prompt
            }

        except Exception as e:
            return {
                "output": None,
                "raw_response": str(e),
                "inference_time": time.time() - start_time,
                "tokens_used": 0,
                "success": False,
                "prompt": prompt
            }

    def check_connection(self) -> bool:
        """Check API connection."""
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False


# ============================================================================
# Data Loading
# ============================================================================

def load_ncc_cases() -> List[dict]:
    """Load NCC cases with all clinical data - ALIGNED WITH MODAL."""
    ncc_file = DATA_DIR / "ncc" / "ncc_cases_json.json"

    if not ncc_file.exists():
        raise FileNotFoundError(f"NCC file not found: {ncc_file}")

    with open(ncc_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = []
    for i, case in enumerate(data.get("cases", []), 1):
        # Handle case_template structure (cases 15-32)
        if "case_template" in case and not case.get("patient", {}).get("nachname"):
            template = case.get("case_template", {})
            patient = template.get("patient", {})
            entities = template.get("entitaeten", [{}])
            anamnese = template.get("anamnese_freitext", "") or case.get("anamnese_freitext", "")
            nebendiagnosen = template.get("nebendiagnosen", []) or case.get("nebendiagnosen", [])
            medikation = template.get("medikation", []) or case.get("medikation", [])
            gt_therapy = template.get("geplantes_therapiekonzept") or case.get("geplantes_therapiekonzept")
        else:
            patient = case.get("patient", {})
            entities = case.get("entitaeten", [{}])
            anamnese = case.get("anamnese_freitext", "")
            nebendiagnosen = case.get("nebendiagnosen", [])
            medikation = case.get("medikation", [])
            gt_therapy = case.get("geplantes_therapiekonzept")

        entity = entities[0] if entities else {}
        qa = entity.get("quick_access", {})
        klassifikation = entity.get("klassifikation", {})
        rcc_spez = entity.get("rcc_spezifisch", {})
        histologie = rcc_spez.get("histologie", {})
        imdc_data = rcc_spez.get("imdc", {})
        systemtherapie = rcc_spez.get("systemtherapie_kontext", {})

        # Extract ECOG/Karnofsky (handle both schema v1.0 flat and v1.1 nested formats)
        ecog = patient.get("ecog") or patient.get("performance_status", {}).get("ecog")
        karnofsky = patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent")

        # For v1.0 schema, Karnofsky may be in marker_oder_labor.sonstige array
        if karnofsky is None:
            marker_labor = entity.get("marker_oder_labor", {})
            for item in marker_labor.get("sonstige", []):
                if item.get("parameter") == "Karnofsky":
                    karnofsky = item.get("wert")
                    break

        cases.append({
            "case_id": f"ncc_{i}",
            # Patient data
            "patient_name": f"{patient.get('nachname', '')}, {patient.get('vorname', '')}",
            "age": patient.get("alter_jahre"),
            "ecog": ecog,
            "karnofsky": karnofsky,
            "comorbidity": patient.get("komorbiditaet_level"),
            "life_expectancy": patient.get("lebenserwartung"),
            # Diagnosis
            "anamnese": anamnese,
            "diagnose_kurz": entity.get("diagnose_kurz", ""),
            "stadium": entity.get("stadium_oder_risikoklasse", ""),
            # TNM staging
            "tnm_clinical": klassifikation.get("tnm_clinical"),
            "tnm_pathological": klassifikation.get("tnm_pathological"),
            "grading": klassifikation.get("grad"),
            # Histologie - CRITICAL for therapy decision
            "histologie_subtyp": histologie.get("subtyp"),
            "histologie_klarzellig": histologie.get("klarzellig"),
            "histologie_sarcomatoid": histologie.get("sarcomatoid"),
            "histologie_grading": histologie.get("grading_value"),
            # IMDC risk factors
            "imdc_kategorie": imdc_data.get("kategorie"),
            "imdc_risikofaktoren": imdc_data.get("risikofaktoren_structured", {}),
            "imdc_laborwerte": imdc_data.get("laborwerte_optional", {}),
            # Systemtherapie context
            "ici_durchfuehrbar": systemtherapie.get("ici_kombination_durchfuehrbar"),
            "ici_gruende_nein": systemtherapie.get("gruende_wenn_nein", []),
            "prior_therapies": systemtherapie.get("vorherige_systemtherapien", []) or qa.get("vorherige_systemtherapien", []),
            # Bildgebung
            "bildgebung": entity.get("bildgebung", []),
            # Additional
            "nebendiagnosen": nebendiagnosen,
            "medikation": medikation,
            # Quick access (legacy)
            "quick_access": qa,
            "histology_clear_cell": qa.get("rcc_histologie_klarzellig"),
            # Ground truth
            "ground_truth_metastatic": qa.get("metastatic"),
            "ground_truth_imdc": qa.get("imdc_risiko") or imdc_data.get("kategorie"),
            "ground_truth_therapy": gt_therapy,
            # Full case for reference
            "full_case": case,
        })

    return cases


# ============================================================================
# Main Runner
# ============================================================================

def setup_run_directory(model_id: str) -> Path:
    """Create timestamped run directory."""
    model_safe = model_id.replace("/", "_").replace(":", "_")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = RESULTS_DIR / "openrouter_treatment" / model_safe / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def setup_logging(run_dir: Path) -> logging.Logger:
    """Setup logging."""
    logger = logging.getLogger("treatment_openrouter")
    logger.setLevel(logging.INFO)
    logger.handlers = []

    fh = logging.FileHandler(run_dir / "run.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def run_treatment_prediction(model: str, temperature: float = 0.3) -> dict:
    """Run treatment prediction on all NCC cases - ALIGNED WITH MODAL."""

    try:
        predictor = OpenRouterTreatmentPredictor(model=model, temperature=temperature)
    except ValueError as e:
        print(f"ERROR: {e}")
        return None

    run_dir = setup_run_directory(predictor.model)
    logger = setup_logging(run_dir)

    logger.info(f"NCC Treatment Prediction (OpenRouter)")
    logger.info(f"=" * 60)
    logger.info(f"Model: {predictor.model}")
    logger.info(f"Run directory: {run_dir}")

    if not predictor.check_connection():
        logger.error("Cannot connect to OpenRouter API")
        return None

    logger.info("OpenRouter connection: OK")

    cases = load_ncc_cases()
    logger.info(f"Loaded {len(cases)} NCC cases")
    logger.info("-" * 60)

    results = []
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    for i, case in enumerate(cases, 1):
        logger.info(f"[{i}/{len(cases)}] {case['case_id']}: {case['patient_name'][:30]}...")

        result = predictor.predict(case)
        prediction = result["output"]

        # Evaluate - ALIGNED WITH MODAL
        gt_met = case.get("ground_truth_metastatic")
        gt_therapy = case.get("ground_truth_therapy", "")
        # Handle list format (multiple therapies)
        if isinstance(gt_therapy, list):
            gt_therapy = " | ".join(str(t) for t in gt_therapy) if gt_therapy else ""
        gt_imdc = case.get("ground_truth_imdc")

        met_correct = None
        therapy_exact = None
        therapy_acceptable = None

        if prediction:
            # Metastatic classification
            if gt_met is not None:
                met_correct = prediction.get("is_metastatic") == gt_met

            # Therapy exact match (fuzzy) - SAME AS MODAL
            if gt_therapy:
                pred_therapy = (prediction.get("recommended_therapy") or "").lower()
                gt_therapy_lower = gt_therapy.lower()
                therapy_exact = (
                    pred_therapy in gt_therapy_lower or
                    gt_therapy_lower in pred_therapy or
                    any(word in gt_therapy_lower for word in pred_therapy.split() if len(word) > 4)
                )

            # Therapy clinically acceptable - SAME AS MODAL
            if gt_met is not None:
                therapy_acceptable = is_therapy_clinically_acceptable(prediction, gt_met, gt_imdc)

        # Save individual result - ALIGNED WITH MODAL FORMAT
        case_result = {
            "case_id": case["case_id"],
            "timestamp": run_timestamp,
            "provider": "openrouter",
            "model": predictor.model,
            "input_case": {
                "case_id": case["case_id"],
                "patient_name": case["patient_name"],
                "age": case.get("age"),
                "ecog": case.get("ecog"),
                "karnofsky": case.get("karnofsky"),
                "comorbidity": case.get("comorbidity"),
                "life_expectancy": case.get("life_expectancy"),
                "anamnese": case.get("anamnese", ""),
                "diagnose_kurz": case.get("diagnose_kurz"),
                "stadium": case.get("stadium"),
                "tnm_clinical": case.get("tnm_clinical"),
                "tnm_pathological": case.get("tnm_pathological"),
                "histologie_subtyp": case.get("histologie_subtyp"),
                "histologie_klarzellig": case.get("histologie_klarzellig"),
                "bildgebung": case.get("bildgebung"),
                "nebendiagnosen": case.get("nebendiagnosen"),
                "medikation": case.get("medikation"),
                "ici_durchfuehrbar": case.get("ici_durchfuehrbar"),
                "prior_therapies": case.get("prior_therapies"),
                "ground_truth_metastatic": gt_met,
                "ground_truth_imdc": gt_imdc,
                "ground_truth_therapy": gt_therapy,
            },
            "prompt_text": result["prompt"],
            "prediction": prediction,
            "raw_response": result["raw_response"],
            "ground_truth_metastatic": gt_met,
            "ground_truth_therapy": gt_therapy,
            "metastatic_correct": met_correct,
            "therapy_exact_match": therapy_exact,
            "therapy_clinically_acceptable": therapy_acceptable,
            "inference_time_seconds": result["inference_time"],
            "tokens_used": result["tokens_used"],
            "success": prediction is not None,
            "error_message": None if prediction else "Failed to parse JSON response",
        }

        # Save individual file
        with open(run_dir / f"{case['case_id']}.json", 'w', encoding='utf-8') as f:
            json.dump(case_result, f, indent=2, ensure_ascii=False, default=str)

        results.append(case_result)

        if not result["success"]:
            logger.info(f"  -> ERROR")
        else:
            status = "CORRECT" if met_correct else ("WRONG" if met_correct is False else "N/A")
            logger.info(f"  -> {status} ({result['inference_time']:.1f}s)")

    # Calculate summary stats - ALIGNED WITH MODAL
    met_correct_count = sum(1 for r in results if r["metastatic_correct"] == True)
    met_total = sum(1 for r in results if r["metastatic_correct"] is not None)
    exact_count = sum(1 for r in results if r["therapy_exact_match"] == True)
    acceptable_count = sum(1 for r in results if r["therapy_clinically_acceptable"] == True)

    summary_data = {
        "model": predictor.model,
        "provider": "openrouter",
        "timestamp": run_timestamp,
        "total_cases": len(results),
        "metastatic_accuracy": met_correct_count / met_total if met_total > 0 else 0,
        "metastatic_correct": met_correct_count,
        "therapy_exact_match_rate": exact_count / len(results) if results else 0,
        "therapy_exact_matches": exact_count,
        "therapy_acceptable_rate": acceptable_count / len(results) if results else 0,
        "therapy_acceptable": acceptable_count,
        "total_time": sum(r["inference_time_seconds"] for r in results),
        "errors": sum(1 for r in results if not r["success"]),
    }

    with open(run_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)

    # Print results - ALIGNED WITH MODAL OUTPUT FORMAT
    logger.info(f"\n{'=' * 50}")
    logger.info(f"RESULTS: {predictor.model}")
    logger.info(f"{'=' * 50}")
    logger.info(f"Metastatic Classification: {summary_data['metastatic_accuracy']*100:.1f}% ({met_correct_count}/{len(results)})")
    logger.info(f"Therapy Exact Match: {summary_data['therapy_exact_match_rate']*100:.1f}% ({exact_count}/{len(results)})")
    logger.info(f"Therapy Clinically Acceptable: {summary_data['therapy_acceptable_rate']*100:.1f}% ({acceptable_count}/{len(results)})")
    logger.info(f"Time: {summary_data['total_time']:.1f}s")
    logger.info(f"Errors: {summary_data['errors']}")
    logger.info(f"\nSaved: {run_dir}")

    return summary_data


def list_models():
    """List available models."""
    print("Available models:")
    print("-" * 60)
    for short, full in sorted(OpenRouterClassifier.MODEL_REGISTRY.items()):
        print(f"  {short:25} -> {full}")


def main():
    parser = argparse.ArgumentParser(description="NCC Treatment Prediction using OpenRouter")
    parser.add_argument("--model", type=str, default="gemma3:27b", help="Model to use")
    parser.add_argument("--temperature", type=float, default=0.3, help="Temperature (default: 0.3)")
    parser.add_argument("--list-models", action="store_true", help="List available models")

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    run_treatment_prediction(args.model, args.temperature)


if __name__ == "__main__":
    main()
