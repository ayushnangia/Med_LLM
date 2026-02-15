#!/usr/bin/env python3
"""Deep schema validation: compare extracted cases against v1.1 schema spec
and verify the inference script can read all fields it needs."""

import json
from pathlib import Path

BASE = Path(__file__).parent.parent
CASES_FILE = BASE / "converted_data" / "send_23_12_25" / "ncc" / "ncc_cases_json.json"
SCHEMA_FILE = BASE / "converted_data" / "send_23_12_25" / "case_structure_json_v_1_1.json"

def get_all_keys(obj, prefix=""):
    """Recursively get all keys from a dict/list structure."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.add(full)
            keys.update(get_all_keys(v, full))
    elif isinstance(obj, list) and obj:
        keys.update(get_all_keys(obj[0], prefix + "[]"))
    return keys

def detect_schema(case):
    """Detect which schema format a case uses.

    Returns one of: 'v1.0', 'v1.1', 'diagnosen', 'english'
    """
    if "case_template" in case and not case.get("patient", {}).get("nachname"):
        return "v1.0"
    if "diagnosen" in case:
        return "diagnosen"
    if "case" in case and isinstance(case.get("case"), dict):
        return "english"
    return "v1.1"


def check_inference_fields(case, case_num):
    """Check all fields that modal_treatment_predict.py actually reads.

    Handles 4 schema formats: v1.0, v1.1, diagnosen, english.
    """
    issues = []
    schema_type = detect_schema(case)

    if schema_type == "v1.0":
        template = case.get("case_template", {})
        patient = template.get("patient", {})
        entities = template.get("entitaeten", [{}])
        anamnese = template.get("anamnese_freitext", "") or case.get("anamnese_freitext", "")
        gt_therapy = template.get("geplantes_therapiekonzept") or case.get("geplantes_therapiekonzept")

    elif schema_type == "diagnosen":
        patient = case.get("patient", {})
        # diagnosen schema uses 'diagnosen' instead of 'entitaeten'
        diagnosen = case.get("diagnosen", [{}])
        # Build a pseudo-entity from the first diagnose for field checks
        diag = diagnosen[0] if diagnosen else {}
        entities = [{}]  # No standard entitaeten
        # No anamnese_freitext — clinical narrative is in tumor_history
        tumor_history = case.get("tumor_history", {})
        primary = tumor_history.get("primary_tumor", {})
        # Build anamnese from tumor_history
        anamnese_parts = []
        if primary.get("organ"):
            anamnese_parts.append(f"Organ: {primary['organ']}")
        if primary.get("seite"):
            anamnese_parts.append(f"Seite: {primary['seite']}")
        if primary.get("histologie"):
            anamnese_parts.append(f"Histologie: {primary['histologie']}")
        op = primary.get("op", {})
        if op.get("datum"):
            anamnese_parts.append(f"OP: {op.get('typ', '')} ({op.get('datum', '')})")
        path_staging = op.get("pathologie_staging", {})
        if path_staging:
            anamnese_parts.append(f"pTNM: pT{path_staging.get('pT','?')} pN{path_staging.get('pN','?')} cM{path_staging.get('cM','?')}")
        prior_tx = tumor_history.get("systemtherapien", [])
        for tx in prior_tx:
            anamnese_parts.append(f"Therapie Linie {tx.get('linie','?')}: {tx.get('regime','?')} ({tx.get('ergebnis','')})")
        anamnese = "; ".join(anamnese_parts) if anamnese_parts else ""
        # Ground truth from therapieplanung
        therapieplanung = case.get("therapieplanung", {})
        gt_parts = []
        for proc in therapieplanung.get("geplante_eingriffe", []):
            gt_parts.append(proc.get("beschreibung", ""))
        therapy_opts = therapieplanung.get("therapieoptionen", [])
        for opt in therapy_opts:
            gt_parts.append(opt.get("option", ""))
        gt_therapy = "; ".join(p for p in gt_parts if p) if gt_parts else None

    elif schema_type == "english":
        # English mRCC_case_schema — wrapped in 'case' key
        c = case.get("case", {})
        patient_en = c.get("patient", {})
        # Map English fields to German equivalents
        patient = {
            "nachname": patient_en.get("last_name"),
            "vorname": patient_en.get("first_name"),
            "alter_jahre": patient_en.get("age_years"),
            "ecog": patient_en.get("ecog"),
            "karnofsky_prozent": patient_en.get("karnofsky_percent"),
        }
        diag_en = c.get("diagnosis", {})
        staging = c.get("staging", {})
        entities = [{}]  # No standard entitaeten
        # Build anamnese from history
        history = c.get("history", {})
        anamnese_parts = []
        primary = history.get("primary_tumor", {})
        if primary:
            anamnese_parts.append(f"Primary: {primary.get('organ','')} {primary.get('histology','')}")
        for tx in history.get("prior_systemic_therapy", []):
            anamnese_parts.append(f"Line {tx.get('line','?')}: {tx.get('regimen','')} ({tx.get('reason_for_stop','')})")
        anamnese = "; ".join(anamnese_parts) if anamnese_parts else ""
        # Ground truth from plan
        plan = c.get("plan", {})
        gt_parts = []
        for opt in plan.get("therapy_options", []):
            gt_parts.append(opt.get("option", ""))
        gt_therapy = "; ".join(p for p in gt_parts if p) if gt_parts else None

    else:  # v1.1
        patient = case.get("patient", {})
        entities = case.get("entitaeten", [{}])
        anamnese = case.get("anamnese_freitext", "")
        gt_therapy = case.get("geplantes_therapiekonzept")

    entity = entities[0] if entities else {}

    # === Fields the inference script reads ===

    # 1. patient.nachname + vorname
    nachname = patient.get("nachname")
    vorname = patient.get("vorname")
    if not nachname:
        # For English schema, try the case.patient directly
        if schema_type == "english":
            c = case.get("case", {})
            nachname = c.get("patient", {}).get("last_name")
            vorname = c.get("patient", {}).get("first_name")
        if not nachname:
            issues.append("INFERENCE: no patient.nachname → can't build case_id")

    # 2. patient.alter_jahre
    age = patient.get("alter_jahre")
    if age is None:
        issues.append("INFERENCE: no patient.alter_jahre")

    # 3. ECOG
    ecog = patient.get("ecog") or patient.get("performance_status", {}).get("ecog")
    if ecog is None and schema_type == "diagnosen":
        ecog = case.get("patient", {}).get("ecog")
    if ecog is None:
        issues.append("DATA: no ecog")

    # 4. Karnofsky
    karnofsky = (patient.get("karnofsky_prozent")
                 or patient.get("karnofsky_percent")
                 or patient.get("performance_status", {}).get("karnofsky_prozent"))
    if karnofsky is None:
        for item in entity.get("marker_oder_labor", {}).get("sonstige", []):
            if item.get("parameter") == "Karnofsky":
                karnofsky = item.get("wert")
    if karnofsky is None:
        issues.append("DATA: no karnofsky")

    # 5. anamnese_freitext
    if not anamnese or len(str(anamnese).strip()) < 10:
        issues.append("CRITICAL: no/short anamnese_freitext → model gets no clinical narrative")

    # 6. diagnose_kurz
    diagnose_kurz = entity.get("diagnose_kurz")
    if not diagnose_kurz and schema_type == "diagnosen":
        diagnosen = case.get("diagnosen", [{}])
        diagnose_kurz = diagnosen[0].get("diagnose_kurz") if diagnosen else None
    if not diagnose_kurz and schema_type == "english":
        c = case.get("case", {})
        diagnose_kurz = c.get("diagnosis", {}).get("short_diagnosis")
    if not diagnose_kurz:
        issues.append("INFERENCE: no diagnose_kurz")

    # 7. stadium
    stadium = entity.get("stadium_oder_risikoklasse")
    if not stadium and schema_type == "diagnosen":
        diagnosen = case.get("diagnosen", [{}])
        if diagnosen:
            stadium = diagnosen[0].get("therapielinie")

    # 8. TNM
    klassifikation = entity.get("klassifikation", {})
    tnm_c = klassifikation.get("tnm_clinical")
    tnm_p = klassifikation.get("tnm_pathological")
    tnm_str = klassifikation.get("tnm") if isinstance(klassifikation.get("tnm"), str) else None
    if not tnm_c and not tnm_p and not tnm_str:
        if schema_type == "diagnosen":
            primary = case.get("tumor_history", {}).get("primary_tumor", {})
            path_staging = primary.get("op", {}).get("pathologie_staging", {})
            if path_staging.get("pT"):
                tnm_p = path_staging
        elif schema_type == "english":
            staging = case.get("case", {}).get("staging", {})
            if staging.get("clinical_tnm"):
                tnm_str = staging.get("clinical_tnm")

    # 9. metastatic status
    qa = entity.get("quick_access", {})
    metastatic = qa.get("metastatic") if qa else None
    if metastatic is None and qa:
        metastatic = qa.get("metastasiert")
    if metastatic is None and schema_type == "diagnosen":
        diagnosen = case.get("diagnosen", [{}])
        if diagnosen:
            met_field = diagnosen[0].get("therapienaiv_metastasiert")
            if met_field is not None:
                metastatic = met_field
    if metastatic is None and schema_type == "english":
        diag = case.get("case", {}).get("diagnosis", {})
        metastatic = diag.get("metastatic")

    # 10. rcc_spezifisch / histologie / imdc
    rcc = entity.get("rcc_spezifisch", {})
    histologie = rcc.get("histologie", {})
    imdc = rcc.get("imdc", {})
    if schema_type == "diagnosen" and not histologie.get("subtyp"):
        diagnosen = case.get("diagnosen", [{}])
        if diagnosen:
            histologie = {"subtyp": diagnosen[0].get("subtyp")}
            imdc = {"kategorie": diagnosen[0].get("imdc_risk_group")}

    # 11. bildgebung
    bildgebung = entity.get("bildgebung", [])
    if not bildgebung and schema_type == "diagnosen":
        bildgebung = case.get("bildgebung", [])
    if not bildgebung:
        issues.append("DATA: no bildgebung (imaging)")
    else:
        for j, img in enumerate(bildgebung):
            if not img.get("modalitaet") and not img.get("modality"):
                issues.append(f"DATA: bildgebung[{j}] missing modalitaet")
            if not img.get("befund_kurz") and not img.get("befund") and not img.get("findings"):
                issues.append(f"DATA: bildgebung[{j}] missing befund/befund_kurz")

    # 12. pathologie
    pathologie = entity.get("pathologie", [])

    # 13. therapien_und_eingriffe
    therapien = entity.get("therapien_und_eingriffe", [])
    if not therapien and schema_type == "diagnosen":
        therapien = case.get("tumor_history", {}).get("systemtherapien", [])

    # 14. ground truth therapy
    if not gt_therapy:
        issues.append("DATA: no geplantes_therapiekonzept (ground truth therapy)")

    return {
        "case_num": case_num,
        "name": f"{nachname}, {vorname}" if nachname else "UNNAMED",
        "schema": schema_type,
        "issues": issues,
        "fields": {
            "nachname": bool(nachname),
            "age": age,
            "ecog": ecog,
            "karnofsky": karnofsky,
            "anamnese_len": len(str(anamnese).strip()) if anamnese else 0,
            "diagnose_kurz": bool(diagnose_kurz),
            "stadium": stadium,
            "tnm": "clinical" if tnm_c else ("pathological" if tnm_p else ("string" if tnm_str else "NONE")),
            "metastatic": metastatic,
            "histologie": bool(histologie.get("subtyp")),
            "imdc": imdc.get("kategorie"),
            "bildgebung": len(bildgebung),
            "pathologie": len(pathologie),
            "therapien": len(therapien),
            "gt_therapy": bool(gt_therapy),
        }
    }


def check_v11_structure(case, case_num, schema_template):
    """Check that a v1.1 case has the same structural keys as the schema."""
    issues = []

    # Top-level keys
    schema_keys = set(schema_template.keys())
    case_keys = set(case.keys())

    # Expected at case level for v1.1 (not wrapped in case_template)
    expected_top = {"patient", "entitaeten", "anamnese_freitext", "geplantes_therapiekonzept"}
    # Some v1.1 cases have case_meta at top level, some have it inside

    # Check entity structure
    entities = case.get("entitaeten", [])
    if not entities:
        issues.append("STRUCTURE: empty entitaeten array")
        return issues

    entity = entities[0]
    schema_entity = schema_template.get("entitaeten", [{}])[0] if schema_template.get("entitaeten") else {}

    # Key entity fields that must exist
    required_entity_keys = ["klassifikation", "bildgebung", "pathologie", "therapien_und_eingriffe"]
    for key in required_entity_keys:
        if key not in entity:
            issues.append(f"STRUCTURE: entity missing '{key}' (present in schema)")

    # Check klassifikation sub-keys
    schema_klass = schema_entity.get("klassifikation", {})
    case_klass = entity.get("klassifikation", {})
    for key in schema_klass:
        if key not in case_klass:
            pass  # Not all cases need all TNM fields

    return issues


def main():
    with open(CASES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    schema_template = schema["cases"][0].get("case_template", {})
    cases = data.get("cases", [])

    print(f"Validating {len(cases)} cases against schema v1.1")
    print(f"Checking all fields read by modal_treatment_predict.py")
    print("=" * 80)

    all_results = []
    critical_count = 0
    runnable_cases = []

    for i, case in enumerate(cases, 1):
        result = check_inference_fields(case, i)
        all_results.append(result)

        # Check structure (only for v1.1 — other schemas have different structures)
        if result["schema"] == "v1.1":
            struct_issues = check_v11_structure(case, i, schema_template)
            result["issues"].extend(struct_issues)

        critical = any("CRITICAL" in iss for iss in result["issues"])
        inference_broken = any("INFERENCE" in iss for iss in result["issues"])

        f = result["fields"]
        status = "SKIP" if critical else ("WARN" if result["issues"] else "OK")

        if critical:
            critical_count += 1

        marker = "X" if critical else ("!" if result["issues"] else " ")
        print(f"[{marker}] Case {i:2d} {result['name']:30s} {result['schema']} | "
              f"ecog={str(f['ecog']):>4s} karn={str(f['karnofsky']):>4s} "
              f"tnm={f['tnm']:12s} met={str(f['metastatic']):>5s} "
              f"img={f['bildgebung']} pat={f['pathologie']} tx={f['therapien']} "
              f"anam={f['anamnese_len']:>4d} gt={'Y' if f['gt_therapy'] else 'N'}"
              f"{'  ← ' + ', '.join(result['issues']) if result['issues'] else ''}")

        if not critical and f["gt_therapy"]:
            runnable_cases.append(i)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(cases)
    ok = sum(1 for r in all_results if not r["issues"])
    warn = sum(1 for r in all_results if r["issues"] and not any("CRITICAL" in i for i in r["issues"]))
    skip = critical_count
    no_gt = sum(1 for r in all_results if not r["fields"]["gt_therapy"])

    # Schema breakdown
    from collections import Counter
    schema_counts = Counter(r["schema"] for r in all_results)

    print(f"Total cases:     {total}")
    print(f"Schema breakdown: {dict(schema_counts)}")
    print(f"Clean (no issues): {ok}")
    print(f"Warnings:        {warn}")
    print(f"Critical (skip): {skip}")
    print(f"No ground truth: {no_gt}")
    print(f"\nRunnable for inference (has anamnese + ground truth): {len(runnable_cases)}")
    print(f"  Already done (1-35): {len([c for c in runnable_cases if c <= 35])}")
    print(f"  NEW to run (36+):    {len([c for c in runnable_cases if c > 35])}")
    print(f"  New case numbers: {[c for c in runnable_cases if c > 35]}")


if __name__ == "__main__":
    main()
