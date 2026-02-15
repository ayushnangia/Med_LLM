#!/usr/bin/env python3
"""
Enrich cases.json with detailed clinical data from the source NCC cases.
Handles both v1.0 and v1.1 schema formats.
"""

import json
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
SOURCE_DATA = Path("/Users/fortuna/Desktop/Colab/Med_LLM/converted_data/send_27_12_25/ncc/ncc_cases_json.json")
CASES_JSON = PROJECT_DIR / "src" / "data" / "cases.json"

def load_json(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: dict, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_case(raw_case: dict) -> dict:
    """
    Normalize case data from both v1.0 and v1.1 schemas to a common format.
    v1.0: data is wrapped in 'case_template'
    v1.1: data is at top level
    """
    if 'case_template' in raw_case:
        # v1.0 schema - unwrap from case_template
        return raw_case['case_template']
    else:
        # v1.1 schema - already at top level
        return raw_case

def extract_patient_name(case_data: dict) -> str:
    """Extract patient name in 'Nachname, Vorname' format."""
    normalized = normalize_case(case_data)
    patient = normalized.get('patient', {})
    nachname = patient.get('nachname', '')
    vorname = patient.get('vorname', '')
    return f"{nachname}, {vorname}"

def find_source_case(source_cases: list, target_name: str) -> dict | None:
    """Find matching source case by patient name."""
    for case in source_cases:
        name = extract_patient_name(case)
        if name == target_name:
            return case
    return None

def extract_clinical_context(raw_case: dict) -> dict:
    """Extract clinical context from source case (handles both schemas)."""
    case_data = normalize_case(raw_case)
    context = {}

    # Anamnese (medical history)
    if case_data.get('anamnese_freitext'):
        context['anamnese_freitext'] = case_data['anamnese_freitext']

    # Clinical question
    if case_data.get('fragestellung'):
        context['fragestellung'] = case_data['fragestellung']

    # Secondary diagnoses
    if case_data.get('nebendiagnosen'):
        context['nebendiagnosen'] = case_data['nebendiagnosen']

    # Medications
    if case_data.get('medikation'):
        context['medikation'] = case_data['medikation']

    # Get data from entities
    entities = case_data.get('entitaeten', [])
    if entities:
        entity = entities[0]  # Primary entity

        # Imaging
        if entity.get('bildgebung'):
            context['bildgebung'] = entity['bildgebung']

        # Pathology
        if entity.get('pathologie'):
            context['pathologie'] = entity['pathologie']

        # Prior therapies
        if entity.get('therapien_und_eingriffe'):
            context['therapien_und_eingriffe'] = entity['therapien_und_eingriffe']

    return context

def extract_diagnosis_details(raw_case: dict) -> dict:
    """Extract additional diagnosis details (handles both schemas)."""
    case_data = normalize_case(raw_case)
    details = {}

    entities = case_data.get('entitaeten', [])
    if not entities:
        return details

    entity = entities[0]
    klassifikation = entity.get('klassifikation', {})

    # TNM staging - handle both v1.0 (single 'tnm' string) and v1.1 (separate objects)
    if klassifikation.get('tnm_clinical'):
        details['tnm_clinical'] = klassifikation['tnm_clinical']

    if klassifikation.get('tnm_pathological'):
        details['tnm_pathological'] = klassifikation['tnm_pathological']

    # v1.0 might have single 'tnm' field
    if klassifikation.get('tnm') and 'tnm_clinical' not in details:
        tnm_str = klassifikation['tnm']
        details['tnm_string'] = tnm_str

    # Grading
    if klassifikation.get('grad'):
        details['grading'] = klassifikation['grad']

    # IMDC risk (for metastatic RCC)
    rcc_specific = entity.get('rcc_spezifisch', {})
    imdc = rcc_specific.get('imdc', {})
    if imdc.get('kategorie'):
        details['imdc_risiko'] = imdc['kategorie']

    # Quick access fields
    quick_access = entity.get('quick_access', {})
    if quick_access.get('imdc_risiko'):
        details['imdc_risiko'] = quick_access['imdc_risiko']

    return details

def extract_patient_details(raw_case: dict) -> dict:
    """Extract additional patient details (handles both schemas)."""
    case_data = normalize_case(raw_case)
    details = {}
    patient = case_data.get('patient', {})

    # Life expectancy
    if patient.get('lebenserwartung'):
        details['life_expectancy'] = patient['lebenserwartung']

    # Karnofsky from v1.0 format (in marker_oder_labor.sonstige)
    entities = case_data.get('entitaeten', [])
    if entities:
        entity = entities[0]
        marker = entity.get('marker_oder_labor', {})
        sonstige = marker.get('sonstige', [])
        for item in sonstige:
            if item.get('parameter') == 'Karnofsky':
                details['karnofsky_from_labor'] = item.get('wert')

    return details

def enrich_cases():
    """Main function to enrich cases with clinical data."""
    print(f"Loading source data from: {SOURCE_DATA}")
    source_data = load_json(SOURCE_DATA)
    source_cases = source_data.get('cases', [])
    print(f"Found {len(source_cases)} source cases")

    print(f"Loading cases.json from: {CASES_JSON}")
    cases_data = load_json(CASES_JSON)
    cases = cases_data.get('cases', [])
    print(f"Found {len(cases)} cases to enrich")

    enriched_count = 0

    for case in cases:
        patient_name = case['patient']['name']
        source_case = find_source_case(source_cases, patient_name)

        if source_case:
            # Add clinical context
            clinical_context = extract_clinical_context(source_case)
            if clinical_context:
                case['clinical_context'] = clinical_context

            # Enrich diagnosis with TNM details
            diagnosis_details = extract_diagnosis_details(source_case)
            case['diagnosis'].update(diagnosis_details)

            # Enrich patient details
            patient_details = extract_patient_details(source_case)
            case['patient'].update(patient_details)

            enriched_count += 1
            print(f"  Enriched: {case['case_id']} ({patient_name})")
        else:
            print(f"  WARNING: No source case found for: {patient_name}")

    print(f"\nEnriched {enriched_count}/{len(cases)} cases")

    # Save enriched data
    save_json(cases_data, CASES_JSON)
    print(f"Saved enriched data to: {CASES_JSON}")

if __name__ == '__main__':
    enrich_cases()
