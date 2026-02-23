#!/usr/bin/env python3
"""
NCC (Kidney Cancer) Treatment Prediction with Modal vLLM

This script predicts:
1. Metastatic vs Non-metastatic classification
2. Treatment reasoning following therapy flowcharts
3. Recommended therapy

Evaluation metrics:
- Metastatic classification accuracy
- Exact match with geplantes_therapiekonzept
- Clinical acceptability (valid option per flowchart)
"""

import modal
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field

# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class MetastaticStatus(str, Enum):
    METASTATIC = "metastasiert"
    NON_METASTATIC = "nicht_metastasiert"

class IMDCRisk(str, Enum):
    FAVORABLE = "guenstig"
    INTERMEDIATE = "intermediaer"
    UNFAVORABLE = "unguenstig"
    NOT_APPLICABLE = "nicht_anwendbar"

class TreatmentPrediction(BaseModel):
    """Structured output for NCC treatment prediction."""

    # Step 1: Metastatic classification
    is_metastatic: bool = Field(..., description="True if metastatic, False if non-metastatic")
    metastatic_reasoning: str = Field(..., description="Reasoning for metastatic classification")

    # Step 2: Risk stratification (if metastatic)
    imdc_risk: Optional[str] = Field(None, description="IMDC risk category if metastatic")
    imdc_reasoning: Optional[str] = Field(None, description="IMDC risk calculation reasoning")

    # Step 3: Treatment recommendation
    treatment_reasoning: str = Field(..., description="Step-by-step reasoning following therapy flowchart")
    recommended_therapy: str = Field(..., description="Specific recommended therapy")
    therapy_category: str = Field(..., description="Category: IO+TKI, TKI mono, Surgery, Surveillance, etc.")
    recommendation_strength: Optional[str] = Field(None, description="A (strong), B (weak), 0 (option)")

    # Confidence
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence 0-1")


class CaseInput(BaseModel):
    """Input case data."""
    case_id: str
    patient_name: str
    age: Optional[int] = None
    ecog: Optional[int] = None
    anamnese: str
    diagnose_kurz: str
    stadium: Optional[str] = None
    tnm_clinical: Optional[dict] = None
    tnm_pathological: Optional[dict] = None
    quick_access: Optional[dict] = None
    ground_truth_metastatic: Optional[bool] = None
    ground_truth_therapy: Optional[str] = None


class PredictionResult(BaseModel):
    """Complete prediction result."""
    case_id: str
    timestamp: str
    provider: str = "modal"
    model: str
    input_case: CaseInput
    prompt_text: str
    prediction: Optional[TreatmentPrediction] = None
    raw_response: str = ""

    # Ground truth comparison
    ground_truth_metastatic: Optional[bool] = None
    ground_truth_therapy: Optional[str] = None

    # Evaluation
    metastatic_correct: Optional[bool] = None
    therapy_exact_match: Optional[bool] = None
    therapy_clinically_acceptable: Optional[bool] = None

    inference_time_seconds: float = 0.0
    tokens_used: int = 0
    success: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Model Configuration
# ============================================================================

MODEL_CONFIGS = {
    # Medical models
    "meditron3-7b": {
        "hf_id": "OpenMeditron/Meditron3-Qwen2.5-7B",
        "gpu": "H100",
        "tp": 1,
    },
    "medgemma-4b": {
        "hf_id": "google/medgemma-4b-it",
        "gpu": "H100",
        "tp": 1,
        "multimodal": True,
    },
    "medgemma-27b": {
        "hf_id": "google/medgemma-27b-text-it",
        "gpu": "H100",
        "tp": 1,
    },
    # General models
    "gemma-3-4b": {
        "hf_id": "google/gemma-3-4b-it",
        "gpu": "H100",
        "tp": 1,
        "multimodal": True,
    },
    "gemma-3-27b": {
        "hf_id": "google/gemma-3-27b-it",
        "gpu": "H100",
        "tp": 1,
        "multimodal": True,
    },
    "olmo-3.1-32b-instruct": {
        "hf_id": "allenai/Olmo-3.1-32B-Instruct",
        "gpu": "H100",
        "tp": 1,
    },
    "olmo-3.1-32b-think": {
        "hf_id": "allenai/Olmo-3.1-32B-Think",
        "gpu": "H100",
        "tp": 1,
        "thinking": True,
    },
}

# ============================================================================
# Therapy Flowchart Summary (embedded for prompt)
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
# Data Loading
# ============================================================================

def _detect_case_format(case: dict) -> str:
    """Detect which schema format a case uses.

    Returns one of: 'case-de', 'diagnosen', 'case-template', 'v1.1'
    """
    if "case" in case and isinstance(case["case"], dict):
        return "case-de"  # mRCC_case_schema with German keys (cases 62-63)
    if "diagnosen" in case:
        return "diagnosen"  # mRCC_case_schema_v1.1 (cases 64-66)
    if "case_template" in case:
        return "case-template"  # v1.0 original + v1.0-new (cases 15-35, 67-69)
    return "v1.1"  # Standard v1.1 (cases 1-14, 36-61)


def _extract_case_de(case: dict) -> dict:
    """Extract fields from case-de format (mRCC_case_schema with German keys)."""
    ci = case.get("case", {})
    patient = ci.get("patient", {})
    diag = ci.get("diagnose", {})
    anam = ci.get("anamnese", {})
    imdc = ci.get("imdc", {})
    staging = ci.get("staging", {})
    tp = ci.get("therapieplan", {})

    # Build anamnese text from structured data
    anamnese_parts = []
    if anam.get("erstdiagnose_metastasiert_datum"):
        anamnese_parts.append(f"Erstdiagnose metastasiert: {anam['erstdiagnose_metastasiert_datum']}")
    for therapy in anam.get("vorherige_systemtherapien", []):
        line = f"Linie {therapy.get('linie')}: {therapy.get('regime')} ({therapy.get('klasse')})"
        if therapy.get("abbruchgrund"):
            line += f" - {therapy['abbruchgrund']}"
        anamnese_parts.append(line)
    for lok in anam.get("vorherige_lokaltherapien", []):
        if isinstance(lok, str):
            anamnese_parts.append(f"Lokaltherapie: {lok}")
        elif isinstance(lok, dict):
            anamnese_parts.append(f"Lokaltherapie: {lok.get('eingriff', '')} ({lok.get('datum', '')})")
    anamnese_text = "\n".join(anamnese_parts) if anamnese_parts else ""

    # Build bildgebung from staging
    bildgebung = []
    if staging:
        entry = {
            "modalitaet": staging.get("modalitaet", ""),
            "region": ", ".join(staging.get("regionen", [])),
            "datum": staging.get("datum"),
        }
        befunde = staging.get("befunde", {})
        befund_parts = []
        for region, findings in befunde.items():
            if isinstance(findings, dict):
                for key, val in findings.items():
                    if isinstance(val, list) and val:
                        befund_parts.append(f"{region}/{key}: {len(val)} Läsionen")
                    elif isinstance(val, str) and val:
                        befund_parts.append(f"{region}/{key}: {val}")
        entry["befund_kurz"] = "; ".join(befund_parts) if befund_parts else ""
        bildgebung.append(entry)

    # Ground truth from therapieplan
    gt_options = tp.get("systemtherapie_optionen_diskutiert", [])
    gt_therapy = " | ".join(gt_options) if gt_options else None

    # Prior therapies
    prior = [f"{t.get('regime', '')} ({t.get('klasse', '')})" for t in anam.get("vorherige_systemtherapien", [])]

    # IMDC
    imdc_kriterien = imdc.get("kriterien", {})
    imdc_werte = imdc.get("werte", {})

    return {
        "patient_name": f"{patient.get('nachname', '')}, {patient.get('vorname', '')}",
        "age": patient.get("alter_jahre"),
        "ecog": patient.get("ecog"),
        "karnofsky": patient.get("karnofsky_prozent"),
        "comorbidity": None,
        "life_expectancy": None,
        "anamnese": anamnese_text,
        "diagnose_kurz": diag.get("entitaet", "") or "",
        "stadium": "",
        "tnm_clinical": None,
        "tnm_pathological": None,
        "grading": None,
        "histologie_subtyp": diag.get("histologie_subtyp"),
        "histologie_klarzellig": None,
        "histologie_sarcomatoid": None,
        "histologie_grading": None,
        "imdc_kategorie": imdc.get("risikogruppe"),
        "imdc_risikofaktoren": imdc_kriterien,
        "imdc_laborwerte": imdc_werte,
        "ici_durchfuehrbar": None,
        "ici_gruende_nein": [],
        "prior_therapies": prior,
        "bildgebung": bildgebung,
        "nebendiagnosen": anam.get("komorbiditaeten", []),
        "medikation": anam.get("medikation", []),
        "quick_access": {},
        "histology_clear_cell": None,
        "ground_truth_metastatic": None,
        "ground_truth_imdc": imdc.get("risikogruppe"),
        "ground_truth_therapy": gt_therapy,
    }


def _extract_diagnosen(case: dict) -> dict:
    """Extract fields from diagnosen format (mRCC_case_schema_v1.1)."""
    patient = case.get("patient", {})
    diags = case.get("diagnosen", [{}])
    d0 = diags[0] if diags else {}
    th = case.get("tumor_history", {})
    tp = case.get("therapieplanung", {})
    bg = case.get("bildgebung", [])
    komorbid = case.get("komorbiditaeten_und_vops", {})
    medikation = case.get("medikation", [])

    # Build anamnese from tumor_history
    anamnese_parts = []
    primary = th.get("primary_tumor", {}) if isinstance(th, dict) else {}
    if primary:
        op = primary.get("op", {})
        if op:
            path = op.get("pathologie", {})
            anamnese_parts.append(
                f"Primärtumor: {primary.get('organ', '')} {primary.get('seite', '')} "
                f"- {op.get('eingriff', '')} ({op.get('datum', '')})"
                f" - {path.get('pT', '')} {path.get('pN', '')} R{path.get('R', '')}"
            )
    # Also include history entries if it's a list
    if isinstance(th, list):
        for entry in th:
            if isinstance(entry, dict):
                anamnese_parts.append(f"{entry.get('datum', '')}: {entry.get('ereignis', '')} - {entry.get('details', '')}")
    anamnese_text = "\n".join(anamnese_parts) if anamnese_parts else ""

    # Normalize bildgebung entries
    norm_bg = []
    for b in bg:
        if isinstance(b, dict):
            entry = {
                "modalitaet": b.get("modalitaet", ""),
                "region": b.get("region", ""),
                "datum": b.get("datum"),
            }
            # Extract befund_kurz from nested befund dict
            befund = b.get("befund", {})
            if isinstance(befund, dict):
                parts = []
                for region, findings in befund.items():
                    if isinstance(findings, str):
                        parts.append(f"{region}: {findings}")
                    elif isinstance(findings, dict):
                        for key, val in findings.items():
                            if isinstance(val, str) and val:
                                parts.append(f"{region}/{key}: {val}")
                entry["befund_kurz"] = "; ".join(parts[:5]) if parts else ""
            elif isinstance(befund, str):
                entry["befund_kurz"] = befund
            norm_bg.append(entry)

    # Ground truth from therapieplanung
    gt_parts = tp.get("geplantes_vorgehen", []) if isinstance(tp, dict) else []
    gt_therapy = " | ".join(gt_parts) if gt_parts else None

    # IMDC
    imdc_factors = d0.get("imdc_factors", {})
    imdc_values = d0.get("imdc_values", {})

    # Histologie from diagnosen or tumor_history
    histologie_subtyp = d0.get("subtyp")
    is_klarzellig = histologie_subtyp in ("ccRCC", "klarzellig") if histologie_subtyp else None
    if not histologie_subtyp and isinstance(primary, dict):
        histologie_subtyp = primary.get("histologie")
        is_klarzellig = histologie_subtyp in ("ccRCC", "klarzellig") if histologie_subtyp else None

    # Nebendiagnosen from komorbiditaeten_und_vops
    nebend = komorbid.get("vorerkrankungen", []) if isinstance(komorbid, dict) else []

    return {
        "patient_name": f"{patient.get('nachname', '')}, {patient.get('vorname', '')}",
        "age": patient.get("alter_jahre"),
        "ecog": patient.get("ecog"),
        "karnofsky": patient.get("karnofsky_percent"),
        "comorbidity": None,
        "life_expectancy": None,
        "anamnese": anamnese_text,
        "diagnose_kurz": d0.get("diagnose_kurz", ""),
        "stadium": f"Linie {d0.get('therapielinie', '?')}" if d0.get("therapielinie") else "",
        "tnm_clinical": None,
        "tnm_pathological": None,
        "grading": None,
        "histologie_subtyp": histologie_subtyp,
        "histologie_klarzellig": is_klarzellig,
        "histologie_sarcomatoid": None,
        "histologie_grading": None,
        "imdc_kategorie": d0.get("imdc_risk_group"),
        "imdc_risikofaktoren": imdc_factors,
        "imdc_laborwerte": imdc_values,
        "ici_durchfuehrbar": None,
        "ici_gruende_nein": [],
        "prior_therapies": [],
        "bildgebung": norm_bg,
        "nebendiagnosen": nebend,
        "medikation": medikation,
        "quick_access": {},
        "histology_clear_cell": is_klarzellig,
        "ground_truth_metastatic": None,
        "ground_truth_imdc": d0.get("imdc_risk_group"),
        "ground_truth_therapy": gt_therapy,
    }


def _extract_case_template(case: dict) -> dict:
    """Extract fields from case_template format (v1.0 original + v1.0-new)."""
    template = case.get("case_template", {})
    patient = template.get("patient", {})
    entities = template.get("entitaeten", [{}])
    entity = entities[0] if entities else {}

    # ECOG/Karnofsky - flat in v1.0
    ecog = patient.get("ecog") or patient.get("performance_status", {}).get("ecog")
    karnofsky = patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent")

    # For v1.0, Karnofsky may be in marker_oder_labor.sonstige array
    if karnofsky is None:
        marker_labor = entity.get("marker_oder_labor", {})
        if isinstance(marker_labor, dict):
            for item in marker_labor.get("sonstige", []):
                if isinstance(item, dict) and item.get("parameter") == "Karnofsky":
                    karnofsky = item.get("wert")
                    break

    # Anamnese: try multiple locations
    anamnese = template.get("anamnese_freitext", "") or case.get("anamnese_freitext", "")

    # v1.0-new: anamnese is in entity.anamnese.onko_verlauf (structured events)
    if not anamnese and isinstance(entity.get("anamnese"), dict):
        entity_anam = entity["anamnese"]
        onko = entity_anam.get("onko_verlauf", [])
        if onko:
            parts = []
            for event in onko:
                if isinstance(event, dict):
                    parts.append(f"{event.get('datum', '')}: {event.get('ereignis', '')} - {event.get('details', '')}")
            anamnese = "\n".join(parts)
        # Also pull in vorerkrankungen/medikation from entity.anamnese
        if not template.get("nebendiagnosen") and entity_anam.get("vorerkrankungen"):
            template["_nebendiagnosen_from_entity"] = entity_anam["vorerkrankungen"]
        if not template.get("medikation") and entity_anam.get("medikation"):
            template["_medikation_from_entity"] = entity_anam["medikation"]

    nebendiagnosen = (template.get("nebendiagnosen", []) or case.get("nebendiagnosen", [])
                      or template.get("_nebendiagnosen_from_entity", []))
    medikation = (template.get("medikation", []) or case.get("medikation", [])
                  or template.get("_medikation_from_entity", []))

    # Ground truth: try multiple locations
    gt_therapy = template.get("geplantes_therapiekonzept") or case.get("geplantes_therapiekonzept")
    # v1.0-new: GT is in entity.therapieplanung.geplantes_konzept
    if gt_therapy is None and isinstance(entity.get("therapieplanung"), dict):
        konzept = entity["therapieplanung"].get("geplantes_konzept", [])
        if konzept:
            gt_parts = [f"{k.get('regime', '')} ({k.get('kategorie', '')})" for k in konzept if isinstance(k, dict)]
            gt_therapy = " | ".join(gt_parts) if gt_parts else None

    qa = entity.get("quick_access", {}) or {}
    klassifikation = entity.get("klassifikation", {}) or {}
    rcc_spez = entity.get("rcc_spezifisch", {}) or {}
    histologie = rcc_spez.get("histologie", {}) or {}
    imdc_data = rcc_spez.get("imdc", {}) or {}
    systemtherapie = rcc_spez.get("systemtherapie_kontext", {}) or {}

    # v1.0-new: IMDC is directly on entity
    entity_imdc = entity.get("imdc", {}) or {}
    if entity_imdc and not imdc_data:
        imdc_data = entity_imdc

    # IMDC category from various locations
    imdc_kategorie = (imdc_data.get("kategorie") or imdc_data.get("risikoklasse")
                      or qa.get("imdc_risiko"))

    # IMDC risk factors
    imdc_rf = imdc_data.get("risikofaktoren_structured", {}) or imdc_data.get("faktoren", {})
    imdc_lab = imdc_data.get("laborwerte_optional", {})

    # Prior therapies from multiple locations
    prior = (systemtherapie.get("vorherige_systemtherapien", [])
             or qa.get("vorherige_systemtherapien", []))

    # Histologie from diagnose_kurz if not in rcc_spezifisch
    histologie_subtyp = histologie.get("subtyp")
    histologie_klarzellig = histologie.get("klarzellig")
    histologie_sarcomatoid = histologie.get("sarcomatoid")
    diag_kurz = entity.get("diagnose_kurz", "") or ""
    if not histologie_subtyp and diag_kurz:
        lower = diag_kurz.lower()
        if "non-ccrcc" in lower or "nicht-klarzellig" in lower:
            histologie_klarzellig = False
            if "pap" in lower:
                histologie_subtyp = "papillär"
            elif "chromophob" in lower:
                histologie_subtyp = "chromophob"
            else:
                histologie_subtyp = "non-ccRCC"
        elif "klarzellig" in lower or "ccrcc" in lower:
            histologie_subtyp = histologie_subtyp or "ccRCC"
            histologie_klarzellig = True
        elif "papill" in lower or "paprcc" in lower:
            histologie_subtyp = histologie_subtyp or "papillär"
            histologie_klarzellig = False
        if "sarkomatoid" in lower or "sarcomatoid" in lower:
            histologie_sarcomatoid = True

    # TNM: v1.0 has string, v1.1 has dict
    tnm_clinical = klassifikation.get("tnm_clinical")
    tnm_pathological = klassifikation.get("tnm_pathological")
    # v1.0 string TNM
    if not tnm_clinical and isinstance(klassifikation.get("tnm"), str):
        tnm_clinical = {"raw": klassifikation["tnm"]}

    return {
        "patient_name": f"{patient.get('nachname', '')}, {patient.get('vorname', '')}",
        "age": patient.get("alter_jahre"),
        "ecog": ecog,
        "karnofsky": karnofsky,
        "comorbidity": patient.get("komorbiditaet_level"),
        "life_expectancy": patient.get("lebenserwartung"),
        "anamnese": anamnese,
        "diagnose_kurz": diag_kurz,
        "stadium": entity.get("stadium_oder_risikoklasse", ""),
        "tnm_clinical": tnm_clinical,
        "tnm_pathological": tnm_pathological,
        "grading": klassifikation.get("grad"),
        "histologie_subtyp": histologie_subtyp,
        "histologie_klarzellig": histologie_klarzellig,
        "histologie_sarcomatoid": histologie_sarcomatoid,
        "histologie_grading": histologie.get("grading_value"),
        "imdc_kategorie": imdc_kategorie,
        "imdc_risikofaktoren": imdc_rf,
        "imdc_laborwerte": imdc_lab,
        "ici_durchfuehrbar": systemtherapie.get("ici_kombination_durchfuehrbar"),
        "ici_gruende_nein": systemtherapie.get("gruende_wenn_nein", []),
        "prior_therapies": prior,
        "bildgebung": entity.get("bildgebung", []),
        "nebendiagnosen": nebendiagnosen,
        "medikation": medikation,
        "quick_access": qa,
        "histology_clear_cell": qa.get("rcc_histologie_klarzellig") or histologie_klarzellig,
        "ground_truth_metastatic": qa.get("metastatic"),
        "ground_truth_imdc": imdc_kategorie,
        "ground_truth_therapy": gt_therapy,
    }


def _extract_v11(case: dict) -> dict:
    """Extract fields from v1.1 standard format (cases 1-14, 36-61)."""
    patient = case.get("patient", {})
    entities = case.get("entitaeten", [{}])
    entity = entities[0] if entities else {}

    # ECOG/Karnofsky
    ecog = patient.get("ecog") or patient.get("performance_status", {}).get("ecog")
    karnofsky = patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent")

    qa = entity.get("quick_access", {}) or {}
    klassifikation = entity.get("klassifikation", {}) or {}
    rcc_spez = entity.get("rcc_spezifisch", {}) or {}
    histologie = rcc_spez.get("histologie", {}) or {}
    imdc_data = rcc_spez.get("imdc", {}) or {}
    systemtherapie = rcc_spez.get("systemtherapie_kontext", {}) or {}

    # v1.1 newer: IMDC is in imdc_addendum instead of rcc_spezifisch
    imdc_addendum = entity.get("imdc_addendum", {}) or {}
    if imdc_addendum and not imdc_data:
        imdc_data = imdc_addendum

    # IMDC category from various locations
    imdc_kategorie = (imdc_data.get("kategorie") or imdc_data.get("imdc_risk_category")
                      or qa.get("imdc_risiko"))

    # IMDC risk factors from imdc_addendum.imdc_parameters
    imdc_rf = imdc_data.get("risikofaktoren_structured", {})
    if not imdc_rf and imdc_addendum.get("imdc_parameters"):
        imdc_rf = imdc_addendum["imdc_parameters"]
    imdc_lab = imdc_data.get("laborwerte_optional", {})

    # Also try to parse IMDC from stadium_oder_risikoklasse text
    stadium = entity.get("stadium_oder_risikoklasse", "") or ""
    if not imdc_kategorie and "imdc" in stadium.lower():
        lower = stadium.lower()
        if "low" in lower:
            imdc_kategorie = "guenstig"
        elif "intermediate" in lower:
            imdc_kategorie = "intermediaer"
        elif "high" in lower:
            imdc_kategorie = "unguenstig"

    # Anamnese
    anamnese = case.get("anamnese_freitext", "")

    # Ground truth therapy (can be string or list)
    gt_therapy = case.get("geplantes_therapiekonzept")

    # Prior therapies from multiple locations
    prior = (systemtherapie.get("vorherige_systemtherapien", [])
             or qa.get("vorherige_systemtherapien", []))

    # Histologie from diagnose_kurz if not in rcc_spezifisch
    histologie_subtyp = histologie.get("subtyp")
    histologie_klarzellig = histologie.get("klarzellig")
    histologie_sarcomatoid = histologie.get("sarcomatoid")
    diag_kurz = entity.get("diagnose_kurz", "") or ""
    if not histologie_subtyp and diag_kurz:
        lower = diag_kurz.lower()
        if "non-ccrcc" in lower or "nicht-klarzellig" in lower:
            histologie_klarzellig = False
            if "pap" in lower:
                histologie_subtyp = "papillär"
            elif "chromophob" in lower:
                histologie_subtyp = "chromophob"
            else:
                histologie_subtyp = "non-ccRCC"
        elif "klarzellig" in lower or "ccrcc" in lower:
            histologie_subtyp = histologie_subtyp or "ccRCC"
            histologie_klarzellig = True
        elif "papill" in lower or "paprcc" in lower:
            histologie_subtyp = histologie_subtyp or "papillär"
            histologie_klarzellig = False
        if "sarkomatoid" in lower or "sarcomatoid" in lower:
            histologie_sarcomatoid = True

    # Also check kommentar for IMDC info
    kommentar = entity.get("kommentar", "")
    if isinstance(kommentar, dict):
        kommentar = str(kommentar)

    return {
        "patient_name": f"{patient.get('nachname', '')}, {patient.get('vorname', '')}",
        "age": patient.get("alter_jahre"),
        "ecog": ecog,
        "karnofsky": karnofsky,
        "comorbidity": patient.get("komorbiditaet_level"),
        "life_expectancy": patient.get("lebenserwartung"),
        "anamnese": anamnese,
        "diagnose_kurz": diag_kurz,
        "stadium": stadium,
        "tnm_clinical": klassifikation.get("tnm_clinical"),
        "tnm_pathological": klassifikation.get("tnm_pathological"),
        "grading": klassifikation.get("grad"),
        "histologie_subtyp": histologie_subtyp,
        "histologie_klarzellig": histologie_klarzellig,
        "histologie_sarcomatoid": histologie_sarcomatoid,
        "histologie_grading": histologie.get("grading_value"),
        "imdc_kategorie": imdc_kategorie,
        "imdc_risikofaktoren": imdc_rf,
        "imdc_laborwerte": imdc_lab,
        "ici_durchfuehrbar": systemtherapie.get("ici_kombination_durchfuehrbar"),
        "ici_gruende_nein": systemtherapie.get("gruende_wenn_nein", []),
        "prior_therapies": prior,
        "bildgebung": entity.get("bildgebung", []),
        "nebendiagnosen": case.get("nebendiagnosen", []),
        "medikation": case.get("medikation", []),
        "quick_access": qa,
        "histology_clear_cell": qa.get("rcc_histologie_klarzellig") or histologie_klarzellig,
        "ground_truth_metastatic": qa.get("metastatic"),
        "ground_truth_imdc": imdc_kategorie or qa.get("imdc_risiko"),
        "ground_truth_therapy": gt_therapy,
    }


def _infer_ground_truth_metastatic(case: dict) -> Optional[bool]:
    """Infer metastatic status from diagnosis text, stadium, and other fields.

    The quick_access.metastatic field only exists in v1.1 cases 1-14.
    For all other cases, we derive it from diagnose_kurz, stadium, entity type, etc.
    """
    # Already set from quick_access
    if case.get("ground_truth_metastatic") is not None:
        return case["ground_truth_metastatic"]

    diag = (case.get("diagnose_kurz") or "").lower()
    stadium = (case.get("stadium") or "").lower()

    # Clear metastatic indicators
    met_keywords = ["metastasiert", "mrcc", "met.", "metastatic", "metastasen"]
    if any(kw in diag for kw in met_keywords):
        return True
    if any(kw in stadium for kw in met_keywords):
        return True

    # Therapy line > 1 implies metastatic
    if "linie" in stadium or "linie" in diag:
        return True

    # IMDC risk only applies to metastatic
    if case.get("imdc_kategorie") and case["imdc_kategorie"] not in ("not_applicable", None):
        return True

    # Clear non-metastatic indicators
    non_met_keywords = ["local begrenzt", "lokal begrenzt", "nicht-metastasiert",
                        "non-metastatic", "nicht metastasiert"]
    if any(kw in diag for kw in non_met_keywords):
        return False
    if any(kw in stadium for kw in non_met_keywords):
        return False

    # Check TNM M status
    tnm = case.get("tnm_clinical") or {}
    if isinstance(tnm, dict):
        m = str(tnm.get("M", ""))
        if m == "1" or m.startswith("1"):
            return True
        if m == "0":
            return False

    return None


def load_ncc_cases(data_dir: str = "converted_data/send_23_12_25", start_case: int = 1, end_case: int = 0) -> List[dict]:
    """Load NCC cases with all relevant clinical data.

    Handles all schema formats:
    1. v1.1 standard: patient, entitaeten, etc. at top level (cases 1-14, 36-61)
    2. case_template: case_template.patient, etc. (v1.0 cases 15-35, v1.0-new cases 67-69)
    3. case-de: mRCC_case_schema with case.patient, case.diagnose, etc. (cases 62-63)
    4. diagnosen: mRCC_case_schema_v1.1 with diagnosen[], tumor_history, etc. (cases 64-66)

    Args:
        data_dir: Path to converted data directory
        start_case: 1-based case number to start from (skip earlier cases)
        end_case: 1-based case number to stop at (inclusive). 0 = no limit.
    """
    base = Path(data_dir)
    ncc_file = base / "ncc" / "ncc_cases_json.json"

    if not ncc_file.exists():
        raise FileNotFoundError(f"NCC cases file not found: {ncc_file}")

    with open(ncc_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = []
    for i, case in enumerate(data.get("cases", []), 1):
        if i < start_case:
            continue
        if end_case > 0 and i > end_case:
            break

        fmt = _detect_case_format(case)
        if fmt == "case-de":
            extracted = _extract_case_de(case)
        elif fmt == "diagnosen":
            extracted = _extract_diagnosen(case)
        elif fmt == "case-template":
            extracted = _extract_case_template(case)
        else:
            extracted = _extract_v11(case)

        extracted["case_id"] = f"ncc_{i}"
        extracted["schema_format"] = fmt
        extracted["full_case"] = case

        # Infer ground_truth_metastatic from diagnosis text if not set
        extracted["ground_truth_metastatic"] = _infer_ground_truth_metastatic(extracted)

        cases.append(extracted)

    return cases


def build_prompt(case: dict) -> str:
    """Build treatment prediction prompt with all clinical data and therapy flowchart context."""

    # Format TNM staging
    tnm_clinical = case.get("tnm_clinical") or {}
    tnm_path = case.get("tnm_pathological") or {}
    tnm_parts = []
    if tnm_clinical:
        if tnm_clinical.get("raw"):
            # v1.0 string TNM
            tnm_parts.append(f"TNM: {tnm_clinical['raw']}")
        else:
            tnm_parts.append(f"cTNM: T{tnm_clinical.get('T', '?')} N{tnm_clinical.get('N', '?')} M{tnm_clinical.get('M', '?')}")
    if tnm_path and (tnm_path.get('T') or tnm_path.get('raw')):
        if tnm_path.get("raw"):
            tnm_parts.append(f"pTNM: {tnm_path['raw']}")
        else:
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
        for c in comorbidities:  # No limit
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
                med_name = m.get("wirkstoff_oder_klasse") or m.get("wirkstoff") or m.get("name", "")
                if m.get("details"):
                    med_name += f" ({m['details']})"
                elif m.get("schema"):
                    med_name += f" ({m['schema']})"
                elif m.get("hinweis"):
                    med_name += f" ({m['hinweis']})"
                if med_name:
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
                elif isinstance(b.get('befund'), dict):
                    # Nested befund structure - extract key findings
                    befund_parts = []
                    for region, findings in b['befund'].items():
                        if isinstance(findings, str) and findings:
                            befund_parts.append(f"{region}: {findings}")
                        elif isinstance(findings, dict):
                            for key, val in findings.items():
                                if isinstance(val, str) and val:
                                    befund_parts.append(f"{region}/{key}: {val}")
                                elif isinstance(val, list) and val:
                                    befund_parts.append(f"{region}/{key}: {len(val)} Befunde")
                                elif isinstance(val, dict) and val:
                                    befund_parts.append(f"{region}/{key}: {json.dumps(val, ensure_ascii=False)[:100]}")
                    if befund_parts:
                        entry += f": {'; '.join(befund_parts[:8])}"
                bildgebung_parts.append(entry)
        bildgebung_str = "\n  - ".join(bildgebung_parts) if bildgebung_parts else "Keine"
    else:
        bildgebung_str = "Keine dokumentiert"

    # Format IMDC risk factors if available (handles multiple field naming conventions)
    imdc_rf = case.get("imdc_risikofaktoren", {})
    imdc_lab = case.get("imdc_laborwerte", {})
    imdc_parts = []
    if imdc_rf:
        # v1.1 original naming
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
        # v1.1 newer: imdc_addendum.imdc_parameters naming
        if not imdc_parts and imdc_rf.get("karnofsky_percent") is not None:
            imdc_parts.append(f"Karnofsky: {imdc_rf['karnofsky_percent']}%")
        # diagnosen format: English boolean keys
        if not imdc_parts:
            for key, label in [("kps_lt_80", "KPS<80"), ("hemoglobin_below_lln", "Hb↓"),
                               ("corrected_calcium_above_uln", "Ca↑"), ("neutrophils_above_uln", "Neutro↑"),
                               ("platelets_above_uln", "Thrombo↑")]:
                if key in imdc_rf:
                    imdc_parts.append(f"{label}: {'Ja' if imdc_rf[key] else 'Nein'}")
        # v1.0-new: faktoren with structured wert/ist_faktor
        if not imdc_parts:
            for key, label in [("karnofsky_lt_80", "KPS<80"), ("haemoglobin_unter_lln", "Hb↓"),
                               ("korr_calcium_ueber_uln", "Ca↑"), ("neutrophile_ueber_uln", "Neutro↑"),
                               ("thrombozyten_ueber_uln", "Thrombo↑")]:
                val = imdc_rf.get(key, {})
                if isinstance(val, dict) and "wert" in val:
                    ist = val.get("ist_faktor", False)
                    imdc_parts.append(f"{label}: {val['wert']} {val.get('einheit', '')} ({'Faktor' if ist else 'kein Faktor'})")
    # Also include lab values if available
    if imdc_lab and not imdc_parts:
        for key, label in [("karnofsky_percent", "Karnofsky"), ("hemoglobin_g_dl", "Hb"),
                           ("corrected_calcium_mmol_l", "Ca"), ("neutrophils_x10e9_l", "Neutro"),
                           ("platelets_x10e9_l", "Thrombo")]:
            if imdc_lab.get(key) is not None:
                imdc_parts.append(f"{label}: {imdc_lab[key]}")
    # Show IMDC category if known
    imdc_kat = case.get("imdc_kategorie")
    if imdc_kat:
        imdc_parts.insert(0, f"Kategorie: {imdc_kat}")
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


# ============================================================================
# Clinically Acceptable Therapies
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


def is_therapy_clinically_acceptable(prediction: TreatmentPrediction, ground_truth_metastatic: bool, ground_truth_imdc: str = None) -> bool:
    """Check if predicted therapy is clinically acceptable per guidelines."""

    if prediction is None:
        return False

    recommended = prediction.recommended_therapy.lower() if prediction.recommended_therapy else ""
    category = prediction.therapy_category.lower() if prediction.therapy_category else ""

    if ground_truth_metastatic:
        # Metastatic: check against valid systemic therapies
        all_valid = []
        risk = ground_truth_imdc or prediction.imdc_risk
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
# Modal App
# ============================================================================

app = modal.App("ncc-treatment-prediction")

vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch>=2.5.0", "transformers>=4.46.0", "accelerate>=0.34.0", "huggingface_hub>=0.26.0")
    .run_commands("pip install vllm --pre --extra-index-url https://wheels.vllm.ai/nightly")
    .run_commands("pip install flashinfer-python -i https://flashinfer.ai/whl/cu124/torch2.6/")
    .pip_install("torch-c-dlpack-ext", "pydantic>=2.0")
    .env({
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        "PYTHONHASHSEED": "42",
    })
)


@app.function(
    image=vllm_image,
    gpu="H100",
    timeout=1800,
    secrets=[modal.Secret.from_name("huggingface-secret-2")],
)
def run_prediction(model_key: str, cases: list, run_timestamp: str):
    """Run treatment prediction on Modal with vLLM."""
    import os
    import time
    from vllm import LLM, SamplingParams

    cfg = MODEL_CONFIGS[model_key]
    hf_id = cfg["hf_id"]
    is_thinking = cfg.get("thinking", False)
    is_multimodal = cfg.get("multimodal", False)

    # Batch invariance for determinism
    if not is_multimodal:
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
        print("Batch invariance: ENABLED")
    else:
        print("Batch invariance: DISABLED (multimodal)")

    # HuggingFace auth - explicit login like modal_classify.py
    import torch
    from huggingface_hub import login

    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print(f"HF_TOKEN: {hf_token[:8]}...{hf_token[-4:]}")
        login(token=hf_token)
    else:
        raise RuntimeError("HF_TOKEN not found!")

    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)

    print(f"Loading {hf_id}...")
    llm = LLM(
        model=hf_id,
        trust_remote_code=True,
        dtype="bfloat16",
        seed=42,
        max_model_len=32768,
        enforce_eager=True,
        disable_log_stats=True,
    )
    print("Model loaded!")

    # Build prompts
    prompts = [build_prompt(c) for c in cases]

    # Sampling params - use structured output for non-thinking models
    if is_thinking:
        # Thinking models: free-form generation, parse JSON manually
        # Need much higher max_tokens because <think> blocks consume many tokens
        params = SamplingParams(
            temperature=0.6,
            top_p=0.95,
            max_tokens=65536,  # Increased from 4096 - thinking needs room for reasoning + JSON
            seed=42,
        )
        print(f"Running inference on {len(cases)} NCC cases (free-form for thinking model)...")
    else:
        # Other models: use structured output for reliable JSON
        from vllm.sampling_params import StructuredOutputsParams
        json_schema = TreatmentPrediction.model_json_schema()
        structured = StructuredOutputsParams(json=json_schema)
        params = SamplingParams(
            temperature=0.3,  # Lower for structured output reliability
            top_p=0.95,
            max_tokens=32768,
            seed=42,
            structured_outputs=structured,
        )
        print(f"Running inference on {len(cases)} NCC cases (structured output)...")
    start = time.time()
    outputs = llm.generate(prompts, params)
    elapsed = time.time() - start

    results = []
    for case, output in zip(cases, outputs):
        text = output.outputs[0].text.strip()
        tokens = len(output.outputs[0].token_ids)

        # Parse response - structured output returns valid JSON directly
        prediction = None
        error_msg = None

        try:
            json_text = text

            # For thinking models, extract JSON from free-form output
            if is_thinking:
                if "</think>" in text:
                    json_text = text.split("</think>")[-1].strip()
                # Find JSON in the response
                json_match = re.search(r'\{[^{}]*"is_metastatic"[^{}]*\}', json_text, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\{[\s\S]*\}', json_text)
                if json_match:
                    json_text = json_match.group(0)

            # Parse JSON and validate with Pydantic
            prediction = TreatmentPrediction.model_validate_json(json_text)
        except Exception as e:
            error_msg = str(e)
            print(f"Warning: Pydantic validation failed for case {case['case_id']}: {e}")
            # Try more lenient parsing as fallback
            try:
                parsed = json.loads(json_text if not is_thinking else text)
                prediction = TreatmentPrediction(**parsed)
                error_msg = None  # Clear error if fallback works
            except:
                pass

        # Evaluate
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
            if gt_met is not None:
                met_correct = prediction.is_metastatic == gt_met

            if gt_therapy:
                # Exact match (fuzzy)
                pred_therapy = prediction.recommended_therapy.lower() if prediction.recommended_therapy else ""
                gt_therapy_lower = gt_therapy.lower()
                therapy_exact = (
                    pred_therapy in gt_therapy_lower or
                    gt_therapy_lower in pred_therapy or
                    any(word in gt_therapy_lower for word in pred_therapy.split() if len(word) > 4)
                )

            if gt_met is not None:
                therapy_acceptable = is_therapy_clinically_acceptable(prediction, gt_met, gt_imdc)

        result = {
            "case_id": case["case_id"],
            "timestamp": run_timestamp,
            "provider": "modal",
            "model": hf_id,
            "input_case": {
                "case_id": case["case_id"],
                "patient_name": case["patient_name"],
                "age": case.get("age"),
                "ecog": case.get("ecog"),
                "karnofsky": case.get("karnofsky"),
                "comorbidity": case.get("comorbidity"),
                "life_expectancy": case.get("life_expectancy"),
                "anamnese": case.get("anamnese", ""),  # Full anamnese, no truncation
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
            "prompt_text": prompts[cases.index(case)],
            "prediction": prediction.model_dump() if prediction else None,
            "raw_response": text,
            "ground_truth_metastatic": gt_met,
            "ground_truth_therapy": gt_therapy,
            "metastatic_correct": met_correct,
            "therapy_exact_match": therapy_exact,
            "therapy_clinically_acceptable": therapy_acceptable,
            "inference_time_seconds": elapsed / len(cases),
            "tokens_used": tokens,
            "success": prediction is not None,
            "error_message": error_msg,
        }
        results.append(result)

    # Summary stats
    met_correct_count = sum(1 for r in results if r["metastatic_correct"] == True)
    met_total = sum(1 for r in results if r["metastatic_correct"] is not None)
    exact_count = sum(1 for r in results if r["therapy_exact_match"] == True)
    acceptable_count = sum(1 for r in results if r["therapy_clinically_acceptable"] == True)

    summary = {
        "model": hf_id,
        "provider": "modal",
        "timestamp": run_timestamp,
        "total_cases": len(results),
        "metastatic_accuracy": met_correct_count / met_total if met_total > 0 else 0,
        "metastatic_correct": met_correct_count,
        "therapy_exact_match_rate": exact_count / len(results) if results else 0,
        "therapy_exact_matches": exact_count,
        "therapy_acceptable_rate": acceptable_count / len(results) if results else 0,
        "therapy_acceptable": acceptable_count,
        "total_time": elapsed,
        "errors": sum(1 for r in results if not r["success"]),
    }

    return {"results": results, "summary": summary}


# ============================================================================
# Local Entry Point
# ============================================================================

@app.local_entrypoint()
def main(model: str = "meditron3-7b", data_dir: str = "converted_data/send_23_12_25", start_case: int = 1, end_case: int = 0):
    """Run NCC treatment prediction.

    Args:
        model: Model key from MODEL_CONFIGS
        data_dir: Path to converted data directory
        start_case: 1-based case number to start from (skip earlier cases)
        end_case: 1-based case number to stop at (inclusive). 0 = no limit.
    """

    if model not in MODEL_CONFIGS:
        print(f"Unknown model: {model}")
        print(f"Available: {list(MODEL_CONFIGS.keys())}")
        return

    cfg = MODEL_CONFIGS[model]
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    print(f"\nNCC Treatment Prediction")
    print(f"Model: {model}")
    print(f"HuggingFace: {cfg['hf_id']}")
    print(f"Start case: {start_case}")
    print(f"End case: {end_case if end_case > 0 else 'all'}")
    print(f"Timestamp: {run_timestamp}")
    print("-" * 50)

    # Load cases
    cases = load_ncc_cases(data_dir, start_case=start_case, end_case=end_case)
    print(f"Loaded {len(cases)} NCC cases (cases {start_case}-{end_case if end_case > 0 else 'end'})")

    # Run prediction
    result = run_prediction.remote(model, cases, run_timestamp)

    # Save results
    base = Path(__file__).parent.parent
    model_slug = cfg["hf_id"].lower().replace("/", "_").replace(":", "_")
    out_dir = base / "results" / "modal_treatment" / model_slug / run_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    # Individual case files
    for r in result["results"]:
        case_file = out_dir / f"{r['case_id']}.json"
        with open(case_file, 'w', encoding='utf-8') as f:
            json.dump(r, f, indent=2, ensure_ascii=False, default=str)

    # Summary
    summary_file = out_dir / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(result["summary"], f, indent=2, ensure_ascii=False)

    # Print results
    s = result["summary"]
    print(f"\n{'='*50}")
    print(f"RESULTS: {model}")
    print(f"{'='*50}")
    print(f"Metastatic Classification: {s['metastatic_accuracy']*100:.1f}% ({s['metastatic_correct']}/{s['total_cases']})")
    print(f"Therapy Exact Match: {s['therapy_exact_match_rate']*100:.1f}% ({s['therapy_exact_matches']}/{s['total_cases']})")
    print(f"Therapy Clinically Acceptable: {s['therapy_acceptable_rate']*100:.1f}% ({s['therapy_acceptable']}/{s['total_cases']})")
    print(f"Time: {s['total_time']:.1f}s")
    print(f"Errors: {s['errors']}")
    print(f"\nSaved: {out_dir}")


if __name__ == "__main__":
    main()
