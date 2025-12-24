#!/usr/bin/env python3
"""
Run classification on medical cases using OpenRouter API.

Usage:
    # Set API key first
    export OPENROUTER_API_KEY="your-key-here"

    # Run classification
    python scripts/classify_openrouter.py --model gemma3:27b
    python scripts/classify_openrouter.py --model google/gemma-3-27b-it

    # List available models
    python scripts/classify_openrouter.py --list-models

Output Structure:
    results/
    └── openrouter/
        └── gemma-3-27b-it/
            └── 2025-12-24_12-30-45/
                ├── config.json          # Model configuration
                ├── predictions.json     # All predictions
                ├── summary.json         # Summary statistics
                └── run.log              # Detailed log
"""

import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from inference_openrouter import OpenRouterClassifier, get_openrouter_models


# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "converted_data" / "send_23_12_25"
RESULTS_DIR = BASE_DIR / "results"

# Ground truth mapping
FOLDER_TO_CLASS = {
    "ncc": "nierenzellkarzinom",
    "pca": "prostatakarzinom",
    "hoden_ca": "hodentumor",
    "penis_ca": "peniskarzinom",
    "uca": "urothelkarzinom",
    "combi": "polymalignancy",
    "non_uro": "non_urological"
}


def setup_run_directory(model_id: str) -> Path:
    """Create timestamped run directory for results."""
    # Sanitize model name for folder
    model_safe = model_id.replace("/", "_").replace(":", "_")

    # Create directory structure
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = RESULTS_DIR / "openrouter" / model_safe / timestamp

    run_dir.mkdir(parents=True, exist_ok=True)

    return run_dir


def setup_logging(run_dir: Path) -> logging.Logger:
    """Setup logging to both file and console."""
    logger = logging.getLogger("classify_openrouter")
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers = []

    # File handler
    fh = logging.FileHandler(run_dir / "run.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


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


def run_classification(model: str, temperature: float = 0.1) -> dict:
    """Run classification on all cases and save results."""

    # Initialize classifier
    try:
        classifier = OpenRouterClassifier(
            model=model,
            temperature=temperature
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        print("Set your API key: export OPENROUTER_API_KEY='your-key'")
        return None

    # Setup run directory
    run_dir = setup_run_directory(classifier.model)
    logger = setup_logging(run_dir)

    logger.info(f"OpenRouter Classification Run")
    logger.info(f"=" * 60)
    logger.info(f"Model: {classifier.model}")
    logger.info(f"Run directory: {run_dir}")

    # Save configuration
    config = classifier.get_config()
    config["run_timestamp"] = datetime.now().isoformat()
    config["run_directory"] = str(run_dir)

    with open(run_dir / "config.json", 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    logger.info(f"Configuration saved to config.json")

    # Check connection
    if not classifier.check_connection():
        logger.error("Cannot connect to OpenRouter API")
        return None

    logger.info("OpenRouter connection: OK")

    # Load cases
    cases = load_all_cases()
    logger.info(f"Loaded {len(cases)} cases")

    # Run classification
    results = {
        "metadata": {
            "provider": "openrouter",
            "model": classifier.model,
            "model_input": model,
            "temperature": temperature,
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

    logger.info(f"\nRunning classification...")
    logger.info("-" * 60)

    for i, case_info in enumerate(cases):
        logger.info(f"[{i+1}/{len(cases)}] {case_info['case_id']}: {case_info['patient_name'][:30]}...")

        result = classifier.classify(case_info['case_data'])

        prediction = {
            "case_id": case_info['case_id'],
            "patient_name": case_info['patient_name'],
            "ground_truth": case_info['ground_truth'],
            "predicted": result['classification'],
            "correct": result['classification'] == case_info['ground_truth'],
            "inference_time": result['inference_time'],
            "tokens_used": result.get('tokens_used', 0),
            "raw_response": result['raw_response'],
            "success": result['success']
        }

        results['predictions'].append(prediction)

        # Log result
        if not result['success']:
            results['summary']['errors'] += 1
            logger.info(f"  -> ERROR: {result['raw_response'][:50]}")
        elif prediction['correct']:
            results['summary']['correct'] += 1
            logger.info(f"  -> CORRECT ({result['inference_time']:.2f}s)")
        else:
            results['summary']['incorrect'] += 1
            logger.info(f"  -> WRONG: {result['classification']} (expected {case_info['ground_truth']}) ({result['inference_time']:.2f}s)")

    # Calculate accuracy
    total_valid = results['summary']['correct'] + results['summary']['incorrect']
    if total_valid > 0:
        results['summary']['accuracy'] = results['summary']['correct'] / total_valid
    else:
        results['summary']['accuracy'] = 0.0

    results['summary']['total_tokens'] = classifier.total_tokens

    # Calculate average inference time
    times = [p['inference_time'] for p in results['predictions'] if p['success']]
    results['summary']['avg_inference_time'] = sum(times) / len(times) if times else 0

    # Save predictions
    with open(run_dir / "predictions.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Save summary
    summary = {
        "model": classifier.model,
        "timestamp": results['metadata']['timestamp'],
        "total_cases": len(cases),
        "correct": results['summary']['correct'],
        "incorrect": results['summary']['incorrect'],
        "errors": results['summary']['errors'],
        "accuracy": results['summary']['accuracy'],
        "total_tokens": results['summary']['total_tokens'],
        "avg_inference_time": results['summary']['avg_inference_time']
    }

    with open(run_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    logger.info(f"\n{'=' * 60}")
    logger.info(f"RESULTS SUMMARY")
    logger.info(f"{'=' * 60}")
    logger.info(f"Model: {classifier.model}")
    logger.info(f"Total cases: {len(cases)}")
    logger.info(f"Correct: {results['summary']['correct']}")
    logger.info(f"Incorrect: {results['summary']['incorrect']}")
    logger.info(f"Errors: {results['summary']['errors']}")
    logger.info(f"Accuracy: {results['summary']['accuracy']:.2%}")
    logger.info(f"Total tokens: {results['summary']['total_tokens']}")
    logger.info(f"Avg time/case: {results['summary']['avg_inference_time']:.2f}s")
    logger.info(f"\nResults saved to: {run_dir}")

    # Also copy to findings for compatibility
    findings_dir = BASE_DIR / "findings"
    findings_dir.mkdir(exist_ok=True)

    model_safe = classifier.model.replace("/", "_").replace(":", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    findings_file = findings_dir / f"results_openrouter_{model_safe}_{timestamp}.json"

    with open(findings_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Also saved to: {findings_file}")

    return results


def list_models():
    """List available models."""
    print("Registered model shortcuts:")
    print("-" * 60)

    for short, full in sorted(OpenRouterClassifier.MODEL_REGISTRY.items()):
        print(f"  {short:25} -> {full}")

    print("\nYou can also use full OpenRouter model IDs directly.")
    print("Browse all models: https://openrouter.ai/models")


def main():
    parser = argparse.ArgumentParser(description="Classify medical cases using OpenRouter")
    parser.add_argument("--model", type=str, default="gemma3:27b",
                        help="Model to use (shortcut or full OpenRouter ID)")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="Sampling temperature (default: 0.1)")
    parser.add_argument("--list-models", action="store_true",
                        help="List available model shortcuts")

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    run_classification(args.model, args.temperature)


if __name__ == "__main__":
    main()
