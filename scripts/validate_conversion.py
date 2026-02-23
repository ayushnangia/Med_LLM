#!/usr/bin/env python3
"""Validate converted NCC JSON data for schema consistency and completeness."""

import json
import sys
from pathlib import Path

NCC_JSON = Path(__file__).parent.parent / "converted_data" / "send_23_12_25" / "ncc" / "ncc_cases_json.json"

def validate():
    with open(NCC_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = data.get("cases", [])
    print(f"Total cases: {len(cases)}")
    print(f"Schema version: {data.get('schema_version')}")
    print("=" * 70)

    issues = []
    schema_v10_count = 0
    schema_v11_count = 0

    for i, case in enumerate(cases, 1):
        case_issues = []
        case_label = f"Case {i}"

        # Detect schema version
        is_v10 = "case_template" in case and not case.get("patient", {}).get("nachname")
        if is_v10:
            schema_v10_count += 1
            template = case.get("case_template", {})
            patient = template.get("patient", {})
            entities = template.get("entitaeten", [{}])
            anamnese = template.get("anamnese_freitext", "") or case.get("anamnese_freitext", "")
            gt_therapy = template.get("geplantes_therapiekonzept") or case.get("geplantes_therapiekonzept")
            nebendiagnosen = template.get("nebendiagnosen", []) or case.get("nebendiagnosen", [])
            medikation = template.get("medikation", []) or case.get("medikation", [])
        else:
            schema_v11_count += 1
            patient = case.get("patient", {})
            entities = case.get("entitaeten", [{}])
            anamnese = case.get("anamnese_freitext", "")
            gt_therapy = case.get("geplantes_therapiekonzept")
            nebendiagnosen = case.get("nebendiagnosen", [])
            medikation = case.get("medikation", [])

        entity = entities[0] if entities else {}

        # Patient name
        nachname = patient.get("nachname")
        vorname = patient.get("vorname")
        if not nachname:
            case_issues.append("MISSING nachname")
        else:
            case_label = f"Case {i} ({nachname}, {vorname})"

        # Age
        age = patient.get("alter_jahre")
        if age is None:
            case_issues.append("MISSING alter_jahre")

        # ECOG / Karnofsky (handle both schemas)
        ecog = patient.get("ecog") or patient.get("performance_status", {}).get("ecog")
        karnofsky = patient.get("karnofsky_prozent") or patient.get("performance_status", {}).get("karnofsky_prozent")
        if karnofsky is None:
            for item in entity.get("marker_oder_labor", {}).get("sonstige", []):
                if item.get("parameter") == "Karnofsky":
                    karnofsky = item.get("wert")
        if ecog is None:
            case_issues.append("MISSING ecog")
        if karnofsky is None:
            case_issues.append("MISSING karnofsky")

        # Anamnese
        if not anamnese or len(str(anamnese).strip()) < 10:
            case_issues.append(f"MISSING/SHORT anamnese ({len(str(anamnese).strip())} chars)")

        # Entity / diagnosis
        if not entities or len(entities) == 0:
            case_issues.append("MISSING entitaeten")
        else:
            klassifikation = entity.get("klassifikation", {})
            # TNM - check all variants
            tnm_clinical = klassifikation.get("tnm_clinical") or klassifikation.get("ctnm")
            tnm_pathological = klassifikation.get("tnm_pathological") or klassifikation.get("ptnm")
            tnm_string = klassifikation.get("tnm") if isinstance(klassifikation.get("tnm"), str) else None
            if not tnm_clinical and not tnm_pathological and not tnm_string:
                case_issues.append("MISSING TNM staging (no clinical, pathological, or string)")

            # Diagnose
            diagnose = klassifikation.get("diagnose_freitext") or klassifikation.get("entitaet_typ")
            if not diagnose:
                case_issues.append("MISSING diagnose")

        # Imaging (bildgebung)
        bildgebung = entity.get("bildgebung", [])
        if not bildgebung or len(bildgebung) == 0:
            case_issues.append("MISSING bildgebung (imaging)")
        else:
            for j, img in enumerate(bildgebung):
                if not img.get("modalitaet") and not img.get("typ"):
                    case_issues.append(f"  bildgebung[{j}]: MISSING modalitaet")
                if not img.get("befund_kurz") and not img.get("befund"):
                    case_issues.append(f"  bildgebung[{j}]: MISSING befund")

        # Pathologie
        pathologie = entity.get("pathologie", [])
        # Not all cases need pathology, but flag if truly empty for metastatic cases

        # Therapien (prior therapies)
        therapien = entity.get("therapien_und_eingriffe", [])

        # Ground truth therapy
        if not gt_therapy:
            case_issues.append("MISSING geplantes_therapiekonzept (ground truth)")
        elif isinstance(gt_therapy, str) and len(gt_therapy.strip()) < 5:
            case_issues.append(f"SHORT geplantes_therapiekonzept: '{gt_therapy}'")

        # Metastatic status - check quick_access
        qa = entity.get("quick_access", {})
        metastatic = qa.get("metastasiert")

        # RCC specific
        rcc = entity.get("rcc_spezifisch", {})
        histologie = rcc.get("histologie", {})
        imdc = rcc.get("imdc", {})

        # Print case summary
        schema = "v1.0" if is_v10 else "v1.1"
        status = "OK" if not case_issues else f"{len(case_issues)} ISSUES"
        met_str = "met" if metastatic else "non-met" if metastatic is False else "unknown"
        therapy_str = "yes" if gt_therapy else "NO"
        img_str = str(len(bildgebung))
        patho_str = str(len(pathologie))
        tx_str = str(len(therapien))

        if case_issues:
            print(f"\n[{status}] {case_label} (schema {schema}, {met_str})")
            print(f"  therapy={therapy_str} img={img_str} patho={patho_str} prior_tx={tx_str}")
            for issue in case_issues:
                print(f"  ! {issue}")
            issues.extend([(case_label, iss) for iss in case_issues])
        else:
            print(f"[OK] {case_label} (schema {schema}, {met_str}) therapy={therapy_str} img={img_str} patho={patho_str} prior_tx={tx_str}")

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total cases: {len(cases)}")
    print(f"Schema v1.0 (case_template): {schema_v10_count}")
    print(f"Schema v1.1 (standard): {schema_v11_count}")
    print(f"Total issues: {len(issues)}")

    if issues:
        # Group by issue type
        from collections import Counter
        issue_types = Counter(iss for _, iss in issues)
        print("\nIssue breakdown:")
        for issue_type, count in issue_types.most_common():
            print(f"  {count}x {issue_type}")

    return len(issues)

if __name__ == "__main__":
    sys.exit(0 if validate() == 0 else 1)
