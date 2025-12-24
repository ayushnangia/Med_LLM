#!/usr/bin/env python3
"""
Run classification on all medical cases using Ollama.

Usage:
    python scripts/classify_cases.py --model qwen3:latest
    python scripts/classify_cases.py --model qwen3:latest --output findings/run_001

Output:
    findings/results_{model}_{timestamp}.json
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from inference_ollama import OllamaClassifier, get_available_models


# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "converted_data" / "send_23_12_25"
FINDINGS_DIR = BASE_DIR / "findings"

# Ground truth mapping (folder name -> class)
FOLDER_TO_CLASS = {
    "ncc": "nierenzellkarzinom",
    "pca": "prostatakarzinom",
    "hoden_ca": "hodentumor",
    "penis_ca": "peniskarzinom",
    "uca": "urothelkarzinom",
    "combi": "polymalignancy",
    "non_uro": "non_urological"
}


def load_all_cases() -> list:
    """Load all cases with ground truth labels."""
    all_cases = []

    for folder, ground_truth in FOLDER_TO_CLASS.items():
        folder_path = DATA_DIR / folder
        if not folder_path.exists():
            continue

        json_files = list(folder_path.glob("*_cases_json.json"))
        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cases = data.get('cases', [])
            for i, case in enumerate(cases):
                # Get patient name for identification
                patient = case.get('patient', {})
                if not patient.get('nachname') and 'case_template' in case:
                    patient = case.get('case_template', {}).get('patient', {})

                case_id = f"{folder}_{i+1}"
                patient_name = f"{patient.get('nachname', 'Unknown')}, {patient.get('vorname', '')}"

                all_cases.append({
                    "case_id": case_id,
                    "patient_name": patient_name,
                    "ground_truth": ground_truth,
                    "folder": folder,
                    "case_data": case
                })

    return all_cases


def run_classification(model: str, output_dir: Path = None) -> dict:
    """Run classification on all cases."""
    # Setup
    classifier = OllamaClassifier(model=model)

    if not classifier.check_connection():
        print(f"ERROR: Cannot connect to Ollama or model '{model}' not available")
        print(f"Available models: {get_available_models()}")
        return None

    # Load cases
    cases = load_all_cases()
    print(f"Loaded {len(cases)} cases")

    # Run classification
    results = {
        "metadata": {
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(cases)
        },
        "predictions": [],
        "summary": {
            "correct": 0,
            "incorrect": 0,
            "errors": 0
        }
    }

    print(f"\nRunning classification with {model}...")
    print("-" * 60)

    for i, case_info in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] {case_info['case_id']}: {case_info['patient_name'][:30]}...", end=" ")

        result = classifier.classify(case_info['case_data'])

        prediction = {
            "case_id": case_info['case_id'],
            "patient_name": case_info['patient_name'],
            "ground_truth": case_info['ground_truth'],
            "predicted": result['classification'],
            "correct": result['classification'] == case_info['ground_truth'],
            "inference_time": result['inference_time'],
            "raw_response": result['raw_response'],
            "success": result['success']
        }

        results['predictions'].append(prediction)

        if not result['success']:
            results['summary']['errors'] += 1
            print(f"ERROR")
        elif prediction['correct']:
            results['summary']['correct'] += 1
            print(f"CORRECT ({result['inference_time']:.2f}s)")
        else:
            results['summary']['incorrect'] += 1
            print(f"WRONG: {result['classification']} (expected {case_info['ground_truth']}) ({result['inference_time']:.2f}s)")

    # Calculate accuracy
    total_valid = results['summary']['correct'] + results['summary']['incorrect']
    if total_valid > 0:
        results['summary']['accuracy'] = results['summary']['correct'] / total_valid
    else:
        results['summary']['accuracy'] = 0.0

    # Save results
    if output_dir is None:
        output_dir = FINDINGS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe = model.replace(":", "_").replace("/", "_")
    output_file = output_dir / f"results_{model_safe}_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"RESULTS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Model: {model}")
    print(f"Total cases: {len(cases)}")
    print(f"Correct: {results['summary']['correct']}")
    print(f"Incorrect: {results['summary']['incorrect']}")
    print(f"Errors: {results['summary']['errors']}")
    print(f"Accuracy: {results['summary']['accuracy']:.2%}")
    print(f"\nResults saved to: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Classify medical cases using Ollama")
    parser.add_argument("--model", type=str, default="qwen3:latest",
                        help="Ollama model to use")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for results")
    parser.add_argument("--list-models", action="store_true",
                        help="List available models and exit")

    args = parser.parse_args()

    if args.list_models:
        models = get_available_models()
        print("Available Ollama models:")
        for m in models:
            print(f"  - {m}")
        return

    output_dir = Path(args.output) if args.output else None
    run_classification(args.model, output_dir)


if __name__ == "__main__":
    main()
