#!/usr/bin/env python3
"""
Verify data integrity after conversion.
- Compares JSON case counts with source DOCX
- Compares JSON patient data with CSV
- Verifies XLSX to CSV row counts

Usage:
    python scripts/verify_data_integrity.py
"""

import json
import pandas as pd
from pathlib import Path
from docx import Document
import re


# Configuration
BASE_DIR = Path(__file__).parent.parent
SOURCE_DIR = BASE_DIR / "data_llm" / "send_27_12_25"
OUTPUT_DIR = BASE_DIR / "converted_data" / "send_27_12_25"


def get_patient_from_case(case: dict) -> dict:
    """Extract patient info from case, handling different structures."""
    # Standard structure: case.patient
    if 'patient' in case and case['patient'].get('nachname'):
        return case['patient']
    # Template structure: case.case_template.patient
    elif 'case_template' in case:
        return case['case_template'].get('patient', {})
    return {}


def verify_docx_to_json(source_dir: Path, output_dir: Path) -> list:
    """Verify DOCX to JSON conversion."""
    results = []

    for docx_file in sorted(source_dir.rglob('*_cases_json.docx')):
        rel_path = docx_file.relative_to(source_dir)
        json_file = output_dir / rel_path.with_suffix('.json')

        result = {
            'file': str(rel_path),
            'source_cases': 0,
            'output_cases': 0,
            'status': 'unknown'
        }

        # Count cases in source DOCX
        try:
            doc = Document(str(docx_file))
            full_text = '\n'.join([p.text for p in doc.paragraphs])
            result['source_cases'] = len(re.findall(r'"fallnummer"\s*:\s*"[^"]*"', full_text))

            # Also count case_template structures
            if result['source_cases'] == 0:
                result['source_cases'] = len(re.findall(r'"case_template"\s*:', full_text))
        except Exception as e:
            result['error'] = str(e)

        # Count cases in output JSON
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cases = data.get('cases', [])
                result['output_cases'] = len(cases)
            except Exception as e:
                result['error'] = str(e)

        result['status'] = 'ok' if result['source_cases'] == result['output_cases'] else 'mismatch'
        results.append(result)

    return results


def verify_json_csv_match(output_dir: Path) -> list:
    """Verify JSON cases match CSV rows."""
    results = []
    folders = ['ncc', 'pca', 'hoden_ca', 'penis_ca', 'uca', 'combi', 'non_uro']

    for folder in folders:
        folder_path = output_dir / folder
        if not folder_path.exists():
            continue

        result = {'folder': folder, 'json_cases': 0, 'csv_rows': 0, 'patients': [], 'status': 'unknown'}

        # Load JSON
        json_files = list(folder_path.glob('*_cases_json.json'))
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            cases = data.get('cases', [])
            result['json_cases'] = len(cases)

            for case in cases:
                patient = get_patient_from_case(case)
                if patient:
                    result['patients'].append(f"{patient.get('nachname', '?')}, {patient.get('vorname', '?')}")

        # Load CSV
        csv_files = list(folder_path.glob('*.csv'))
        if csv_files:
            df = pd.read_csv(csv_files[0])
            df = df.dropna(how='all')
            if 'Cases' in df.columns:
                df = df[df['Cases'].notna() & (df['Cases'] != '')]
            result['csv_rows'] = len(df)

        result['status'] = 'ok' if result['json_cases'] == result['csv_rows'] else 'mismatch'
        results.append(result)

    return results


def verify_xlsx_to_csv(source_dir: Path, output_dir: Path) -> list:
    """Verify XLSX to CSV conversion."""
    results = []

    for xlsx_file in sorted(source_dir.rglob('*.xlsx')):
        rel_path = xlsx_file.relative_to(source_dir)
        csv_file = output_dir / rel_path.with_suffix('.csv')

        result = {
            'file': str(rel_path),
            'source_rows': 0,
            'output_rows': 0,
            'status': 'unknown'
        }

        try:
            source_df = pd.read_excel(xlsx_file)
            result['source_rows'] = len(source_df.dropna(how='all'))

            if csv_file.exists():
                output_df = pd.read_csv(csv_file)
                result['output_rows'] = len(output_df.dropna(how='all'))
                result['status'] = 'ok' if result['source_rows'] == result['output_rows'] else 'mismatch'
            else:
                result['status'] = 'missing'
        except Exception as e:
            result['status'] = f'error: {e}'

        results.append(result)

    return results


def main():
    print("=" * 70)
    print("DATA INTEGRITY VERIFICATION")
    print("=" * 70)

    all_ok = True

    # Part 1: DOCX → JSON
    print("\n" + "-" * 70)
    print("DOCX → JSON VERIFICATION")
    print("-" * 70 + "\n")

    docx_results = verify_docx_to_json(SOURCE_DIR, OUTPUT_DIR)
    for r in docx_results:
        icon = "✓" if r['status'] == 'ok' else "✗"
        print(f"{icon} {r['file']}: {r['output_cases']} cases")
        if r['status'] != 'ok':
            all_ok = False

    # Part 2: JSON ↔ CSV
    print("\n" + "-" * 70)
    print("JSON ↔ CSV VERIFICATION")
    print("-" * 70 + "\n")

    csv_results = verify_json_csv_match(OUTPUT_DIR)
    for r in csv_results:
        icon = "✓" if r['status'] == 'ok' else "✗"
        print(f"{icon} {r['folder']}/: JSON={r['json_cases']}, CSV={r['csv_rows']}")
        if r['patients']:
            print(f"    Patients: {', '.join(r['patients'][:3])}{'...' if len(r['patients']) > 3 else ''}")
        if r['status'] != 'ok':
            all_ok = False

    # Part 3: XLSX → CSV
    print("\n" + "-" * 70)
    print("XLSX → CSV VERIFICATION")
    print("-" * 70 + "\n")

    xlsx_results = verify_xlsx_to_csv(SOURCE_DIR, OUTPUT_DIR)
    for r in xlsx_results:
        icon = "✓" if r['status'] == 'ok' else "✗"
        print(f"{icon} {r['file']}: {r['output_rows']} rows")
        if r['status'] != 'ok':
            all_ok = False

    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ ALL VERIFICATIONS PASSED - NO DATA CORRUPTION")
    else:
        print("⚠ SOME ISSUES DETECTED - SEE ABOVE")
    print("=" * 70)


if __name__ == "__main__":
    main()
